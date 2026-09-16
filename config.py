import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB
PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 days


def load_config():
    """Read config from the current environment. Called at create_app() time
    (not import time) so tests can override env vars before building the app."""
    return {
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        "APP_PASSWORD": os.environ.get("APP_PASSWORD", "change-me"),
        "DATABASE_PATH": os.environ.get(
            "DATABASE_PATH", os.path.join(BASE_DIR, "app.db")
        ),
        "UPLOAD_FOLDER": os.environ.get(
            "UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads")
        ),
        "MAX_CONTENT_LENGTH": MAX_CONTENT_LENGTH,
        "PERMANENT_SESSION_LIFETIME": PERMANENT_SESSION_LIFETIME,
    }
