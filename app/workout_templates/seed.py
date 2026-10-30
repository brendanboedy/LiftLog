"""Loads the predefined workout templates into the database (FR-19).

There are no admin accounts, so the team adds predefined templates by editing
seed_data.py and running (after seed-exercises):

    flask --app run seed-templates

It is safe to run more than once: templates already in the database are
updated to match seed_data.py instead of being added again. Sessions already
started from a template keep their own copy of its exercises (FR-22).
"""
import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Exercise, WorkoutTemplate, WorkoutTemplateExercise
from app.workout_templates.seed_data import PREDEFINED_TEMPLATES


def seed_templates():
    """Add or update every predefined template. Returns (added, updated) counts.

    Raises click.ClickException if a template uses an exercise that isn't a
    predefined exercise in the database (run seed-exercises first).
    """
    exercise_ids = {
        name.lower(): exercise_id
        for exercise_id, name in db.session.execute(
            db.select(Exercise.id, Exercise.name).where(Exercise.created_by.is_(None))
        )
    }
    missing = sorted({
        name for data in PREDEFINED_TEMPLATES for name, *_ in data["exercises"]
        if name.lower() not in exercise_ids
    })
    if missing:
        raise click.ClickException(
            "These exercises aren't in the database: " + ", ".join(missing)
            + ". Run `flask --app run seed-exercises` first."
        )

    existing = {
        template.name.lower(): template
        for template in db.session.execute(
            db.select(WorkoutTemplate).where(WorkoutTemplate.user_id.is_(None))
        ).scalars()
    }
    added = updated = 0
    for data in PREDEFINED_TEMPLATES:
        wanted = [(exercise_ids[name.lower()], sets, low, high) for name, sets, low, high in data["exercises"]]
        template = existing.get(data["name"].lower())
        if template is None:
            template = WorkoutTemplate(user_id=None)
            db.session.add(template)
            added += 1
        else:
            current = [(i.exercise_id, i.target_sets, i.rep_range_min, i.rep_range_max) for i in template.items]
            same = (template.name, template.difficulty, template.description, current) == \
                (data["name"], data["difficulty"], data["description"], wanted)
            if same:
                continue
            updated += 1
            template.items.clear()
            db.session.flush()  # delete the old rows first so the new order numbers don't clash
        template.name = data["name"]
        template.difficulty = data["difficulty"]
        template.description = data["description"]
        for position, (exercise_id, sets, low, high) in enumerate(wanted, start=1):
            template.items.append(WorkoutTemplateExercise(
                exercise_id=exercise_id, order_index=position,
                target_sets=sets, rep_range_min=low, rep_range_max=high,
            ))
    db.session.commit()
    return added, updated


@click.command("seed-templates")
@with_appcontext
def seed_templates_command():
    """Load the predefined workout templates from app/workout_templates/seed_data.py."""
    added, updated = seed_templates()
    click.echo(f"Predefined templates: {added} added, {updated} updated.")
