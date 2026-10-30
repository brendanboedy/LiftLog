"""Profile pages. Both only ever touch the logged-in user's own account (NFR-2, NFR-3)."""
from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.profile import bp
from app.profile.forms import ChangePasswordForm, ProfileForm


@bp.route("/", methods=["GET", "POST"])
@login_required
def edit():
    """FR-4: view and update the profile. The form starts filled in with the saved values."""
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.goal_type = form.goal_type.data or None
        current_user.experience_level = form.experience_level.data or None
        current_user.body_weight = form.body_weight.data
        current_user.age = form.age.data
        current_user.gender = form.gender.data or None
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("profile.edit"))
    return render_template("profile/edit.html", form=form)


@bp.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    """FR-5: change the password after re-entering the current one."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Your current password is incorrect.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Your password was changed.", "success")
            return redirect(url_for("profile.edit"))
    return render_template("profile/password.html", form=form)
