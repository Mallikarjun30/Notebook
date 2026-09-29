import os
import hashlib
import tempfile
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from processing import PDFProcessor, VectorStore, NotesGenerator
from document_cache import DocumentCache

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = "./uploads"
app.config["MAX_CONTENT_LENGTH"] = 2000 * 1024 * 1024  # 2GB
load_dotenv()

# ----------------------------------------------------------------------
# Global state
# ----------------------------------------------------------------------
vector_store = VectorStore()
processed_hashes: set[str] = set()
pdf_processor = PDFProcessor()
# NOTE: here we use file_hash as the "document id" key, not an actual path.
# This is fine with the current DocumentCache implementation: TTL works and
# mtime-based invalidation is simply bypassed (file_mtime=None).
document_cache = DocumentCache(ttl=3600)


@app.route("/upload", methods=["POST"])
def handle_upload():
    global vector_store, processed_hashes

    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded_files = request.files.getlist("files")
    new_uploads: list[str] = []

    for file in uploaded_files:
        if file.filename == "" or not file.filename.lower().endswith(".pdf"):
            continue

        try:
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            orig_filename = secure_filename(file.filename)

            # Skip if exact file (by hash) already processed in this session
            if file_hash in processed_hashes:
                continue

            # Try to get cached parsed pages using file_hash as logical key
            cached_data = document_cache.get_document(file_hash)
            if not cached_data:
                # Save to a temporary file for PDFProcessor
                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                temp_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], f"{file_hash}.pdf"
                )
                with open(temp_path, "wb") as f:
                    f.write(file_content)

                pages = pdf_processor.process_pdf(temp_path)

                # Remove temp file once processed
                try:
                    os.remove(temp_path)
                except OSError:
                    app.logger.warning(
                        "Temp file '%s' could not be removed.", temp_path
                    )

                # Cache parsed pages keyed by file_hash
                document_cache.add_document(file_hash, pages)
                cached_data = pages

            # Index each page into the vector store (Qdrant under the hood)
            for page in cached_data:
                metadata = {
                    "doc_id": file_hash,
                    "filename": orig_filename,
                    "page": page["metadata"]["page"],
                    "doc_text": page["text"],
                }
                vector_store.add_document(page["text"], metadata)

            processed_hashes.add(file_hash)
            new_uploads.append(orig_filename)

        except Exception as e:
            app.logger.error("Error processing %s: %s", file.filename, str(e))
            return (
                jsonify({"error": f"Failed to process {file.filename}"}),
                500,
            )

    return jsonify(
        {
            "message": f"Processed {len(new_uploads)} new files",
            "files": new_uploads,
        }
    )


@app.route("/generate", methods=["POST"])
def handle_generation():
    global vector_store

    if not processed_hashes:
        return jsonify({"error": "No documents processed"}), 400

    data = request.json or {}
    try:
        base_prompt = data.get("base_prompt", "Generate comprehensive notes about:")
        topics = data.get("topics", [])
        batch_size_raw = data.get("batch_size", 1)

        # Basic validation & normalization
        if not isinstance(topics, list) or not topics:
            return jsonify({"error": "No topics provided or invalid format"}), 400

        try:
            batch_size = max(1, int(batch_size_raw))
        except (TypeError, ValueError):
            batch_size = 1

        notes_generator = NotesGenerator(
            os.environ["GEMINI_API_KEY_GENERATE"], topics
        )
        results: list[str] = []

        # Batch topics so you don't overload a single request
        for i in range(0, len(topics), batch_size):
            batch = topics[i : i + batch_size]
            batch_results = notes_generator.generate_notes(
                vector_store,
                base_prompt=base_prompt,
                topics=batch,
            )
            results.extend(batch_results)

        # Combine all generated note pieces into one Markdown string
        full_md = "\n\n".join(results)

        return Response(
            full_md,
            mimetype="text/markdown",
            headers={
                "Content-Disposition": 'attachment; filename="generated_notes.md"'
            },
        )
    except Exception as e:
        app.logger.error("Gen error: %s", e)
        return jsonify({"error": "Generation failed"}), 500
    
    
@app.route('/chat', methods=['POST'])
def handle_chat():
    """
    Chat-style endpoint:
    - Expects JSON: { "prompt": "<user question or topic>", optional "base_prompt": "<instructions>" }
    - Uses the same NotesGenerator + vector_store pipeline as /generate
    - Returns a single Markdown answer (no attachment header, just plain text/markdown)
    """
    global vector_store

    if not processed_hashes:
        return jsonify({'error': 'No documents processed'}), 400

    data = request.json or {}
    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400

    # Optional custom instructions; falls back to a generic chat-style base prompt
    base_prompt = data.get(
        'base_prompt',
        'Answer the user query using the provided document context and your own knowledge. '
        'Be clear, structured, and concise in Markdown format.'
    )

    try:
        # We treat this as a single-topic batch
        topics = [prompt]

        notes_generator = NotesGenerator(
            os.environ["GEMINI_API_KEY_GENERATE"],
            topics
        )

        answers = notes_generator.generate_notes(
            vector_store,
            base_prompt=base_prompt,
            topics=topics
        )

        # Usually this will be a single answer string, but we join for safety
        full_md = "\n\n".join(answers)

        # For chat we just return markdown text, no download headers
        return Response(
            full_md,
            mimetype='text/markdown'
        )

    except Exception as e:
        app.logger.error(f"Chat gen error: {e}")
        return jsonify({'error': 'Chat generation failed'}), 500



@app.route("/reset", methods=["POST"])
def handle_reset():
    global vector_store, processed_hashes
    # Qdrant-backed VectorStore: re-instantiating will logically give you
    # a "fresh" in-memory handle. If you want a true wipe, you would also
    # drop/clear the Qdrant collection separately.
    vector_store = VectorStore()
    processed_hashes = set()
    return jsonify({"message": "System reset successfully"})


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
