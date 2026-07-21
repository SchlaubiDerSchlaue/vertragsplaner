from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import login_user, logout_user, verify_secret
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.is_active and verify_secret(user.password_hash, password):
            login_user(user)
            next_url = request.args.get("next") or url_for("dashboard.dashboard")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard.dashboard")
            return redirect(next_url)

        flash("Benutzername oder Passwort ist ungültig.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Sie wurden abgemeldet.", "success")
    return redirect(url_for("auth.login"))
