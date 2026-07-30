from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from flask import Blueprint, g, jsonify, request, url_for
from sqlalchemy.exc import IntegrityError

from app import db
from app.auth import authenticate_api_token, role_allows
from app.models import Customer, Supplier, Contract, ContractPosition, ContractPositionVersion
from app.planning import generate_planning_lines

api_bp = Blueprint("api", __name__)


@api_bp.before_request
def require_api_token():
    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        return error_response(
            "unauthorized",
            "Bitte Authorization: Bearer <API_TOKEN> senden.",
            401,
        )

    provided_token = auth_header[len(prefix):].strip()
    api_token = authenticate_api_token(provided_token)
    if api_token is None:
        return error_response("unauthorized", "Ungültiger API-Token.", 401)
    if not role_allows(api_token.role, "read"):
        return error_response("forbidden", "Der API-Token hat nicht die erforderliche Rolle.", 403)

    g.api_token = api_token
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not role_allows(api_token.role, "write"):
        return error_response(
            "forbidden",
            "Für diesen API-Zugriff ist mindestens die Rolle write erforderlich.",
            403,
        )
    return None


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "api": "v1"})


@api_bp.route("/customers", methods=["GET", "POST"])
def customers():
    if request.method == "POST":
        return create_customer()

    query = apply_partner_filters(Customer.query, Customer)
    total = query.count()
    items, meta = paginate(query.order_by(Customer.name), total)
    return jsonify({"data": [serialize_customer(item) for item in items], "meta": meta})


@api_bp.route("/customers/<int:customer_id>", methods=["GET", "PATCH"])
def update_customer(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    if request.method == "GET":
        return jsonify({"data": serialize_customer(customer)})

    payload, response = json_payload(CUSTOMER_FIELDS)
    if response:
        return response

    values, errors = validate_partner_payload(payload, "customer", partial=True, current=customer)
    if errors:
        return validation_error(errors)

    apply_values(customer, values)
    return commit_response(customer, serialize_customer)


@api_bp.route("/suppliers", methods=["GET", "POST"])
def suppliers():
    if request.method == "POST":
        return create_supplier()

    query = apply_partner_filters(Supplier.query, Supplier)
    total = query.count()
    items, meta = paginate(query.order_by(Supplier.name), total)
    return jsonify({"data": [serialize_supplier(item) for item in items], "meta": meta})


@api_bp.route("/suppliers/<int:supplier_id>", methods=["GET", "PATCH"])
def update_supplier(supplier_id):
    supplier = db.get_or_404(Supplier, supplier_id)
    if request.method == "GET":
        return jsonify({"data": serialize_supplier(supplier)})

    payload, response = json_payload(SUPPLIER_FIELDS)
    if response:
        return response

    values, errors = validate_partner_payload(payload, "supplier", partial=True, current=supplier)
    if errors:
        return validation_error(errors)

    apply_values(supplier, values)
    return commit_response(supplier, serialize_supplier)


@api_bp.route("/contracts", methods=["GET", "POST"])
def contracts():
    if request.method == "POST":
        return create_contract()

    query = Contract.query.outerjoin(Customer).outerjoin(Supplier)
    query = apply_contract_filters(query)
    total = query.count()
    items, meta = paginate(query.order_by(Contract.start_date.desc(), Contract.id.desc()), total)
    return jsonify({"data": [serialize_contract(item) for item in items], "meta": meta})


@api_bp.route("/contracts/<int:contract_id>", methods=["GET", "PATCH"])
def contract_detail(contract_id):
    contract = db.get_or_404(Contract, contract_id)
    if request.method == "PATCH":
        payload, response = json_payload(CONTRACT_FIELDS)
        if response:
            return response

        values, errors = validate_contract_payload(payload, partial=True, current=contract)
        if errors:
            return validation_error(errors)

        apply_values(contract, values)
        return commit_response(contract, lambda item: serialize_contract(item, include_positions=True))

    return jsonify({"data": serialize_contract(contract, include_positions=True)})


@api_bp.route("/positions")
def positions():
    query = ContractPosition.query.join(Contract).outerjoin(Customer).outerjoin(Supplier)
    query = apply_position_filters(query)
    total = query.count()
    items, meta = paginate(query.order_by(Contract.title, ContractPosition.sort_order), total)
    return jsonify({"data": [serialize_position(item, include_versions=True) for item in items], "meta": meta})


@api_bp.route("/contracts/<int:contract_id>/positions", methods=["POST"])
def create_position(contract_id):
    contract = db.get_or_404(Contract, contract_id)
    payload, response = json_payload(POSITION_FIELDS)
    if response:
        return response

    values, errors = validate_position_payload(payload, partial=False, contract=contract)
    if errors:
        return validation_error(errors)

    position = ContractPosition(contract=contract)
    apply_values(position, values)
    db.session.add(position)
    return commit_response(
        position,
        lambda item: serialize_position(item, include_versions=True),
        created=True,
        location_endpoint="api.update_position",
        location_values=lambda item: {"position_id": item.id},
    )


@api_bp.route("/positions/<int:position_id>", methods=["GET", "PATCH"])
def update_position(position_id):
    position = db.get_or_404(ContractPosition, position_id)
    if request.method == "GET":
        return jsonify({"data": serialize_position(position, include_versions=True)})

    payload, response = json_payload(POSITION_FIELDS)
    if response:
        return response

    values, errors = validate_position_payload(payload, partial=True, contract=position.contract)
    if errors:
        return validation_error(errors)

    apply_values(position, values)
    return commit_response(position, lambda item: serialize_position(item, include_versions=True))


@api_bp.route("/positions/<int:position_id>/versions", methods=["POST"])
def create_version(position_id):
    position = db.get_or_404(ContractPosition, position_id)
    payload, response = json_payload(VERSION_CREATE_FIELDS)
    if response:
        return response

    values, errors = validate_version_payload(payload, partial=False, position=position)
    if errors:
        return validation_error(errors)

    version = ContractPositionVersion(position=position)
    apply_values(version, values)
    db.session.add(version)
    close_previous_versions(position, version.valid_from)
    return commit_response(
        version,
        serialize_version,
        created=True,
        location_endpoint="api.update_version",
        location_values=lambda item: {"version_id": item.id},
    )


@api_bp.route("/versions/<int:version_id>", methods=["GET", "PATCH"])
def update_version(version_id):
    version = db.get_or_404(ContractPositionVersion, version_id)
    if request.method == "GET":
        return jsonify({"data": serialize_version(version)})

    payload, response = json_payload(VERSION_UPDATE_FIELDS)
    if response:
        return response

    values, errors = validate_version_payload(
        payload,
        partial=True,
        position=version.position,
        current=version,
    )
    if errors:
        return validation_error(errors)

    apply_values(version, values)
    return commit_response(version, serialize_version)


@api_bp.route("/<path:_resource>", methods=["PUT", "DELETE"])
def unsupported_write_method(_resource):
    return method_not_allowed(None)


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


def error_response(code, message, status_code, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    response = jsonify({"error": error})
    response.status_code = status_code
    return response


@api_bp.errorhandler(404)
def not_found(_error):
    return error_response("not_found", "Die angeforderte Ressource wurde nicht gefunden.", 404)


@api_bp.errorhandler(405)
def method_not_allowed(_error):
    return error_response("method_not_allowed", "Diese HTTP-Methode wird nicht unterstützt.", 405)


CUSTOMER_FIELDS = {
    "customer_no", "name", "status", "contact_name", "email", "street",
    "postal_code", "city", "country", "notes",
}
SUPPLIER_FIELDS = {
    "supplier_no", "name", "status", "contact_name", "email", "street",
    "postal_code", "city", "country", "notes",
}
CONTRACT_FIELDS = {
    "partner_type", "partner_id", "contract_no", "title", "contract_type", "status",
    "start_date", "end_date", "cancellation_date", "cancellation_period_value",
    "cancellation_period_unit", "renewal_type", "responsible", "contract_link",
    "invoice_link", "description",
}
POSITION_FIELDS = {"name", "position_type", "status", "sort_order"}
VERSION_CREATE_FIELDS = {
    "valid_from", "amount", "currency", "account", "cost_center_1", "cost_center_2",
    "recurrence", "billing_day", "is_active", "note",
}
VERSION_UPDATE_FIELDS = VERSION_CREATE_FIELDS | {"valid_to"}

PARTNER_STATUS = {"active", "inactive"}
CONTRACT_TYPES = {"revenue", "cost"}
CONTRACT_STATUS = {"draft", "active", "forecast", "cancelled", "ended"}
POSITION_STATUS = {"active", "inactive"}
RENEWAL_TYPES = {"none", "manual", "automatic"}
CANCELLATION_UNITS = {"days", "weeks", "months"}
RECURRENCES = {"monthly", "quarterly", "yearly", "once"}


def create_customer():
    payload, response = json_payload(CUSTOMER_FIELDS)
    if response:
        return response
    values, errors = validate_partner_payload(payload, "customer", partial=False)
    if errors:
        return validation_error(errors)
    customer = Customer()
    apply_values(customer, values)
    db.session.add(customer)
    return commit_response(
        customer,
        serialize_customer,
        created=True,
        location_endpoint="api.update_customer",
        location_values=lambda item: {"customer_id": item.id},
    )


def create_supplier():
    payload, response = json_payload(SUPPLIER_FIELDS)
    if response:
        return response
    values, errors = validate_partner_payload(payload, "supplier", partial=False)
    if errors:
        return validation_error(errors)
    supplier = Supplier()
    apply_values(supplier, values)
    db.session.add(supplier)
    return commit_response(
        supplier,
        serialize_supplier,
        created=True,
        location_endpoint="api.update_supplier",
        location_values=lambda item: {"supplier_id": item.id},
    )


def create_contract():
    payload, response = json_payload(CONTRACT_FIELDS)
    if response:
        return response
    values, errors = validate_contract_payload(payload, partial=False)
    if errors:
        return validation_error(errors)
    contract = Contract()
    apply_values(contract, values)
    db.session.add(contract)
    return commit_response(
        contract,
        lambda item: serialize_contract(item, include_positions=True),
        created=True,
        location_endpoint="api.contract_detail",
        location_values=lambda item: {"contract_id": item.id},
    )


def json_payload(allowed_fields):
    if not request.is_json:
        return None, error_response(
            "unsupported_media_type",
            "Der Request muss Content-Type application/json verwenden.",
            415,
        )
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, error_response("invalid_json", "Der JSON-Body muss ein Objekt sein.", 400)
    if not payload:
        return None, error_response("empty_payload", "Der JSON-Body darf nicht leer sein.", 400)
    unknown = sorted(set(payload) - allowed_fields)
    if unknown:
        return None, error_response(
            "unknown_fields",
            "Der JSON-Body enthält unbekannte Felder.",
            400,
            {"fields": unknown},
        )
    return payload, None


def validation_error(errors):
    return error_response(
        "validation_error",
        "Die übermittelten Daten sind ungültig.",
        400,
        errors,
    )


def add_error(errors, field, message):
    errors.setdefault(field, []).append(message)


def parse_string(payload, field, errors, *, required=False, nullable=True, max_length=None, default=None):
    if field not in payload:
        if required:
            add_error(errors, field, "Dieses Feld ist erforderlich.")
        return default
    value = payload[field]
    if value is None:
        if not nullable or required:
            add_error(errors, field, "Dieses Feld darf nicht null sein.")
        return None
    if not isinstance(value, str):
        add_error(errors, field, "Dieses Feld muss eine Zeichenkette sein.")
        return None
    value = value.strip()
    if required and not value:
        add_error(errors, field, "Dieses Feld darf nicht leer sein.")
    if max_length and len(value) > max_length:
        add_error(errors, field, f"Dieses Feld darf höchstens {max_length} Zeichen lang sein.")
    return value or None


def parse_choice(payload, field, errors, choices, *, required=False, default=None, nullable=False):
    value = parse_string(
        payload,
        field,
        errors,
        required=required,
        nullable=nullable,
        default=default,
    )
    if value is not None and value not in choices:
        add_error(errors, field, "Erlaubte Werte: " + ", ".join(sorted(choices)) + ".")
    return value


def parse_date_value(payload, field, errors, *, required=False, default=None):
    if field not in payload:
        if required:
            add_error(errors, field, "Dieses Feld ist erforderlich.")
        return default
    value = payload[field]
    if value is None:
        if required:
            add_error(errors, field, "Dieses Feld darf nicht null sein.")
        return None
    if not isinstance(value, str):
        add_error(errors, field, "Dieses Feld muss ein Datum im Format YYYY-MM-DD sein.")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        add_error(errors, field, "Dieses Feld muss ein gültiges Datum im Format YYYY-MM-DD sein.")
        return None


def parse_integer(payload, field, errors, *, required=False, default=None, minimum=None, maximum=None):
    if field not in payload:
        if required:
            add_error(errors, field, "Dieses Feld ist erforderlich.")
        return default
    value = payload[field]
    if value is None:
        if required:
            add_error(errors, field, "Dieses Feld darf nicht null sein.")
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        add_error(errors, field, "Dieses Feld muss eine ganze Zahl sein.")
        return None
    if minimum is not None and value < minimum:
        add_error(errors, field, f"Der Wert muss mindestens {minimum} sein.")
    if maximum is not None and value > maximum:
        add_error(errors, field, f"Der Wert darf höchstens {maximum} sein.")
    return value


def parse_decimal_value(payload, field, errors, *, required=False, default=None):
    if field not in payload:
        if required:
            add_error(errors, field, "Dieses Feld ist erforderlich.")
        return default
    value = payload[field]
    if value is None or isinstance(value, bool):
        add_error(errors, field, "Dieses Feld muss eine gültige Dezimalzahl sein.")
        return None
    try:
        parsed = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        add_error(errors, field, "Dieses Feld muss eine gültige Dezimalzahl sein.")
        return None
    if not parsed.is_finite():
        add_error(errors, field, "Dieses Feld muss eine endliche Dezimalzahl sein.")
        return None
    if abs(parsed) > Decimal("9999999999.99"):
        add_error(errors, field, "Der Betrag ist zu groß.")
    return parsed


def parse_boolean(payload, field, errors, *, default=None):
    if field not in payload:
        return default
    value = payload[field]
    if not isinstance(value, bool):
        add_error(errors, field, "Dieses Feld muss true oder false sein.")
        return None
    return value


def validate_partner_payload(payload, partner_kind, *, partial, current=None):
    errors = {}
    number_field = "customer_no" if partner_kind == "customer" else "supplier_no"
    model = Customer if partner_kind == "customer" else Supplier
    values = {}

    string_fields = {
        number_field: 50,
        "contact_name": 255,
        "email": 255,
        "street": 255,
        "postal_code": 20,
        "city": 255,
        "country": 100,
        "notes": None,
    }
    for field, max_length in string_fields.items():
        if field in payload:
            values[field] = parse_string(payload, field, errors, max_length=max_length)

    if "name" in payload or not partial:
        values["name"] = parse_string(
            payload, "name", errors, required="name" in payload or not partial,
            nullable=False, max_length=255
        )
    if "status" in payload or not partial:
        values["status"] = parse_choice(
            payload, "status", errors, PARTNER_STATUS,
            required="status" in payload,
            default="active" if not partial else None,
        )

    name = values.get("name")
    if name:
        existing = model.query.filter(model.name == name).first()
        if existing and (current is None or existing.id != current.id):
            add_error(errors, "name", f"Ein {partner_kind} mit diesem Namen existiert bereits.")
    return values, errors


def validate_contract_payload(payload, *, partial, current=None):
    errors = {}
    values = {}

    partner_fields_present = "partner_type" in payload or "partner_id" in payload
    if partner_fields_present or not partial:
        current_type = None
        current_id = None
        if current:
            if current.customer_id:
                current_type, current_id = "customer", current.customer_id
            elif current.supplier_id:
                current_type, current_id = "supplier", current.supplier_id
        partner_type = parse_choice(
            payload, "partner_type", errors, {"customer", "supplier"},
            required=not partial and current_type is None,
            default=current_type,
        )
        partner_id = parse_integer(
            payload, "partner_id", errors,
            required=not partial and current_id is None,
            default=current_id,
            minimum=1,
        )
        if (
            partial
            and "partner_type" in payload
            and "partner_id" not in payload
            and partner_type != current_type
        ):
            add_error(
                errors,
                "partner_id",
                "Beim Wechsel des Partnertyps muss partner_id mitgesendet werden.",
            )
        if partner_type and partner_id:
            partner_model = Customer if partner_type == "customer" else Supplier
            if db.session.get(partner_model, partner_id) is None:
                add_error(errors, "partner_id", "Der angegebene Vertragspartner wurde nicht gefunden.")
            values["customer_id"] = partner_id if partner_type == "customer" else None
            values["supplier_id"] = partner_id if partner_type == "supplier" else None

    optional_strings = {
        "contract_no": 50,
        "responsible": 255,
        "description": None,
    }
    for field, max_length in optional_strings.items():
        if field in payload:
            values[field] = parse_string(payload, field, errors, max_length=max_length)

    if "title" in payload or not partial:
        values["title"] = parse_string(
            payload, "title", errors, required="title" in payload or not partial,
            nullable=False, max_length=255
        )
    if "contract_type" in payload or not partial:
        values["contract_type"] = parse_choice(
            payload, "contract_type", errors, CONTRACT_TYPES,
            required="contract_type" in payload,
            default="revenue" if not partial else None,
        )
    if "status" in payload or not partial:
        values["status"] = parse_choice(
            payload, "status", errors, CONTRACT_STATUS,
            required="status" in payload,
            default="draft" if not partial else None,
        )
    if "renewal_type" in payload or not partial:
        values["renewal_type"] = parse_choice(
            payload, "renewal_type", errors, RENEWAL_TYPES,
            required="renewal_type" in payload,
            default="none" if not partial else None,
        )

    for field in ("start_date", "end_date", "cancellation_date"):
        if field in payload or (field == "start_date" and not partial):
            values[field] = parse_date_value(
                payload,
                field,
                errors,
                required=field == "start_date" and (field in payload or not partial),
            )

    if "cancellation_period_value" in payload:
        values["cancellation_period_value"] = parse_integer(
            payload, "cancellation_period_value", errors, minimum=0
        )
    if "cancellation_period_unit" in payload:
        values["cancellation_period_unit"] = parse_choice(
            payload, "cancellation_period_unit", errors, CANCELLATION_UNITS, nullable=True
        )

    cancellation_value = values.get(
        "cancellation_period_value",
        current.cancellation_period_value if current else None,
    )
    cancellation_unit = values.get(
        "cancellation_period_unit",
        current.cancellation_period_unit if current else None,
    )
    if cancellation_value is None:
        values["cancellation_period_unit"] = None
    elif not cancellation_unit:
        add_error(errors, "cancellation_period_unit", "Bei einer Kündigungsfrist ist die Einheit erforderlich.")

    for field in ("contract_link", "invoice_link"):
        if field in payload:
            value = parse_string(payload, field, errors, max_length=2048)
            value = normalize_url(value)
            if not is_valid_url(value):
                add_error(errors, field, "Bitte eine gültige HTTP- oder HTTPS-URL angeben.")
            values[field] = value

    start_date = values.get("start_date", current.start_date if current else None)
    end_date = values.get("end_date", current.end_date if current else None)
    cancellation_date = values.get("cancellation_date", current.cancellation_date if current else None)
    if start_date and end_date and end_date < start_date:
        add_error(errors, "end_date", "Das Enddatum darf nicht vor dem Startdatum liegen.")
    if start_date and cancellation_date and cancellation_date < start_date:
        add_error(errors, "cancellation_date", "Das Kündigungsdatum darf nicht vor dem Startdatum liegen.")

    return values, errors


def validate_position_payload(payload, *, partial, contract):
    errors = {}
    values = {}
    if "name" in payload or not partial:
        values["name"] = parse_string(
            payload, "name", errors, required="name" in payload or not partial,
            nullable=False, max_length=255
        )
    if "position_type" in payload or not partial:
        values["position_type"] = parse_choice(
            payload, "position_type", errors, CONTRACT_TYPES,
            required="position_type" in payload,
            default=contract.contract_type if not partial else None,
        )
    if "status" in payload or not partial:
        values["status"] = parse_choice(
            payload, "status", errors, POSITION_STATUS,
            required="status" in payload,
            default="active" if not partial else None,
        )
    if "sort_order" in payload or not partial:
        values["sort_order"] = parse_integer(
            payload, "sort_order", errors, default=0 if not partial else None
        )
    return values, errors


def validate_version_payload(payload, *, partial, position, current=None):
    errors = {}
    values = {}
    if "valid_from" in payload or not partial:
        values["valid_from"] = parse_date_value(
            payload, "valid_from", errors,
            required="valid_from" in payload or not partial,
        )
    if "valid_to" in payload:
        values["valid_to"] = parse_date_value(payload, "valid_to", errors)
    if "amount" in payload or not partial:
        values["amount"] = parse_decimal_value(
            payload, "amount", errors, required=not partial
        )
    if "currency" in payload or not partial:
        currency = parse_string(
            payload, "currency", errors, required="currency" in payload,
            nullable=False, max_length=3,
            default="EUR" if not partial else None,
        )
        if currency is not None:
            currency = currency.upper()
            if len(currency) != 3 or not currency.isalpha():
                add_error(errors, "currency", "Die Währung muss aus genau drei Buchstaben bestehen.")
        values["currency"] = currency
    if "recurrence" in payload or not partial:
        values["recurrence"] = parse_choice(
            payload, "recurrence", errors, RECURRENCES,
            required="recurrence" in payload,
            default="monthly" if not partial else None,
        )
    if "billing_day" in payload:
        values["billing_day"] = parse_integer(
            payload, "billing_day", errors, minimum=1, maximum=31
        )
    if "is_active" in payload or not partial:
        values["is_active"] = parse_boolean(
            payload, "is_active", errors, default=True if not partial else None
        )
    for field, max_length in {
        "account": 50,
        "cost_center_1": 100,
        "cost_center_2": 100,
        "note": None,
    }.items():
        if field in payload:
            values[field] = parse_string(payload, field, errors, max_length=max_length)

    valid_from = values.get("valid_from", current.valid_from if current else None)
    valid_to = values.get("valid_to", current.valid_to if current else None)
    if valid_from and valid_to and valid_to < valid_from:
        add_error(errors, "valid_to", "Gültig bis darf nicht vor Gültig ab liegen.")
    if valid_from:
        existing = ContractPositionVersion.query.filter_by(
            position_id=position.id,
            valid_from=valid_from,
        ).first()
        if existing and (current is None or existing.id != current.id):
            add_error(errors, "valid_from", "Es gibt bereits eine Version mit diesem Gültig-ab-Datum.")
    return values, errors


def apply_values(instance, values):
    for field, value in values.items():
        setattr(instance, field, value)


def commit_response(
    instance,
    serializer,
    *,
    created=False,
    location_endpoint=None,
    location_values=None,
):
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response(
            "conflict",
            "Die Änderung konnte wegen eines Datenkonflikts nicht gespeichert werden.",
            409,
        )

    response = jsonify({"data": serializer(instance)})
    response.status_code = 201 if created else 200
    if created and location_endpoint:
        values = location_values(instance) if location_values else {}
        response.headers["Location"] = url_for(location_endpoint, **values)
    return response


def close_previous_versions(position, valid_from):
    previous_valid_to = valid_from - timedelta(days=1)
    for old_version in position.versions:
        if old_version.valid_from < valid_from and (
            old_version.valid_to is None or old_version.valid_to >= valid_from
        ):
            old_version.valid_to = previous_valid_to


def normalize_url(value):
    if not value:
        return None
    if "://" not in value:
        return f"https://{value}"
    return value


def is_valid_url(value):
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def parse_date_arg(name):
    value = request.args.get(name)
    if not value:
        return None, error_response("missing_parameter", f"{name} ist erforderlich.", 400)

    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, error_response(
            "invalid_parameter",
            f"{name} muss im Format YYYY-MM-DD übergeben werden.",
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
                Contract.contract_link.ilike(search),
                Contract.invoice_link.ilike(search),
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
        "cancellation_period_value": contract.cancellation_period_value,
        "cancellation_period_unit": contract.cancellation_period_unit,
        "cancellation_period_label": contract.cancellation_period_label,
        "cancellation_deadline": iso_date(contract.cancellation_deadline),
        "renewal_type": contract.renewal_type,
        "responsible": contract.responsible,
        "contract_link": contract.contract_link,
        "invoice_link": contract.invoice_link,
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
