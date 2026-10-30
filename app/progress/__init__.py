"""The "progress" blueprint: a chart of how an exercise is going over time (FR-32)."""
from flask import Blueprint

bp = Blueprint("progress", __name__, url_prefix="/progress")

from app.progress import routes  # noqa: E402,F401
