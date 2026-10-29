"""Tests for workout templates (FR-14 to FR-18, FR-13, FR-36, NFR-3)."""
import pytest

from app.exercises.seed import seed_exercises
from app.extensions import db
from app.models import Exercise, User, WorkoutTemplate, WorkoutTemplateExercise


# ---------- helpers ----------

def sign_up(client, username="olivia", password="strongpass1"):
    client.post("/auth/register", data={
        "username": username, "password": password, "confirm_password": password,
    })


def log_out(client):
    client.post("/auth/logout")


def create_template(client, name="Push Day", difficulty="Intermediate", description="Chest and arms"):
    return client.post("/templates/new",
                       data={"name": name, "difficulty": difficulty, "description": description},
                       follow_redirects=True)


def get_template(name="Push Day"):
    return db.session.execute(
        db.select(WorkoutTemplate).where(WorkoutTemplate.name == name)
    ).scalar_one_or_none()


def exercise_id(name):
    return db.session.execute(db.select(Exercise.id).where(Exercise.name == name)).scalar_one()


def add_exercise(client, template, name="Barbell Bench Press", sets=3, low=8, high=12):
    return client.post(f"/templates/{template.id}/exercises",
                       data={"exercise_id": exercise_id(name), "target_sets": sets,
                             "rep_range_min": low, "rep_range_max": high},
                       follow_redirects=True)


def item_names(template):
    """The template's exercise names in saved order, read fresh from the database."""
    db.session.expire_all()
    return [item.exercise.name for item in get_template(template.name).items]


def count(model):
    return db.session.execute(db.select(db.func.count(model.id))).scalar()


@pytest.fixture(autouse=True)
def seeded(app):
    seed_exercises()


# ---------- creating and listing (FR-14, FR-16) ----------

def test_template_pages_require_login(client):
    for url in ["/templates/", "/templates/new"]:
        response = client.get(url)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


def test_create_template(client):
    sign_up(client)
    response = create_template(client)
    assert b"Created Push Day" in response.data
    template = get_template()
    assert template.user_id == User.find_by_username("olivia").id
    assert template.difficulty == "Intermediate"
    assert template.description == "Chest and arms"
    assert template.is_public is False  # new templates are private (FR-20)


def test_template_needs_name_and_difficulty(client):
    sign_up(client)
    response = client.post("/templates/new", data={"name": "  ", "difficulty": "", "description": ""})
    assert b"This field is required." in response.data
    assert b"Choose a difficulty." in response.data
    assert count(WorkoutTemplate) == 0


def test_list_shows_only_my_templates(client):
    sign_up(client, "olivia")
    create_template(client, name="Olivia Legs")
    log_out(client)
    sign_up(client, "brendan")
    create_template(client, name="Brendan Push")

    response = client.get("/templates/")
    assert b"Brendan Push" in response.data
    assert b"Olivia Legs" not in response.data


def test_empty_list_explains_templates(client):
    sign_up(client)
    assert b"Create your first template" in client.get("/templates/").data


# ---------- adding exercises (FR-15) ----------

def test_add_exercises_in_order(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    add_exercise(client, template, "Barbell Bench Press", sets=4, low=6, high=8)
    response = add_exercise(client, template, "Triceps Pushdown", sets=3, low=10, high=15)

    assert b"Exercise added." in response.data
    assert b"4 sets \xc3\x97 6-8 reps" in response.data  # \xc3\x97 is the "×" sign
    assert item_names(template) == ["Barbell Bench Press", "Triceps Pushdown"]
    assert [i.order_index for i in get_template().items] == [1, 2]


def test_can_add_own_custom_exercise(client):
    sign_up(client)
    client.post("/exercises/new", data={
        "name": "Sled Push", "muscle_group": "Full Body", "equipment_type": "Other",
        "movement_type": "Compound", "difficulty": "Intermediate", "instructions": "",
    })
    create_template(client)
    add_exercise(client, get_template(), "Sled Push")
    assert item_names(get_template()) == ["Sled Push"]


def test_cannot_add_another_users_custom_exercise(client):
    sign_up(client, "olivia")
    client.post("/exercises/new", data={
        "name": "Secret Lift", "muscle_group": "Back", "equipment_type": "Other",
        "movement_type": "Compound", "difficulty": "Beginner", "instructions": "",
    })
    log_out(client)
    sign_up(client, "brendan")
    create_template(client)
    response = add_exercise(client, get_template(), "Secret Lift")
    assert b"Not a valid choice" in response.data
    assert count(WorkoutTemplateExercise) == 0


def test_archived_exercise_is_not_offered_but_stays_in_template(client):
    """FR-13: archived exercises can't be added, but templates that have one still show it."""
    sign_up(client)
    client.post("/exercises/new", data={
        "name": "Sled Push", "muscle_group": "Full Body", "equipment_type": "Other",
        "movement_type": "Compound", "difficulty": "Intermediate", "instructions": "",
    })
    create_template(client)
    template = get_template()
    add_exercise(client, template, "Sled Push")
    client.post(f"/exercises/{exercise_id('Sled Push')}/archive")

    page = client.get(f"/templates/{template.id}").data
    assert b"Sled Push" in page and b"Archived" in page              # still in the template
    assert b"Sled Push (Full Body" not in page                       # but not in the drop-down
    response = add_exercise(client, template, "Sled Push")
    assert b"Not a valid choice" in response.data
    assert count(WorkoutTemplateExercise) == 1


@pytest.mark.parametrize("sets, low, high, message", [
    (0, 8, 12, b"Sets must be a whole number from 1 to 20."),
    (21, 8, 12, b"Sets must be a whole number from 1 to 20."),
    (3, 0, 12, b"Reps must be a whole number from 1 to 100."),
    (3, 8, 101, b"Reps must be a whole number from 1 to 100."),
    (3, 12, 8, b"Max reps can&#39;t be less than min reps."),
    ("2.5", 8, 12, b"Not a valid integer value."),
    ("", 8, 12, b"Enter the number of sets."),
])
def test_bad_numbers_are_rejected(client, sets, low, high, message):
    sign_up(client)
    create_template(client)
    template = get_template()
    response = client.post(f"/templates/{template.id}/exercises", data={
        "exercise_id": exercise_id("Plank"), "target_sets": sets,
        "rep_range_min": low, "rep_range_max": high,
    })
    assert response.status_code == 200
    assert message in response.data
    assert count(WorkoutTemplateExercise) == 0


def test_same_min_and_max_reps_is_allowed(client):
    sign_up(client)
    create_template(client)
    response = add_exercise(client, get_template(), "Deadlift", sets=5, low=5, high=5)
    assert b"5 sets \xc3\x97 5 reps" in response.data


def test_must_choose_an_exercise(client):
    sign_up(client)
    create_template(client)
    response = client.post(f"/templates/{get_template().id}/exercises", data={
        "exercise_id": "", "target_sets": 3, "rep_range_min": 8, "rep_range_max": 12,
    })
    assert b"Choose an exercise." in response.data


# ---------- editing, reordering, removing (FR-17) ----------

def test_edit_template_details(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    response = client.post(f"/templates/{template.id}/edit",
                           data={"name": "Push Day A", "difficulty": "Advanced", "description": ""},
                           follow_redirects=True)
    assert b"Template updated." in response.data
    edited = get_template("Push Day A")
    assert edited.difficulty == "Advanced"
    assert edited.description is None


def test_edit_exercise_targets(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    add_exercise(client, template)
    item = template.items[0]
    assert b'value="3"' in client.get(f"/templates/{template.id}/exercises/{item.id}/edit").data

    response = client.post(f"/templates/{template.id}/exercises/{item.id}/edit",
                           data={"target_sets": 5, "rep_range_min": 3, "rep_range_max": 5},
                           follow_redirects=True)
    assert b"5 sets \xc3\x97 3-5 reps" in response.data


def test_move_exercise_up_and_down(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    for name in ["Barbell Bench Press", "Incline Dumbbell Press", "Triceps Pushdown"]:
        add_exercise(client, template, name)
    pushdown = get_template().items[2]

    client.post(f"/templates/{template.id}/exercises/{pushdown.id}/move", data={"direction": "up"})
    assert item_names(template) == ["Barbell Bench Press", "Triceps Pushdown", "Incline Dumbbell Press"]

    client.post(f"/templates/{template.id}/exercises/{pushdown.id}/move", data={"direction": "up"})
    client.post(f"/templates/{template.id}/exercises/{pushdown.id}/move", data={"direction": "up"})  # already first
    assert item_names(template) == ["Triceps Pushdown", "Barbell Bench Press", "Incline Dumbbell Press"]

    client.post(f"/templates/{template.id}/exercises/{pushdown.id}/move", data={"direction": "down"})
    assert item_names(template) == ["Barbell Bench Press", "Triceps Pushdown", "Incline Dumbbell Press"]
    assert [i.order_index for i in get_template().items] == [1, 2, 3]


def test_move_needs_a_valid_direction(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    add_exercise(client, template)
    item = get_template().items[0]
    response = client.post(f"/templates/{template.id}/exercises/{item.id}/move", data={"direction": "left"})
    assert response.status_code == 400


def test_remove_exercise_renumbers_the_rest(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    for name in ["Barbell Bench Press", "Incline Dumbbell Press", "Triceps Pushdown"]:
        add_exercise(client, template, name)
    middle = get_template().items[1]

    response = client.post(f"/templates/{template.id}/exercises/{middle.id}/remove", follow_redirects=True)
    assert b"Removed Incline Dumbbell Press." in response.data
    assert item_names(template) == ["Barbell Bench Press", "Triceps Pushdown"]
    assert [i.order_index for i in get_template().items] == [1, 2]
    assert db.session.get(Exercise, exercise_id("Incline Dumbbell Press")) is not None  # still in the library


def test_changing_pages_only_accept_post(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    add_exercise(client, template)
    item = get_template().items[0]
    for action in ["remove", "move"]:
        assert client.get(f"/templates/{template.id}/exercises/{item.id}/{action}").status_code == 405


# ---------- deleting (FR-18) ----------

def test_delete_asks_first_then_deletes(client):
    sign_up(client)
    create_template(client)
    template = get_template()
    add_exercise(client, template)

    confirm = client.get(f"/templates/{template.id}/delete")
    assert b"Delete Push Day?" in confirm.data
    assert get_template() is not None  # just looking at the page deletes nothing

    response = client.post(f"/templates/{template.id}/delete", follow_redirects=True)
    assert b"Deleted Push Day." in response.data
    assert get_template() is None
    assert count(WorkoutTemplateExercise) == 0                    # its rows are gone
    assert count(Exercise) > 0                                    # the exercises are not


# ---------- privacy (NFR-3) ----------

def test_other_users_cannot_see_or_change_my_template(client):
    sign_up(client, "olivia")
    create_template(client)
    template = get_template()
    add_exercise(client, template)
    item_id = get_template().items[0].id
    log_out(client)

    sign_up(client, "brendan")
    base = f"/templates/{template.id}"
    assert client.get(base).status_code == 404
    assert client.get(f"{base}/edit").status_code == 404
    assert client.post(f"{base}/edit", data={"name": "Hacked", "difficulty": "Beginner"}).status_code == 404
    assert client.post(f"{base}/delete").status_code == 404
    assert client.post(f"{base}/exercises", data={
        "exercise_id": exercise_id("Plank"), "target_sets": 3, "rep_range_min": 8, "rep_range_max": 12,
    }).status_code == 404
    assert client.post(f"{base}/exercises/{item_id}/remove").status_code == 404
    assert client.post(f"{base}/exercises/{item_id}/move", data={"direction": "down"}).status_code == 404

    db.session.expire_all()
    assert get_template().name == "Push Day"
    assert len(get_template().items) == 1


def test_item_must_belong_to_the_template_in_the_address(client):
    """Using my own template's address with an exercise row from a different template gives 404."""
    sign_up(client)
    create_template(client, name="A")
    create_template(client, name="B")
    add_exercise(client, get_template("B"))
    b_item = get_template("B").items[0]
    a = get_template("A")
    assert client.post(f"/templates/{a.id}/exercises/{b_item.id}/remove").status_code == 404
    assert client.get(f"/templates/{a.id}/exercises/{b_item.id}/edit").status_code == 404
