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
    os.environ["DATABASE_PATH"] = db_path
    os.environ["UPLOAD_FOLDER"] = upload_dir

    flask_app = create_app()
    flask_app.config.update(TESTING=True)

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    return client.post("/login", data={"password": "testpass"}, follow_redirects=True)


def test_index_requires_login(client):
    resp = client.get("/", follow_redirects=True)
    assert b"Sign in" in resp.data


def test_login_success(client):
    resp = login(client)
    assert resp.status_code == 200
    assert b"Documents" in resp.data


def test_login_failure(client):
    resp = client.post("/login", data={"password": "wrong"}, follow_redirects=True)
    assert b"Incorrect password" in resp.data


def test_upload_round_trip(client):
    login(client)
    data = {
        "title": "Test PDF",
        "uploader_name": "Alex",
        "file": (io.BytesIO(b"%PDF-1.4 fake pdf content"), "test.pdf"),
    }
    resp = client.post(
        "/upload", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert b"Test PDF" in resp.data


def test_reject_non_pdf(client):
    login(client)
    data = {
        "title": "Bad File",
        "uploader_name": "Alex",
        "file": (io.BytesIO(b"not a pdf"), "test.txt"),
    }
    resp = client.post(
        "/upload", data=data, content_type="multipart/form-data", follow_redirects=True
    )
    assert b"Only PDF files are allowed" in resp.data


def test_add_link_round_trip(client):
    login(client)
    resp = client.post(
        "/add-link",
        data={
            "title": "Shotlist",
            "uploader_name": "Alex",
            "drive_url": "https://drive.google.com/file/d/abc123/view",
        },
        follow_redirects=True,
    )
    assert b"Shotlist" in resp.data
