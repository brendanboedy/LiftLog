"""Database tables, written as Python classes (SQLAlchemy "models").

Based on the team's ER model. Only the User table exists so far; Exercise,
WorkoutTemplate, WorkoutSession and the others will be added here as those
features are built.
"""
from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import bcrypt, db, login_manager


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """A LiftLog account (ER model: User).

    UserMixin gives Flask-Login what it needs (is_authenticated, get_id, ...).
    """

    # "user" is a reserved word in some databases, so the table is named "users".
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    # Only the bcrypt hash is stored - never the password itself (NFR-1).
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    # Profile fields from the ER model. Optional for now; the profile page
    # (FR-4, Increment 2) will let users fill them in.
    goal_type = db.Column(db.String(50))
    experience_level = db.Column(db.String(50))
    body_weight = db.Column(db.Float)

    def set_password(self, password):
        """Hash the password with bcrypt and store only the hash."""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        """True if `password` matches the stored hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    @staticmethod
    def find_by_username(username):
        """Look up a user, ignoring upper/lower case ("Olivia" == "olivia")."""
        return db.session.execute(
            db.select(User).where(db.func.lower(User.username) == username.strip().lower())
        ).scalar_one_or_none()

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on each request to get the logged-in user from their ID."""
    return db.session.get(User, int(user_id))
