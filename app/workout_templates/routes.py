"""Workout template pages (FR-14 to FR-18).

Templates are private: every page needs a login (NFR-3), and someone else's
template answers "404 Not Found" so its existence isn't revealed.
Pages that change data only accept POST (a button with a CSRF token).
"""
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Exercise, WorkoutTemplate, WorkoutTemplateExercise
from app.workout_templates import bp
from app.workout_templates.forms import AddExerciseForm, TargetsForm, TemplateForm


# ---------- helpers ----------

def own_template_or_404(template_id):
    """The template, if the logged-in user owns it."""
    template = db.session.get(WorkoutTemplate, template_id)
    if template is None or not template.is_owned_by(current_user):
        abort(404)
    return template


def item_or_404(template, item_id):
    """One exercise row of `template` (404 if it belongs to a different template)."""
    item = db.session.get(WorkoutTemplateExercise, item_id)
    if item is None or item.template_id != template.id:
        abort(404)
    return item


def exercise_choices():
    """Drop-down options: exercises this user can see, minus archived ones (FR-13)."""
    exercises = db.session.execute(
        Exercise.visible_to(current_user)
        .where(Exercise.is_archived.is_(False))
        .order_by(Exercise.name)
    ).scalars()
    return [("", "Choose an exercise...")] + [
        (exercise.id, f"{exercise.name} ({exercise.muscle_group}, {exercise.equipment_type})")
        for exercise in exercises
    ]


def make_add_form():
    form = AddExerciseForm()
    form.exercise_id.choices = exercise_choices()
    return form


def copy_targets(form, item):
    item.target_sets = form.target_sets.data
    item.rep_range_min = form.rep_range_min.data
    item.rep_range_max = form.rep_range_max.data


def copy_details(form, template):
    template.name = form.name.data
    template.description = form.description.data or None
    template.difficulty = form.difficulty.data


def back_to(template):
    return redirect(url_for("workout_templates.detail", template_id=template.id))


# ---------- templates ----------

@bp.route("/")
@login_required
def list_templates():
    """FR-16: the user's own templates."""
    templates = db.session.execute(
        db.select(WorkoutTemplate)
        .where(WorkoutTemplate.user_id == current_user.id)
        .order_by(db.func.lower(WorkoutTemplate.name))
    ).scalars().all()
    return render_template("workout_templates/list.html", templates=templates)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    """FR-14: make a new (private) template, then add exercises on its page."""
    form = TemplateForm()
    if form.validate_on_submit():
        template = WorkoutTemplate(user_id=current_user.id)
        copy_details(form, template)
        db.session.add(template)
        db.session.commit()
        flash(f"Created {template.name}. Now add some exercises.", "success")
        return back_to(template)
    return render_template("workout_templates/form.html", form=form, template=None)


@bp.route("/<int:template_id>")
@login_required
def detail(template_id):
    """FR-16: the template's exercises in order, with sets and rep ranges."""
    template = own_template_or_404(template_id)
    return render_template("workout_templates/detail.html", template=template, add_form=make_add_form())


@bp.route("/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def edit(template_id):
    """FR-17: change the name, description or difficulty."""
    template = own_template_or_404(template_id)
    form = TemplateForm(obj=template)
    if form.validate_on_submit():
        copy_details(form, template)
        db.session.commit()
        flash("Template updated.", "success")
        return back_to(template)
    return render_template("workout_templates/form.html", form=form, template=template)


@bp.route("/<int:template_id>/delete", methods=["GET", "POST"])
@login_required
def delete(template_id):
    """FR-18: GET asks "are you sure?", POST deletes.

    Deleting a template deletes its exercise rows, but not the exercises
    themselves. (What happens to sessions started from it is decided when
    sessions are built - open team decision #3.)
    """
    template = own_template_or_404(template_id)
    if request.method == "POST":
        name = template.name
        db.session.delete(template)
        db.session.commit()
        flash(f"Deleted {name}.", "info")
        return redirect(url_for("workout_templates.list_templates"))
    return render_template("workout_templates/confirm_delete.html", template=template)


# ---------- exercises inside a template ----------

@bp.route("/<int:template_id>/exercises", methods=["POST"])
@login_required
def add_exercise(template_id):
    """FR-15: add an exercise to the end of the template."""
    template = own_template_or_404(template_id)
    form = make_add_form()
    if form.validate_on_submit():
        item = WorkoutTemplateExercise(exercise_id=form.exercise_id.data,
                                       order_index=len(template.items) + 1)
        copy_targets(form, item)
        template.items.append(item)
        db.session.commit()
        flash("Exercise added.", "success")
        return back_to(template)
    # Show the template page again, with the error messages under the add form.
    return render_template("workout_templates/detail.html", template=template, add_form=form)


@bp.route("/<int:template_id>/exercises/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exercise(template_id, item_id):
    """FR-17: change the sets or rep range of one exercise in the template."""
    template = own_template_or_404(template_id)
    item = item_or_404(template, item_id)
    form = TargetsForm(obj=item)
    if form.validate_on_submit():
        copy_targets(form, item)
        db.session.commit()
        flash("Exercise updated.", "success")
        return back_to(template)
    return render_template("workout_templates/item_form.html", form=form, template=template, item=item)


@bp.route("/<int:template_id>/exercises/<int:item_id>/remove", methods=["POST"])
@login_required
def remove_exercise(template_id, item_id):
    """FR-17: take an exercise out of the template (the exercise itself stays in the library)."""
    template = own_template_or_404(template_id)
    item = item_or_404(template, item_id)
    name = item.exercise.name  # read it now - the row is gone after the commit
    template.items.remove(item)  # delete-orphan: removing it from the list deletes the row
    template.renumber()
    db.session.commit()
    flash(f"Removed {name}.", "info")
    return back_to(template)


@bp.route("/<int:template_id>/exercises/<int:item_id>/move", methods=["POST"])
@login_required
def move_exercise(template_id, item_id):
    """FR-17: move an exercise one place up or down by swapping it with its neighbour."""
    template = own_template_or_404(template_id)
    item = item_or_404(template, item_id)
    items = sorted(template.items, key=lambda row: row.order_index)
    position = items.index(item)
    direction = request.form.get("direction")
    if direction == "up":
        other = position - 1
    elif direction == "down":
        other = position + 1
    else:
        abort(400)
    if 0 <= other < len(items):  # moving the first one up (or last one down) does nothing
        items[position], items[other] = items[other], items[position]
        for number, row in enumerate(items, start=1):
            row.order_index = number
        db.session.commit()
    return back_to(template)
