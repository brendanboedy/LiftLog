"""Flask add-ons, created once here and connected to the app in create_app().

Keeping them in their own file lets any part of the app import them
(for example: `from app.extensions import db`) without circular imports.
"""
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()        # database access
migrate = Migrate()      # database table changes ("migrations")
bcrypt = Bcrypt()        # password hashing
csrf = CSRFProtect()     # protects every form from cross-site request forgery

# Flask-Login is added with the login feature, because it needs the User model.
