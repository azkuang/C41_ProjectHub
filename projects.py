import os
from datetime import datetime

from flask import Blueprint, abort, current_app, redirect, render_template, send_from_directory

from db import get_db

bp = Blueprint("projects", __name__)

WEEKDAYS = [
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY",
]


def _get_project_or_404(slug):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
    if project is None:
        abort(404)
    return project


def _augment_callsheet(doc, index):
    date = datetime.strptime(doc["entry_date"], "%Y-%m-%d")
    return {
        **dict(doc),
        "day_label": f"DAY{index:02d}",
        "display_date": date.strftime("%d %b %Y").upper(),
        "weekday": WEEKDAYS[date.weekday()],
    }


def _augment_menu(doc):
    date = datetime.strptime(doc["entry_date"], "%Y-%m-%d")
    return {**dict(doc), "display_date": date.strftime("%d %b").upper()}


@bp.route("/")
def landing():
    db = get_db()
    projects = db.execute(
        "SELECT * FROM projects ORDER BY created_at DESC, id DESC"
    ).fetchall()
    return render_template("landing.html", projects=projects)


@bp.route("/p/<slug>")
def hub(slug):
    project = _get_project_or_404(slug)
    db = get_db()
    credits = db.execute(
        "SELECT * FROM credits WHERE project_id = ? ORDER BY sort_order, id",
        (project["id"],),
    ).fetchall()
    documents = db.execute(
        "SELECT * FROM documents WHERE project_id = ? AND section = 'document' "
        "ORDER BY sort_order, id",
        (project["id"],),
    ).fetchall()
    callsheet_rows = db.execute(
        "SELECT * FROM documents WHERE project_id = ? AND section = 'callsheet' "
        "ORDER BY sort_order, id",
        (project["id"],),
    ).fetchall()
    menu_rows = db.execute(
        "SELECT * FROM documents WHERE project_id = ? AND section = 'menu' "
        "ORDER BY sort_order, id",
        (project["id"],),
    ).fetchall()

    callsheets = [
        _augment_callsheet(row, i) for i, row in enumerate(callsheet_rows, start=1)
    ]
    menus = [_augment_menu(row) for row in menu_rows]

    return render_template(
        "hub.html",
        project=project,
        credits=credits,
        documents=documents,
        callsheets=callsheets,
        menus=menus,
    )


@bp.route("/p/<slug>/documents/<int:doc_id>/open")
def open_document(slug, doc_id):
    project = _get_project_or_404(slug)
    db = get_db()
    doc = db.execute(
        "SELECT * FROM documents WHERE id = ? AND project_id = ?",
        (doc_id, project["id"]),
    ).fetchone()
    if doc is None:
        abort(404)

    if doc["source_type"] == "drive":
        return redirect(doc["drive_url"])

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(project["id"]))
    return send_from_directory(
        upload_dir,
        doc["filename"],
        mimetype="application/pdf",
        as_attachment=False,
    )
