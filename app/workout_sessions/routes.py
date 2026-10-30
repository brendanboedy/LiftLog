"""Workout session pages (FR-22 to FR-31).

A session is either in progress (the user is working out and logging sets)
or completed (part of their history). A user has at most one in-progress
session at a time. Completed sessions can be viewed and deleted, not changed.

Sessions are private: every page needs a login (NFR-3) and someone else's
session answers "404 Not Found". Pages that change data only accept POST.
"""
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Exercise, SetEntry, WorkoutSession, WorkoutSessionExercise, WorkoutTemplate
from app.workout_sessions import bp
from app.workout_sessions.forms import FinishForm, SessionExerciseForm, SetForm

EMPTY_SESSION_NAME = "Quick workout"


# ---------- helpers ----------

def own_session_or_404(session_id):
    workout = db.session.get(WorkoutSession, session_id)
    if workout is None or not workout.is_owned_by(current_user):
        abort(404)
    return workout


def in_progress_session_or_404(session_id):
    """Like own_session_or_404, but a finished workout can't be changed (400 Bad Request)."""
    workout = own_session_or_404(session_id)
    if workout.completed:
        abort(400)
    return workout


def session_item_or_404(workout, item_id):
    item = db.session.get(WorkoutSessionExercise, item_id)
    if item is None or item.session_id != workout.id:
        abort(404)
    return item


def set_entry_or_404(workout, set_id):
    entry = db.session.get(SetEntry, set_id)
    if entry is None or entry.session_exercise.session_id != workout.id:
        abort(404)
    return entry


def exercise_choices():
    """Exercises the user can see, minus archived ones (FR-13)."""
    exercises = db.session.execute(
        Exercise.visible_to(current_user)
        .where(Exercise.is_archived.is_(False))
        .order_by(Exercise.name)
    ).scalars()
    return [("", "Choose an exercise...")] + [
        (exercise.id, f"{exercise.name} ({exercise.muscle_group}, {exercise.equipment_type})")
        for exercise in exercises
    ]


def make_exercise_form():
    form = SessionExerciseForm()
    form.exercise_id.choices = exercise_choices()
    return form


def set_prefix(item):
    """Each exercise on the workout page has its own "add a set" form. A prefix
    (set12-weight, set12-reps...) keeps their boxes apart."""
    return f"set{item.id}"


def blank_set_form(item):
    """An "add a set" form, filled in with the last set's numbers to save typing."""
    # formdata=None: start empty instead of reading what was just submitted
    form = SetForm(formdata=None, prefix=set_prefix(item))
    if item.sets:
        form.weight.data = item.sets[-1].weight
        form.reps.data = item.sets[-1].reps
    return form


def render_workout(workout, set_forms=None, exercise_form=None, status=200):
    """The in-progress workout page. set_forms can replace one exercise's form to show its errors."""
    forms = {item.id: blank_set_form(item) for item in workout.items}
    forms.update(set_forms or {})
    return render_template(
        "workout_sessions/active.html",
        workout=workout,
        set_forms=forms,
        exercise_form=exercise_form or make_exercise_form(),
    ), status


def back_to(workout):
    return redirect(url_for("workout_sessions.detail", session_id=workout.id))


def add_to_session(workout, exercise_id, template_item=None):
    item = WorkoutSessionExercise(exercise_id=exercise_id, order_index=len(workout.items) + 1)
    if template_item is not None:
        item.target_sets = template_item.target_sets
        item.rep_range_min = template_item.rep_range_min
        item.rep_range_max = template_item.rep_range_max
    workout.items.append(item)


# ---------- history and starting ----------

@bp.route("/")
@login_required
def history():
    """FR-29: completed sessions, most recent first."""
    workouts = db.session.execute(
        db.select(WorkoutSession)
        .where(WorkoutSession.user_id == current_user.id, WorkoutSession.completed.is_(True))
        .order_by(WorkoutSession.date_performed.desc(), WorkoutSession.id.desc())
    ).scalars().all()
    return render_template(
        "workout_sessions/history.html",
        workouts=workouts,
        active=WorkoutSession.active_for(current_user),
    )


@bp.route("/start", methods=["POST"])
@login_required
def start():
    """FR-22: start from one of the user's templates or a predefined one (copying
    its exercises), or FR-23: start an empty workout when no template is chosen."""
    active = WorkoutSession.active_for(current_user)
    if active is not None:
        flash("Finish or cancel this workout before starting another one.", "info")
        return back_to(active)

    template_id = request.form.get("template_id", "")
    if template_id:
        template = db.session.get(WorkoutTemplate, int(template_id)) if template_id.isdigit() else None
        if template is None or not template.is_startable_by(current_user):
            abort(404)
        workout = WorkoutSession(user_id=current_user.id, template_id=template.id, name=template.name)
        for template_item in template.items:
            add_to_session(workout, template_item.exercise_id, template_item)
    else:
        workout = WorkoutSession(user_id=current_user.id, name=EMPTY_SESSION_NAME)

    db.session.add(workout)
    db.session.commit()
    flash(f"Started {workout.name}. Log each set as you go.", "success")
    return back_to(workout)


@bp.route("/<int:session_id>")
@login_required
def detail(session_id):
    """In progress: the workout page (FR-24). Completed: what was done (FR-30)."""
    workout = own_session_or_404(session_id)
    if workout.completed:
        return render_template("workout_sessions/detail.html", workout=workout)
    return render_workout(workout)


# ---------- exercises in the session (FR-23, FR-26) ----------

@bp.route("/<int:session_id>/exercises", methods=["POST"])
@login_required
def add_exercise(session_id):
    """Add an exercise to this workout only - the template is not changed (FR-26)."""
    workout = in_progress_session_or_404(session_id)
    form = make_exercise_form()
    if form.validate_on_submit():
        add_to_session(workout, form.exercise_id.data)
        db.session.commit()
        flash("Exercise added.", "success")
        return back_to(workout)
    return render_workout(workout, exercise_form=form)


@bp.route("/<int:session_id>/exercises/<int:item_id>/remove", methods=["POST"])
@login_required
def remove_exercise(session_id, item_id):
    """Take an exercise (and any sets logged for it) out of this workout (FR-26)."""
    workout = in_progress_session_or_404(session_id)
    item = session_item_or_404(workout, item_id)
    name = item.exercise.name
    workout.items.remove(item)
    workout.renumber()
    db.session.commit()
    flash(f"Removed {name} from this workout.", "info")
    return back_to(workout)


# ---------- sets (FR-24, FR-25) ----------

@bp.route("/<int:session_id>/exercises/<int:item_id>/sets", methods=["POST"])
@login_required
def add_set(session_id, item_id):
    """FR-24: record a set for an exercise in the active session."""
    workout = in_progress_session_or_404(session_id)
    item = session_item_or_404(workout, item_id)
    form = SetForm(prefix=set_prefix(item))
    if form.validate_on_submit():
        item.sets.append(SetEntry(
            set_number=len(item.sets) + 1,
            weight=form.weight.data,
            reps=form.reps.data,
            notes=form.notes.data or None,
        ))
        db.session.commit()
        return back_to(workout)
    return render_workout(workout, set_forms={item.id: form})


@bp.route("/<int:session_id>/sets/<int:set_id>/edit", methods=["GET", "POST"])
@login_required
def edit_set(session_id, set_id):
    """FR-25: fix a set's weight, reps or notes."""
    workout = in_progress_session_or_404(session_id)
    entry = set_entry_or_404(workout, set_id)
    form = SetForm(obj=entry)
    form.submit.label.text = "Save set"
    if form.validate_on_submit():
        entry.weight = form.weight.data
        entry.reps = form.reps.data
        entry.notes = form.notes.data or None
        db.session.commit()
        flash("Set updated.", "success")
        return back_to(workout)
    return render_template("workout_sessions/edit_set.html", form=form, workout=workout, entry=entry)


@bp.route("/<int:session_id>/sets/<int:set_id>/delete", methods=["POST"])
@login_required
def delete_set(session_id, set_id):
    """FR-25: delete a set. The sets after it move up a number."""
    workout = in_progress_session_or_404(session_id)
    entry = set_entry_or_404(workout, set_id)
    item = entry.session_exercise
    item.sets.remove(entry)
    item.renumber_sets()
    db.session.commit()
    flash("Set deleted.", "info")
    return back_to(workout)


# ---------- finishing, cancelling, deleting ----------

@bp.route("/<int:session_id>/finish", methods=["GET", "POST"])
@login_required
def finish(session_id):
    """FR-27: mark the workout completed with its date, duration, energy and notes."""
    workout = in_progress_session_or_404(session_id)
    form = FinishForm()
    if request.method == "GET":
        form.duration_minutes.data = workout.minutes_so_far()  # a suggestion the user can change
    if form.validate_on_submit():
        workout.date_performed = form.date_performed.data
        workout.duration_minutes = form.duration_minutes.data
        workout.energy_rating = form.energy_rating.data
        workout.notes = form.notes.data or None
        workout.completed = True
        db.session.commit()
        flash("Workout saved. Nice work!", "success")
        return back_to(workout)
    return render_template("workout_sessions/finish.html", form=form, workout=workout)


@bp.route("/<int:session_id>/delete", methods=["GET", "POST"])
@login_required
def delete(session_id):
    """GET asks "are you sure?", POST deletes.

    In progress: this is cancelling the workout (FR-28).
    Completed: this removes it from the history (FR-31).
    Either way its exercises and sets are deleted too; the template is not touched.
    """
    workout = own_session_or_404(session_id)
    if request.method == "POST":
        was_completed = workout.completed
        db.session.delete(workout)
        db.session.commit()
        flash("Workout deleted." if was_completed else "Workout cancelled.", "info")
        return redirect(url_for("workout_sessions.history"))
    return render_template("workout_sessions/confirm_delete.html", workout=workout)
