"""Tests for public templates (FR-20, FR-21, FR-11, NFR-2, NFR-3)."""
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


def templates_named(name):
    db.session.expire_all()
    return db.session.execute(
        db.select(WorkoutTemplate).where(WorkoutTemplate.name == name).order_by(WorkoutTemplate.id)
    ).scalars().all()


def make_template(client, name="Push Day", exercises=(("Barbell Bench Press", 3, 8, 12),)):
    # follow_redirects shows (and so clears) the confirmation message, so it doesn't
    # stay in this browser's session when the next person logs in.
    client.post("/templates/new", data={"name": name, "difficulty": "Beginner",
                                        "description": "Chest day"}, follow_redirects=True)
    template = templates_named(name)[0]
    for exercise, sets, low, high in exercises:
        client.post(f"/templates/{template.id}/exercises", data={
            "exercise_id": exercise_id(exercise), "target_sets": sets,
            "rep_range_min": low, "rep_range_max": high,
        }, follow_redirects=True)
    return template


def make_custom_exercise(client, name="Zercher Squat"):
    client.post("/exercises/new", data={
        "name": name, "muscle_group": "Quadriceps", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Advanced", "instructions": "",
    }, follow_redirects=True)


def set_visibility(client, template, value):
    return client.post(f"/templates/{template.id}/visibility", data={"visibility": value},
                       follow_redirects=True)


@pytest.fixture(autouse=True)
def seeded(app):
    seed_exercises()


# ---------- login (NFR-3) ----------

def test_sharing_pages_need_login(client):
    for method, url in [("get", "/templates/public"), ("post", "/templates/1/visibility"),
                        ("post", "/templates/1/copy")]:
        response = getattr(client, method)(url)
        assert response.status_code == 302, url
        assert "/auth/login" in response.headers["Location"], url


# ---------- making public or private (FR-20) ----------

def test_new_templates_are_private(client):
    sign_up(client)
    template = make_template(client)
    assert template.is_public is False
    assert b"Make public" in client.get(f"/templates/{template.id}").data


def test_owner_can_make_template_public_and_private_again(client):
    sign_up(client)
    template = make_template(client)

    response = set_visibility(client, template, "public")
    assert b"is now public" in response.data
    assert b"Make private" in response.data
    assert templates_named("Push Day")[0].is_public is True

    response = set_visibility(client, template, "private")
    assert b"is now private" in response.data
    assert templates_named("Push Day")[0].is_public is False


def test_invalid_visibility_value_is_rejected(client):
    sign_up(client)
    template = make_template(client)
    assert client.post(f"/templates/{template.id}/visibility", data={"visibility": "everyone"}).status_code == 400
    assert client.post(f"/templates/{template.id}/visibility", data={}).status_code == 400
    assert templates_named("Push Day")[0].is_public is False


def test_only_the_owner_can_change_visibility(client):
    sign_up(client, "olivia")
    template = make_template(client)
    set_visibility(client, template, "public")
    log_out(client)

    sign_up(client, "brendan")
    assert client.post(f"/templates/{template.id}/visibility", data={"visibility": "private"}).status_code == 404
    assert templates_named("Push Day")[0].is_public is True


def test_own_list_marks_public_templates(client):
    sign_up(client)
    template = make_template(client)
    assert b"<span>Public</span>" not in client.get("/templates/").data
    set_visibility(client, template, "public")
    assert b"<span>Public</span>" in client.get("/templates/").data


# ---------- browsing (FR-21) ----------

def test_private_templates_are_never_listed_or_viewable_by_others(client):
    sign_up(client, "olivia")
    template = make_template(client, "Secret Plan")
    log_out(client)

    sign_up(client, "brendan")
    assert b"Secret Plan" not in client.get("/templates/public").data
    assert b"Secret Plan" not in client.get("/templates/").data
    assert client.get(f"/templates/{template.id}").status_code == 404


def test_public_templates_are_listed_with_their_creator(client):
    sign_up(client, "olivia")
    set_visibility(client, make_template(client, "Push Day"), "public")
    log_out(client)

    sign_up(client, "brendan")
    response = client.get("/templates/public")
    assert b"Push Day" in response.data
    assert b"by olivia" in response.data


def test_own_and_ready_made_templates_are_not_in_the_public_list(client):
    from app.workout_templates.seed import seed_templates
    seed_templates()
    sign_up(client, "olivia")
    set_visibility(client, make_template(client, "My Public One"), "public")
    response = client.get("/templates/public")
    assert b"My Public One" not in response.data   # already in my own list
    assert b"Full Body Beginner" not in response.data  # ready-made, has no owner
    assert b"Nobody has shared a template yet" in response.data


def test_public_template_page_is_view_only_for_others(client):
    sign_up(client, "olivia")
    template = make_template(client)
    set_visibility(client, template, "public")
    log_out(client)

    sign_up(client, "brendan")
    response = client.get(f"/templates/{template.id}")
    assert response.status_code == 200
    assert b"Barbell Bench Press" in response.data
    assert b"by olivia" in response.data
    assert b"Copy to my templates" in response.data
    assert b"Edit details" not in response.data
    assert b"Add an exercise" not in response.data
    assert b"Make private" not in response.data
    assert b"Start this workout" not in response.data


def test_others_cannot_change_a_public_template(client):
    """NFR-2: seeing a template does not allow changing it; the server refuses."""
    sign_up(client, "olivia")
    template = make_template(client)
    item_id = templates_named("Push Day")[0].items[0].id
    set_visibility(client, template, "public")
    log_out(client)

    sign_up(client, "brendan")
    base = f"/templates/{template.id}"
    assert client.get(f"{base}/edit").status_code == 404
    assert client.post(f"{base}/edit", data={"name": "Hacked", "difficulty": "Beginner"}).status_code == 404
    assert client.post(f"{base}/delete").status_code == 404
    assert client.post(f"{base}/exercises", data={
        "exercise_id": exercise_id("Plank"), "target_sets": 3, "rep_range_min": 8, "rep_range_max": 12,
    }).status_code == 404
    assert client.post(f"{base}/exercises/{item_id}/remove").status_code == 404
    assert client.post(f"{base}/exercises/{item_id}/move", data={"direction": "down"}).status_code == 404

    original = templates_named("Push Day")[0]
    assert original.name == "Push Day"
    assert len(original.items) == 1


def test_cannot_start_a_workout_from_someone_elses_public_template(client):
    sign_up(client, "olivia")
    template = make_template(client)
    set_visibility(client, template, "public")
    log_out(client)

    sign_up(client, "brendan")
    assert client.post("/sessions/start", data={"template_id": template.id}).status_code == 404
    assert db.session.execute(db.select(db.func.count(WorkoutSession.id))).scalar() == 0


def test_making_a_template_private_hides_it_again(client):
    sign_up(client, "olivia")
    template = make_template(client)
    set_visibility(client, template, "public")
    set_visibility(client, template, "private")
    log_out(client)

    sign_up(client, "brendan")
    assert b"Push Day" not in client.get("/templates/public").data
    assert client.get(f"/templates/{template.id}").status_code == 404


# ---------- copying (FR-21) ----------

def test_copy_makes_a_private_template_of_my_own(client):
    sign_up(client, "olivia")
    make_template(client, exercises=(("Barbell Bench Press", 4, 6, 10), ("Triceps Pushdown", 3, 10, 15)))
    original = templates_named("Push Day")[0]
    set_visibility(client, original, "public")
    log_out(client)

    sign_up(client, "brendan")
    response = client.post(f"/templates/{original.id}/copy", follow_redirects=True)
    assert b"Copied Push Day to your templates." in response.data
    assert b"Edit details" in response.data  # the copy is mine, so it can be edited

    copies = [t for t in templates_named("Push Day") if t.id != original.id]
    assert len(copies) == 1
    copy = copies[0]
    assert copy.owner.username == "brendan"
    assert copy.is_public is False
    assert copy.description == "Chest day"
    assert copy.difficulty == "Beginner"
    assert [(i.exercise.name, i.order_index, i.target_sets, i.rep_range_min, i.rep_range_max)
            for i in copy.items] == [("Barbell Bench Press", 1, 4, 6, 10), ("Triceps Pushdown", 2, 3, 10, 15)]
    assert b"Push Day" in client.get("/templates/").data


def test_copy_is_independent_of_the_original(client):
    sign_up(client, "olivia")
    original = make_template(client)
    set_visibility(client, original, "public")
    log_out(client)

    sign_up(client, "brendan")
    client.post(f"/templates/{original.id}/copy")
    copy = [t for t in templates_named("Push Day") if t.id != original.id][0]
    client.post(f"/templates/{copy.id}/edit", data={"name": "Brendan's Push", "difficulty": "Advanced"})
    client.post(f"/templates/{copy.id}/delete")
    log_out(client)

    sign_up(client, "carol")  # the original is untouched, and still copyable
    kept = templates_named("Push Day")[0]
    assert kept.id == original.id and len(kept.items) == 1
    assert client.get(f"/templates/{original.id}").status_code == 200


def test_copy_keeps_working_after_the_original_goes_private(client):
    sign_up(client, "olivia")
    original = make_template(client)
    set_visibility(client, original, "public")
    log_out(client)
    sign_up(client, "brendan")
    client.post(f"/templates/{original.id}/copy")
    log_out(client)
    log_in = client.post("/auth/login", data={"username": "olivia", "password": "strongpass1"})
    assert log_in.status_code == 302
    set_visibility(client, original, "private")
    log_out(client)

    client.post("/auth/login", data={"username": "brendan", "password": "strongpass1"})
    assert b"Push Day" in client.get("/templates/").data  # his copy is still his
    assert client.post(f"/templates/{original.id}/copy").status_code == 404  # but the original is closed


def test_copy_leaves_out_private_custom_exercises_and_says_so(client):
    sign_up(client, "olivia")
    make_custom_exercise(client, "Zercher Squat")
    original = make_template(client, exercises=(
        ("Barbell Bench Press", 3, 8, 12), ("Zercher Squat", 3, 5, 8), ("Plank", 3, 30, 60)))
    set_visibility(client, original, "public")
    log_out(client)

    sign_up(client, "brendan")
    page = client.get(f"/templates/{original.id}")
    assert b"Zercher Squat" in page.data   # the name is shown, as the owner chose to share the plan
    assert b"Custom" in page.data
    custom = db.session.execute(db.select(Exercise).where(Exercise.name == "Zercher Squat")).scalar_one()
    assert f"/exercises/{custom.id}".encode() not in page.data  # but there's no link to a page he can't open

    response = client.post(f"/templates/{original.id}/copy", follow_redirects=True)
    assert b"1 exercise left out because it is private to olivia." in response.data
    copy = [t for t in templates_named("Push Day") if t.id != original.id][0]
    assert [i.exercise.name for i in copy.items] == ["Barbell Bench Press", "Plank"]
    assert [i.order_index for i in copy.items] == [1, 2]  # no gap where the custom one was


def test_cannot_copy_private_own_ready_made_or_missing_templates(client):
    from app.workout_templates.seed import seed_templates
    seed_templates()
    sign_up(client, "olivia")
    private = make_template(client, "Private Plan")
    public = make_template(client, "Public Plan")
    set_visibility(client, public, "public")
    ready_made = templates_named("Full Body Beginner")[0]

    assert client.post(f"/templates/{public.id}/copy").status_code == 404      # my own
    assert client.post(f"/templates/{ready_made.id}/copy").status_code == 404  # has no owner
    assert client.post("/templates/99999/copy").status_code == 404
    log_out(client)

    sign_up(client, "brendan")
    assert client.post(f"/templates/{private.id}/copy").status_code == 404     # not shared
    assert len(templates_named("Private Plan")) == 1
    assert len(templates_named("Public Plan")) == 1


def test_copy_only_accepts_post(client):
    sign_up(client, "olivia")
    template = make_template(client)
    set_visibility(client, template, "public")
    log_out(client)
    sign_up(client, "brendan")
    assert client.get(f"/templates/{template.id}/copy").status_code == 405
    assert len(templates_named("Push Day")) == 1
