"""Progress chart page (FR-32). Needs a login (NFR-3) and only ever reads the user's own data (NFR-2)."""
from flask import render_template, request
from flask_login import current_user, login_required

from app.progress import bp
from app.progress.queries import exercise_progress, logged_exercises


@bp.route("/")
@login_required
def chart():
    """Pick an exercise, e.g. /progress/?exercise_id=3, and see its chart.

    The picker only offers exercises the user has logged, so an id that isn't
    in that list (someone else's custom exercise, a typo) just shows no chart.
    """
    exercises = logged_exercises(current_user)
    chosen = None
    if request.args.get("exercise_id", "").isdigit():
        wanted = int(request.args["exercise_id"])
        chosen = next((e for e in exercises if e.id == wanted), None)
    points = exercise_progress(current_user, chosen.id) if chosen else []
    return render_template("progress/chart.html", exercises=exercises, chosen=chosen, points=points)
