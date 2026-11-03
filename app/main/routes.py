"""Pages for the main blueprint."""
from flask import jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import text

from app.extensions import db
from app.main import bp
from app.models import WorkoutSession, WorkoutTemplate


@bp.route("/")
def index():
    """Home page."""
    return render_template("main/index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """The logged-in user's home page. @login_required sends visitors to the login page (NFR-3).

    Links to the user's templates, exercises and history, and to their
    in-progress workout if they have one.
    """
    routines = db.session.execute(
        db.select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == current_user.id)
        .order_by(db.func.lower(WorkoutTemplate.name))
    ).scalars().all()
    ready_made = db.session.execute(
        db.select(WorkoutTemplate).where(WorkoutTemplate.user_id.is_(None))
        .order_by(db.func.lower(WorkoutTemplate.name))
    ).scalars().all() if not routines else []
    return render_template("main/dashboard.html", active=WorkoutSession.active_for(current_user),
                           routines=routines, ready_made=ready_made)


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
