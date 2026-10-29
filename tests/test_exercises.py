"""Tests for the exercise library (FR-7 to FR-13, FR-36, NFR-3)."""
import pytest

from app.exercises.seed import seed_exercises
from app.exercises.seed_data import PREDEFINED_EXERCISES
from app.extensions import db
from app.models import DIFFICULTIES, EQUIPMENT_TYPES, MOVEMENT_TYPES, MUSCLE_GROUPS, Exercise, User


# ---------- helpers ----------

def sign_up(client, username="olivia", password="strongpass1"):
    """Register (which also logs in) as `username`."""
    client.post("/auth/register", data={
        "username": username, "password": password, "confirm_password": password,
    })


def log_out(client):
    client.post("/auth/logout")


GOOD_EXERCISE = {
    "name": "Zercher Squat",
    "muscle_group": "Quadriceps",
    "equipment_type": "Barbell",
    "movement_type": "Compound",
    "difficulty": "Advanced",
    "instructions": "Hold the bar in the crook of your elbows and squat.",
}


def create_exercise(client, **changes):
    return client.post("/exercises/new", data={**GOOD_EXERCISE, **changes}, follow_redirects=True)


def get_exercise(name):
    return db.session.execute(db.select(Exercise).where(Exercise.name == name)).scalar_one_or_none()


def exercise_count():
    return db.session.execute(db.select(db.func.count(Exercise.id))).scalar()


@pytest.fixture
def seeded(app):
    seed_exercises()


# ---------- predefined exercises (FR-7) ----------

def test_seed_data_is_valid():
    """Every predefined exercise uses allowed values, and names are unique."""
    names = [e["name"].lower() for e in PREDEFINED_EXERCISES]
    assert len(names) == len(set(names))
    for e in PREDEFINED_EXERCISES:
        assert e["muscle_group"] in MUSCLE_GROUPS, e["name"]
        assert e["equipment_type"] in EQUIPMENT_TYPES, e["name"]
        assert e["movement_type"] in MOVEMENT_TYPES, e["name"]
        assert e["difficulty"] in DIFFICULTIES, e["name"]
        assert e["instructions"], e["name"]


def test_seed_adds_predefined_exercises_once(app):
    assert seed_exercises() == (len(PREDEFINED_EXERCISES), 0)
    assert seed_exercises() == (0, 0)  # running it again adds nothing
    assert exercise_count() == len(PREDEFINED_EXERCISES)
    assert get_exercise("Barbell Bench Press").is_predefined


def test_seed_updates_changed_predefined_exercise(app):
    seed_exercises()
    get_exercise("Plank").difficulty = "Advanced"
    db.session.commit()
    assert seed_exercises() == (0, 1)
    assert get_exercise("Plank").difficulty == "Beginner"


def test_seed_command_runs(app):
    result = app.test_cli_runner().invoke(args=["seed-exercises"])
    assert "added" in result.output
    assert exercise_count() == len(PREDEFINED_EXERCISES)


# ---------- browsing and searching (FR-8, FR-9, FR-10) ----------

def test_exercise_pages_require_login(client, seeded):
    bench = get_exercise("Barbell Bench Press")
    for url in ["/exercises/", f"/exercises/{bench.id}", "/exercises/new"]:
        response = client.get(url)
        assert response.status_code == 302, url
        assert "/auth/login" in response.headers["Location"]


def test_list_shows_predefined_exercises(client, seeded):
    sign_up(client)
    response = client.get("/exercises/")
    assert response.status_code == 200
    assert b"Barbell Bench Press" in response.data
    assert b"Deadlift" in response.data


def test_search_by_name_ignores_case(client, seeded):
    sign_up(client)
    response = client.get("/exercises/?q=SQUAT")
    assert b"Barbell Back Squat" in response.data
    assert b"Goblet Squat" in response.data
    assert b"Barbell Bench Press" not in response.data


def test_search_treats_percent_sign_as_text(client, seeded):
    """A lone % must not act as a wildcard that matches everything."""
    sign_up(client)
    response = client.get("/exercises/?q=%25")  # %25 is "%" in a web address
    assert b"No exercises match" in response.data


def test_filter_by_muscle_group_and_equipment(client, seeded):
    sign_up(client)
    response = client.get("/exercises/?muscle_group=Back&equipment_type=Cable")
    assert b"Lat Pulldown" in response.data
    assert b"Seated Cable Row" in response.data
    assert b"Deadlift" not in response.data          # Back, but Barbell
    assert b"Cable Chest Fly" not in response.data   # Cable, but Chest


def test_unknown_filter_value_is_ignored(client, seeded):
    sign_up(client)
    response = client.get("/exercises/?muscle_group=Nonsense")
    assert response.status_code == 200
    assert b"Barbell Bench Press" in response.data


def test_detail_page_shows_all_details(client, seeded):
    sign_up(client)
    bench = get_exercise("Barbell Bench Press")
    response = client.get(f"/exercises/{bench.id}")
    assert response.status_code == 200
    for text in [b"Barbell Bench Press", b"Chest", b"Barbell", b"Compound", b"Intermediate", b"flat bench"]:
        assert text in response.data
    assert b"Edit" not in response.data  # predefined exercises can't be edited


def test_missing_exercise_is_404(client):
    sign_up(client)
    assert client.get("/exercises/9999").status_code == 404


# ---------- custom exercises (FR-11) ----------

def test_create_custom_exercise(client, seeded):
    sign_up(client)
    response = create_exercise(client)
    assert b"Added Zercher Squat to your exercises." in response.data
    exercise = get_exercise("Zercher Squat")
    assert exercise.created_by == User.find_by_username("olivia").id
    assert not exercise.is_predefined
    assert b"Zercher Squat" in client.get("/exercises/").data


def test_name_is_trimmed_and_instructions_are_optional(client):
    sign_up(client)
    create_exercise(client, name="  Sled Push  ", instructions="   ")
    exercise = get_exercise("Sled Push")
    assert exercise is not None
    assert exercise.instructions is None


def test_custom_exercise_is_private(client, seeded):
    sign_up(client, "olivia")
    create_exercise(client)
    exercise_id = get_exercise("Zercher Squat").id
    log_out(client)

    sign_up(client, "brendan")
    assert b"Zercher Squat" not in client.get("/exercises/").data
    assert b"Zercher Squat" not in client.get("/exercises/?q=zercher").data
    assert client.get(f"/exercises/{exercise_id}").status_code == 404


def test_two_users_can_use_the_same_custom_name(client):
    sign_up(client, "olivia")
    create_exercise(client)
    log_out(client)
    sign_up(client, "brendan")
    create_exercise(client)
    assert exercise_count() == 2


def test_required_fields_are_checked(client):
    sign_up(client)
    # A browser sends empty boxes and "Choose..." drop-downs as empty text.
    response = client.post("/exercises/new", data={field: "" for field in GOOD_EXERCISE})
    assert response.status_code == 200
    assert b"This field is required." in response.data   # name
    assert b"Choose a muscle group." in response.data
    assert b"Choose the equipment." in response.data
    assert exercise_count() == 0


def test_values_outside_the_lists_are_rejected(client):
    sign_up(client)
    response = create_exercise(client, muscle_group="Elbows")
    assert b"Not a valid choice" in response.data
    assert exercise_count() == 0


def test_too_long_name_is_rejected(client):
    sign_up(client)
    response = create_exercise(client, name="x" * 101)
    assert b"100 characters or fewer" in response.data
    assert exercise_count() == 0


def test_name_matching_a_predefined_exercise_is_rejected(client, seeded):
    sign_up(client)
    response = create_exercise(client, name="barbell bench press")
    assert b"already have an exercise with this name" in response.data
    assert exercise_count() == len(PREDEFINED_EXERCISES)


# ---------- editing (FR-12) ----------

def test_edit_own_custom_exercise(client):
    sign_up(client)
    create_exercise(client)
    exercise = get_exercise("Zercher Squat")
    page = client.get(f"/exercises/{exercise.id}/edit")
    assert b'value="Zercher Squat"' in page.data  # form starts filled in

    response = client.post(f"/exercises/{exercise.id}/edit",
                           data={**GOOD_EXERCISE, "difficulty": "Intermediate"},
                           follow_redirects=True)
    assert b"Exercise updated." in response.data
    assert get_exercise("Zercher Squat").difficulty == "Intermediate"  # same name is allowed


def test_cannot_edit_predefined_exercise(client, seeded):
    sign_up(client)
    bench = get_exercise("Barbell Bench Press")
    assert client.get(f"/exercises/{bench.id}/edit").status_code == 403
    response = client.post(f"/exercises/{bench.id}/edit", data={**GOOD_EXERCISE, "name": "Hacked"})
    assert response.status_code == 403
    assert get_exercise("Barbell Bench Press") is not None


def test_cannot_edit_another_users_exercise(client):
    sign_up(client, "olivia")
    create_exercise(client)
    exercise_id = get_exercise("Zercher Squat").id
    log_out(client)

    sign_up(client, "brendan")
    response = client.post(f"/exercises/{exercise_id}/edit", data={**GOOD_EXERCISE, "name": "Hacked"})
    assert response.status_code == 404
    assert get_exercise("Zercher Squat") is not None


# ---------- archiving (FR-13) ----------

def test_archive_hides_exercise_but_keeps_it(client):
    sign_up(client)
    create_exercise(client)
    exercise = get_exercise("Zercher Squat")

    response = client.post(f"/exercises/{exercise.id}/archive", follow_redirects=True)
    assert b"was archived" in response.data
    assert get_exercise("Zercher Squat").is_archived

    assert b"Zercher Squat" not in client.get("/exercises/").data            # hidden by default
    assert b"Zercher Squat" in client.get("/exercises/?archived=1").data     # shown when asked
    assert client.get(f"/exercises/{exercise.id}").status_code == 200        # detail still works


def test_restore_archived_exercise(client):
    sign_up(client)
    create_exercise(client)
    exercise = get_exercise("Zercher Squat")
    client.post(f"/exercises/{exercise.id}/archive")
    client.post(f"/exercises/{exercise.id}/restore")
    assert not get_exercise("Zercher Squat").is_archived
    assert b"Zercher Squat" in client.get("/exercises/").data


def test_archive_only_accepts_post(client):
    sign_up(client)
    create_exercise(client)
    exercise = get_exercise("Zercher Squat")
    assert client.get(f"/exercises/{exercise.id}/archive").status_code == 405


def test_cannot_archive_predefined_or_another_users_exercise(client, seeded):
    sign_up(client, "olivia")
    create_exercise(client)
    custom_id = get_exercise("Zercher Squat").id
    log_out(client)

    sign_up(client, "brendan")
    bench = get_exercise("Barbell Bench Press")
    assert client.post(f"/exercises/{bench.id}/archive").status_code == 403
    assert client.post(f"/exercises/{custom_id}/archive").status_code == 404
    assert not get_exercise("Barbell Bench Press").is_archived
    assert not get_exercise("Zercher Squat").is_archived
