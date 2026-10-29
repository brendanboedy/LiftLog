"""The "workout_sessions" blueprint: doing a workout and seeing past ones (FR-22 to FR-31).

(Not called "sessions" so it isn't confused with Flask's login `session`.)
"""
from flask import Blueprint

# Every page here starts with /sessions, e.g. /sessions/start
bp = Blueprint("workout_sessions", __name__, url_prefix="/sessions")

from app.workout_sessions import routes  # noqa: E402,F401
