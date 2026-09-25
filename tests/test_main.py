"""Checks that the app starts and its basic pages work."""


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to LiftLog" in response.data


def test_health_check_reports_database_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_unknown_page_returns_404(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
