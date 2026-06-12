from flask import Blueprint, render_template
from app.models import Customer, Supplier, Contract, ContractPosition

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():
    stats = {
        "customers": Customer.query.count(),
        "suppliers": Supplier.query.count(),
        "contracts": Contract.query.count(),
        "positions": ContractPosition.query.count(),
        "forecast_contracts": Contract.query.filter_by(status="forecast").count(),
    }
    return render_template("dashboard.html", stats=stats)
