"""Flask backend for EPUB Metadata Editor Web App."""
import json
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file, after_this_request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# Ensure src is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from epub_handler import EpubHandler
from metadata import EpubMetadata

# In-memory store for temp files (session_id -> epub_path)
_temp_store: dict[str, str] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "epub" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["epub"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save to temp file
    suffix = Path(file.filename).suffix or ".epub"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    # Parse metadata
    handler = EpubHandler()
    try:
        handler.open_epub(tmp_path)
        meta = handler.get_metadata()
    except Exception as e:
        os.unlink(tmp_path)
        return jsonify({"error": str(e)}), 400
    finally:
        handler.close()

    # Store temp path keyed by session token
    session_id = str(uuid.uuid4())
    _temp_store[session_id] = tmp_path

    # Cleanup old entries to prevent memory leak
    _cleanup_old_files()

    return jsonify({
        "session_id": session_id,
        "metadata": {
            "title": meta.title,
            "creators": meta.creators,
            "language": meta.language,
            "identifiers": meta.identifiers,
            "description": meta.description,
            "publisher": meta.publisher,
            "date": meta.date,
            "rights": meta.rights,
            "subjects": meta.subjects,
            "series": meta.series,
            "series_index": meta.series_index,
            "title_sort": meta.title_sort,
            "author_sort": meta.author_sort,
            "rating": meta.rating,
            "modification_date": meta.modification_date,
        },
        "filename": file.filename,
    })


@app.route("/save", methods=["POST"])
def save():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    session_id = data.get("session_id")
    if not session_id or session_id not in _temp_store:
        return jsonify({"error": "Invalid or expired session"}), 400

    tmp_path = _temp_store[session_id]
    if not os.path.exists(tmp_path):
        return jsonify({"error": "Original file no longer available"}), 400

    handler = EpubHandler()
    try:
        handler.open_epub(tmp_path)
        meta = handler.get_metadata()

        # Update fields
        meta.title = data.get("title", meta.title)
        meta.creators = data.get("creators", meta.creators)
        meta.language = data.get("language", meta.language)
        meta.identifiers = data.get("identifiers", meta.identifiers)
        meta.description = data.get("description", meta.description)
        meta.publisher = data.get("publisher", meta.publisher)
        meta.date = data.get("date", meta.date)
        meta.rights = data.get("rights", meta.rights)
        meta.subjects = data.get("subjects", meta.subjects)
        meta.series = data.get("series", meta.series)
        meta.series_index = data.get("series_index", meta.series_index)
        meta.title_sort = data.get("title_sort", meta.title_sort)
        meta.author_sort = data.get("author_sort", meta.author_sort)
        meta.rating = data.get("rating", meta.rating)
        meta.modification_date = data.get("modification_date", meta.modification_date)

        handler.set_metadata(meta)
        handler.save_metadata()
    except Exception as e:
        handler.close()
        return jsonify({"error": str(e)}), 400
    finally:
        handler.close()

    # Generate download filename
    original_name = Path(tmp_path).stem
    download_name = f"{original_name}_edited.epub"

    @after_this_request
    def cleanup(response):
        # Optional: delete temp file after download
        # os.unlink(tmp_path)
        # del _temp_store[session_id]
        return response

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/epub+zip",
    )


def _cleanup_old_files():
    """Remove orphaned temp files that no longer have a session entry."""
    # Simple cleanup: if file doesn't exist, remove key
    stale = [sid for sid, path in _temp_store.items() if not os.path.exists(path)]
    for sid in stale:
        del _temp_store[sid]


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
