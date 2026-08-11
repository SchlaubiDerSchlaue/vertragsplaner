from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from pathlib import Path
import json
import os
from datetime import datetime

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


@admin_bp.route("/logs", methods=["GET", "POST"])
@admin_required
def view_logs():
    """Log viewer for admin users."""
    from app.logging_config import LOG_DIR

    log_dir = Path(LOG_DIR)

    log_files = {
        "app": "Anwendungs-Logs",
        "audit": "Audit-Trail (Datenänderungen)",
        "access": "Zugriffs-Logs (HTTP Requests)",
        "error": "Fehler-Logs",
    }

    selected_log = request.args.get("log", "audit")
    lines_count = min(int(request.args.get("lines", 100)), 1000)
    search = request.args.get("q", "").strip()

    log_entries = []
    log_path = log_dir / f"{selected_log}.log"

    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            for line in reversed(all_lines):
                line = line.strip()
                if not line:
                    continue

                if search and search.lower() not in line.lower():
                    continue

                try:
                    entry = json.loads(line)
                    entry["_raw"] = line[:500]
                except json.JSONDecodeError:
                    entry = {
                        "timestamp": datetime.now().isoformat(),
                        "message": line,
                        "level": "INFO",
                        "_raw": line[:500],
                    }

                log_entries.append(entry)

                if len(log_entries) >= lines_count:
                    break

        except Exception as e:
            flash(f"Fehler beim Lesen der Log-Datei: {e}", "danger")

    log_info = {}
    for key in log_files.keys():
        path = log_dir / f"{key}.log"
        if path.exists():
            size = path.stat().st_size
            log_info[key] = {
                "size": size,
                "size_human": _format_size(size),
                "exists": True,
            }
        else:
            log_info[key] = {"exists": False, "size": 0, "size_human": "0 B"}

    return render_template(
        "admin_logs.html",
        log_files=log_files,
        selected_log=selected_log,
        log_entries=log_entries,
        lines_count=lines_count,
        search=search,
        log_info=log_info,
        log_dir=str(log_dir),
    )


@admin_bp.route("/logs/download.csv", methods=["GET"])
@admin_required
def download_logs_csv():
    """Download log entries as CSV."""
    from flask import Response
    from app.logging_config import LOG_DIR

    log_dir = Path(LOG_DIR)

    selected_log = request.args.get("log", "audit")
    search = request.args.get("q", "").strip()
    lines_count = min(int(request.args.get("lines", 1000)), 1000)

    log_path = log_dir / f"{selected_log}.log"
    csv_content = ""

    if log_path.exists():
        csv_content = _export_logs_to_csv(log_path, lines_count, search)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=vertragsplaner_{selected_log}_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


def _format_size(size_bytes):
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _export_logs_to_csv(log_path, lines_count, search):
    """Export log entries to CSV format with proper escaping."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Write header
    writer.writerow([
        "timestamp",
        "level",
        "action",
        "resource_type",
        "resource_id",
        "username",
        "api_token_name",
        "ip_address",
        "message",
        "old_values",
        "new_values",
        "request_id",
        "duration_ms",
        "status_code",
        "method",
        "path",
    ])

    with open(log_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    count = 0
    for line in reversed(all_lines):
        line = line.strip()
        if not line:
            continue

        if search and search.lower() not in line.lower():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            entry = {"message": line}

        row = [
            entry.get("timestamp", ""),
            entry.get("level", ""),
            entry.get("action", ""),
            entry.get("resource_type", ""),
            entry.get("resource_id", ""),
            entry.get("username", ""),
            entry.get("api_token_name", ""),
            entry.get("ip_address", ""),
            entry.get("message", ""),
            json.dumps(entry.get("old_values", {}), ensure_ascii=False) if entry.get("old_values") else "",
            json.dumps(entry.get("new_values", {}), ensure_ascii=False) if entry.get("new_values") else "",
            entry.get("request_id", ""),
            entry.get("duration_ms", ""),
            entry.get("status_code", ""),
            entry.get("method", ""),
            entry.get("path", ""),
        ]
        writer.writerow(row)

        count += 1
        if count >= lines_count:
            break

    return buffer.getvalue()


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
