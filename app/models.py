"""Database tables, written as Python classes (SQLAlchemy "models").

Based on the team's ER model: User, Exercise, WorkoutTemplate,
WorkoutTemplateExercise, WorkoutSession, WorkoutSessionExercise and SetEntry.
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

    # Profile fields (FR-4). All optional; users fill them in on the profile page.
    # age and gender are not in the ER model: they were added because the AI
    # suggestions (FR-33) use them (open team decision on FR-4).
    goal_type = db.Column(db.String(50))
    experience_level = db.Column(db.String(50))
    body_weight = db.Column(db.Float)  # lb, like set weights
    age = db.Column(db.Integer)
    gender = db.Column(db.String(30))

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

# Choices for the profile page (FR-4).
GOAL_TYPES = ["Build muscle", "Get stronger", "Lose fat", "Improve endurance", "General fitness"]
EXPERIENCE_LEVELS = DIFFICULTIES
GENDERS = ["Female", "Male", "Non-binary", "Prefer not to say"]
MIN_AGE, MAX_AGE = 13, 100
MAX_BODY_WEIGHT = 1000  # lb


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

    Predefined templates (FR-19) work like predefined exercises: they have no
    owner (user_id is empty), every user can view them and start a session
    from them, and nobody can change them on the website. The team loads them
    with `flask --app run seed-templates`.
    """

    __tablename__ = "workout_templates"

    id = db.Column(db.Integer, primary_key=True)
    # Empty (NULL) = predefined.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_workout_templates_user_id_users"),
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

    @property
    def is_predefined(self):
        return self.user_id is None

    def is_owned_by(self, user):
        return self.user_id is not None and self.user_id == user.id

    def is_visible_to(self, user):
        """Everyone sees predefined templates; the user's own templates only they see."""
        return self.is_predefined or self.is_owned_by(user)

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


# Limits for what a user can record (FR-24, FR-27, FR-36).
MAX_WEIGHT = 2000          # the app doesn't convert units; the pages label weight as lb (team decision)
MAX_DURATION_MINUTES = 600
ENERGY_RATINGS = [1, 2, 3, 4, 5]  # 1 = exhausted, 5 = great (open team decision #5)


def as_utc(moment):
    """SQLite gives dates back without a time zone; treat those as UTC so times can be compared."""
    if moment is not None and moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


class WorkoutSession(db.Model):
    """One workout the user actually did, or is doing right now (ER model: WorkoutSession).

    A session copies its exercises from a template when it starts (FR-22), so
    editing or deleting the template later never changes this session (FR-26).
    If the template is deleted, template_id just becomes empty (open team
    decision #3) and the session keeps its own copy of the template's name.

    Not in the ER model (added so the pages make sense):
    - name: copy of the template's name ("Quick workout" for an empty session)
    - created_at: when the workout was started, used to suggest its duration
    """

    __tablename__ = "workout_sessions"
    __table_args__ = (
        db.CheckConstraint("energy_rating IS NULL OR energy_rating BETWEEN 1 AND 5",
                           name="ck_ws_energy_rating_range"),
        db.CheckConstraint("duration_minutes IS NULL OR duration_minutes >= 1",
                           name="ck_ws_duration_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE", name="fk_workout_sessions_user_id_users"),
        nullable=False,
        index=True,
    )
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_templates.id", ondelete="SET NULL",
                      name="fk_workout_sessions_template_id_workout_templates"),
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer)
    energy_rating = db.Column(db.Integer)
    # False while the workout is in progress; True once the user finishes it (FR-27).
    completed = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    # Filled in when the session is finished.
    date_performed = db.Column(db.Date)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    owner = db.relationship(
        "User",
        backref=db.backref("workout_sessions", cascade="all, delete-orphan"),
    )
    # No delete cascade here: deleting a template leaves its sessions alone
    # and SQLAlchemy sets their template_id to empty.
    template = db.relationship("WorkoutTemplate", backref=db.backref("sessions"))
    items = db.relationship(
        "WorkoutSessionExercise",
        back_populates="session",
        order_by="WorkoutSessionExercise.order_index",
        cascade="all, delete-orphan",
    )

    def is_owned_by(self, user):
        return self.user_id == user.id

    @property
    def set_count(self):
        return sum(len(item.sets) for item in self.items)

    def minutes_so_far(self):
        """Whole minutes since the session started (at least 1)."""
        elapsed = utc_now() - as_utc(self.created_at)
        return max(1, int(elapsed.total_seconds() // 60))

    def renumber(self):
        for position, item in enumerate(self.items, start=1):
            item.order_index = position

    @staticmethod
    def active_for(user):
        """The user's in-progress session, or None. A user has at most one at a time."""
        return db.session.execute(
            db.select(WorkoutSession)
            .where(WorkoutSession.user_id == user.id, WorkoutSession.completed.is_(False))
            .order_by(WorkoutSession.id.desc())
            .limit(1)
        ).scalar_one_or_none()

    def __repr__(self):
        return f"<WorkoutSession {self.id} {self.name}>"


class WorkoutSessionExercise(db.Model):
    """One exercise done in a session (ER model: WorkoutSessionExercise).

    target_sets / rep_range_* are copied from the template so the workout page
    can show what the plan was (not in the ER model; empty for exercises the
    user added during the workout).
    """

    __tablename__ = "workout_session_exercises"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_sessions.id", ondelete="CASCADE",
                      name="fk_wse_session_id_workout_sessions"),
        nullable=False,
        index=True,
    )
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("exercises.id", name="fk_wse_exercise_id_exercises"),
        nullable=False,
        index=True,
    )
    order_index = db.Column(db.Integer, nullable=False)
    target_sets = db.Column(db.Integer)
    rep_range_min = db.Column(db.Integer)
    rep_range_max = db.Column(db.Integer)

    session = db.relationship("WorkoutSession", back_populates="items")
    exercise = db.relationship("Exercise")
    sets = db.relationship(
        "SetEntry",
        back_populates="session_exercise",
        order_by="SetEntry.set_number",
        cascade="all, delete-orphan",
    )

    @property
    def target(self):
        """ "3 × 8-12", or None when there was no plan for this exercise."""
        if self.target_sets is None:
            return None
        if self.rep_range_min == self.rep_range_max:
            reps = str(self.rep_range_min)
        else:
            reps = f"{self.rep_range_min}-{self.rep_range_max}"
        return f"{self.target_sets} × {reps}"

    def renumber_sets(self):
        for number, entry in enumerate(self.sets, start=1):
            entry.set_number = number

    def __repr__(self):
        return f"<WorkoutSessionExercise {self.order_index}: {self.exercise_id}>"


class SetEntry(db.Model):
    """One set the user did: weight and reps (ER model: SetEntry)."""

    __tablename__ = "set_entries"
    __table_args__ = (
        db.CheckConstraint("set_number >= 1", name="ck_set_entries_set_number_positive"),
        db.CheckConstraint("weight >= 0", name="ck_set_entries_weight_not_negative"),
        db.CheckConstraint("reps >= 1", name="ck_set_entries_reps_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_exercise_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_session_exercises.id", ondelete="CASCADE",
                      name="fk_set_entries_session_exercise_id_workout_session_exercises"),
        nullable=False,
        index=True,
    )
    set_number = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)  # 0 for bodyweight exercises
    reps = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200))

    session_exercise = db.relationship("WorkoutSessionExercise", back_populates="sets")

    @property
    def weight_text(self):
        """135.0 -> "135", 22.5 -> "22.5"."""
        return f"{self.weight:g}"

    def __repr__(self):
        return f"<SetEntry {self.set_number}: {self.weight} x {self.reps}>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on each request to get the logged-in user from their ID."""
    return db.session.get(User, int(user_id))
