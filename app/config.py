"""App settings.

Values come from environment variables (loaded from the .env file by run.py),
so passwords and keys stay out of the code and out of GitHub.
"""
import os
import secrets


class Config:
    # Used to sign login sessions and CSRF tokens. If .env doesn't set one,
    # a random key is made each time the app starts (fine for development,
    # but everyone gets logged out on restart).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Database location. None means "use the SQLite file" (set up in create_app).
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or None

    # Turn off a Flask-SQLAlchemy feature we don't use (saves memory).
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestConfig(Config):
    """Settings used by the automated tests."""
    TESTING = True
    SECRET_KEY = "test-secret-key"
    # A throwaway database that lives only in memory while tests run.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Tests submit forms directly, so skip the CSRF token check there.
    WTF_CSRF_ENABLED = False
