from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app import db
from app.auth import admin_required, create_api_token_secret, hash_secret, normalize_role
from app.models import ApiToken, User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@admin_required
def index():
    users = User.query.order_by(User.username).all()
    tokens = ApiToken.query.order_by(ApiToken.name).all()
    return render_template("admin.html", users=users, tokens=tokens)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    user = User(role="read", is_active=True)
    if request.method == "POST":
        errors = save_user_from_form(user, require_password=True)
        if not errors:
            db.session.add(user)
            db.session.commit()
            flash("Benutzer wurde angelegt.", "success")
            return redirect(url_for("admin.index"))
        for error in errors:
            flash(error, "danger")
    return render_template("user_form.html", user=user, mode="new")


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        errors = save_user_from_form(user, require_password=False)
        if not errors:
            db.session.commit()
            flash("Benutzer wurde gespeichert.", "success")
            return redirect(url_for("admin.index"))
        for error in errors:
            flash(error, "danger")
    return render_template("user_form.html", user=user, mode="edit")


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if g.current_user and user.id == g.current_user.id:
        flash("Das eigene Benutzerkonto kann nicht gelöscht werden.", "danger")
        return redirect(url_for("admin.index"))

    if user.role == "admin" and user.is_active:
        active_admin_count = User.query.filter_by(role="admin", is_active=True).count()
        if active_admin_count <= 1:
            flash("Der letzte aktive Admin kann nicht gelöscht werden.", "danger")
            return redirect(url_for("admin.index"))

    db.session.delete(user)
    db.session.commit()
    flash("Benutzer wurde gelöscht.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/tokens/new", methods=["GET", "POST"])
@admin_required
def new_token():
    token = ApiToken(role="read", is_active=True)
    if request.method == "POST":
        raw_token = create_api_token_secret()
        errors = save_token_from_form(token, raw_token)
        if not errors:
            db.session.add(token)
            db.session.commit()
            flash("API-Token wurde angelegt. Token jetzt kopieren: " + raw_token, "success")
            return redirect(url_for("admin.index"))
        for error in errors:
            flash(error, "danger")
    return render_template("token_form.html", token=token)


@admin_bp.route("/tokens/<int:token_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_token(token_id):
    token = ApiToken.query.get_or_404(token_id)
    if request.method == "POST":
        token.name = request.form.get("name", "").strip()
        token.role = normalize_role(request.form.get("role", "read"))
        token.is_active = request.form.get("is_active") == "on"
        errors = validate_token(token)
        if not errors:
            db.session.commit()
            flash("API-Token wurde gespeichert.", "success")
            return redirect(url_for("admin.index"))
        for error in errors:
            flash(error, "danger")
    return render_template("token_form.html", token=token)


@admin_bp.route("/tokens/<int:token_id>/delete", methods=["POST"])
@admin_required
def delete_token(token_id):
    token = ApiToken.query.get_or_404(token_id)
    db.session.delete(token)
    db.session.commit()
    flash("API-Token wurde gelöscht.", "success")
    return redirect(url_for("admin.index"))


def save_user_from_form(user, require_password):
    user.username = request.form.get("username", "").strip()
    user.role = normalize_role(request.form.get("role", "read"))
    user.is_active = request.form.get("is_active") == "on"
    password = request.form.get("password", "")

    errors = []
    if not user.username:
        errors.append("Bitte einen Benutzernamen eingeben.")
    existing = User.query.filter_by(username=user.username).first()
    if existing and existing.id != user.id:
        errors.append("Ein Benutzer mit diesem Namen existiert bereits.")
    if require_password and not password:
        errors.append("Bitte ein Passwort eingeben.")
    if password:
        user.password_hash = hash_secret(password)
    return errors


def save_token_from_form(token, raw_token):
    token.name = request.form.get("name", "").strip()
    token.role = normalize_role(request.form.get("role", "read"))
    token.is_active = request.form.get("is_active") == "on"
    token.token_hash = hash_secret(raw_token)
    return validate_token(token)


def validate_token(token):
    errors = []
    if not token.name:
        errors.append("Bitte einen Token-Namen eingeben.")
    existing = ApiToken.query.filter_by(name=token.name).first()
    if existing and existing.id != token.id:
        errors.append("Ein API-Token mit diesem Namen existiert bereits.")
    return errors
