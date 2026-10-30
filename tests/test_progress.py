"""Tests for the progress chart (FR-32, FR-13, NFR-2, NFR-3)."""
import json
import re
from datetime import date, timedelta

import pytest

from app.exercises.seed import seed_exercises
from app.extensions import db
from app.models import Exercise, User, WorkoutSession
from app.progress.queries import exercise_progress, logged_exercises


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
    db.session.expire_all()
    return db.session.execute(
        db.select(WorkoutSession).order_by(WorkoutSession.id.desc()).limit(1)
    ).scalar_one()


def do_workout(client, sets_by_exercise, days_ago=0, finish=True, name="Quick workout"):
    """Start an empty workout, log sets and (by default) finish it.

    sets_by_exercise is {"Barbell Bench Press": [(weight, reps), ...], ...}.
    """
    client.post("/sessions/start")
    workout = latest_session()
    for exercise_name, sets in sets_by_exercise.items():
        client.post(f"/sessions/{workout.id}/exercises", data={"exercise_id": exercise_id(exercise_name)})
        db.session.expire_all()
        item = latest_session().items[-1]
        for weight, reps in sets:
            prefix = f"set{item.id}-"
            client.post(f"/sessions/{workout.id}/exercises/{item.id}/sets", data={
                prefix + "weight": weight, prefix + "reps": reps, prefix + "notes": "",
            })
    if finish:
        when = (date.today() - timedelta(days=days_ago)).isoformat()
        client.post(f"/sessions/{workout.id}/finish", data={
            "date_performed": when, "duration_minutes": 40, "energy_rating": 3, "notes": "",
        })
    return workout.id


def chart_points(response):
    """The numbers the page hands to the chart."""
    match = re.search(rb'<script id="progress-data" type="application/json">(.*?)</script>',
                      response.data, re.S)
    return json.loads(match.group(1))


BENCH = "Barbell Bench Press"


@pytest.fixture(autouse=True)
def seeded(app):
    seed_exercises()


# ---------- login (NFR-3) ----------

def test_progress_page_needs_login(client):
    response = client.get("/progress/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


# ---------- the numbers (FR-32) ----------

def test_progress_is_max_weight_and_volume_per_workout_oldest_first(client):
    sign_up(client)
    do_workout(client, {BENCH: [(135, 8), (155, 5), (145, 6)]}, days_ago=7)
    do_workout(client, {BENCH: [(145, 8), (165, 4)]}, days_ago=1)
    user = User.find_by_username("olivia")
    points = exercise_progress(user, exercise_id(BENCH))

    assert [p["date"] for p in points] == [
        (date.today() - timedelta(days=7)).isoformat(),
        (date.today() - timedelta(days=1)).isoformat(),
    ]
    assert points[0]["max_weight"] == 155
    assert points[0]["volume"] == 135 * 8 + 155 * 5 + 145 * 6   # 2725
    assert points[1]["max_weight"] == 165
    assert points[1]["volume"] == 145 * 8 + 165 * 4             # 1820


def test_only_the_chosen_exercise_is_counted(client):
    sign_up(client)
    do_workout(client, {BENCH: [(135, 8)], "Triceps Pushdown": [(60, 12)]})
    points = exercise_progress(User.find_by_username("olivia"), exercise_id(BENCH))
    assert len(points) == 1
    assert points[0]["volume"] == 135 * 8


def test_unfinished_workouts_are_not_counted(client):
    sign_up(client)
    do_workout(client, {BENCH: [(135, 8)]}, finish=False)
    user = User.find_by_username("olivia")
    assert exercise_progress(user, exercise_id(BENCH)) == []
    assert logged_exercises(user) == []


def test_exercise_added_twice_in_one_workout_is_combined(client):
    sign_up(client)
    client.post("/sessions/start")
    workout = latest_session()
    for weight in (100, 140):
        client.post(f"/sessions/{workout.id}/exercises", data={"exercise_id": exercise_id(BENCH)})
        db.session.expire_all()
        item = latest_session().items[-1]
        client.post(f"/sessions/{workout.id}/exercises/{item.id}/sets", data={
            f"set{item.id}-weight": weight, f"set{item.id}-reps": 5, f"set{item.id}-notes": "",
        })
    client.post(f"/sessions/{workout.id}/finish", data={
        "date_performed": date.today().isoformat(), "duration_minutes": 30, "energy_rating": 3, "notes": "",
    })
    points = exercise_progress(User.find_by_username("olivia"), exercise_id(BENCH))
    assert len(points) == 1
    assert points[0]["max_weight"] == 140
    assert points[0]["volume"] == 100 * 5 + 140 * 5


def test_bodyweight_sets_count_with_zero_volume(client):
    sign_up(client)
    do_workout(client, {"Push-Up": [(0, 20)]})
    points = exercise_progress(User.find_by_username("olivia"), exercise_id("Push-Up"))
    assert points[0]["max_weight"] == 0
    assert points[0]["volume"] == 0


def test_exercise_with_no_logged_sets_is_not_offered(client):
    sign_up(client)
    do_workout(client, {BENCH: []})  # added to the workout, but no sets recorded
    assert logged_exercises(User.find_by_username("olivia")) == []


# ---------- the page ----------

def test_page_with_no_history_says_so(client):
    sign_up(client)
    response = client.get("/progress/")
    assert response.status_code == 200
    assert b"Nothing to chart yet" in response.data
    assert b"<canvas" not in response.data


def test_picker_lists_only_logged_exercises_by_name(client):
    sign_up(client)
    do_workout(client, {"Plank": [(0, 1)], BENCH: [(135, 8)]})
    response = client.get("/progress/")
    html = response.data.decode()
    assert html.index("Barbell Bench Press</option>") < html.index("Plank</option>")
    assert "Deadlift</option>" not in html
    assert b"<canvas" not in response.data  # nothing chosen yet


def test_chosen_exercise_shows_chart_data_and_table(client):
    sign_up(client)
    do_workout(client, {BENCH: [(135, 8), (155, 5)]}, days_ago=3)
    response = client.get(f"/progress/?exercise_id={exercise_id(BENCH)}")
    assert response.status_code == 200
    assert b'id="weight-chart"' in response.data
    assert b'id="volume-chart"' in response.data
    points = chart_points(response)
    assert points == [{
        "date": (date.today() - timedelta(days=3)).isoformat(),
        "workout": "Quick workout", "max_weight": 155.0, "volume": 1855.0,
    }]
    assert b"<td>155</td>" in response.data  # the same numbers in the table


def test_unknown_or_bad_exercise_id_shows_no_chart(client):
    sign_up(client)
    do_workout(client, {BENCH: [(135, 8)]})
    for value in ["9999", "abc", "-1", ""]:
        response = client.get(f"/progress/?exercise_id={value}")
        assert response.status_code == 200, value
        assert b"<canvas" not in response.data, value
    assert b"nothing to chart" in client.get("/progress/?exercise_id=9999").data


def test_archived_custom_exercise_history_still_charts(client):
    sign_up(client)
    client.post("/exercises/new", data={
        "name": "Zercher Squat", "muscle_group": "Quadriceps", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Advanced", "instructions": "",
    })
    do_workout(client, {"Zercher Squat": [(185, 5)]})
    custom = db.session.execute(db.select(Exercise).where(Exercise.name == "Zercher Squat")).scalar_one()
    client.post(f"/exercises/{custom.id}/archive")
    response = client.get(f"/progress/?exercise_id={custom.id}")
    assert chart_points(response)[0]["max_weight"] == 185


# ---------- privacy (NFR-2) ----------

def test_other_users_data_is_never_included(client):
    sign_up(client, "olivia")
    do_workout(client, {BENCH: [(300, 1)]})
    log_out(client)

    sign_up(client, "brendan")
    do_workout(client, {BENCH: [(100, 10)]})
    response = client.get(f"/progress/?exercise_id={exercise_id(BENCH)}")
    points = chart_points(response)
    assert len(points) == 1
    assert points[0]["max_weight"] == 100
    assert b"300" not in response.data


def test_someone_elses_custom_exercise_is_not_chartable(client):
    sign_up(client, "olivia")
    # follow_redirects shows (and so clears) the "Added Secret Lift" message, which would otherwise
    # still be waiting in this browser's session when the next person logs in.
    client.post("/exercises/new", data={
        "name": "Secret Lift", "muscle_group": "Back", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Advanced", "instructions": "",
    }, follow_redirects=True)
    secret = db.session.execute(db.select(Exercise).where(Exercise.name == "Secret Lift")).scalar_one()
    do_workout(client, {"Secret Lift": [(200, 3)]})
    log_out(client)

    sign_up(client, "brendan")
    response = client.get(f"/progress/?exercise_id={secret.id}")
    assert response.status_code == 200
    assert b"Secret Lift" not in response.data
    assert b"<canvas" not in response.data


def test_progress_link_is_in_the_nav(client):
    sign_up(client)
    assert b'href="/progress/"' in client.get("/dashboard").data
