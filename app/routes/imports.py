import os
from flask import Blueprint, request, render_template, current_app
from werkzeug.utils import secure_filename
from app.auth import can_admin, write_required
from app.database_backup import import_database_backup
from app.imports import import_contract_rows

imports_bp = Blueprint("imports", __name__)


@imports_bp.route("/", methods=["GET", "POST"])
@write_required
def import_view():
    message = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        import_type = request.form.get("import_type", "contracts")

        if not file or not file.filename:
            error = "Bitte eine Datei auswählen."
        elif import_type == "backup":
            if not can_admin():
                return ("Zugriff verweigert.", 403)
            try:
                count = import_database_backup(file)
                message = f"Datenbank-Sicherung importiert: {count} Datensätze wiederhergestellt."
            except Exception as exc:
                error = str(exc)
        else:
            os.makedirs(current_app.instance_path, exist_ok=True)
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.instance_path, filename)
            file.save(upload_path)

            try:
                count = import_contract_rows(upload_path)
                message = f"{count} Vertragszeilen importiert."
            except Exception as exc:
                error = str(exc)

    return render_template("import.html", message=message, error=error)
