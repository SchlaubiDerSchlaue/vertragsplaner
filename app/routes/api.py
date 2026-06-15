from datetime import datetime
from decimal import Decimal
from hmac import compare_digest

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import Customer, Supplier, Contract, ContractPosition
from app.planning import generate_planning_lines

api_bp = Blueprint("api", __name__)


@api_bp.before_request
def require_api_token():
    token = current_app.config.get("API_TOKEN")
    if not token:
        return error_response(
            "api_disabled",
            "Die JSON-API ist deaktiviert, weil API_TOKEN nicht gesetzt ist.",
            503,
        )

    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        return error_response(
            "unauthorized",
            "Bitte Authorization: Bearer <API_TOKEN> senden.",
            401,
        )

    provided_token = auth_header[len(prefix):].strip()
    if not compare_digest(provided_token, token):
        return error_response("unauthorized", "Ungueltiger API-Token.", 401)

    return None


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "api": "v1"})


@api_bp.route("/customers")
def customers():
    query = apply_partner_filters(Customer.query, Customer)
    total = query.count()
    items, meta = paginate(query.order_by(Customer.name), total)
    return jsonify({"data": [serialize_customer(item) for item in items], "meta": meta})


@api_bp.route("/suppliers")
def suppliers():
    query = apply_partner_filters(Supplier.query, Supplier)
    total = query.count()
    items, meta = paginate(query.order_by(Supplier.name), total)
    return jsonify({"data": [serialize_supplier(item) for item in items], "meta": meta})


@api_bp.route("/contracts")
def contracts():
    query = Contract.query.outerjoin(Customer).outerjoin(Supplier)
    query = apply_contract_filters(query)
    total = query.count()
    items, meta = paginate(query.order_by(Contract.start_date.desc(), Contract.id.desc()), total)
    return jsonify({"data": [serialize_contract(item) for item in items], "meta": meta})


@api_bp.route("/contracts/<int:contract_id>")
def contract_detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    return jsonify({"data": serialize_contract(contract, include_positions=True)})


@api_bp.route("/positions")
def positions():
    query = ContractPosition.query.join(Contract).outerjoin(Customer).outerjoin(Supplier)
    query = apply_position_filters(query)
    total = query.count()
    items, meta = paginate(query.order_by(Contract.title, ContractPosition.sort_order), total)
    return jsonify({"data": [serialize_position(item, include_versions=True) for item in items], "meta": meta})


@api_bp.route("/planning")
def planning():
    start_date, start_error = parse_date_arg("start_date")
    if start_error:
        return start_error

    end_date, end_error = parse_date_arg("end_date")
    if end_error:
        return end_error

    if end_date < start_date:
        return error_response(
            "invalid_date_range",
            "end_date darf nicht vor start_date liegen.",
            400,
        )

    lines = generate_planning_lines(
        start_date=start_date,
        end_date=end_date,
        include_revenue=parse_bool_arg("include_revenue", True),
        include_cost=parse_bool_arg("include_cost", False),
        include_forecast=parse_bool_arg("include_forecast", False),
    )

    return jsonify({"data": [serialize_planning_line(line) for line in lines], "meta": {"count": len(lines)}})


def error_response(code, message, status_code):
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status_code
    return response


@api_bp.errorhandler(404)
def not_found(_error):
    return error_response("not_found", "Die angeforderte Ressource wurde nicht gefunden.", 404)


def parse_date_arg(name):
    value = request.args.get(name)
    if not value:
        return None, error_response("missing_parameter", f"{name} ist erforderlich.", 400)

    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, error_response(
            "invalid_parameter",
            f"{name} muss im Format YYYY-MM-DD uebergeben werden.",
            400,
        )


def parse_bool_arg(name, default):
    value = request.args.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "ja"}


def parse_int_arg(name, default, minimum=0, maximum=None):
    raw_value = request.args.get(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def paginate(query, total):
    limit = parse_int_arg("limit", 100, minimum=1, maximum=500)
    offset = parse_int_arg("offset", 0, minimum=0)
    items = query.limit(limit).offset(offset).all()
    return items, {"count": len(items), "total": total, "limit": limit, "offset": offset}


def apply_partner_filters(query, model):
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                model.name.ilike(search),
                model.contact_name.ilike(search),
                model.email.ilike(search),
            )
        )
    if status:
        query = query.filter(model.status == status)

    return query


def apply_contract_filters(query):
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    contract_type = request.args.get("contract_type", "").strip()
    partner_type = request.args.get("partner_type", "").strip()

    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                Contract.contract_no.ilike(search),
                Contract.title.ilike(search),
                Contract.responsible.ilike(search),
                Customer.name.ilike(search),
                Supplier.name.ilike(search),
            )
        )
    if status:
        query = query.filter(Contract.status == status)
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    if partner_type == "customer":
        query = query.filter(Contract.customer_id.isnot(None))
    elif partner_type == "supplier":
        query = query.filter(Contract.supplier_id.isnot(None))

    return query


def apply_position_filters(query):
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    position_type = (
        request.args.get("position_type", "").strip()
        or request.args.get("contract_type", "").strip()
    )
    partner_type = request.args.get("partner_type", "").strip()

    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                ContractPosition.name.ilike(search),
                Contract.title.ilike(search),
                Customer.name.ilike(search),
                Supplier.name.ilike(search),
            )
        )
    if status:
        query = query.filter(ContractPosition.status == status)
    if position_type:
        query = query.filter(ContractPosition.position_type == position_type)
    if partner_type == "customer":
        query = query.filter(Contract.customer_id.isnot(None))
    elif partner_type == "supplier":
        query = query.filter(Contract.supplier_id.isnot(None))

    return query


def iso_date(value):
    return value.isoformat() if value else None


def iso_datetime(value):
    return value.isoformat() if value else None


def money(value):
    if value is None:
        return None
    return f"{Decimal(value):.2f}"


def serialize_customer(customer):
    return {
        "id": customer.id,
        "customer_no": customer.customer_no,
        "name": customer.name,
        "status": customer.status,
        "contact_name": customer.contact_name,
        "email": customer.email,
        "street": customer.street,
        "postal_code": customer.postal_code,
        "city": customer.city,
        "country": customer.country,
        "notes": customer.notes,
        "created_at": iso_datetime(customer.created_at),
        "updated_at": iso_datetime(customer.updated_at),
    }


def serialize_supplier(supplier):
    return {
        "id": supplier.id,
        "supplier_no": supplier.supplier_no,
        "name": supplier.name,
        "status": supplier.status,
        "contact_name": supplier.contact_name,
        "email": supplier.email,
        "street": supplier.street,
        "postal_code": supplier.postal_code,
        "city": supplier.city,
        "country": supplier.country,
        "notes": supplier.notes,
        "created_at": iso_datetime(supplier.created_at),
        "updated_at": iso_datetime(supplier.updated_at),
    }


def serialize_contract(contract, include_positions=False):
    data = {
        "id": contract.id,
        "contract_no": contract.contract_no,
        "title": contract.title,
        "contract_type": contract.contract_type,
        "status": contract.status,
        "start_date": iso_date(contract.start_date),
        "end_date": iso_date(contract.end_date),
        "cancellation_date": iso_date(contract.cancellation_date),
        "renewal_type": contract.renewal_type,
        "responsible": contract.responsible,
        "description": contract.description,
        "partner": serialize_partner_ref(contract),
        "created_at": iso_datetime(contract.created_at),
        "updated_at": iso_datetime(contract.updated_at),
    }
    if include_positions:
        data["positions"] = [serialize_position(position, include_versions=True) for position in contract.positions]
    return data


def serialize_partner_ref(contract):
    if contract.customer:
        return {"type": "customer", "id": contract.customer.id, "name": contract.customer.name}
    if contract.supplier:
        return {"type": "supplier", "id": contract.supplier.id, "name": contract.supplier.name}
    return None


def serialize_position(position, include_versions=False):
    data = {
        "id": position.id,
        "contract_id": position.contract_id,
        "contract_title": position.contract.title if position.contract else None,
        "name": position.name,
        "position_type": position.position_type,
        "status": position.status,
        "sort_order": position.sort_order,
        "created_at": iso_datetime(position.created_at),
        "updated_at": iso_datetime(position.updated_at),
    }
    if include_versions:
        data["versions"] = [serialize_version(version) for version in position.versions]
    return data


def serialize_version(version):
    return {
        "id": version.id,
        "position_id": version.position_id,
        "valid_from": iso_date(version.valid_from),
        "valid_to": iso_date(version.valid_to),
        "amount": money(version.amount),
        "currency": version.currency,
        "account": version.account,
        "cost_center_1": version.cost_center_1,
        "cost_center_2": version.cost_center_2,
        "recurrence": version.recurrence,
        "billing_day": version.billing_day,
        "is_active": version.is_active,
        "note": version.note,
        "created_at": iso_datetime(version.created_at),
        "updated_at": iso_datetime(version.updated_at),
    }


def serialize_planning_line(line):
    return {
        key: money(value) if key == "amount" else value
        for key, value in line.items()
    }
