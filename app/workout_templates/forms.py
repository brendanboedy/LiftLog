"""Forms for workout templates. Failed checks show a message next to the field (FR-36)."""
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError

from app.models import DIFFICULTIES, MAX_REPS, MAX_TARGET_SETS


def strip_spaces(value):
    return value.strip() if isinstance(value, str) else value


def int_or_none(value):
    """Turn the chosen drop-down value into a number; the empty "Choose..." option becomes None."""
    if value in ("", None):
        return None
    return int(value)


class TemplateForm(FlaskForm):
    """FR-14 / FR-17: a template's name, description and difficulty."""
    name = StringField(
        "Name",
        filters=[strip_spaces],
        validators=[DataRequired(), Length(max=100, message="Name must be 100 characters or fewer.")],
    )
    description = TextAreaField(
        "Description (optional)",
        filters=[strip_spaces],
        validators=[Optional(), Length(max=1000, message="Description must be 1000 characters or fewer.")],
    )
    difficulty = SelectField(
        "Difficulty",
        choices=[("", "Choose...")] + [(d, d) for d in DIFFICULTIES],
        validators=[DataRequired(message="Choose a difficulty.")],
    )
    submit = SubmitField("Save template")


class TargetsForm(FlaskForm):
    """FR-15 / FR-17: target sets and rep range for one exercise in a template."""
    target_sets = IntegerField(
        "Sets",
        default=3,
        validators=[
            InputRequired(message="Enter the number of sets."),
            NumberRange(min=1, max=MAX_TARGET_SETS,
                        message=f"Sets must be a whole number from 1 to {MAX_TARGET_SETS}."),
        ],
    )
    rep_range_min = IntegerField(
        "Min reps",
        default=8,
        validators=[
            InputRequired(message="Enter the minimum reps."),
            NumberRange(min=1, max=MAX_REPS, message=f"Reps must be a whole number from 1 to {MAX_REPS}."),
        ],
    )
    rep_range_max = IntegerField(
        "Max reps",
        default=12,
        validators=[
            InputRequired(message="Enter the maximum reps."),
            NumberRange(min=1, max=MAX_REPS, message=f"Reps must be a whole number from 1 to {MAX_REPS}."),
        ],
    )
    submit = SubmitField("Save")

    def validate_rep_range_max(self, field):
        """FR-36: the minimum can't be bigger than the maximum. Same number twice is fine (e.g. 5-5)."""
        low, high = self.rep_range_min.data, field.data
        if low is not None and high is not None and low > high:
            raise ValidationError("Max reps can't be less than min reps.")


class AddExerciseForm(TargetsForm):
    """FR-15: pick an exercise and its targets. The route fills in the choices
    with exercises the user can see that aren't archived (FR-13)."""
    exercise_id = SelectField(
        "Exercise",
        coerce=int_or_none,
        validators=[DataRequired(message="Choose an exercise.")],
    )
    submit = SubmitField("Add to template")
