"""Tests for predefined workout templates (FR-19, FR-22, NFR-2)."""
import pytest

from app.exercises.seed import seed_exercises
from app.exercises.seed_data import PREDEFINED_EXERCISES
from app.extensions import db
from app.models import DIFFICULTIES, MAX_REPS, MAX_TARGET_SETS, WorkoutSession, WorkoutTemplate
from app.workout_templates.seed import seed_templates
from app.workout_templates.seed_data import PREDEFINED_TEMPLATES


# ---------- helpers ----------

def sign_up(client, username="olivia", password="strongpass1"):
    client.post("/auth/register", data={
        "username": username, "password": password, "confirm_password": password,
    })


def get_template(name):
    db.session.expire_all()
    return db.session.execute(
        db.select(WorkoutTemplate).where(WorkoutTemplate.name == name)
    ).scalar_one_or_none()


def template_count():
    return db.session.execute(db.select(db.func.count(WorkoutTemplate.id))).scalar()


@pytest.fixture
def seeded(app):
    seed_exercises()
    seed_templates()


# ---------- seed data and command ----------

def test_seed_data_is_valid():
    """Names are unique, values are allowed, and every exercise is a predefined one."""
    exercise_names = {e["name"] for e in PREDEFINED_EXERCISES}
    names = [t["name"].lower() for t in PREDEFINED_TEMPLATES]
    assert len(names) == len(set(names))
    for t in PREDEFINED_TEMPLATES:
        assert t["difficulty"] in DIFFICULTIES, t["name"]
        assert t["exercises"], t["name"]
        for name, sets, low, high in t["exercises"]:
            assert name in exercise_names, (t["name"], name)
            assert 1 <= sets <= MAX_TARGET_SETS, (t["name"], name)
            assert 1 <= low <= high <= MAX_REPS, (t["name"], name)


def test_seed_adds_predefined_templates_once(app):
    seed_exercises()
    assert seed_templates() == (len(PREDEFINED_TEMPLATES), 0)
    assert seed_templates() == (0, 0)  # running it again adds nothing
    assert template_count() == len(PREDEFINED_TEMPLATES)
    push = get_template("Push Day")
    assert push.is_predefined
    assert [item.exercise.name for item in push.items][0] == "Barbell Bench Press"
    assert [item.order_index for item in push.items] == list(range(1, len(push.items) + 1))


def test_seed_puts_changed_template_back(app):
    seed_exercises()
    seed_templates()
    push = get_template("Push Day")
    push.difficulty = "Advanced"
    push.items[0].target_sets = 10
    db.session.commit()
    assert seed_templates() == (0, 1)
    push = get_template("Push Day")
    assert push.difficulty == "Intermediate"
    assert push.items[0].target_sets == 4
    assert len(push.items) == 5


def test_seed_needs_exercises_first(app):
    result = app.test_cli_runner().invoke(args=["seed-templates"])
    assert result.exit_code != 0
    assert "seed-exercises" in result.output
    assert template_count() == 0


def test_seed_command_runs(app):
    seed_exercises()
    result = app.test_cli_runner().invoke(args=["seed-templates"])
    assert result.exit_code == 0
    assert "added" in result.output
    assert template_count() == len(PREDEFINED_TEMPLATES)


# ---------- viewing (FR-19) ----------

def test_template_list_shows_predefined_templates(client, seeded):
    sign_up(client)
    response = client.get("/templates/")
    assert b"Ready-made templates" in response.data
    assert b"Full Body Beginner" in response.data
    assert b"You don't have any templates yet." in response.data  # own list is still empty


def test_predefined_template_page_is_view_only(client, seeded):
    sign_up(client)
    push = get_template("Push Day")
    response = client.get(f"/templates/{push.id}")
    assert response.status_code == 200
    assert b"Barbell Bench Press" in response.data
    assert b"Start this workout" in response.data
    assert b"Ready-made" in response.data
    assert b"Edit details" not in response.data
    assert b"Add an exercise" not in response.data
    assert b">Remove<" not in response.data


def test_nobody_can_change_a_predefined_template(client, seeded):
    """NFR-2: the server refuses, not just the page hiding the buttons."""
    sign_up(client)
    push = get_template("Push Day")
    item_id = push.items[0].id
    base = f"/templates/{push.id}"
    assert client.get(f"{base}/edit").status_code == 404
    assert client.post(f"{base}/edit", data={"name": "Mine", "difficulty": "Beginner"}).status_code == 404
    assert client.post(f"{base}/delete").status_code == 404
    assert client.post(f"{base}/exercises", data={
        "exercise_id": push.items[0].exercise_id, "target_sets": 3, "rep_range_min": 8, "rep_range_max": 12,
    }).status_code == 404
    assert client.post(f"{base}/exercises/{item_id}/remove").status_code == 404
    assert client.post(f"{base}/exercises/{item_id}/move", data={"direction": "down"}).status_code == 404
    assert client.get(f"{base}/exercises/{item_id}/edit").status_code == 404

    push = get_template("Push Day")
    assert push.name == "Push Day"
    assert len(push.items) == 5


def test_predefined_template_page_needs_login(client, seeded):
    push = get_template("Push Day")
    response = client.get(f"/templates/{push.id}")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# ---------- starting a session (FR-22) ----------

def test_start_session_from_predefined_template(client, seeded):
    sign_up(client)
    push = get_template("Push Day")
    response = client.post("/sessions/start", data={"template_id": push.id}, follow_redirects=True)
    assert b"Started Push Day" in response.data
    workout = db.session.execute(db.select(WorkoutSession)).scalar_one()
    assert workout.template_id == push.id
    assert [i.exercise_id for i in workout.items] == [i.exercise_id for i in push.items]
    assert workout.items[0].target_sets == 4


def test_reseeding_does_not_change_started_sessions(client, seeded):
    """The session keeps its own copy of the exercises (FR-22, FR-26)."""
    sign_up(client)
    push = get_template("Push Day")
    client.post("/sessions/start", data={"template_id": push.id})
    push.items[0].target_sets = 10
    db.session.commit()
    seed_templates()
    workout = db.session.execute(db.select(WorkoutSession)).scalar_one()
    assert len(workout.items) == 5
    assert workout.items[0].target_sets == 4
