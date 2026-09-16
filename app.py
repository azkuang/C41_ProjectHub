import os

from flask import Flask

from config import load_config
from db import close_db, init_db


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(load_config())

    if not os.path.exists(app.config["DATABASE_PATH"]):
        init_db(app)
    else:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.teardown_appcontext(close_db)

    import auth
    import documents

    app.register_blueprint(auth.bp)
    app.register_blueprint(documents.bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
