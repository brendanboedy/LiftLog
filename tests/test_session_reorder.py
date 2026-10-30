"""Tests for reordering exercises inside a workout (FR-26, FR-22, NFR-2, NFR-3)."""
from datetime import date

import pytest

from app.exercises.seed import seed_exercises
from app.extensions import db
from app.models import Exercise, WorkoutSession, WorkoutTemplate


# ---------- helpers ----------

def sign_up(client, username="olivia", password="strongpass1"):
    client.post("/auth/register", data={
        "username": username, "password": password, "confirm_password": password,
    })


def log_out(client):
    client.post("/auth/logout")


def exercise_id(name):
    return db.session.execute(db.select(Exercise.id).where(Exercise.name == name)).scalar_one()


def latest_session():
    """The newest session, read fresh from the database."""
    db.session.expire_all()
    return db.session.execute(
        db.select(WorkoutSession).order_by(WorkoutSession.id.desc()).limit(1)
    ).scalar_one()


def names(workout):
    return [item.exercise.name for item in workout.items]


def start_workout(client, exercises=("Barbell Bench Press", "Triceps Pushdown", "Plank")):
    """Start an empty workout and add the exercises to it in order."""
    client.post("/sessions/start")
    workout = latest_session()
    for name in exercises:
        client.post(f"/sessions/{workout.id}/exercises", data={"exercise_id": exercise_id(name)})
    return latest_session()


def move(client, workout, item, direction):
    return client.post(f"/sessions/{workout.id}/exercises/{item.id}/move", data={"direction": direction})


def log_set(client, workout, item, weight=135, reps=8):
    prefix = f"set{item.id}-"
    client.post(f"/sessions/{workout.id}/exercises/{item.id}/sets", data={
        prefix + "weight": weight, prefix + "reps": reps, prefix + "notes": "",
    })


@pytest.fixture(autouse=True)
def seeded(app):
    seed_exercises()


# ---------- login (NFR-3) ----------

def test_move_needs_login(client):
    response = client.post("/sessions/1/exercises/1/move", data={"direction": "up"})
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# ---------- moving (FR-26) ----------

def test_move_down_and_up(client):
    sign_up(client)
    workout = start_workout(client)
    first = workout.items[0]

    assert move(client, workout, first, "down").status_code == 302
    workout = latest_session()
    assert names(workout) == ["Triceps Pushdown", "Barbell Bench Press", "Plank"]
    assert [i.order_index for i in workout.items] == [1, 2, 3]

    move(client, workout, workout.items[2], "up")  # Plank up, past the bench press
    assert names(latest_session()) == ["Triceps Pushdown", "Plank", "Barbell Bench Press"]


def test_moving_past_the_ends_changes_nothing(client):
    sign_up(client)
    workout = start_workout(client)
    move(client, workout, workout.items[0], "up")
    move(client, workout, workout.items[2], "down")
    workout = latest_session()
    assert names(workout) == ["Barbell Bench Press", "Triceps Pushdown", "Plank"]
    assert [i.order_index for i in workout.items] == [1, 2, 3]


def test_sets_move_with_their_exercise(client):
    sign_up(client)
    workout = start_workout(client)
    bench, pushdown = workout.items[0], workout.items[1]
    log_set(client, workout, bench, weight=135, reps=8)
    log_set(client, workout, bench, weight=145, reps=6)
    log_set(client, workout, pushdown, weight=60, reps=12)

    move(client, workout, latest_session().items[0], "down")
    workout = latest_session()
    assert names(workout) == ["Triceps Pushdown", "Barbell Bench Press", "Plank"]
    assert [(s.weight, s.reps) for s in workout.items[0].sets] == [(60, 12)]
    assert [(s.weight, s.reps) for s in workout.items[1].sets] == [(135, 8), (145, 6)]
    assert [s.set_number for s in workout.items[1].sets] == [1, 2]


def test_new_order_shows_on_the_workout_page(client):
    sign_up(client)
    workout = start_workout(client)
    move(client, workout, workout.items[2], "up")
    page = client.get(f"/sessions/{workout.id}").data.decode()
    assert page.index("2. Plank") < page.index("3. Triceps Pushdown")


def test_first_and_last_buttons_are_disabled(client):
    sign_up(client)
    workout = start_workout(client)
    html = client.get(f"/sessions/{workout.id}").data.decode()
    assert 'disabled aria-label="Move Barbell Bench Press up"' in html
    assert 'disabled aria-label="Move Plank down"' in html
    assert 'disabled aria-label="Move Triceps Pushdown up"' not in html


def test_invalid_direction_is_rejected(client):
    sign_up(client)
    workout = start_workout(client)
    item = workout.items[0]
    for data in ({"direction": "sideways"}, {"direction": ""}, {}):
        response = client.post(f"/sessions/{workout.id}/exercises/{item.id}/move", data=data)
        assert response.status_code == 400
    assert names(latest_session()) == ["Barbell Bench Press", "Triceps Pushdown", "Plank"]


def test_move_only_accepts_post(client):
    sign_up(client)
    workout = start_workout(client)
    assert client.get(f"/sessions/{workout.id}/exercises/{workout.items[0].id}/move").status_code == 405


# ---------- the template is not changed (FR-26) ----------

def test_reordering_does_not_change_the_template(client):
    sign_up(client)
    client.post("/templates/new", data={"name": "Push Day", "difficulty": "Beginner", "description": ""})
    template = db.session.execute(db.select(WorkoutTemplate)).scalar_one()
    for name in ("Barbell Bench Press", "Triceps Pushdown"):
        client.post(f"/templates/{template.id}/exercises", data={
            "exercise_id": exercise_id(name), "target_sets": 3, "rep_range_min": 8, "rep_range_max": 12,
        })
    client.post("/sessions/start", data={"template_id": template.id})
    workout = latest_session()
    move(client, workout, workout.items[0], "down")

    assert names(latest_session()) == ["Triceps Pushdown", "Barbell Bench Press"]
    db.session.expire_all()
    template = db.session.execute(db.select(WorkoutTemplate)).scalar_one()
    assert [i.exercise.name for i in template.items] == ["Barbell Bench Press", "Triceps Pushdown"]
    assert latest_session().items[1].target_sets == 3  # the plan's targets travelled with the exercise


# ---------- who can move what (NFR-2) ----------

def test_cannot_reorder_a_finished_workout(client):
    sign_up(client)
    workout = start_workout(client)
    client.post(f"/sessions/{workout.id}/finish", data={
        "date_performed": date.today().isoformat(), "duration_minutes": 30, "energy_rating": 3, "notes": "",
    })
    response = move(client, workout, workout.items[0], "down")
    assert response.status_code == 400
    assert names(latest_session()) == ["Barbell Bench Press", "Triceps Pushdown", "Plank"]


def test_other_users_cannot_reorder_my_workout(client):
    sign_up(client, "olivia")
    workout = start_workout(client)
    item = workout.items[0]
    log_out(client)

    sign_up(client, "brendan")
    assert move(client, workout, item, "down").status_code == 404
    assert names(latest_session()) == ["Barbell Bench Press", "Triceps Pushdown", "Plank"]


def test_item_must_belong_to_the_workout_in_the_address(client):
    """My own workout's address with an exercise row from a different workout gives 404."""
    sign_up(client)
    first = start_workout(client)
    client.post(f"/sessions/{first.id}/finish", data={
        "date_performed": date.today().isoformat(), "duration_minutes": 30, "energy_rating": 3, "notes": "",
    })
    other_item = first.items[0]
    second = start_workout(client, exercises=("Plank", "Push-Up"))
    assert move(client, second, other_item, "down").status_code == 404
    assert names(latest_session()) == ["Plank", "Push-Up"]


def test_unknown_exercise_row_is_404(client):
    sign_up(client)
    workout = start_workout(client)
    response = client.post(f"/sessions/{workout.id}/exercises/99999/move", data={"direction": "up"})
    assert response.status_code == 404
