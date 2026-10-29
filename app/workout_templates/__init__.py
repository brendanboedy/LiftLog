"""The "workout_templates" blueprint: create and manage workout templates (FR-14 to FR-18).

(The folder isn't called "templates" because Flask already uses app/templates
for the HTML pages.)
"""
from flask import Blueprint

# Every page here starts with /templates, e.g. /templates/new
bp = Blueprint("workout_templates", __name__, url_prefix="/templates")

from app.workout_templates import routes  # noqa: E402,F401
