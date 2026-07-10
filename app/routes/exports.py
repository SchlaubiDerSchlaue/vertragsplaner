from datetime import date, datetime

from flask import Blueprint, make_response, render_template, request, send_file

from app.auth import admin_required
from app.database_backup import export_database_backup
from app.exports import export_planning_csv, export_planning_excel
from app.planning import generate_planning_lines

exports_bp = Blueprint("exports", __name__)


@exports_bp.route("/database", methods=["POST"])
@admin_required
def export_database_view():
    output = export_database_backup()
    return send_file(
        output,
        as_attachment=True,
        download_name=f"vertragsplanung-backup-{date.today().isoformat()}.json",
        mimetype="application/json",
    )


@exports_bp.route("/", methods=["GET", "POST"])
def export_view():
    today = date.today()
    form_data = {
        "start_date": date(today.year, 1, 1).isoformat(),
        "end_date": date(today.year, 12, 31).isoformat(),
        "include_revenue": "on",
        "include_cost": "",
        "include_forecast": "",
        "export_format": "xlsx",
    }
    error = None

    if request.method == "POST":
        form_data.update(request.form.to_dict())
        try:
            start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            start_date = None
            end_date = None
            error = "Bitte einen gueltigen Zeitraum eingeben."

        if start_date and end_date and end_date < start_date:
            error = "Das Bis-Datum darf nicht vor dem Von-Datum liegen."

        if not error:
            lines = generate_planning_lines(
                start_date=start_date,
                end_date=end_date,
                include_revenue=request.form.get("include_revenue") == "on",
                include_cost=request.form.get("include_cost") == "on",
                include_forecast=request.form.get("include_forecast") == "on",
            )

            export_format = request.form.get("export_format", "xlsx")
            if export_format == "csv":
                output = export_planning_csv(lines)
                response = make_response(output.getvalue())
                response.headers["Content-Disposition"] = "attachment; filename=planung.csv"
                response.headers["Content-Type"] = "text/csv; charset=utf-8"
                return response

            output = export_planning_excel(lines)
            return send_file(
                output,
                as_attachment=True,
                download_name="planung.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    return render_template("export.html", form_data=form_data, error=error)
