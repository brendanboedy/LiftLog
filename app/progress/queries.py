"""Database questions behind the progress chart (FR-32).

Only the user's own completed workouts count: an unfinished workout isn't
history yet, and nobody else's sets are ever included (NFR-2).
"""
from app.extensions import db
from app.models import Exercise, SetEntry, WorkoutSession, WorkoutSessionExercise


def logged_exercises(user):
    """Exercises the user has recorded at least one set for in a completed workout, by name.

    Archived exercises are included on purpose: their past sessions still exist (FR-13).
    """
    return db.session.execute(
        db.select(Exercise)
        .join(WorkoutSessionExercise, WorkoutSessionExercise.exercise_id == Exercise.id)
        .join(WorkoutSession, WorkoutSession.id == WorkoutSessionExercise.session_id)
        .join(SetEntry, SetEntry.session_exercise_id == WorkoutSessionExercise.id)
        .where(WorkoutSession.user_id == user.id, WorkoutSession.completed.is_(True))
        .distinct()
        .order_by(Exercise.name)
    ).scalars().all()


def exercise_progress(user, exercise_id):
    """One row per completed workout the user did `exercise_id` in, oldest first.

    Each row is {"date", "workout", "max_weight", "volume"}:
    - max_weight: the heaviest weight lifted in any set that day
    - volume: total of weight x reps over every set that day
    If the exercise was added to a workout twice, its sets are combined.
    """
    rows = db.session.execute(
        db.select(
            WorkoutSession.id,
            WorkoutSession.name,
            WorkoutSession.date_performed,
            db.func.max(SetEntry.weight),
            db.func.sum(SetEntry.weight * SetEntry.reps),
        )
        .join(WorkoutSessionExercise, WorkoutSessionExercise.session_id == WorkoutSession.id)
        .join(SetEntry, SetEntry.session_exercise_id == WorkoutSessionExercise.id)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.completed.is_(True),
            WorkoutSessionExercise.exercise_id == exercise_id,
        )
        .group_by(WorkoutSession.id, WorkoutSession.name, WorkoutSession.date_performed)
        .order_by(WorkoutSession.date_performed, WorkoutSession.id)
    ).all()
    return [
        {"date": performed.isoformat(), "workout": name, "max_weight": max_weight, "volume": volume}
        for _, name, performed, max_weight, volume in rows
    ]
