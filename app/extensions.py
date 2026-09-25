"""Flask add-ons, created once here and connected to the app in create_app().

Keeping them in their own file lets any part of the app import them
(for example: `from app.extensions import db`) without circular imports.
"""
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()             # database access
migrate = Migrate()           # database table changes ("migrations")
bcrypt = Bcrypt()             # password hashing
csrf = CSRFProtect()          # protects every form from cross-site request forgery
login_manager = LoginManager()  # remembers who is logged in

# Where Flask-Login sends people who try to open a page that needs a login.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to see that page."
login_manager.login_message_category = "info"
