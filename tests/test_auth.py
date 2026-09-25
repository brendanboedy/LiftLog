"""Tests for registration, login and logout (issue #9: FR-1, FR-2, FR-3, FR-36, NFR-1, NFR-3, NFR-4)."""
from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import User


# ---------- helpers ----------

def register(client, username="olivia", password="strongpass1", confirm=None):
    return client.post(
        "/auth/register",
        data={"username": username, "password": password,
              "confirm_password": password if confirm is None else confirm},
        follow_redirects=True,
    )


def login(client, username="olivia", password="strongpass1", next_url=None):
    url = "/auth/login" + (f"?next={next_url}" if next_url else "")
    return client.post(url, data={"username": username, "password": password})


def logout(client):
    return client.post("/auth/logout", follow_redirects=True)


# ---------- registration (FR-1) ----------

def test_register_page_loads(client):
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Create your account" in response.data


def test_register_creates_user_and_logs_them_in(client):
    response = register(client)
    assert b"Your account was created" in response.data
    assert b"Hi, olivia!" in response.data  # landed on the dashboard, logged in
    assert User.find_by_username("olivia") is not None


def test_password_is_stored_hashed_not_plain_text(client):
    register(client, password="strongpass1")
    user = User.find_by_username("olivia")
    assert user.password_hash != "strongpass1"
    assert user.password_hash.startswith("$2")  # bcrypt hashes start with $2a$/$2b$
    assert user.check_password("strongpass1")
    assert not user.check_password("wrongpass1")


def test_duplicate_username_is_rejected_ignoring_case(client):
    register(client, username="olivia")
    logout(client)
    response = register(client, username="OLIVIA")
    assert b"That username is already taken." in response.data
    assert db.session.execute(db.select(db.func.count(User.id))).scalar() == 1


def test_passwords_must_match(client):
    response = register(client, password="strongpass1", confirm="different1")
    assert b"Passwords do not match." in response.data
    assert User.find_by_username("olivia") is None


def test_short_password_is_rejected(client):
    response = register(client, password="short")
    assert b"at least 8 characters" in response.data
    assert User.find_by_username("olivia") is None


def test_username_with_invalid_characters_is_rejected(client):
    response = register(client, username="bad name!")
    assert b"Use only letters, numbers" in response.data
    assert User.find_by_username("bad name!") is None


def test_empty_form_shows_required_errors(client):
    response = client.post("/auth/register", data={}, follow_redirects=True)
    assert b"This field is required." in response.data


# ---------- login (FR-2) ----------

def test_login_with_correct_password(client):
    register(client)
    logout(client)
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert client.get("/dashboard").status_code == 200


def test_login_with_wrong_password_shows_generic_error(client):
    register(client)
    logout(client)
    response = client.post("/auth/login", data={"username": "olivia", "password": "wrongpass1"})
    assert response.status_code == 200
    assert b"Incorrect username or password." in response.data


def test_login_with_unknown_username_shows_same_error(client):
    response = client.post("/auth/login", data={"username": "nobody", "password": "whatever1"})
    assert b"Incorrect username or password." in response.data


def test_login_returns_to_the_page_the_user_wanted(client):
    register(client)
    logout(client)
    response = login(client, next_url="/dashboard")
    assert response.headers["Location"].endswith("/dashboard")


def test_login_ignores_next_links_to_other_websites(client):
    register(client)
    logout(client)
    response = login(client, next_url="https://evil.example.com")
    assert "evil.example.com" not in response.headers["Location"]


# ---------- logout (FR-3) and private pages (NFR-3) ----------

def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_logout_ends_the_session(client):
    register(client)
    response = logout(client)
    assert b"You have been logged out." in response.data
    assert client.get("/dashboard").status_code == 302  # private page is locked again


def test_logout_only_accepts_post(client):
    register(client)
    assert client.get("/auth/logout").status_code == 405  # 405 = method not allowed


# ---------- CSRF protection (NFR-4) ----------

def test_forms_are_rejected_without_csrf_token():
    """With CSRF protection on (as in the real app), a form posted without its token is refused."""
    class CsrfOnConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfOnConfig)
    with app.app_context():
        db.create_all()
        response = app.test_client().post(
            "/auth/register",
            data={"username": "olivia", "password": "strongpass1", "confirm_password": "strongpass1"},
        )
        assert response.status_code == 400
        assert User.find_by_username("olivia") is None
        db.drop_all()
