"""Builds the LiftLog Flask app.

create_app() is an "app factory": it makes a fresh app each time it's called.
run.py calls it to start the website, and the tests call it with TestConfig
to get a separate app with a throwaway database.
"""
import os

from flask import Flask

from app.config import Config
from app.extensions import bcrypt, csrf, db, migrate


def create_app(config_class=Config):
    # instance_relative_config puts local-only files (like the SQLite database)
    # in the "instance" folder, which .gitignore keeps out of GitHub.
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # If no DATABASE_URL was given, use a SQLite file in the instance folder.
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        os.makedirs(app.instance_path, exist_ok=True)
        db_path = os.path.join(app.instance_path, "liftlog.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    # Connect the add-ons to this app.
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)

    # Blueprints group related pages. Each feature (auth, exercises,
    # templates, sessions...) will get its own blueprint folder like app/main.
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
