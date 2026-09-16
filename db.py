import os
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]) or ".", exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    with sqlite3.connect(app.config["DATABASE_PATH"]) as conn:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path) as f:
            conn.executescript(f.read())
