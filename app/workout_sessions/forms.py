"""Forms for workout sessions. Failed checks show a message next to the field (FR-36)."""
import math
from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError

from app.models import ENERGY_RATINGS, MAX_DURATION_MINUTES, MAX_REPS, MAX_WEIGHT
from app.workout_templates.forms import int_or_none, strip_spaces


def real_number(form, field):
    """Python accepts "nan" as a number; a weight has to be an actual number."""
    if field.data is not None and not math.isfinite(field.data):
        raise ValidationError("Enter the weight as a number.")


class SetForm(FlaskForm):
    """FR-24 / FR-25: one set's weight and reps."""
    weight = FloatField(
        "Weight (lb)",
        validators=[
            InputRequired(message="Enter the weight (0 for bodyweight)."),
            real_number,
            NumberRange(min=0, max=MAX_WEIGHT, message=f"Weight must be from 0 to {MAX_WEIGHT}."),
        ],
    )
    reps = IntegerField(
        "Reps",
        validators=[
            InputRequired(message="Enter the reps."),
            NumberRange(min=1, max=MAX_REPS, message=f"Reps must be a whole number from 1 to {MAX_REPS}."),
        ],
    )
    notes = StringField(
        "Notes (optional)",
        filters=[strip_spaces],
        validators=[Optional(), Length(max=200, message="Notes must be 200 characters or fewer.")],
    )
    submit = SubmitField("Log set")


class SessionExerciseForm(FlaskForm):
    """FR-23 / FR-26: add an exercise to the workout. The route fills in the choices."""
    exercise_id = SelectField(
        "Exercise",
        coerce=int_or_none,
        validators=[DataRequired(message="Choose an exercise.")],
    )
    submit = SubmitField("Add exercise")


ENERGY_LABELS = {1: "1 - exhausted", 3: "3 - okay", 5: "5 - great"}


def not_in_future(form, field):
    if field.data and field.data > date.today():
        raise ValidationError("The date can't be in the future.")


class FinishForm(FlaskForm):
    """FR-27: mark the workout completed and record how it went."""
    date_performed = DateField(
        "Date",
        default=date.today,
        validators=[InputRequired(message="Enter the date."), not_in_future],
    )
    duration_minutes = IntegerField(
        "Duration in minutes (optional)",
        validators=[
            Optional(),
            NumberRange(min=1, max=MAX_DURATION_MINUTES,
                        message=f"Duration must be a whole number from 1 to {MAX_DURATION_MINUTES}."),
        ],
    )
    energy_rating = SelectField(
        "Energy (optional)",
        coerce=int_or_none,
        choices=[("", "Choose...")] + [(n, ENERGY_LABELS.get(n, str(n))) for n in ENERGY_RATINGS],
        validators=[Optional()],
    )
    notes = TextAreaField(
        "Notes (optional)",
        filters=[strip_spaces],
        validators=[Optional(), Length(max=1000, message="Notes must be 1000 characters or fewer.")],
    )
    submit = SubmitField("Finish workout")
