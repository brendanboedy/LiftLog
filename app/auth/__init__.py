"""The "auth" blueprint: register, log in and log out (FR-1, FR-2, FR-3)."""
from flask import Blueprint

# url_prefix means every page here starts with /auth, e.g. /auth/login
bp = Blueprint("auth", __name__, url_prefix="/auth")

from app.auth import routes  # noqa: E402,F401
