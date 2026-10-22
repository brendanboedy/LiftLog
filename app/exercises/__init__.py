"""The "exercises" blueprint: the exercise library (FR-7 to FR-13)."""
from flask import Blueprint

# Every page here starts with /exercises, e.g. /exercises/new
bp = Blueprint("exercises", __name__, url_prefix="/exercises")

from app.exercises import routes  # noqa: E402,F401
