"""Tests for the profile pages (FR-4, FR-5, FR-36, NFR-2, NFR-3)."""
from app.models import User


# ---------- helpers ----------

def sign_up(client, username="olivia", password="strongpass1"):
    client.post("/auth/register", data={
        "username": username, "password": password, "confirm_password": password,
    })


def log_out(client):
    client.post("/auth/logout")


def log_in(client, username="olivia", password="strongpass1"):
    return client.post("/auth/login", data={"username": username, "password": password})


FULL_PROFILE = {
    "goal_type": "Build muscle", "experience_level": "Intermediate",
    "body_weight": "180.5", "age": "25", "gender": "Female",
}


def save_profile(client, **changes):
    return client.post("/profile/", data={**FULL_PROFILE, **changes}, follow_redirects=True)


def change_password(client, current="strongpass1", new="newstrongpass2", confirm=None):
    return client.post("/profile/password", data={
        "current_password": current, "new_password": new,
        "confirm_password": new if confirm is None else confirm,
    }, follow_redirects=True)


# ---------- login required (NFR-3) ----------

def test_profile_pages_need_login(client):
    for url in ("/profile/", "/profile/password"):
        response = client.get(url)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


# ---------- view and update the profile (FR-4) ----------

def test_profile_page_shows_username_and_empty_fields(client):
    sign_up(client)
    response = client.get("/profile/")
    assert response.status_code == 200
    assert b"My profile" in response.data
    assert b"olivia" in response.data


def test_saving_profile_stores_every_field(client):
    sign_up(client)
    response = save_profile(client)
    assert b"Profile saved." in response.data
    user = User.find_by_username("olivia")
    assert user.goal_type == "Build muscle"
    assert user.experience_level == "Intermediate"
    assert user.body_weight == 180.5
    assert user.age == 25
    assert user.gender == "Female"


def test_profile_page_shows_saved_values(client):
    sign_up(client)
    save_profile(client)
    response = client.get("/profile/")
    assert b'value="180.5"' in response.data
    assert b'value="25"' in response.data
    assert b'<option selected value="Build muscle">' in response.data


def test_fields_can_be_cleared(client):
    sign_up(client)
    save_profile(client)
    save_profile(client, goal_type="", experience_level="", body_weight="", age="", gender="")
    user = User.find_by_username("olivia")
    assert (user.goal_type, user.experience_level, user.body_weight, user.age, user.gender) == \
        (None, None, None, None, None)


def test_invalid_profile_values_are_rejected(client):
    sign_up(client)
    cases = [
        ({"body_weight": "-5"}, b"Body weight must be from 1 to 1000 lb."),
        ({"body_weight": "nan"}, b"Enter the weight as a number."),
        ({"age": "12"}, b"Age must be a whole number from 13 to 100."),
        ({"age": "25.5"}, b"Not a valid integer value."),
        ({"goal_type": "Win the lottery"}, b"Not a valid choice."),
        ({"gender": "Robot"}, b"Not a valid choice."),
    ]
    for changes, message in cases:
        response = save_profile(client, **changes)
        assert message in response.data, changes
        assert b"Profile saved." not in response.data
    assert User.find_by_username("olivia").age is None  # nothing was saved


def test_saving_profile_only_changes_your_own_account(client):
    """NFR-2: the page has no user id in it; it always edits whoever is logged in."""
    sign_up(client, username="olivia")
    log_out(client)
    sign_up(client, username="brendan")
    save_profile(client)
    assert User.find_by_username("brendan").age == 25
    assert User.find_by_username("olivia").age is None


# ---------- change password (FR-5) ----------

def test_change_password_with_correct_current_password(client):
    sign_up(client)
    response = change_password(client)
    assert b"Your password was changed." in response.data
    log_out(client)
    assert log_in(client, password="strongpass1").status_code == 200  # old one no longer works
    assert log_in(client, password="newstrongpass2").status_code == 302


def test_wrong_current_password_is_rejected(client):
    sign_up(client)
    response = change_password(client, current="wrongpass1")
    assert b"Your current password is incorrect." in response.data
    assert User.find_by_username("olivia").check_password("strongpass1")


def test_new_password_rules_are_checked(client):
    sign_up(client)
    cases = [
        ({"new": "short"}, b"at least 8 characters"),
        ({"new": "newstrongpass2", "confirm": "different2"}, b"Passwords do not match."),
        ({"new": "a" * 73}, b"Password is too long"),
        ({"current": ""}, b"This field is required."),
    ]
    for kwargs, message in cases:
        response = change_password(client, **kwargs)
        assert message in response.data, kwargs
    assert User.find_by_username("olivia").check_password("strongpass1")


def test_new_password_is_stored_hashed(client):
    sign_up(client)
    change_password(client)
    user = User.find_by_username("olivia")
    assert user.password_hash != "newstrongpass2"
    assert user.password_hash.startswith("$2")


# ---------- navigation ----------

def test_username_in_nav_links_to_profile(client):
    sign_up(client)
    response = client.get("/dashboard")
    assert b'href="/profile/"' in response.data
