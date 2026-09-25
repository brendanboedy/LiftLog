"""Pages for the main blueprint."""
from flask import jsonify, render_template
from flask_login import login_required
from sqlalchemy import text

from app.extensions import db
from app.main import bp


@bp.route("/")
def index():
    """Home page."""
    return render_template("main/index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """The logged-in user's home page. @login_required sends visitors to the login page (NFR-3).

    For now it just greets the user; workout templates, sessions and history
    will be linked from here as they are built.
    """
    return render_template("main/dashboard.html")


@bp.route("/health")
def health():
    """Quick check that the app is running and can reach the database.

    Visit http://127.0.0.1:5000/health - it should show {"status": "ok", "database": "ok"}.
    Handy after switching DATABASE_URL to MySQL.
    """
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # any connection problem
        database = "unreachable"
    status = 200 if database == "ok" else 503
    return jsonify(status="ok" if status == 200 else "error", database=database), status
