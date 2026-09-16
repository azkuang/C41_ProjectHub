import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["APP_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

from app import create_app  # noqa: E402


@pytest.fixture
def app():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    upload_dir = os.path.join(tmp_dir, "uploads")
    static_dir = os.path.join(tmp_dir, "static")
    os.makedirs(static_dir, exist_ok=True)
    os.environ["DATABASE_PATH"] = db_path
    os.environ["UPLOAD_FOLDER"] = upload_dir

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    # Logos are saved under static_folder (admin.py:_save_logo), which isn't
    # controlled by an env var like DATABASE_PATH/UPLOAD_FOLDER are — point it
    # at a scratch dir so tests never touch the real repo's static/logos/.
    flask_app.static_folder = static_dir

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post("/login", data={"password": "testpass"}, follow_redirects=True)


def create_project(client, title="Test Project", eyebrow="TEST"):
    # Use the redirect target (not a lookup by title) to identify the new
    # project — titles aren't unique, and the seed data ships a real project
    # also titled "Zegna SS27", so a title lookup can silently grab that one
    # instead of the project this call just created.
    resp = client.post(
        "/admin/projects/new",
        data={
            "title": title,
            "eyebrow": eyebrow,
            "production_label": "PRODUCTION / SS27",
            "date_range_text": "17 — 19 SEPTEMBER",
            "date_year": "2026",
            "coordinator_name": "Micol Lupi",
            "coordinator_phone": "+393401458343",
            "emergency_phone": "112",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    project_id = int(resp.headers["Location"].rstrip("/").rsplit("/", 1)[-1])
    with client.application.app_context():
        from db import get_db

        row = get_db().execute(
            "SELECT slug FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    return project_id, row["slug"]


def test_landing_is_public(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Sign in" not in resp.data


def test_admin_requires_login(client):
    resp = client.get("/admin/", follow_redirects=True)
    assert b"Sign in" in resp.data


def test_login_success(client):
    resp = login(client)
    assert resp.status_code == 200
    assert b"Projects" in resp.data


def test_login_failure(client):
    resp = client.post("/login", data={"password": "wrong"}, follow_redirects=True)
    assert b"Incorrect password" in resp.data


def test_create_project_and_public_hub(client):
    login(client)
    project_id, slug = create_project(client)

    landing_resp = client.get("/")
    assert b"Test Project" in landing_resp.data

    hub_resp = client.get(f"/p/{slug}")
    assert hub_resp.status_code == 200
    assert b"TEST" in hub_resp.data
    assert b"Sign in" not in hub_resp.data


def test_unknown_slug_404s(client):
    resp = client.get("/p/does-not-exist")
    assert resp.status_code == 404


def test_add_credit_appears_on_hub(client):
    login(client)
    project_id, slug = create_project(client)
    client.post(
        f"/admin/projects/{project_id}/credits",
        data={"role": "creative director", "name": "Alessandro Sartori"},
        follow_redirects=True,
    )
    resp = client.get(f"/p/{slug}")
    assert b"ALESSANDRO SARTORI" in resp.data
    assert b"creative director" in resp.data


def test_upload_document_round_trip(client):
    login(client)
    project_id, slug = create_project(client)
    data = {
        "title": "ADV Shotlist",
        "uploader_name": "Alex",
        "file": (io.BytesIO(b"%PDF-1.4 fake pdf content"), "test.pdf"),
    }
    resp = client.post(
        f"/admin/projects/{project_id}/documents/document/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"ADV Shotlist" in resp.data

    hub_resp = client.get(f"/p/{slug}")
    assert b"ADV Shotlist" in hub_resp.data

    with client.application.app_context():
        from db import get_db

        doc = get_db().execute(
            "SELECT id FROM documents WHERE title = ?", ("ADV Shotlist",)
        ).fetchone()

    open_resp = client.get(f"/p/{slug}/documents/{doc['id']}/open")
    assert open_resp.status_code == 200
    assert open_resp.data.startswith(b"%PDF-")


def test_open_document_wrong_project_404s(client):
    login(client)
    _, slug_a = create_project(client, title="Project A", eyebrow="A")
    project_b, _ = create_project(client, title="Project B", eyebrow="B")
    client.post(
        f"/admin/projects/{project_b}/documents/document/link",
        data={
            "title": "Other project doc",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/xyz/view",
        },
        follow_redirects=True,
    )
    with client.application.app_context():
        from db import get_db

        doc = get_db().execute(
            "SELECT id FROM documents WHERE title = ?", ("Other project doc",)
        ).fetchone()

    resp = client.get(f"/p/{slug_a}/documents/{doc['id']}/open")
    assert resp.status_code == 404


def test_reject_non_pdf(client):
    login(client)
    project_id, _ = create_project(client)
    data = {
        "title": "Bad File",
        "uploader_name": "Alex",
        "file": (io.BytesIO(b"not a pdf"), "test.txt"),
    }
    resp = client.post(
        f"/admin/projects/{project_id}/documents/document/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Only PDF files are allowed" in resp.data


def test_add_link_round_trip(client):
    login(client)
    project_id, slug = create_project(client)
    resp = client.post(
        f"/admin/projects/{project_id}/documents/document/link",
        data={
            "title": "Shotlist",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/abc123/view",
        },
        follow_redirects=True,
    )
    assert b"Shotlist" in resp.data
    hub_resp = client.get(f"/p/{slug}")
    assert b"Shotlist" in hub_resp.data


def test_callsheet_requires_date_and_location(client):
    login(client)
    project_id, slug = create_project(client)
    resp = client.post(
        f"/admin/projects/{project_id}/documents/callsheet/link",
        data={
            "title": "Day 1",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/abc123/view",
        },
        follow_redirects=True,
    )
    assert b"A date is required" in resp.data

    resp = client.post(
        f"/admin/projects/{project_id}/documents/callsheet/link",
        data={
            "title": "Day 1",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/abc123/view",
            "entry_date": "2026-09-17",
        },
        follow_redirects=True,
    )
    assert b"A location is required" in resp.data

    client.post(
        f"/admin/projects/{project_id}/documents/callsheet/link",
        data={
            "title": "Day 1",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/abc123/view",
            "entry_date": "2026-09-17",
            "location": "CA GIANIN",
        },
        follow_redirects=True,
    )
    hub_resp = client.get(f"/p/{slug}")
    assert b"DAY01" in hub_resp.data
    assert b"CA GIANIN" in hub_resp.data
    assert b"THURSDAY" in hub_resp.data


def test_menu_appears_on_hub(client):
    login(client)
    project_id, slug = create_project(client)
    client.post(
        f"/admin/projects/{project_id}/documents/menu/link",
        data={
            "title": "Brand Ambassador Lunch",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/abc123/view",
            "entry_date": "2026-09-17",
        },
        follow_redirects=True,
    )
    hub_resp = client.get(f"/p/{slug}")
    assert b"17 SEP" in hub_resp.data


def test_delete_document_removes_file(client):
    login(client)
    project_id, slug = create_project(client)
    client.post(
        f"/admin/projects/{project_id}/documents/document/upload",
        data={
            "title": "ADV Shotlist",
            "uploader_name": "Alex",
            "file": (io.BytesIO(b"%PDF-1.4 fake pdf content"), "test.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with client.application.app_context():
        from db import get_db

        doc = get_db().execute(
            "SELECT id, filename FROM documents WHERE title = ?", ("ADV Shotlist",)
        ).fetchone()
        upload_path = os.path.join(
            client.application.config["UPLOAD_FOLDER"], str(project_id), doc["filename"]
        )
        assert os.path.exists(upload_path)

    client.post(
        f"/admin/documents/{doc['id']}/delete", follow_redirects=True
    )
    assert not os.path.exists(upload_path)
    hub_resp = client.get(f"/p/{slug}")
    assert b"ADV Shotlist" not in hub_resp.data


def test_delete_project_cascades(client):
    login(client)
    project_id, slug = create_project(client)
    client.post(
        f"/admin/projects/{project_id}/credits",
        data={"role": "director", "name": "Someone"},
        follow_redirects=True,
    )
    client.post(
        f"/admin/projects/{project_id}/documents/document/upload",
        data={
            "title": "ADV Shotlist",
            "uploader_name": "Alex",
            "file": (io.BytesIO(b"%PDF-1.4 fake pdf content"), "test.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    upload_dir = os.path.join(client.application.config["UPLOAD_FOLDER"], str(project_id))
    assert os.path.isdir(upload_dir)

    client.post(f"/admin/projects/{project_id}/delete", follow_redirects=True)

    assert not os.path.isdir(upload_dir)
    assert client.get(f"/p/{slug}").status_code == 404

    with client.application.app_context():
        from db import get_db

        db = get_db()
        assert db.execute(
            "SELECT COUNT(*) AS n FROM credits WHERE project_id = ?", (project_id,)
        ).fetchone()["n"] == 0
        assert db.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE project_id = ?", (project_id,)
        ).fetchone()["n"] == 0


def test_unauthenticated_admin_post_redirects_to_login(client):
    project_id, _ = 1, "whatever"
    resp = client.post(
        f"/admin/projects/{project_id}/delete", follow_redirects=False
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_reorder_credits(client):
    login(client)
    project_id, slug = create_project(client)
    client.post(
        f"/admin/projects/{project_id}/credits",
        data={"role": "director", "name": "A"},
        follow_redirects=True,
    )
    client.post(
        f"/admin/projects/{project_id}/credits",
        data={"role": "dop", "name": "B"},
        follow_redirects=True,
    )

    with client.application.app_context():
        from db import get_db

        rows = get_db().execute(
            "SELECT id, name FROM credits WHERE project_id = ? ORDER BY sort_order",
            (project_id,),
        ).fetchall()
    assert [r["name"] for r in rows] == ["A", "B"]
    ids = [r["id"] for r in rows]

    resp = client.post(
        f"/admin/projects/{project_id}/credits/reorder",
        json={"order": list(reversed(ids))},
    )
    assert resp.status_code == 200

    with client.application.app_context():
        from db import get_db

        rows = get_db().execute(
            "SELECT name FROM credits WHERE project_id = ? ORDER BY sort_order",
            (project_id,),
        ).fetchall()
    assert [r["name"] for r in rows] == ["B", "A"]

    hub_resp = client.get(f"/p/{slug}")
    b_index = hub_resp.data.index(b"B</dd>")
    a_index = hub_resp.data.index(b"A</dd>")
    assert b_index < a_index


def test_reorder_documents_scoped_to_project_and_section(client):
    login(client)
    project_id, slug = create_project(client)
    other_id, _ = create_project(client, title="Other Project", eyebrow="OTHER")

    for title in ("Doc A", "Doc B"):
        client.post(
            f"/admin/projects/{project_id}/documents/document/link",
            data={
                "title": title,
                "uploader_name": "Alex",
                "drive_url": "https://drive.google.com/file/d/x/view",
            },
            follow_redirects=True,
        )
    client.post(
        f"/admin/projects/{other_id}/documents/document/link",
        data={
            "title": "Other Doc",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/y/view",
        },
        follow_redirects=True,
    )

    with client.application.app_context():
        from db import get_db

        db = get_db()
        rows = db.execute(
            "SELECT id, title FROM documents WHERE project_id = ? AND section = 'document' "
            "ORDER BY sort_order",
            (project_id,),
        ).fetchall()
        other_doc = db.execute(
            "SELECT id, sort_order FROM documents WHERE project_id = ?", (other_id,)
        ).fetchone()
    assert [r["title"] for r in rows] == ["Doc A", "Doc B"]
    doc_a_id, doc_b_id = rows[0]["id"], rows[1]["id"]

    # Include another project's document id in the payload — it must be ignored.
    resp = client.post(
        f"/admin/projects/{project_id}/documents/document/reorder",
        json={"order": [doc_b_id, doc_a_id, other_doc["id"]]},
    )
    assert resp.status_code == 200

    with client.application.app_context():
        from db import get_db

        db = get_db()
        rows = db.execute(
            "SELECT title FROM documents WHERE project_id = ? AND section = 'document' "
            "ORDER BY sort_order",
            (project_id,),
        ).fetchall()
        other_doc_after = db.execute(
            "SELECT sort_order FROM documents WHERE id = ?", (other_doc["id"],)
        ).fetchone()
    assert [r["title"] for r in rows] == ["Doc B", "Doc A"]
    assert other_doc_after["sort_order"] == other_doc["sort_order"]


def test_reorder_requires_login(client):
    project_id, _ = 1, "whatever"
    resp = client.post(
        f"/admin/projects/{project_id}/credits/reorder",
        json={"order": []},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
