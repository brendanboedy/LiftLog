"""The "main" blueprint: general pages that don't belong to a specific feature."""
from flask import Blueprint

bp = Blueprint("main", __name__)

# Imported at the bottom so the routes can use `bp` defined above.
from app.main import routes  # noqa: E402,F401
