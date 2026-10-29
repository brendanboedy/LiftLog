"""Loads the predefined exercises into the database (FR-7).

There are no admin accounts, so the team adds predefined exercises by editing
seed_data.py and running:

    flask --app run seed-exercises

It is safe to run more than once: exercises already in the database are
updated to match seed_data.py instead of being added again.
"""
import click
from flask.cli import with_appcontext

from app.exercises.seed_data import PREDEFINED_EXERCISES
from app.extensions import db
from app.models import Exercise


def seed_exercises():
    """Add or update every predefined exercise. Returns (added, updated) counts."""
    existing = {
        exercise.name.lower(): exercise
        for exercise in db.session.execute(
            db.select(Exercise).where(Exercise.created_by.is_(None))
        ).scalars()
    }
    added = updated = 0
    for data in PREDEFINED_EXERCISES:
        exercise = existing.get(data["name"].lower())
        if exercise is None:
            db.session.add(Exercise(**data))
            added += 1
        else:
            changed = False
            for field, value in data.items():
                if getattr(exercise, field) != value:
                    setattr(exercise, field, value)
                    changed = True
            updated += changed
    db.session.commit()
    return added, updated


@click.command("seed-exercises")
@with_appcontext
def seed_exercises_command():
    """Load the predefined exercises from app/exercises/seed_data.py."""
    added, updated = seed_exercises()
    click.echo(f"Predefined exercises: {added} added, {updated} updated.")
