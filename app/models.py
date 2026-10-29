"""Database tables, written as Python classes (SQLAlchemy "models").

Based on the team's ER model. User, Exercise, WorkoutTemplate and
WorkoutTemplateExercise exist so far; WorkoutSession and the others will be added here as those
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


# Fixed lists of choices for exercise details. The forms and the search filters
# use these, so every exercise is labelled the same way and filtering works.
MUSCLE_GROUPS = [
    "Chest", "Back", "Shoulders", "Biceps", "Triceps", "Forearms", "Core",
    "Quadriceps", "Hamstrings", "Glutes", "Calves", "Full Body",
]
EQUIPMENT_TYPES = [
    "Barbell", "Dumbbell", "Machine", "Cable", "Bodyweight", "Kettlebell",
    "Resistance Band", "Other",
]
MOVEMENT_TYPES = ["Compound", "Isolation"]
DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]


class Exercise(db.Model):
    """One exercise, e.g. "Barbell Bench Press" (ER model: Exercise).

    Two kinds share this table:
    - predefined exercises, loaded by the team with `flask --app run seed-exercises`
      (created_by is empty) - every user sees these (FR-7, FR-8);
    - custom exercises a user made (created_by is that user's id) - only that
      user sees them (FR-11).

    created_by is not in the original ER model; it was added for FR-11
    (open team decision #2 in the RD).
    """

    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    muscle_group = db.Column(db.String(30), nullable=False)
    equipment_type = db.Column(db.String(30), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    instructions = db.Column(db.Text)
    # Archived exercises are hidden from the library and (later) from the
    # "add exercise" lists, but stay in old templates and sessions (FR-13).
    # We archive instead of deleting so past workouts never lose an exercise.
    is_archived = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    # Empty (NULL) = predefined. If the user's account is deleted, their
    # custom exercises go with it (FR-6).
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_exercises_created_by_users"),
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    owner = db.relationship(
        "User",
        backref=db.backref("custom_exercises", cascade="all, delete-orphan", passive_deletes=True),
    )

    @property
    def is_predefined(self):
        return self.created_by is None

    def is_owned_by(self, user):
        """True if `user` created this custom exercise."""
        return self.created_by is not None and self.created_by == user.id

    def is_visible_to(self, user):
        """Everyone sees predefined exercises; custom ones only their creator (FR-11)."""
        return self.is_predefined or self.is_owned_by(user)

    @staticmethod
    def visible_to(user):
        """A query for every exercise `user` may see. Add .where(...) to narrow it down."""
        return db.select(Exercise).where(
            db.or_(Exercise.created_by.is_(None), Exercise.created_by == user.id)
        )

    @staticmethod
    def name_taken(name, user, exclude_id=None):
        """True if `user` can already see an exercise with this name (ignoring case).

        Stops a user from making a custom "bench press" that looks identical
        to the predefined "Bench Press" in their lists.
        """
        query = Exercise.visible_to(user).where(
            db.func.lower(Exercise.name) == name.strip().lower()
        )
        if exclude_id is not None:
            query = query.where(Exercise.id != exclude_id)
        return db.session.execute(query.limit(1)).first() is not None

    def __repr__(self):
        return f"<Exercise {self.name}>"


# Limits for the numbers typed into a workout template (FR-15, FR-36).
MAX_TARGET_SETS = 20
MAX_REPS = 100


class WorkoutTemplate(db.Model):
    """A reusable workout plan, e.g. "Push Day" (ER model: WorkoutTemplate).

    A template is only the plan. When workout sessions are built, starting a
    session will copy the template's exercises, so later edits to the template
    never change past sessions (FR-22, FR-26).

    Not built yet: is_prebuilt / predefined templates (FR-19) - the ER model
    says every template has an owner who must exist, which doesn't fit
    templates that belong to no one, so the team needs to decide that first.
    """

    __tablename__ = "workout_templates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_workout_templates_user_id_users"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20), nullable=False)
    # In the ER model. New templates are private (FR-20); sharing comes later (FR-21).
    is_public = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    owner = db.relationship(
        "User",
        backref=db.backref("workout_templates", cascade="all, delete-orphan"),
    )
    # The template's exercises, always in their saved order. Deleting a
    # template also deletes these rows (ER model) - but never the exercises themselves.
    items = db.relationship(
        "WorkoutTemplateExercise",
        back_populates="template",
        order_by="WorkoutTemplateExercise.order_index",
        cascade="all, delete-orphan",
    )

    def is_owned_by(self, user):
        return self.user_id == user.id

    def renumber(self):
        """Number the exercises 1, 2, 3... with no gaps, in their current order."""
        for position, item in enumerate(self.items, start=1):
            item.order_index = position

    def __repr__(self):
        return f"<WorkoutTemplate {self.name}>"


class WorkoutTemplateExercise(db.Model):
    """One exercise inside a template, with its targets (ER model: WorkoutTemplateExercise).

    The same exercise may appear more than once in a template (for example a
    light warm-up and a heavy set of squats).
    """

    __tablename__ = "workout_template_exercises"
    # The database itself refuses impossible numbers, as a second line of
    # defence behind the form checks (FR-36).
    __table_args__ = (
        db.CheckConstraint("target_sets >= 1", name="ck_wte_target_sets_positive"),
        db.CheckConstraint("rep_range_min >= 1", name="ck_wte_rep_range_min_positive"),
        db.CheckConstraint("rep_range_min <= rep_range_max", name="ck_wte_rep_range_order"),
    )

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_templates.id", ondelete="CASCADE",
                      name="fk_wte_template_id_workout_templates"),
        nullable=False,
        index=True,
    )
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("exercises.id", name="fk_wte_exercise_id_exercises"),
        nullable=False,
        index=True,
    )
    # Position in the template: 1 is first. Kept gap-free by WorkoutTemplate.renumber().
    order_index = db.Column(db.Integer, nullable=False)
    target_sets = db.Column(db.Integer, nullable=False)
    rep_range_min = db.Column(db.Integer, nullable=False)
    rep_range_max = db.Column(db.Integer, nullable=False)

    template = db.relationship("WorkoutTemplate", back_populates="items")
    exercise = db.relationship("Exercise")

    @property
    def rep_range(self):
        """ "8-12", or just "10" when min and max are the same."""
        if self.rep_range_min == self.rep_range_max:
            return str(self.rep_range_min)
        return f"{self.rep_range_min}-{self.rep_range_max}"

    def __repr__(self):
        return f"<WorkoutTemplateExercise {self.order_index}: {self.exercise_id}>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on each request to get the logged-in user from their ID."""
    return db.session.get(User, int(user_id))
