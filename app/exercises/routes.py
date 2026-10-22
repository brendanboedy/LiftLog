"""Exercise library pages.

Every page needs a login (NFR-3). Users can see predefined exercises and their
own custom ones; another user's custom exercise answers "404 Not Found", so the
page doesn't even reveal that it exists.
"""
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.exercises import bp
from app.exercises.forms import ExerciseForm
from app.extensions import db
from app.models import EQUIPMENT_TYPES, MUSCLE_GROUPS, Exercise


def visible_exercise_or_404(exercise_id):
    """The exercise, if the logged-in user is allowed to see it."""
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None or not exercise.is_visible_to(current_user):
        abort(404)
    return exercise


def copy_form_to_exercise(form, exercise):
    """Save what the user typed into the exercise."""
    exercise.name = form.name.data
    exercise.muscle_group = form.muscle_group.data
    exercise.equipment_type = form.equipment_type.data
    exercise.movement_type = form.movement_type.data
    exercise.difficulty = form.difficulty.data
    exercise.instructions = form.instructions.data or None  # store "no instructions" as empty


def own_custom_exercise_or_404(exercise_id):
    """The exercise, if it is a custom exercise the logged-in user created.

    Predefined exercises are shared by everyone, so nobody can change them
    through the website (403 Forbidden). Only the team changes them, in seed_data.py.
    """
    exercise = visible_exercise_or_404(exercise_id)
    if exercise.is_predefined:
        abort(403)
    return exercise


@bp.route("/")
@login_required
def list_exercises():
    """FR-8 browse, FR-10 search by name and filter by muscle group / equipment.

    The filters come from the address, e.g. /exercises/?q=press&muscle_group=Chest,
    so a filtered list can be bookmarked or refreshed.
    """
    search = request.args.get("q", "").strip()
    muscle_group = request.args.get("muscle_group", "")
    equipment_type = request.args.get("equipment_type", "")
    show_archived = request.args.get("archived") == "1"

    query = Exercise.visible_to(current_user)
    if search:
        # autoescape=True makes % and _ in the search box count as normal characters.
        query = query.where(Exercise.name.icontains(search, autoescape=True))
    if muscle_group in MUSCLE_GROUPS:
        query = query.where(Exercise.muscle_group == muscle_group)
    if equipment_type in EQUIPMENT_TYPES:
        query = query.where(Exercise.equipment_type == equipment_type)
    if not show_archived:
        query = query.where(Exercise.is_archived.is_(False))
    exercises = db.session.execute(query.order_by(Exercise.name)).scalars().all()

    return render_template(
        "exercises/list.html",
        exercises=exercises,
        search=search,
        muscle_group=muscle_group,
        equipment_type=equipment_type,
        show_archived=show_archived,
        muscle_groups=MUSCLE_GROUPS,
        equipment_types=EQUIPMENT_TYPES,
    )


@bp.route("/<int:exercise_id>")
@login_required
def detail(exercise_id):
    """FR-9: all the details of one exercise."""
    exercise = visible_exercise_or_404(exercise_id)
    return render_template("exercises/detail.html", exercise=exercise)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    """FR-11: make a custom exercise that only this user can see."""
    form = ExerciseForm()
    if form.validate_on_submit():
        exercise = Exercise(created_by=current_user.id)
        copy_form_to_exercise(form, exercise)
        db.session.add(exercise)
        db.session.commit()
        flash(f"Added {exercise.name} to your exercises.", "success")
        return redirect(url_for("exercises.detail", exercise_id=exercise.id))
    return render_template("exercises/form.html", form=form, exercise=None)


@bp.route("/<int:exercise_id>/edit", methods=["GET", "POST"])
@login_required
def edit(exercise_id):
    """FR-12: change a custom exercise the user created."""
    exercise = own_custom_exercise_or_404(exercise_id)
    # obj=exercise fills the boxes with the current values when the page first opens.
    form = ExerciseForm(obj=exercise, exercise_id=exercise.id)
    if form.validate_on_submit():
        copy_form_to_exercise(form, exercise)
        db.session.commit()
        flash("Exercise updated.", "success")
        return redirect(url_for("exercises.detail", exercise_id=exercise.id))
    return render_template("exercises/form.html", form=form, exercise=exercise)


@bp.route("/<int:exercise_id>/archive", methods=["POST"])
@login_required
def archive(exercise_id):
    """FR-13: hide a custom exercise from the library without deleting it.

    POST only (a button with a CSRF token), like logging out.
    """
    exercise = own_custom_exercise_or_404(exercise_id)
    exercise.is_archived = True
    db.session.commit()
    flash(f"{exercise.name} was archived. It won't be offered for new workouts.", "info")
    return redirect(url_for("exercises.detail", exercise_id=exercise.id))


@bp.route("/<int:exercise_id>/restore", methods=["POST"])
@login_required
def restore(exercise_id):
    """Undo an archive, in case it was a mistake."""
    exercise = own_custom_exercise_or_404(exercise_id)
    exercise.is_archived = False
    db.session.commit()
    flash(f"{exercise.name} is back in your library.", "success")
    return redirect(url_for("exercises.detail", exercise_id=exercise.id))
