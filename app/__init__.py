"""Builds the LiftLog Flask app.

create_app() is an "app factory": it makes a fresh app each time it's called.
run.py calls it to start the website, and the tests call it with TestConfig
to get a separate app with a throwaway database.
"""
import os

from flask import Flask

from app.config import Config
from app.extensions import bcrypt, csrf, db, login_manager, migrate


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
    # render_as_batch lets migrations change existing tables on SQLite too.
    migrate.init_app(app, db, render_as_batch=True)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Import the models so the database (and Flask-Migrate) knows about every table.
    from app import models  # noqa: F401

    # Blueprints group related pages. Each feature (auth, exercises,
    # templates, sessions...) will get its own blueprint folder like app/main.
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.exercises import bp as exercises_bp
    app.register_blueprint(exercises_bp)

    from app.workout_templates import bp as workout_templates_bp
    app.register_blueprint(workout_templates_bp)

    # Adds the `flask --app run seed-exercises` command (loads predefined exercises).
    from app.exercises.seed import seed_exercises_command
    app.cli.add_command(seed_exercises_command)

    return app
