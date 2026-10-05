"""Register, log in and log out pages."""
from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.extensions import db
from app.models import User


def safe_next_url():
    """Where to go after logging in.

    If someone was sent to the login page from a private page, the address has
    ?next=/that/page. Only follow it if it points inside LiftLog, so a bad link
    can't send users to another website after they log in.
    """
    target = request.args.get("next", "")
    parts = urlsplit(target)
    if target.startswith("/") and not target.startswith("//") and not parts.netloc:
        return target
    return url_for("main.dashboard")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """FR-1: create an account. GET shows the form; POST handles the submitted form."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():  # True only for a POST where every field passed its checks
        user = User(username=form.username.data.strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)  # log them straight in after signing up
        flash("Welcome to LiftLog! Your account was created.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """FR-2: log in with username and password."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_username(form.username.data)
        if user is not None and user.check_password(form.password.data):
            login_user(user)
            return redirect(safe_next_url())
        # Same message whether the username or the password was wrong,
        # so nobody can use this page to find out which usernames exist.
        flash("Incorrect username or password.", "error")

    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """FR-3: log out.

    Only accepts POST (a form button with a CSRF token), so another website
    can't log users out just by linking to this address.
    """
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
