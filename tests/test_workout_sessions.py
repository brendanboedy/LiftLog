"""Tests for workout sessions (FR-22 to FR-31, FR-13, FR-36, NFR-3)."""
import re
from datetime import date, timedelta

import pytest

from app.exercises.seed import seed_exercises
from app.extensions import db
from app.models import (Exercise, SetEntry, WorkoutSession, WorkoutSessionExercise,
                        WorkoutTemplate, WorkoutTemplateExercise)


# ---------- helpers ----------

def sign_up(client, username="olivia", password="strongpass1"):
    client.post("/auth/register", data={
        "username": username, "password": password, "confirm_password": password,
    })


def log_out(client):
    client.post("/auth/logout")


def exercise_id(name):
    return db.session.execute(db.select(Exercise.id).where(Exercise.name == name)).scalar_one()


def get_template(name):
    return db.session.execute(
        db.select(WorkoutTemplate).where(WorkoutTemplate.name == name)
    ).scalar_one_or_none()


PUSH_DAY = [("Barbell Bench Press", 3, 8, 12), ("Triceps Pushdown", 3, 10, 15)]


def make_template(client, name="Push Day", exercises=PUSH_DAY):
    client.post("/templates/new", data={"name": name, "difficulty": "Beginner", "description": ""})
    template = get_template(name)
    for exercise, sets, low, high in exercises:
        client.post(f"/templates/{template.id}/exercises", data={
            "exercise_id": exercise_id(exercise), "target_sets": sets,
            "rep_range_min": low, "rep_range_max": high,
        })
    return template


def start(client, template=None):
    data = {"template_id": template.id} if template else {}
    return client.post("/sessions/start", data=data, follow_redirects=True)


def latest_session():
    """The newest session, read fresh from the database."""
    db.session.expire_all()
    return db.session.execute(
        db.select(WorkoutSession).order_by(WorkoutSession.id.desc()).limit(1)
    ).scalar_one_or_none()


def log_set(client, workout, item, weight=135, reps=8, notes=""):
    # Each exercise's form has its own prefix, e.g. "set3-weight".
    prefix = f"set{item.id}-"
    return client.post(f"/sessions/{workout.id}/exercises/{item.id}/sets", data={
        prefix + "weight": weight, prefix + "reps": reps, prefix + "notes": notes,
    }, follow_redirects=True)


def finish(client, workout, **changes):
    data = {"date_performed": date.today().isoformat(), "duration_minutes": 45,
            "energy_rating": 4, "notes": ""}
    data.update(changes)
    return client.post(f"/sessions/{workout.id}/finish", data=data, follow_redirects=True)


def count(model):
    return db.session.execute(db.select(db.func.count(model.id))).scalar()


@pytest.fixture(autouse=True)
def seeded(app):
    seed_exercises()


# ---------- starting (FR-22, FR-23) ----------

def test_session_pages_require_login(client):
    for response in [client.get("/sessions/"), client.post("/sessions/start")]:
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


def test_start_from_template_copies_its_exercises(client):
    sign_up(client)
    template = make_template(client)
    response = start(client, template)

    assert b"Started Push Day." in response.data
    assert b"Target: 3 \xc3\x97 8-12 reps" in response.data  # \xc3\x97 is the "x" sign
    workout = latest_session()
    assert workout.name == "Push Day"
    assert workout.template_id == template.id
    assert workout.completed is False
    assert [i.exercise.name for i in workout.items] == ["Barbell Bench Press", "Triceps Pushdown"]
    assert [i.order_index for i in workout.items] == [1, 2]


def test_changing_the_template_later_does_not_change_the_session(client):
    """FR-26: the session has its own copy of the exercises."""
    sign_up(client)
    template = make_template(client)
    start(client, template)
    first_row = get_template("Push Day").items[0]
    client.post(f"/templates/{template.id}/exercises/{first_row.id}/remove")

    assert len(get_template("Push Day").items) == 1
    assert len(latest_session().items) == 2


def test_start_empty_session_and_add_exercise(client):
    sign_up(client)
    response = start(client)
    assert b"Started Quick workout." in response.data
    workout = latest_session()
    assert workout.items == []

    response = client.post(f"/sessions/{workout.id}/exercises",
                           data={"exercise_id": exercise_id("Plank")}, follow_redirects=True)
    assert b"Exercise added." in response.data
    assert [i.exercise.name for i in latest_session().items] == ["Plank"]


def test_only_one_workout_in_progress_at_a_time(client):
    sign_up(client)
    start(client)
    response = start(client, make_template(client))
    assert b"Finish or cancel this workout before starting another one." in response.data
    assert count(WorkoutSession) == 1


def test_cannot_start_from_another_users_template(client):
    sign_up(client, "olivia")
    template = make_template(client)
    log_out(client)
    sign_up(client, "brendan")
    assert client.post("/sessions/start", data={"template_id": template.id}).status_code == 404
    assert client.post("/sessions/start", data={"template_id": "abc"}).status_code == 404
    assert count(WorkoutSession) == 0


def test_archived_exercise_is_not_offered_in_a_session(client):
    sign_up(client)
    client.post("/exercises/new", data={
        "name": "Sled Push", "muscle_group": "Full Body", "equipment_type": "Other",
        "movement_type": "Compound", "difficulty": "Intermediate", "instructions": "",
    })
    client.post(f"/exercises/{exercise_id('Sled Push')}/archive")
    start(client)
    workout = latest_session()
    assert b"Sled Push" not in client.get(f"/sessions/{workout.id}").data
    response = client.post(f"/sessions/{workout.id}/exercises", data={"exercise_id": exercise_id("Sled Push")})
    assert b"Not a valid choice" in response.data


def test_remove_exercise_from_session_only(client):
    sign_up(client)
    template = make_template(client)
    start(client, template)
    workout = latest_session()
    first = workout.items[0]
    log_set(client, workout, first)

    response = client.post(f"/sessions/{workout.id}/exercises/{first.id}/remove", follow_redirects=True)
    assert b"Removed Barbell Bench Press from this workout." in response.data
    workout = latest_session()
    assert [i.exercise.name for i in workout.items] == ["Triceps Pushdown"]
    assert workout.items[0].order_index == 1
    assert count(SetEntry) == 0                              # its sets went with it
    assert len(get_template("Push Day").items) == 2          # the template is unchanged


# ---------- logging sets (FR-24, FR-25) ----------

def test_log_sets(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    bench = workout.items[0]

    log_set(client, workout, bench, weight=135, reps=8)
    response = log_set(client, workout, bench, weight=145.5, reps=6, notes="felt heavy")

    sets = latest_session().items[0].sets
    assert [(s.set_number, s.weight, s.reps) for s in sets] == [(1, 135, 8), (2, 145.5, 6)]
    assert sets[1].notes == "felt heavy"
    assert b"145.5" in response.data
    assert b'value="145.5"' in response.data  # the next set's form starts with the last weight


def test_bodyweight_set_with_zero_weight_is_allowed(client):
    sign_up(client)
    start(client)
    workout = latest_session()
    client.post(f"/sessions/{workout.id}/exercises", data={"exercise_id": exercise_id("Pull-Up")})
    workout = latest_session()
    log_set(client, workout, workout.items[0], weight=0, reps=10)
    assert latest_session().items[0].sets[0].weight == 0


@pytest.mark.parametrize("weight, reps, message", [
    (-5, 8, b"Weight must be from 0 to 2000."),
    (2001, 8, b"Weight must be from 0 to 2000."),
    ("", 8, b"Enter the weight (0 for bodyweight)."),
    ("nan", 8, b"Enter the weight as a number."),
    ("heavy", 8, b"Not a valid float value."),
    (100, 0, b"Reps must be a whole number from 1 to 100."),
    (100, "8.5", b"Not a valid integer value."),
    (100, "", b"Enter the reps."),
])
def test_bad_set_values_are_rejected(client, weight, reps, message):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    response = log_set(client, workout, workout.items[0], weight=weight, reps=reps)
    assert response.status_code == 200
    assert message in response.data
    assert count(SetEntry) == 0


def test_edit_set(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    log_set(client, workout, workout.items[0], weight=135, reps=8)
    entry = latest_session().items[0].sets[0]

    assert b'value="135.0"' in client.get(f"/sessions/{workout.id}/sets/{entry.id}/edit").data
    response = client.post(f"/sessions/{workout.id}/sets/{entry.id}/edit",
                           data={"weight": 140, "reps": 7, "notes": ""}, follow_redirects=True)
    assert b"Set updated." in response.data
    entry = latest_session().items[0].sets[0]
    assert (entry.weight, entry.reps) == (140, 7)


def test_delete_set_renumbers_the_rest(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    bench = workout.items[0]
    for weight in [100, 110, 120]:
        log_set(client, workout, bench, weight=weight)
    middle = latest_session().items[0].sets[1]

    client.post(f"/sessions/{workout.id}/sets/{middle.id}/delete")
    sets = latest_session().items[0].sets
    assert [(s.set_number, s.weight) for s in sets] == [(1, 100), (2, 120)]


def test_set_must_belong_to_the_session_in_the_address(client):
    sign_up(client)
    start(client, make_template(client))
    first = latest_session()
    log_set(client, first, first.items[0])
    entry_id = latest_session().items[0].sets[0].id
    finish(client, first)  # finish it (the set still exists)...
    start(client)          # ...and start another
    second = latest_session()
    assert client.post(f"/sessions/{second.id}/sets/{entry_id}/delete").status_code == 404


# ---------- finishing (FR-27) ----------

def test_finish_page_suggests_a_duration(client):
    sign_up(client)
    start(client)
    page = client.get(f"/sessions/{latest_session().id}/finish")
    assert page.status_code == 200
    # Just started, so the suggested duration is 1 minute.
    assert re.search(rb'<input[^>]*name="duration_minutes"[^>]*value="1"', page.data)


def test_finish_workout(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    log_set(client, workout, workout.items[0])

    response = finish(client, workout, duration_minutes=50, energy_rating=4, notes="Good session")
    assert b"Workout saved." in response.data
    workout = latest_session()
    assert workout.completed is True
    assert workout.date_performed == date.today()
    assert (workout.duration_minutes, workout.energy_rating, workout.notes) == (50, 4, "Good session")
    assert b"50 min" in response.data and b"4 / 5" in response.data   # the summary page


def test_duration_and_energy_are_optional(client):
    sign_up(client)
    start(client)
    workout = latest_session()
    finish(client, workout, duration_minutes="", energy_rating="")
    workout = latest_session()
    assert workout.completed is True
    assert workout.duration_minutes is None and workout.energy_rating is None


@pytest.mark.parametrize("changes, message", [
    ({"date_performed": (date.today() + timedelta(days=1)).isoformat()}, b"The date can&#39;t be in the future."),
    ({"date_performed": ""}, b"Enter the date."),
    ({"duration_minutes": 0}, b"Duration must be a whole number from 1 to 600."),
    ({"energy_rating": 7}, b"Not a valid choice"),
])
def test_bad_finish_values_are_rejected(client, changes, message):
    sign_up(client)
    start(client)
    workout = latest_session()
    response = finish(client, workout, **changes)
    assert message in response.data
    assert latest_session().completed is False


def test_finished_workout_cannot_be_changed(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    item = workout.items[0]
    log_set(client, workout, item)
    entry_id = latest_session().items[0].sets[0].id
    finish(client, workout)

    prefix = f"set{item.id}-"
    assert client.post(f"/sessions/{workout.id}/exercises/{item.id}/sets",
                       data={prefix + "weight": 1, prefix + "reps": 1}).status_code == 400
    assert client.post(f"/sessions/{workout.id}/sets/{entry_id}/delete").status_code == 400
    assert client.post(f"/sessions/{workout.id}/exercises", data={"exercise_id": exercise_id("Plank")}).status_code == 400
    assert client.get(f"/sessions/{workout.id}/finish").status_code == 400
    assert count(SetEntry) == 1


def test_can_start_a_new_workout_after_finishing(client):
    sign_up(client)
    start(client)
    finish(client, latest_session())
    start(client)
    assert count(WorkoutSession) == 2


# ---------- history (FR-29, FR-30) ----------

def test_history_is_newest_first_and_only_completed(client):
    sign_up(client)
    for name, days_ago in [("Alpha Day", 10), ("Bravo Day", 2), ("Charlie Day", 5)]:
        start(client, make_template(client, name=name))
        finish(client, latest_session(), date_performed=(date.today() - timedelta(days=days_ago)).isoformat())
    start(client, make_template(client, name="Delta Day"))  # still in progress

    page = client.get("/sessions/").data
    assert page.index(b"Bravo Day") < page.index(b"Charlie Day") < page.index(b"Alpha Day")
    assert b"Completed workouts" in page
    assert b"Delta Day</strong> is in progress" in page   # shown as the active workout, not in the list
    assert page.count(b"Delta Day") == 1


def test_past_session_shows_every_set(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    bench, pushdown = workout.items
    log_set(client, workout, bench, weight=135, reps=8)
    log_set(client, workout, pushdown, weight=50, reps=12, notes="rope")
    finish(client, workout)

    page = client.get(f"/sessions/{workout.id}").data
    for text in [b"Barbell Bench Press", b"Triceps Pushdown", b"135", b"50", b"12", b"rope", b"Push Day"]:
        assert text in page


def test_history_does_not_show_other_users_sessions(client):
    sign_up(client, "olivia")
    start(client, make_template(client, name="Olivia Legs"))
    finish(client, latest_session())
    log_out(client)
    sign_up(client, "brendan")
    assert b"Olivia Legs" not in client.get("/sessions/").data


# ---------- cancelling and deleting (FR-28, FR-31, FR-18) ----------

def test_cancel_in_progress_workout(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    log_set(client, workout, workout.items[0])

    confirm = client.get(f"/sessions/{workout.id}/delete")
    assert b"Cancel Push Day?" in confirm.data
    assert count(WorkoutSession) == 1  # just looking deletes nothing

    response = client.post(f"/sessions/{workout.id}/delete", follow_redirects=True)
    assert b"Workout cancelled." in response.data
    assert count(WorkoutSession) == 0
    assert count(WorkoutSessionExercise) == 0 and count(SetEntry) == 0
    assert get_template("Push Day") is not None


def test_delete_completed_workout(client):
    sign_up(client)
    start(client, make_template(client))
    workout = latest_session()
    log_set(client, workout, workout.items[0])
    finish(client, workout)

    assert b"Delete Push Day?" in client.get(f"/sessions/{workout.id}/delete").data
    response = client.post(f"/sessions/{workout.id}/delete", follow_redirects=True)
    assert b"Workout deleted." in response.data
    assert count(WorkoutSession) == 0 and count(SetEntry) == 0
    assert count(WorkoutTemplateExercise) == 2  # the template still has its exercises


def test_deleting_a_template_keeps_its_past_sessions(client):
    sign_up(client)
    template = make_template(client)
    start(client, template)
    workout = latest_session()
    log_set(client, workout, workout.items[0])
    finish(client, workout)

    client.post(f"/templates/{template.id}/delete")
    workout = latest_session()
    assert workout is not None
    assert workout.template_id is None
    assert workout.name == "Push Day"
    page = client.get(f"/sessions/{workout.id}")
    assert page.status_code == 200
    assert b"Barbell Bench Press" in page.data


# ---------- privacy (NFR-3) and dashboard ----------

def test_other_users_cannot_see_or_change_my_session(client):
    sign_up(client, "olivia")
    start(client, make_template(client))
    workout = latest_session()
    item = workout.items[0]
    log_set(client, workout, item)
    entry_id = latest_session().items[0].sets[0].id
    log_out(client)

    sign_up(client, "brendan")
    base = f"/sessions/{workout.id}"
    prefix = f"set{item.id}-"
    assert client.get(base).status_code == 404
    assert client.post(f"{base}/exercises/{item.id}/sets",
                       data={prefix + "weight": 1, prefix + "reps": 1}).status_code == 404
    assert client.post(f"{base}/sets/{entry_id}/delete").status_code == 404
    assert client.post(f"{base}/finish", data={"date_performed": date.today().isoformat()}).status_code == 404
    assert client.post(f"{base}/delete").status_code == 404
    assert count(SetEntry) == 1
    assert latest_session().completed is False


def test_dashboard_links_to_workout_in_progress(client):
    sign_up(client)
    assert b"Continue workout" not in client.get("/dashboard").data
    start(client)
    assert b"Continue workout" in client.get("/dashboard").data
