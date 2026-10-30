"""Forms for the profile pages. Failed checks show a message next to the field (FR-36)."""
from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional

from app.auth.forms import password_not_too_long
from app.models import EXPERIENCE_LEVELS, GENDERS, GOAL_TYPES, MAX_AGE, MAX_BODY_WEIGHT, MIN_AGE
from app.workout_sessions.forms import real_number


def optional_choices(options):
    return [("", "Not set")] + [(o, o) for o in options]


class ProfileForm(FlaskForm):
    """FR-4: goal, experience, body weight, age and gender. Every field is optional."""
    goal_type = SelectField("Goal", choices=optional_choices(GOAL_TYPES), validators=[Optional()])
    experience_level = SelectField(
        "Experience level", choices=optional_choices(EXPERIENCE_LEVELS), validators=[Optional()],
    )
    body_weight = FloatField(
        "Body weight in lb (optional)",
        validators=[
            Optional(),
            real_number,
            NumberRange(min=1, max=MAX_BODY_WEIGHT,
                        message=f"Body weight must be from 1 to {MAX_BODY_WEIGHT} lb."),
        ],
    )
    age = IntegerField(
        "Age (optional)",
        validators=[
            Optional(),
            NumberRange(min=MIN_AGE, max=MAX_AGE,
                        message=f"Age must be a whole number from {MIN_AGE} to {MAX_AGE}."),
        ],
    )
    gender = SelectField("Gender", choices=optional_choices(GENDERS), validators=[Optional()])
    submit = SubmitField("Save profile")


class ChangePasswordForm(FlaskForm):
    """FR-5: the current password must be re-entered before setting a new one."""
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters."),
            password_not_too_long,
        ],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords do not match.")],
    )
    submit = SubmitField("Change password")
