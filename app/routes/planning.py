from datetime import datetime
from flask import Blueprint, request, render_template, send_file, make_response
from app.planning import generate_planning_lines
from app.exports import export_planning_excel, export_planning_csv

planning_bp = Blueprint("planning", __name__)


@planning_bp.route("/", methods=["GET", "POST"])
def planning():
    lines = []
    form_data = {}

    if request.method == "POST":
        form_data = request.form.to_dict()
        start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()

        include_forecast = request.form.get("include_forecast") == "on"
        include_revenue = request.form.get("include_revenue") == "on"
        include_cost = request.form.get("include_cost") == "on"

        lines = generate_planning_lines(
            start_date=start_date,
            end_date=end_date,
            include_revenue=include_revenue,
            include_cost=include_cost,
            include_forecast=include_forecast,
        )

        export_format = request.form.get("export_format")

        if export_format == "xlsx":
            output = export_planning_excel(lines)
            return send_file(
                output,
                as_attachment=True,
                download_name="planung.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if export_format == "csv":
            output = export_planning_csv(lines)
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = "attachment; filename=planung.csv"
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            return response

    return render_template("planning.html", lines=lines, form_data=form_data)
