"""Pages shouldn't get slower as a user's history grows (NFR-13).

These tests count the database queries a page runs. If a change makes a page
run one query per past workout (or per set), the count goes up with history
and the test fails.
"""
from contextlib import contextmanager
from datetime import date, timedelta

from sqlalchemy import event

from app.extensions import db
from app.models import Exercise, SetEntry, User, WorkoutSession, WorkoutSessionExercise


def sign_in(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


@contextmanager
def count_queries():
    """Counts every SQL statement sent to the database inside the `with` block."""
    counter = {"queries": 0}

    def on_query(*args):
        counter["queries"] += 1

    event.listen(db.engine, "before_cursor_execute", on_query)
    try:
        yield counter
    finally:
        event.remove(db.engine, "before_cursor_execute", on_query)


def make_exercises(n=3):
    exercises = [
        Exercise(name=f"Exercise {i}", muscle_group="Chest", equipment_type="Barbell",
                 movement_type="Compound", difficulty="Beginner")
        for i in range(n)
    ]
    db.session.add_all(exercises)
    db.session.flush()
    return exercises


def add_past_workouts(user, exercises, how_many, start=date(2026, 1, 1)):
    """Completed workouts with 3 sets of every exercise, one per day."""
    for day in range(how_many):
        workout = WorkoutSession(user_id=user.id, name="Past", completed=True,
                                 date_performed=start + timedelta(days=day))
        for position, exercise in enumerate(exercises, start=1):
            item = WorkoutSessionExercise(exercise_id=exercise.id, order_index=position)
            for number in (1, 2, 3):
                item.sets.append(SetEntry(set_number=number, weight=100 + day, reps=8))
            workout.items.append(item)
        db.session.add(workout)


def active_workout(user, exercises):
    workout = WorkoutSession(user_id=user.id, name="Today")
    for position, exercise in enumerate(exercises, start=1):
        workout.items.append(WorkoutSessionExercise(exercise_id=exercise.id, order_index=position))
    db.session.add(workout)
    return workout


def workout_page_queries(client, workout_id):
    """How many queries the active workout page runs."""
    db.session.expire_all()  # start from an empty cache, like a real request
    with count_queries() as counter:
        page = client.get(f"/sessions/{workout_id}")
    assert page.status_code == 200
    return counter["queries"]


def test_workout_page_query_count_does_not_grow_with_history(client, app):
    user = User(username="me", password_hash="unused")
    db.session.add(user)
    db.session.flush()
    exercises = make_exercises()
    add_past_workouts(user, exercises, how_many=2)
    workout = active_workout(user, exercises)
    db.session.commit()
    workout_id = workout.id
    sign_in(client, user)

    with_little_history = workout_page_queries(client, workout_id)
    add_past_workouts(user, exercises, how_many=20, start=date(2026, 2, 1))
    db.session.commit()
    with_more_history = workout_page_queries(client, workout_id)

    assert with_more_history == with_little_history


def test_last_time_comes_from_the_newest_workout(client, app):
    """Uses the workout with the latest date, even if an older-dated one was logged afterwards."""
    user = User(username="me", password_hash="unused")
    db.session.add(user)
    db.session.flush()
    (squat,) = make_exercises(1)

    def past(day, weight, reps):
        workout = WorkoutSession(user_id=user.id, name="Past", completed=True, date_performed=day)
        item = WorkoutSessionExercise(exercise_id=squat.id, order_index=1)
        item.sets.append(SetEntry(set_number=1, weight=weight - 10, reps=reps))
        item.sets.append(SetEntry(set_number=2, weight=weight, reps=reps))  # last set of the day
        workout.items.append(item)
        db.session.add(workout)

    past(date(2026, 3, 10), weight=225, reps=5)   # newest date
    past(date(2026, 3, 1), weight=185, reps=8)    # older date, but added later
    workout = active_workout(user, [squat])
    db.session.commit()

    sign_in(client, user)
    page = client.get(f"/sessions/{workout.id}")
    assert "Last time: 225 lb × 5 reps".encode() in page.data
