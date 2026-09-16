import secrets
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        submitted = request.form.get("password", "")
        if secrets.compare_digest(submitted, current_app.config["APP_PASSWORD"]):
            session.clear()
            session["authenticated"] = True
            session.permanent = True
            next_url = request.form.get("next") or url_for("documents.index")
            return redirect(next_url)
        flash("Incorrect password.")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
