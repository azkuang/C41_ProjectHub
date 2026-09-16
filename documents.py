import os
import secrets
from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from auth import login_required
from db import get_db

bp = Blueprint("documents", __name__)

PDF_MAGIC = b"%PDF-"


@bp.route("/")
@login_required
def index():
    db = get_db()
    docs = db.execute(
        "SELECT * FROM documents ORDER BY upload_date DESC, id DESC"
    ).fetchall()
    return render_template("index.html", documents=docs)


@bp.route("/upload", methods=["POST"])
@login_required
def upload():
    title = request.form.get("title", "").strip()
    uploader_name = request.form.get("uploader_name", "").strip()
    file = request.files.get("file")

    if not title or not uploader_name:
        flash("Title and your name are required.")
        return redirect(url_for("documents.index"))

    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("documents.index"))

    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files are allowed.")
        return redirect(url_for("documents.index"))

    header = file.stream.read(len(PDF_MAGIC))
    file.stream.seek(0)
    if header != PDF_MAGIC:
        flash("That file doesn't look like a valid PDF.")
        return redirect(url_for("documents.index"))

    original_name = secure_filename(file.filename)
    stored_name = (
        f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-"
        f"{secrets.token_hex(4)}-{original_name}"
    )
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, stored_name))

    db = get_db()
    db.execute(
        "INSERT INTO documents (title, source_type, filename, uploader_name) "
        "VALUES (?, 'upload', ?, ?)",
        (title, stored_name, uploader_name),
    )
    db.commit()
    flash("PDF uploaded.")
    return redirect(url_for("documents.index"))


@bp.route("/add-link", methods=["POST"])
@login_required
def add_link():
    title = request.form.get("title", "").strip()
    uploader_name = request.form.get("uploader_name", "").strip()
    drive_url = request.form.get("drive_url", "").strip()

    if not title or not uploader_name or not drive_url:
        flash("Title, your name, and a Drive link are required.")
        return redirect(url_for("documents.index"))

    if not drive_url.lower().startswith(("http://", "https://")):
        flash("That doesn't look like a valid URL.")
        return redirect(url_for("documents.index"))

    db = get_db()
    db.execute(
        "INSERT INTO documents (title, source_type, drive_url, uploader_name) "
        "VALUES (?, 'drive', ?, ?)",
        (title, drive_url, uploader_name),
    )
    db.commit()
    flash("Drive link added.")
    return redirect(url_for("documents.index"))


@bp.route("/documents/<int:doc_id>/open")
@login_required
def open_document(doc_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is None:
        flash("Document not found.")
        return redirect(url_for("documents.index"))

    if doc["source_type"] == "drive":
        return redirect(doc["drive_url"])

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        doc["filename"],
        mimetype="application/pdf",
        as_attachment=False,
    )


@bp.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete_document(doc_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is not None:
        if doc["source_type"] == "upload" and doc["filename"]:
            file_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], doc["filename"]
            )
            try:
                os.remove(file_path)
            except OSError:
                pass
        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        db.commit()
        flash("Document deleted.")
    return redirect(url_for("documents.index"))
