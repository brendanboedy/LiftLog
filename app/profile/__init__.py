"""The "profile" blueprint: view and update your profile, change your password (FR-4, FR-5)."""
from flask import Blueprint

bp = Blueprint("profile", __name__, url_prefix="/profile")

from app.profile import routes  # noqa: E402,F401
