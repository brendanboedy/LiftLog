"""Form for creating and editing a custom exercise (FR-11, FR-12).

The drop-downs only accept values from the fixed lists in app/models.py, and
each check that fails shows a message next to its field (FR-36).
"""
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.models import DIFFICULTIES, EQUIPMENT_TYPES, MOVEMENT_TYPES, MUSCLE_GROUPS, Exercise


def strip_spaces(value):
    """Remove spaces around typed text, so "  Squat " is saved as "Squat"."""
    return value.strip() if isinstance(value, str) else value


def choices(values):
    # The first, empty option makes the user pick on purpose; DataRequired rejects it.
    return [("", "Choose...")] + [(v, v) for v in values]


class ExerciseForm(FlaskForm):
    name = StringField(
        "Name",
        filters=[strip_spaces],
        validators=[DataRequired(), Length(max=100, message="Name must be 100 characters or fewer.")],
    )
    muscle_group = SelectField(
        "Muscle group", choices=choices(MUSCLE_GROUPS),
        validators=[DataRequired(message="Choose a muscle group.")],
    )
    equipment_type = SelectField(
        "Equipment", choices=choices(EQUIPMENT_TYPES),
        validators=[DataRequired(message="Choose the equipment.")],
    )
    movement_type = SelectField(
        "Movement type", choices=choices(MOVEMENT_TYPES),
        validators=[DataRequired(message="Choose a movement type.")],
    )
    difficulty = SelectField(
        "Difficulty", choices=choices(DIFFICULTIES),
        validators=[DataRequired(message="Choose a difficulty.")],
    )
    instructions = TextAreaField(
        "Instructions (optional)",
        filters=[strip_spaces],
        validators=[Optional(), Length(max=2000, message="Instructions must be 2000 characters or fewer.")],
    )
    submit = SubmitField("Save exercise")

    def __init__(self, *args, exercise_id=None, **kwargs):
        """exercise_id: when editing, the exercise being edited (so its own name doesn't count as taken)."""
        super().__init__(*args, **kwargs)
        self.exercise_id = exercise_id

    def validate_name(self, field):
        if field.data and Exercise.name_taken(field.data, current_user, exclude_id=self.exercise_id):
            raise ValidationError("You already have an exercise with this name in your library.")
