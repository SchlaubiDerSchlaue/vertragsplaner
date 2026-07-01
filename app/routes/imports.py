import os
from flask import Blueprint, request, render_template, current_app
from werkzeug.utils import secure_filename
from app.auth import write_required
from app.imports import import_contract_rows

imports_bp = Blueprint("imports", __name__)


@imports_bp.route("/", methods=["GET", "POST"])
@write_required
def import_view():
    message = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")

        if not file or not file.filename:
            error = "Bitte eine Datei auswählen."
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
            finally:
                try:
                    os.remove(upload_path)
                except OSError:
                    current_app.logger.warning("Import-Upload konnte nicht geloescht werden: %s", upload_path)

    return render_template("import.html", message=message, error=error)
