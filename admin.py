import os
import re
import secrets
import shutil
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from auth import login_required
from db import get_db

bp = Blueprint("admin", __name__)

PDF_MAGIC = b"%PDF-"
SECTIONS = ("document", "callsheet", "menu")
LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".webp")


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "project"


def unique_slug(db, base_slug, exclude_id=None):
    slug = base_slug
    n = 2
    while True:
        row = db.execute(
            "SELECT id FROM projects WHERE slug = ? AND id != ?",
            (slug, exclude_id or 0),
        ).fetchone()
        if row is None:
            return slug
        slug = f"{base_slug}-{n}"
        n += 1


def _get_project(project_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        abort(404)
    return project


def _project_form_fields():
    return {
        "title": request.form.get("title", "").strip(),
        "eyebrow": request.form.get("eyebrow", "").strip(),
        "production_label": request.form.get("production_label", "").strip(),
        "date_range_text": request.form.get("date_range_text", "").strip(),
        "date_year": request.form.get("date_year", "").strip(),
        "coordinator_name": request.form.get("coordinator_name", "").strip(),
        "coordinator_phone": request.form.get("coordinator_phone", "").strip(),
        "emergency_phone": request.form.get("emergency_phone", "").strip() or "112",
    }


def _save_logo(file):
    if not file or file.filename == "":
        return None
    if not file.filename.lower().endswith(LOGO_EXTENSIONS):
        flash("Logo must be an image file (png, jpg, svg, webp).")
        return None
    logos_dir = os.path.join(current_app.static_folder, "logos")
    os.makedirs(logos_dir, exist_ok=True)
    original_name = secure_filename(file.filename)
    stored_name = f"{secrets.token_hex(8)}-{original_name}"
    file.save(os.path.join(logos_dir, stored_name))
    return stored_name


def _remove_logo(filename):
    path = os.path.join(current_app.static_folder, "logos", filename)
    try:
        os.remove(path)
    except OSError:
        pass


@bp.route("/")
@login_required
def dashboard():
    db = get_db()
    projects = db.execute(
        "SELECT * FROM projects ORDER BY created_at DESC, id DESC"
    ).fetchall()
    return render_template("admin_dashboard.html", projects=projects)


@bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def new_project():
    if request.method == "POST":
        fields = _project_form_fields()
        if not fields["title"] or not fields["eyebrow"]:
            flash("Title and eyebrow are required.")
            return render_template("admin_project_form.html", project=fields)

        db = get_db()
        slug = unique_slug(db, slugify(fields["title"]))
        logo_filename = _save_logo(request.files.get("client_logo"))

        cursor = db.execute(
            "INSERT INTO projects "
            "(slug, title, eyebrow, production_label, date_range_text, date_year, "
            " client_logo_filename, coordinator_name, coordinator_phone, emergency_phone) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                slug,
                fields["title"],
                fields["eyebrow"],
                fields["production_label"],
                fields["date_range_text"],
                fields["date_year"],
                logo_filename,
                fields["coordinator_name"],
                fields["coordinator_phone"],
                fields["emergency_phone"],
            ),
        )
        db.commit()
        flash("Project created.")
        return redirect(url_for("admin.project_detail", project_id=cursor.lastrowid))

    return render_template("admin_project_form.html", project=None)


@bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    db = get_db()
    project = _get_project(project_id)

    if request.method == "GET":
        return redirect(url_for("admin.project_detail", project_id=project_id))

    fields = _project_form_fields()
    if not fields["title"] or not fields["eyebrow"]:
        flash("Title and eyebrow are required.")
        return redirect(url_for("admin.project_detail", project_id=project_id))

    requested_slug = request.form.get("slug", "").strip()
    slug = unique_slug(
        db, slugify(requested_slug or fields["title"]), exclude_id=project_id
    )

    logo_file = request.files.get("client_logo")
    logo_filename = project["client_logo_filename"]
    if logo_file and logo_file.filename:
        new_logo = _save_logo(logo_file)
        if new_logo:
            if logo_filename:
                _remove_logo(logo_filename)
            logo_filename = new_logo

    db.execute(
        "UPDATE projects SET slug=?, title=?, eyebrow=?, production_label=?, "
        "date_range_text=?, date_year=?, client_logo_filename=?, coordinator_name=?, "
        "coordinator_phone=?, emergency_phone=?, updated_at=datetime('now') WHERE id=?",
        (
            slug,
            fields["title"],
            fields["eyebrow"],
            fields["production_label"],
            fields["date_range_text"],
            fields["date_year"],
            logo_filename,
            fields["coordinator_name"],
            fields["coordinator_phone"],
            fields["emergency_phone"],
            project_id,
        ),
    )
    db.commit()
    flash("Project updated.")
    return redirect(url_for("admin.project_detail", project_id=project_id))

    return render_template(
        "admin_project_form.html", project=project, mode="edit", project_id=project_id
    )


@bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    db = get_db()
    project = _get_project(project_id)
    if project["client_logo_filename"]:
        _remove_logo(project["client_logo_filename"])
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(project_id))
    shutil.rmtree(upload_dir, ignore_errors=True)
    flash("Project deleted.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    db = get_db()
    project = _get_project(project_id)
    credits = db.execute(
        "SELECT * FROM credits WHERE project_id = ? ORDER BY sort_order, id", (project_id,)
    ).fetchall()
    documents_by_section = {
        section: db.execute(
            "SELECT * FROM documents WHERE project_id = ? AND section = ? "
            "ORDER BY sort_order, id",
            (project_id, section),
        ).fetchall()
        for section in SECTIONS
    }
    return render_template(
        "admin_project_detail.html",
        project=project,
        credits=credits,
        documents_by_section=documents_by_section,
    )


@bp.route("/projects/<int:project_id>/credits", methods=["POST"])
@login_required
def add_credit(project_id):
    _get_project(project_id)
    role = request.form.get("role", "").strip()
    name = request.form.get("name", "").strip()
    if not role or not name:
        flash("Role and name are required.")
        return redirect(url_for("admin.project_detail", project_id=project_id))

    db = get_db()
    next_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM credits WHERE project_id = ?",
        (project_id,),
    ).fetchone()["n"]
    cursor = db.execute(
        "INSERT INTO credits (project_id, role, name, sort_order) VALUES (?, ?, ?, ?)",
        (project_id, role, name, next_order),
    )
    db.commit()
    flash("Credit added.")
    return redirect(
        url_for(
            "admin.project_detail",
            project_id=project_id,
            _anchor=f"credit-{cursor.lastrowid}",
        )
    )


@bp.route("/projects/<int:project_id>/credits/reorder", methods=["POST"])
@login_required
def reorder_credits(project_id):
    _get_project(project_id)
    order = (request.get_json(silent=True) or {}).get("order", [])
    db = get_db()
    for index, credit_id in enumerate(order):
        db.execute(
            "UPDATE credits SET sort_order = ? WHERE id = ? AND project_id = ?",
            (index, credit_id, project_id),
        )
    db.commit()
    return {"status": "ok"}


@bp.route("/credits/<int:credit_id>/edit", methods=["POST"])
@login_required
def edit_credit(credit_id):
    db = get_db()
    credit = db.execute("SELECT * FROM credits WHERE id = ?", (credit_id,)).fetchone()
    if credit is None:
        return redirect(url_for("admin.dashboard"))

    role = request.form.get("role", "").strip()
    name = request.form.get("name", "").strip()
    if not role or not name:
        flash("Role and name are required.")
        return redirect(url_for("admin.project_detail", project_id=credit["project_id"]))

    db.execute(
        "UPDATE credits SET role = ?, name = ? WHERE id = ?",
        (role, name, credit_id),
    )
    db.commit()
    flash("Credit updated.")
    return redirect(url_for("admin.project_detail", project_id=credit["project_id"]))


@bp.route("/credits/<int:credit_id>/delete", methods=["POST"])
@login_required
def delete_credit(credit_id):
    db = get_db()
    credit = db.execute("SELECT * FROM credits WHERE id = ?", (credit_id,)).fetchone()
    if credit is not None:
        db.execute("DELETE FROM credits WHERE id = ?", (credit_id,))
        db.commit()
        flash("Credit removed.")
        return redirect(url_for("admin.project_detail", project_id=credit["project_id"]))
    return redirect(url_for("admin.dashboard"))


def _next_doc_sort_order(db, project_id, section):
    return db.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM documents "
        "WHERE project_id = ? AND section = ?",
        (project_id, section),
    ).fetchone()["n"]


def _section_extra_fields(section):
    entry_date = request.form.get("entry_date", "").strip()
    location = request.form.get("location", "").strip()
    subtitle = request.form.get("subtitle", "").strip()

    if section in ("callsheet", "menu") and not entry_date:
        return None, "A date is required."
    if section == "callsheet" and not location:
        return None, "A location is required for callsheets."

    return {
        "entry_date": entry_date or None,
        "location": location or None,
        "subtitle": subtitle or None,
    }, None


@bp.route(
    "/projects/<int:project_id>/documents/<any(document,callsheet,menu):section>/upload",
    methods=["POST"],
)
@login_required
def upload_document(project_id, section):
    _get_project(project_id)
    title = request.form.get("title", "").strip()
    uploader_name = request.form.get("uploader_name", "").strip()
    file = request.files.get("file")
    extra, error = _section_extra_fields(section)

    if not title or not uploader_name:
        flash("Title and your name are required.")
        return redirect(url_for("admin.project_detail", project_id=project_id))
    if error:
        flash(error)
        return redirect(url_for("admin.project_detail", project_id=project_id))
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("admin.project_detail", project_id=project_id))
    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files are allowed.")
        return redirect(url_for("admin.project_detail", project_id=project_id))

    header = file.stream.read(len(PDF_MAGIC))
    file.stream.seek(0)
    if header != PDF_MAGIC:
        flash("That file doesn't look like a valid PDF.")
        return redirect(url_for("admin.project_detail", project_id=project_id))

    original_name = secure_filename(file.filename)
    stored_name = (
        f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-"
        f"{secrets.token_hex(4)}-{original_name}"
    )
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(project_id))
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, stored_name))

    db = get_db()
    sort_order = _next_doc_sort_order(db, project_id, section)
    cursor = db.execute(
        "INSERT INTO documents "
        "(project_id, section, title, subtitle, source_type, filename, entry_date, "
        " location, uploader_name, sort_order) "
        "VALUES (?, ?, ?, ?, 'upload', ?, ?, ?, ?, ?)",
        (
            project_id,
            section,
            title,
            extra["subtitle"],
            stored_name,
            extra["entry_date"],
            extra["location"],
            uploader_name,
            sort_order,
        ),
    )
    db.commit()
    flash("PDF uploaded.")
    return redirect(
        url_for(
            "admin.project_detail",
            project_id=project_id,
            _anchor=f"document-{cursor.lastrowid}",
        )
    )


@bp.route(
    "/projects/<int:project_id>/documents/<any(document,callsheet,menu):section>/link",
    methods=["POST"],
)
@login_required
def add_document_link(project_id, section):
    _get_project(project_id)
    title = request.form.get("title", "").strip()
    uploader_name = request.form.get("uploader_name", "").strip()
    drive_url = request.form.get("drive_url", "").strip()
    extra, error = _section_extra_fields(section)

    if not title or not uploader_name or not drive_url:
        flash("Title, your name, and a link are required.")
        return redirect(url_for("admin.project_detail", project_id=project_id))
    if error:
        flash(error)
        return redirect(url_for("admin.project_detail", project_id=project_id))
    if not drive_url.lower().startswith(("http://", "https://")):
        flash("That doesn't look like a valid URL.")
        return redirect(url_for("admin.project_detail", project_id=project_id))

    db = get_db()
    sort_order = _next_doc_sort_order(db, project_id, section)
    cursor = db.execute(
        "INSERT INTO documents "
        "(project_id, section, title, subtitle, source_type, drive_url, entry_date, "
        " location, uploader_name, sort_order) "
        "VALUES (?, ?, ?, ?, 'drive', ?, ?, ?, ?, ?)",
        (
            project_id,
            section,
            title,
            extra["subtitle"],
            drive_url,
            extra["entry_date"],
            extra["location"],
            uploader_name,
            sort_order,
        ),
    )
    db.commit()
    flash("Link added.")
    return redirect(
        url_for(
            "admin.project_detail",
            project_id=project_id,
            _anchor=f"document-{cursor.lastrowid}",
        )
    )


@bp.route(
    "/projects/<int:project_id>/documents/<any(document,callsheet,menu):section>/reorder",
    methods=["POST"],
)
@login_required
def reorder_documents(project_id, section):
    _get_project(project_id)
    order = (request.get_json(silent=True) or {}).get("order", [])
    db = get_db()
    for index, doc_id in enumerate(order):
        db.execute(
            "UPDATE documents SET sort_order = ? WHERE id = ? AND project_id = ? AND section = ?",
            (index, doc_id, project_id, section),
        )
    db.commit()
    return {"status": "ok"}


@bp.route("/documents/<int:doc_id>/edit", methods=["POST"])
@login_required
def edit_document(doc_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is None:
        return redirect(url_for("admin.dashboard"))

    title = request.form.get("title", "").strip()
    uploader_name = request.form.get("uploader_name", "").strip()
    extra, error = _section_extra_fields(doc["section"])
    project_url = url_for("admin.project_detail", project_id=doc["project_id"])

    if not title or not uploader_name:
        flash("Title and your name are required.")
        return redirect(project_url)
    if error:
        flash(error)
        return redirect(project_url)

    drive_url = doc["drive_url"]
    if doc["source_type"] == "drive":
        drive_url = request.form.get("drive_url", "").strip()
        if not drive_url:
            flash("A link is required.")
            return redirect(project_url)
        if not drive_url.lower().startswith(("http://", "https://")):
            flash("That doesn't look like a valid URL.")
            return redirect(project_url)

    filename = doc["filename"]
    replacement = request.files.get("file")
    if replacement and replacement.filename:
        if doc["source_type"] != "upload":
            abort(400)
        if not replacement.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.")
            return redirect(project_url)
        header = replacement.stream.read(len(PDF_MAGIC))
        replacement.stream.seek(0)
        if header != PDF_MAGIC:
            flash("That file doesn't look like a valid PDF.")
            return redirect(project_url)

        original_name = secure_filename(replacement.filename)
        filename = (
            f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-"
            f"{secrets.token_hex(4)}-{original_name}"
        )
        upload_dir = os.path.join(
            current_app.config["UPLOAD_FOLDER"], str(doc["project_id"])
        )
        os.makedirs(upload_dir, exist_ok=True)
        replacement.save(os.path.join(upload_dir, filename))

    db.execute(
        "UPDATE documents SET title = ?, subtitle = ?, drive_url = ?, filename = ?, "
        "entry_date = ?, location = ?, uploader_name = ? WHERE id = ?",
        (
            title,
            extra["subtitle"],
            drive_url,
            filename,
            extra["entry_date"],
            extra["location"],
            uploader_name,
            doc_id,
        ),
    )
    db.commit()

    if filename != doc["filename"] and doc["filename"]:
        try:
            os.remove(
                os.path.join(
                    current_app.config["UPLOAD_FOLDER"],
                    str(doc["project_id"]),
                    doc["filename"],
                )
            )
        except OSError:
            pass

    flash("Item updated.")
    return redirect(project_url)


@bp.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete_document(doc_id):
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is not None:
        if doc["source_type"] == "upload" and doc["filename"]:
            path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], str(doc["project_id"]), doc["filename"]
            )
            try:
                os.remove(path)
            except OSError:
                pass
        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        db.commit()
        flash("Deleted.")
        return redirect(url_for("admin.project_detail", project_id=doc["project_id"]))
    return redirect(url_for("admin.dashboard"))
