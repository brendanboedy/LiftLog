"""The history page shouldn't get slower as a user's history grows (FR-29, NFR-13).

Counts the database queries the page runs. If the page goes back to loading
each workout's exercises and sets one workout at a time, the count grows with
history and the test fails.
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


def add_past_workouts(user, exercises, how_many, start, sets_each=3):
    for day in range(how_many):
        workout = WorkoutSession(user_id=user.id, name="Past", completed=True,
                                 date_performed=start + timedelta(days=day))
        for position, exercise in enumerate(exercises, start=1):
            item = WorkoutSessionExercise(exercise_id=exercise.id, order_index=position)
            for number in range(1, sets_each + 1):
                item.sets.append(SetEntry(set_number=number, weight=100, reps=8))
            workout.items.append(item)
        db.session.add(workout)


def history_queries(client):
    db.session.expire_all()  # start from an empty cache, like a real request
    with count_queries() as counter:
        page = client.get("/sessions/")
    assert page.status_code == 200
    return counter["queries"], page


def make_user_and_exercises(n):
    user = User(username="me", password_hash="unused")
    exercises = [
        Exercise(name=f"Exercise {i}", muscle_group="Chest", equipment_type="Barbell",
                 movement_type="Compound", difficulty="Beginner")
        for i in range(n)
    ]
    db.session.add(user)
    db.session.add_all(exercises)
    db.session.flush()
    return user, exercises


def test_history_query_count_does_not_grow_with_history(client, app):
    user, exercises = make_user_and_exercises(3)
    add_past_workouts(user, exercises, how_many=2, start=date(2026, 1, 1))
    db.session.commit()
    sign_in(client, user)

    with_little_history, _ = history_queries(client)
    add_past_workouts(user, exercises, how_many=20, start=date(2026, 2, 1))
    db.session.commit()
    with_more_history, _ = history_queries(client)

    assert with_more_history == with_little_history


def test_history_still_shows_exercise_and_set_counts(client, app):
    user, exercises = make_user_and_exercises(2)
    add_past_workouts(user, exercises, how_many=1, start=date(2026, 1, 1), sets_each=4)
    db.session.commit()
    sign_in(client, user)

    _, page = history_queries(client)
    assert b"2 exercises" in page.data
    assert b"8 sets" in page.data
