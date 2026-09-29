import os
import ast
from typing import List, Union, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Optional: Qdrant + FastEmbed for KB awareness
try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None  # type: ignore[assignment]

try:
    from fastembed import TextEmbedding as FastTextEmbedding
except ImportError:
    FastTextEmbedding = None  # type: ignore[assignment]


class QueryBuilder:
    """
    Builds high-quality semantic search queries for a vector database (Qdrant)
    using Gemini via LangChain.

    Public methods:
    - convert_query(text: str) -> Union[list, str]
    - get_and_process_query(topic: str, number_of_queries: int = 10) -> List[str]

    Extra behavior:
    - If QDRANT_URL + QDRANT_COLLECTION and fastembed are available, the class:
        * Probes Qdrant once per topic to see a few relevant snippets.
        * Feeds those snippets into the LLM as 'kb_context' to align queries
          with actual KB content (coverage + vocabulary).
    """

    def __init__(self):
        """
        Initializes:
        - LangChain Gemini client (GEMINI_API_KEY_QUERY).
        - Optional Qdrant + FastEmbed for KB probing (QDRANT_URL/KEY/COLLECTION).
        """
        api_key = os.environ.get("GEMINI_API_KEY_QUERY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY_QUERY not set in environment variables.")

        # LangChain LLM (Gemini) configuration
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.65,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
        )

        # --- Optional KB awareness setup (Qdrant + FastEmbed) ---
        self._kb_client: Optional[QdrantClient] = None  # type: ignore[assignment]
        self._kb_collection: Optional[str] = None
        self._kb_embedder = None  # FastTextEmbedding instance
        self._kb_probe_enabled: bool = False

        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_collection = os.getenv("QDRANT_COLLECTION", "kb_documents")

        if qdrant_url and QdrantClient is not None and FastTextEmbedding is not None:
            try:
                # Light-weight client: no connection test yet, handled lazily on search.
                self._kb_client = QdrantClient(url=qdrant_url)
                # Use the same embedding family as your main vector store.
                self._kb_embedder = FastTextEmbedding(
                    model_name="BAAI/bge-small-en-v1.5"
                )
                self._kb_collection = qdrant_collection
                self._kb_probe_enabled = True
            except Exception as e:
                print("DEBUG: KB probe disabled due to init error:", e)
                self._kb_client = None
                self._kb_embedder = None
                self._kb_collection = None
                self._kb_probe_enabled = False
        else:
            # No Qdrant or no fastembed – fall back to pure prompt-based queries.
            self._kb_probe_enabled = False

        # ------------------------------------------------------------------
        # Prompt: LLM is a query-expansion engine, optionally seeing kb_context
        # ------------------------------------------------------------------
        system_prompt = """
You are an expert research assistant helping to build high-quality notes from a
vector database (Qdrant) of documents.

Your job is:
- To take a study topic (or list of topics) and generate a small set of *search queries* that will retrieve the most useful passages from the vector database.
- The queries will be used to fetch context for an LLM that generates exam-ready notes.

You may also receive a small sample of text from the existing knowledge base (called "KB context"). This KB context:
- Is only a tiny slice of the actual database.
- Helps you align terminology and subtopics with what actually exists.
- Should guide the distribution and wording of your queries, but you must
  still cover the full topic as much as possible.

Guidelines for the queries:
- Each query must be **short but precise** (1–2 sentences or phrases).
- Cover:
  - Definitions and core concepts
  - Subtopics, algorithms, steps, and workflows
  - Examples, use-cases, and typical exam questions
  - Comparisons or edge cases when relevant
- Avoid duplicating queries; each query should add a new “angle” on the topic.
- Do **not** mention “vector database”, “Qdrant”, or “embedding” in the queries.
  They are just normal human-readable search queries.

**Output format (very strict):**
- Return **only** a Python-style list of strings inside a Markdown code block.
- Example of a **valid** response:

    ```
    ["Query 1", "Query 2", "Query 3"]
    ```

- Do **NOT**:
  - Add any text before or after the code block.
  - Add language tags like ```python or ```json.
  - Return anything that is not a valid Python list literal.
"""

        human_prompt = """
Topic(s):
{topic}

Number of queries to generate: {number_of_queries}

Small sample of existing KB content (may be empty if unavailable):

{kb_context}

Instructions:
- Never exceed the requested number_of_queries.
- Make queries diverse but tightly relevant to the given topic(s).
- Use the KB sample to align terminology and subtopics with what is already
  present, but do NOT restrict yourself only to those snippets.
- Return only the code block containing a Python list of queries as specified.
"""

        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )
        self._output_parser = StrOutputParser()
        self._chain = self._prompt | self.llm | self._output_parser

    # ----------------------------------------------------------------------
    # KB awareness helpers
    # ----------------------------------------------------------------------
    def _embed_for_kb(self, text: str):
        """
        Embed a single text using FastEmbed in BGE style.

        Returns:
        - list[float] on success
        - None on failure / if embedder is not available
        """
        if not (self._kb_probe_enabled and self._kb_embedder and text):
            return None

        try:
            vectors = list(self._kb_embedder.embed([text]))
            if not vectors:
                return None
            vec0 = vectors[0]
            if hasattr(vec0, "tolist"):
                return vec0.tolist()
            # Fallback if it's already a list-like
            return list(vec0)
        except Exception as e:
            print("DEBUG: KB embedding failed:", e)
            return None

    def _probe_kb(self, topic: str, max_hits: int = 6, max_chars_per_hit: int = 220) -> str:
        """
        Probe Qdrant with the raw topic to get a small, cheap glimpse of the KB.

        Returns a compact text block (kb_context) with:
        - filename/page (if present)
        - truncated snippet of text or doc_text

        If anything fails, returns an empty string.
        """
        if not self._kb_probe_enabled or not self._kb_client or not self._kb_collection:
            return ""

        topic = (topic or "").strip()
        if not topic:
            return ""

        # Embed topic in BGE query style
        vec = self._embed_for_kb(f"query: {topic}")
        if vec is None:
            return ""

        try:
            # FIX: Use query_points instead of search for modern QdrantClient (v1.10+)
            search_result = self._kb_client.query_points(
                collection_name=self._kb_collection,
                query=vec,
                limit=max_hits,
                with_payload=True,
            )
            # query_points returns a generic response object; we must access .points
            hits = search_result.points
        except Exception as e:
            print("DEBUG: KB probe search failed:", e)
            return ""

        if not hits:
            return ""

        snippets: List[str] = []
        for hit in hits:
            payload = hit.payload or {}
            filename = payload.get("filename") or payload.get("file_name") or payload.get("source") or "Unknown"
            page = payload.get("page") or payload.get("page_num") or payload.get("chunk_id") or "N/A"

            raw_text = payload.get("doc_text") or payload.get("text") or ""
            if isinstance(raw_text, str):
                text_snip = raw_text.replace("\n", " ").strip()
                if len(text_snip) > max_chars_per_hit:
                    # truncate at word boundary if possible
                    truncated = text_snip[:max_chars_per_hit]
                    last_space = truncated.rfind(" ")
                    if last_space > 40:  # avoid cutting after just a word or two
                        truncated = truncated[:last_space]
                    text_snip = truncated + " ..."
            else:
                text_snip = ""

            entry_lines = [
                f"- File: {filename}, Page: {page}",
            ]
            if text_snip:
                entry_lines.append(f"  Snippet: {text_snip}")
            snippets.append("\n".join(entry_lines))

        if not snippets:
            return ""

        kb_context = "Sample of existing KB content related to this topic:\n" + "\n".join(
            snippets
        )
        return kb_context

    # ----------------------------------------------------------------------
    # Parsing helpers
    # ----------------------------------------------------------------------
    def convert_query(self, text: str):
        """
        Convert the raw model text response into a Python list using ast.literal_eval.

        This is kept for backward compatibility:
        - On success: returns `list` (list of queries).
        - On failure: returns the string "Invalid".

        NOTE:
        - `get_and_process_query()` wraps this and guarantees a List[str] to callers.
        """
        text = (text or "").strip()

        # Case 1: whole response is directly a list literal
        if text.startswith("[") and text.endswith("]"):
            try:
                return ast.literal_eval(text)
            except Exception as ex:
                print("Exception in query.py (convert_query, direct list):", ex)

        # Case 2: look inside code blocks separated by ```
        parts = text.split("```")
        for raw in parts:
            candidate = raw.strip()
            if not candidate:
                continue

            # Strip common language tags like "python" or "json"
            lowered = candidate.lower()
            if lowered.startswith("python"):
                candidate = candidate[len("python"):].lstrip()
            elif lowered.startswith("json"):
                candidate = candidate[len("json"):].lstrip()
            candidate = candidate.strip()

            if candidate.startswith("[") and candidate.endswith("]"):
                try:
                    return ast.literal_eval(candidate)
                except Exception as ex:
                    print("Exception in query.py (convert_query, code block):", ex)
                    continue

        print("DEBUG : Invalid query format from model in convert_query()")
        return "Invalid"

    @staticmethod
    def _normalize_result_list(
        result: Union[str, List[object]], number_of_queries: int
    ) -> List[str]:
        """
        Normalize the parsed result into a clean List[str] with:
        - no empty strings
        - no duplicates
        - length <= number_of_queries
        """
        number_of_queries = max(1, int(number_of_queries))

        # If result is a bare string, treat as single query
        if isinstance(result, str):
            q = result.strip()
            return [q] if q else []

        if not isinstance(result, list):
            return []

        normalized: List[str] = []
        seen = set()

        for item in result:
            q = item if isinstance(item, str) else str(item)
            q = q.strip()
            if not q:
                continue
            if q in seen:
                continue
            seen.add(q)
            normalized.append(q)
            if len(normalized) >= number_of_queries:
                break

        return normalized

    @staticmethod
    def _fallback_queries(topic: str, number_of_queries: int) -> List[str]:
        """
        Fallback if the model output cannot be parsed:
        - Split the topic string into smaller parts (by newlines, ';', '-').
        - Use unique non-empty segments as queries.
        """
        number_of_queries = max(1, int(number_of_queries))
        base = (topic or "").strip()
        if not base:
            return []

        # Break topic into candidate pieces
        raw_segments = []
        for sep in ["\n", ";"]:
            if sep in base:
                raw_segments.extend(base.split(sep))
            else:
                raw_segments.append(base)

        # Also split bullet-style "- topic" lines
        segments: List[str] = []
        for seg in raw_segments:
            seg = seg.strip()
            if not seg:
                continue
            if seg.startswith("-"):
                seg = seg.lstrip("-").strip()
            if seg:
                segments.append(seg)

        # Deduplicate while preserving order
        unique: List[str] = []
        seen = set()
        for seg in segments:
            if seg not in seen:
                seen.add(seg)
                unique.append(seg)
            if len(unique) >= number_of_queries:
                break

        if not unique:
            unique = [base]

        return unique[:number_of_queries]

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def get_and_process_query(
        self, topic: str, number_of_queries: int = 10
    ) -> List[str]:
        """
        Sends the topic to the Gemini model via LangChain and returns a robust
        list of queries.

        Pipeline:
        1. Optionally probe Qdrant with the raw topic to build a small kb_context.
        2. Ask Gemini (via LangChain) to generate query list using topic + kb_context.
        3. Parse the result into a Python list and normalize it.
        4. If everything fails, fall back to heuristic queries derived from the topic.

        Guarantees:
        - Returns List[str] (never a raw "Invalid" string).
        - len(result) <= number_of_queries.
        """
        number_of_queries = max(1, int(number_of_queries))

        # 1) Tiny KB probe (cheap, bounded)
        kb_context = ""
        if self._kb_probe_enabled:
            kb_context = self._probe_kb(topic)

        # 2) Run LangChain chain: prompt -> LLM -> StrOutputParser -> raw string
        raw_response = self._chain.invoke(
            {
                "topic": topic,
                "number_of_queries": number_of_queries,
                "kb_context": kb_context,
            }
        )

        print("\nDEBUG : (Returned response)", raw_response)

        # 3) Parse model output
        parsed = self.convert_query(raw_response)
        queries = self._normalize_result_list(parsed, number_of_queries)

        # 4) Fallback if parsing produced nothing
        if not queries:
            print("DEBUG : Falling back to heuristic queries from topic.")
            queries = self._fallback_queries(topic, number_of_queries)

        return queries


if __name__ == "__main__":
    # Simple manual test harness
    client = QueryBuilder()
    test_queries = [
        "Explain register allocation strategies.",
        "What is peephole optimization?",
    ]

    for query in test_queries:
        print("\n==============================")
        print("Topic :", query)
        result = client.get_and_process_query(query, number_of_queries=6)
        for i, text in enumerate(result):
            print(f"{i} : {text}")