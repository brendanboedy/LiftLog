"""Shared setup for the tests. pytest finds this file automatically."""
import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture
def app():
    """A fresh app with an empty in-memory database for each test."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A fake browser that can visit pages without starting the server."""
    return app.test_client()
