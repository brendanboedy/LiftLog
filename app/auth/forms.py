"""Forms for the auth pages.

Flask-WTF checks each field with its validators and adds a hidden CSRF token
to every form (NFR-4). If a check fails, the error message is shown next to
the field (FR-36).
"""
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from app.models import User

USERNAME_RULE = Regexp(
    r"^[A-Za-z0-9_.-]+$",
    message="Use only letters, numbers, dots, dashes and underscores.",
)


def password_not_too_long(form, field):
    """bcrypt can only use the first 72 bytes of a password, so reject longer ones."""
    if len(field.data.encode("utf-8")) > 72:
        raise ValidationError("Password is too long (72 bytes maximum).")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=30), USERNAME_RULE],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters."),
            password_not_too_long,
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords do not match.")],
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        """WTForms runs any method named validate_<field> automatically (FR-1: unique usernames)."""
        if User.find_by_username(field.data):
            raise ValidationError("That username is already taken.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")
