import os
import time
import hashlib
import re
import numpy as np
import google.generativeai as genai
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from uuid import uuid4
from query import QueryBuilder

# --- FastEmbed (bge-small) ---
try:
    from fastembed import TextEmbedding
except ImportError as e:
    raise ImportError(
        "fastembed is required for VectorStore. Install it with: pip install fastembed"
    ) from e

# --- Qdrant (vector database) ---
try:
    from qdrant_client import QdrantClient, models
except ImportError as e:
    raise ImportError(
        "qdrant-client is required for VectorStore. Install it with: pip install qdrant-client"
    ) from e

# Optional PaddleOCR + PP-Structure (local, no cloud)
try:
    from paddleocr import PPStructure  # PP-Structure API from PaddleOCR whl
    _HAS_PADDLE_OCR = True
except ImportError:
    PPStructure = None  # type: ignore[assignment]
    _HAS_PADDLE_OCR = False


class VectorStore:
    """
    Handles document embeddings and semantic search using FastEmbed + bge-small,
    with Qdrant (running in Docker) as the vector database.

    - Embedding backend: FastEmbed(TextEmbedding) with model "BAAI/bge-small-en-v1.5"
    - Dimensionality: detected at runtime (expected 384 for this model)
    - Document texts are embedded with "passage: " prefix
    - Query texts are embedded with "query: " prefix
    - Qdrant connection is configured via environment variables:

        QDRANT_URL          (required)  e.g. 'http://qdrant:6333' or 'http://localhost:6333'
        QDRANT_API_KEY      (optional)  for secured/cloud instances
        QDRANT_COLLECTION   (optional)  defaults to 'kb_documents'
    """

    _embedding_model = None  # type: ignore[assignment]
    _dim = None

    def __init__(self, collection_name: str | None = None):
        # Lazily initialize the shared embedding model and dimension
        if VectorStore._embedding_model is None:
            VectorStore._embedding_model = TextEmbedding(
                model_name="BAAI/bge-small-en-v1.5"
            )
            # Probe the dimensionality once using a dummy embedding
            sample_vec = next(
                VectorStore._embedding_model.embed(["dimension probe"])
            )
            VectorStore._dim = int(len(sample_vec))

        if VectorStore._dim is None:
            raise RuntimeError("Failed to infer embedding dimension for VectorStore.")

        # Resolve collection name from argument or env, fallback to default
        self.collection_name = (
            collection_name
            or os.getenv("QDRANT_COLLECTION", "kb_documents")
        )

        # Qdrant connection via env vars (Docker / remote)
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_url:
            raise RuntimeError(
                "QDRANT_URL environment variable is not set. "
                "Set it to your Qdrant Docker URL, e.g. 'http://qdrant:6333'"
            )

        # Connect to Qdrant over HTTP
        client_kwargs: dict = {"url": qdrant_url}
        if qdrant_api_key:
            client_kwargs["api_key"] = qdrant_api_key

        self.client = QdrantClient(**client_kwargs)

        # Ensure collection exists with correct vector size & metric
        try:
            exists = self.client.collection_exists(
                collection_name=self.collection_name
            )
        except Exception:
            exists = False

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=VectorStore._dim,
                    distance=models.Distance.COSINE,
                ),
            )
        # If it already exists, we assume it has the correct size & metric.

    @property
    def _model(self) -> TextEmbedding:
        # Small helper for type clarity
        return VectorStore._embedding_model  # type: ignore[return-value]

    def _embed_texts(self, texts):
        """
        Internal helper to embed a batch of texts with FastEmbed.

        - Accepts either a single string or an iterable of strings.
        - Returns a 2D float32 NumPy array of shape (N, D).
        """
        if isinstance(texts, str):
            batch = [texts]
        else:
            batch = list(texts)

        if not batch:
            # No texts to embed; return an empty (0, dim) array
            return np.empty((0, VectorStore._dim), dtype="float32")

        # FastEmbed returns a generator of 1D NumPy arrays
        vectors = list(self._model.embed(batch))
        if not vectors:
            return np.empty((0, VectorStore._dim), dtype="float32")

        embeddings = np.asarray(vectors, dtype="float32")
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        # Final safety check on dimensionality
        if embeddings.shape[1] != VectorStore._dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {VectorStore._dim}, "
                f"got {embeddings.shape[1]}"
            )
        return embeddings

    def add_document(self, text, metadata):
        """
        Add a document (or multiple chunks) to Qdrant.

        - `text` can be:
          - a single string, or
          - an iterable of strings (multiple chunks)
        - Every vector stored gets the same `metadata` dict (caller may include
          page, filename, doc_text, etc. inside this metadata).
        """
        if isinstance(text, str):
            passages = [f"passage: {text}"]
        else:
            passages = [f"passage: {t}" for t in text]

        embeddings = self._embed_texts(passages)
        if embeddings.shape[0] == 0:
            return  # Nothing to add

        # Ensure payload is always a dict (Qdrant requirement)
        if isinstance(metadata, dict):
            base_payload = metadata
        else:
            base_payload = {"metadata": metadata}

        points = []
        for vec in embeddings:
            points.append(
                models.PointStruct(
                    id=uuid4().hex,  # collision-free ID per point
                    vector=vec.tolist(),
                    payload=base_payload,
                )
            )

        # Upsert into Qdrant; wait=True to ensure write is complete
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

    def search(self, query, k=5):
        """
        Semantic search for the top-k most similar documents.

        - `query` is a string.
        - Uses BGE-style "query: " prefix for the query embedding.
        - Returns a list of (metadata, score) pairs, where:
          - metadata is the Qdrant payload (dict),
          - score is the similarity score (higher is better with COSINE).
        """
        if k <= 0:
            return []

        # Build query embedding
        prefixed_query = f"query: {query}"
        query_embedding = self._embed_texts(prefixed_query)
        if query_embedding.shape[0] == 0:
            return []

        query_vector = query_embedding[0].tolist()

        try:
            # Preferred: new Query API
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=k,
                    with_payload=True,
                )
                hits = getattr(response, "points", response)
            # Fallback: older client API
            elif hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=k,
                    with_payload=True,
                )
            else:
                raise RuntimeError(
                    "QdrantClient has neither 'query_points' nor 'search' method."
                )
        except Exception as e:
            # Fail soft: log + return empty
            print(f"Qdrant search failed: {e}")
            return []

        results = []
        for hit in hits:
            payload = getattr(hit, "payload", None)
            score = getattr(hit, "score", None)

            if payload is None:
                continue

            meta = payload or {}
            results.append((meta, float(score) if score is not None else 0.0))

        return results


class PDFProcessor:
    """Handles PDF text extraction with PaddleOCR + PP-Structure OCR for image pages"""

    def __init__(self, tesseract_cmd: str = r'/usr/bin/tesseract'):
        """
        tesseract_cmd is kept only for backward compatibility.
        It is not used anymore (no Tesseract in this pipeline).
        """
        # PP-Structure engine (PaddleOCR) – primary OCR path
        self._use_paddle = False
        self._paddle_engine = None
        self._paddle_cache = {}  # {pdf_path: {"mtime": float, "pages": List[str]}}

        if _HAS_PADDLE_OCR and PPStructure is not None:
            try:
                # Layout analysis + OCR; no tables->Excel etc., just text
                self._paddle_engine = PPStructure(
                    show_log=False,
                    # you can add lang='en' or others if needed:
                    # lang='en'
                )
                self._use_paddle = True
            except Exception as e:
                print(f"PP-Structure initialization failed; OCR for image pages disabled: {e}")
                self._paddle_engine = None
                self._use_paddle = False

    @staticmethod
    def _strip_html(html: str) -> str:
        """Minimal HTML-to-text cleanup for table/structured regions."""
        if not html:
            return ""
        text = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(text.split())

    def _extract_text_from_block(self, block: dict) -> str:
        """
        Extract readable text from a single PP-Structure layout block.

        Handles several possible shapes of `block['res']` that appear
        in different PaddleOCR versions:
        - list of dicts: [{'text': ..., 'confidence': ..., 'text_region': ...}, ...]
        - list/tuple of (text, score)
        - dict with 'html' (tables) or 'text'
        - tuple like (boxes, rec_res)
        """
        texts: list[str] = []
        res = block.get("res")

        # Case 1: list of dicts or (text, score) pairs
        if isinstance(res, list):
            for item in res:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
                elif isinstance(item, (list, tuple)) and item:
                    text = item[0]
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())

        # Case 2: tuple (boxes, rec_res)
        elif isinstance(res, tuple) and len(res) >= 2:
            rec_res = res[1]
            if isinstance(rec_res, list):
                for item in rec_res:
                    if isinstance(item, (list, tuple)) and item:
                        text = item[0]
                        if isinstance(text, str) and text.strip():
                            texts.append(text.strip())

        # Case 3: dict with 'html' or 'text'
        elif isinstance(res, dict):
            html = res.get("html")
            if isinstance(html, str) and html.strip():
                texts.append(self._strip_html(html))
            else:
                text = res.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

        return "\n".join(texts).strip()

    def _run_paddle_on_pdf(self, pdf_path: str):
        """
        Run PP-Structure on all pages of a PDF and return a list of
        per-page plain-text strings.

        - Uses `pdf2image.convert_from_path` to render pages as images.
        - Feeds each page image (as numpy array) to `PPStructure`.
        - Aggregates all text-like blocks into a single page string.
        - If PP-Structure is not available or fails, returns [].
        """
        if not (self._use_paddle and self._paddle_engine is not None):
            return []

        try:
            mtime = os.path.getmtime(pdf_path)
        except OSError:
            mtime = None

        if mtime is not None:
            cached = self._paddle_cache.get(pdf_path)
            if cached and cached.get("mtime") == mtime:
                return cached["pages"]

        pages: list[str] = []
        try:
            images = convert_from_path(pdf_path)
        except Exception as e:
            print(f"PP-Structure: failed to render PDF '{pdf_path}' to images: {e}")
            images = []

        for img in images:
            page_text = ""
            try:
                img_np = np.array(img)  # H x W x 3, RGB
                result = self._paddle_engine(img_np)
                page_lines: list[str] = []
                for block in result:
                    block_text = self._extract_text_from_block(block)
                    if block_text:
                        page_lines.append(block_text)
                page_text = "\n".join(page_lines).strip()
            except Exception as e:
                print(f"PP-Structure OCR failed on a page of '{pdf_path}': {e}")
                page_text = ""
            pages.append(page_text)

        if mtime is not None:
            self._paddle_cache[pdf_path] = {"mtime": mtime, "pages": pages}
        return pages

    def _extract_with_ocr(self, pdf_path: str, page_num: int) -> str:
        """
        OCR path for image-based pages.

        - Only uses PaddleOCR + PP-Structure.
        - If it fails or returns nothing, returns "" (no Tesseract, no backup).
        """
        pages_from_paddle = self._run_paddle_on_pdf(pdf_path)
        if 0 <= page_num < len(pages_from_paddle):
            text = pages_from_paddle[page_num]
            if isinstance(text, str) and text.strip():
                return text.strip()
        return ""

    def process_page(self, page, pdf_path: str, page_num: int) -> str:
        """
        Process a single page:

        1. Try native text layer via PyPDF2.
        2. If text is missing or too short (likely scanned/image PDF),
           use PP-Structure OCR.
        """
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        # If there's a decent amount of real text, use it directly.
        if text and len(text) >= 200:
            return text

        # Otherwise, rely on PP-Structure OCR. If it fails, this will be "".
        return self._extract_with_ocr(pdf_path, page_num)

    def process_pdf(self, file_path: str):
        """Process a single PDF file into a list of per-page {text, metadata}."""
        doc_id = hashlib.md5(os.path.basename(file_path).encode()).hexdigest()[:8]
        contents = []

        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = self.process_page(page, file_path, page_num)
                contents.append({
                    "text": text,
                    "metadata": {
                        "doc_id": doc_id,
                        "filename": os.path.basename(file_path),
                        "page": page_num + 1,
                    },
                })
        return contents


class NotesGenerator:
    """Handles note generation using Gemini API"""

    def __init__(self, api_key, all_topics):
        self.all_topics = all_topics
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.75,
                "top_p": 0.85,
                "top_k": 30,
                "max_output_tokens": 8192,
            },
        )

        self.SYSTEM_PROMPT = """
You are an **Expert Academic Tutor and Note-Taker**.

Your job is to turn the given **Context** (class notes, slides, book extracts, or any material) plus your own knowledge into **exam-ready, easy-to-understand answers and study notes** for the user’s questions.

---

## 🎯 Core Objectives

1. **Clarity first**
   - Explain ideas in **simple, step-by-step language**.
   - Break big ideas into small, logical chunks.
   - Assume the reader is a **student preparing for exams**, not an expert.

2. **Exam focus**
   - Prioritize: **definitions, key steps, reasons, diagrams (described), pros/cons, formulas, and short summaries**.
   - Always make it clear **what to write in an exam** (points, structure, flow).

3. **Readable structure**
   - Use **clear headings, subheadings, bullet points, and short paragraphs**.
   - Make the answer **easy to scan quickly** before an exam.

4. **Use Context + your knowledge**
   - Treat the provided **Context as the primary source of truth**.
   - Use your own knowledge to:
     - Fill gaps
     - Explain jargon
     - Give simple examples
   - If the Context conflicts with your knowledge, **follow the Context**, but you may gently clarify in a short note.

---

## 📚 How to Use the Context

- **Do NOT copy the Context word-for-word.**
- **Extract only what is needed** for the given question(s).
- If the Context is noisy, incomplete, or unrelated:
  - Still give a **complete, high-quality answer** using your own understanding.
- If formulas, steps, or diagrams are unclear in the Context, you may **reconstruct or simplify them**.

---

## 🧱 Output Structure (Global Rules)

For every answer you generate:

1. **No preamble.**  
   - Do NOT write things like “Here is your answer” or “Sure, I can explain”.
   - Start **directly with the heading that contains the question** (as instructed in the user prompt).

2. **Headings & flow**
   - Use **Markdown headings**: `#`, `##`, `###` as needed.
   - Maintain a **logical flow**:
     - Definition / statement
     - Explanation
     - Steps / working / structure
     - Examples or comparisons
     - Short final summary (exam-focused)

3. **Highlighting**
   - Use **bold** for key terms, formulas, and important phrases.
   - Use *italics* for extra notes, side comments, or subtle distinctions.
   - Use `code blocks` **only** for:
     - Code
     - Pseudo-code
     - Exact syntax
     - ASCII-style diagrams or graph descriptions (NOT Mermaid).

4. **Tables (very important)**
   - You are **encouraged to create tables** to compare concepts, list differences, summarize pros/cons, etc.
   - You **do NOT need to copy tables from the Context exactly**.
     - You may **design your own clean tables** using your own understanding.
     - If the Context has messy or partial data, you may **reorganize or recompute** it into a clearer table.
   - Do **not** skip tables just because the Context does not already contain them.
   - Only avoid tables if they genuinely don’t help for that specific question.

5. **Multiple questions in one prompt**
   - If there are many questions (Q1, Q2, Q3, …):
     - Answer them **one after another**, **not mixed together**.
     - Use the **same question numbers** as given by the user.
   - Do **not** merge answers for different questions.

6. **Headings from the Context**
   - If the Context or topics use Markdown-style headings for sections (e.g., `# Trapezoidal Rule`, `## CUDA threads`):
     - Treat those as **main or sub-headings** inside the answer **when relevant to the question**.
   - This helps keep **terminology and structure consistent** with the course material.

7. **Graphs and diagrams**
   - Do **NOT** use Mermaid or any graph-drawing language.
   - If you need to show a graph / flowchart / block diagram:
     - Use a **code block** with a simple **text or ASCII description** of the figure.
     - Example (pattern only, do not copy literally):
       ```text
       [Graph of y = f(x):
        - x-axis: ...
        - y-axis: ...
        - Curve starts at ...
       ]
       ```

8. **Follow the user’s Answer Format Rules**
   - The user prompt will include **“Answer Format Rules”** or similar instructions.
   - You **MUST strictly follow** those format rules on top of these system-level rules.
   - If there is any conflict, **follow the user’s Answer Format Rules first**, then adapt the rest as closely as possible.

---

## ✅ Quality & Style Checks Before Finishing

Before finalizing your answer, quickly self-check:

- Are **important terms** clearly defined **before** being used?
- Is the **flow** from one section to the next smooth and logical?
- Are there **unnecessary digressions**? (Remove them.)
- Is there at least:
  - One **short example** OR
  - One **table** OR
  - One **comparison / contrast section**
  if they naturally help understanding?
- Does the answer feel like **something a student can directly write in an exam** (maybe with minor trimming)?

Do **not** mention these checks explicitly; just use them internally.

"""
    def _build_context(self, relevant_passages):
        context = "RELEVANT PASSAGES:\n"
        for (meta, score) in relevant_passages:
            context += f"\nDocument: {meta['filename']} (Page {meta['page']})\n"
            context += f"Content: {meta['doc_text']}\n"
            context += f"Relevance Score: {score:.2f}\n{'-' * 40}"
        return context

    def generate_notes(self, vector_store, base_prompt, topics, max_retries: int = 3):
        """
        Generate notes for multiple topics, retrying if the LLM returns an empty response.
        """
        self.max_queries = 10
        queryBuilder = QueryBuilder()
        queries = queryBuilder.get_and_process_query(
            "- " + "- ".join(topics), self.max_queries
        )

        # Build the overall context
        context = ""
        for query in queries[: self.max_queries]:
            k_per_query = max(1, self.max_queries // max(len(queries), 1))
            relevant_passages = vector_store.search(query, k=k_per_query)
            context += self._build_context(relevant_passages)

        # Prepare the chat
        chat = self.model.start_chat(history=[])
        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Topics:\n" + "\n".join(f"- {t}" for t in topics) + "\n\n"
            f"Context:\n{context}\n\n"
            f"Notes structure instructions:\n{base_prompt}"
        )

        # Retry loop
        for attempt in range(1, max_retries + 1):
            response = chat.send_message(prompt)
            try:
                return [response.text]
            except Exception as e:
                print("Error : (Processing.py[157])", e, sep="\n")

        # All retries exhausted
        raise RuntimeError(
            f"LLM failed to return any content after {max_retries} attempts."
        )
