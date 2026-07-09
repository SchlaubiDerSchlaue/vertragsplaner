from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from app import db
from app.auth import write_required
from app.models import Customer, Supplier, Contract, ContractPosition, ContractPositionVersion
from app.routes.listing import active_filters, apply_sort, get_list_params

contracts_bp = Blueprint("contracts", __name__)


@contracts_bp.route("/")
def list_contracts():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    contract_type = request.args.get("contract_type", "").strip()
    partner_type = request.args.get("partner_type", "").strip()
    sort, direction = get_list_params("start_date", "desc")

    query = Contract.query.outerjoin(Customer).outerjoin(Supplier)
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

    partner_name = func.coalesce(Customer.name, Supplier.name)
    sort_map = {
        "contract_no": Contract.contract_no,
        "partner": partner_name,
        "contract_type": Contract.contract_type,
        "title": Contract.title,
        "status": Contract.status,
        "start_date": Contract.start_date,
        "end_date": Contract.end_date,
        "responsible": Contract.responsible,
    }
    contracts = apply_sort(query, sort, direction, sort_map, "start_date").all()
    statuses = [row[0] for row in db.session.query(Contract.status).distinct().order_by(Contract.status).all() if row[0]]
    contract_types = [row[0] for row in db.session.query(Contract.contract_type).distinct().order_by(Contract.contract_type).all() if row[0]]

    return render_template(
        "contracts.html",
        contracts=contracts,
        filters={
            "q": q,
            "status": status,
            "contract_type": contract_type,
            "partner_type": partner_type,
        },
        sort=sort,
        direction=direction,
        sort_filters=active_filters(
            q=q,
            status=status,
            contract_type=contract_type,
            partner_type=partner_type,
        ),
        statuses=statuses,
        contract_types=contract_types,
    )


@contracts_bp.route("/positions/")
def list_positions():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    position_type = request.args.get("position_type", "").strip()
    partner_type = request.args.get("partner_type", "").strip()
    sort, direction = get_list_params("contract")

    query = ContractPosition.query.join(Contract).outerjoin(Customer).outerjoin(Supplier)
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

    partner_name = func.coalesce(Customer.name, Supplier.name)
    sort_map = {
        "name": ContractPosition.name,
        "contract": Contract.title,
        "partner": partner_name,
        "position_type": ContractPosition.position_type,
        "status": ContractPosition.status,
        "sort_order": ContractPosition.sort_order,
        "created_at": ContractPosition.created_at,
    }
    positions = apply_sort(query, sort, direction, sort_map, "contract").all()
    statuses = [
        row[0]
        for row in db.session.query(ContractPosition.status).distinct().order_by(ContractPosition.status).all()
        if row[0]
    ]
    position_types = [
        row[0]
        for row in db.session.query(ContractPosition.position_type).distinct().order_by(ContractPosition.position_type).all()
        if row[0]
    ]

    return render_template(
        "positions.html",
        positions=positions,
        filters={
            "q": q,
            "status": status,
            "position_type": position_type,
            "partner_type": partner_type,
        },
        sort=sort,
        direction=direction,
        sort_filters=active_filters(
            q=q,
            status=status,
            position_type=position_type,
            partner_type=partner_type,
        ),
        statuses=statuses,
        position_types=position_types,
    )


@contracts_bp.route("/new", methods=["GET", "POST"])
@write_required
def new_contract():
    contract = Contract(status="draft", contract_type="revenue", renewal_type="none")
    customers = Customer.query.order_by(Customer.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()

    if request.method == "POST":
        errors = save_contract_from_form(contract)
        if not errors:
            db.session.add(contract)
            db.session.commit()
            flash("Vertrag wurde angelegt.", "success")
            return redirect(url_for("contracts.contract_detail", contract_id=contract.id))

        for error in errors:
            flash(error, "danger")

    return render_template(
        "contract_form.html",
        contract=contract,
        customers=customers,
        suppliers=suppliers,
        mode="new",
    )


@contracts_bp.route("/<int:contract_id>")
def contract_detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    return render_template("contract_detail.html", contract=contract)


@contracts_bp.route("/<int:contract_id>/edit", methods=["GET", "POST"])
@write_required
def edit_contract(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    customers = Customer.query.order_by(Customer.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()

    if request.method == "POST":
        errors = save_contract_from_form(contract)
        if not errors:
            db.session.commit()
            flash("Vertrag wurde gespeichert.", "success")
            return redirect(url_for("contracts.contract_detail", contract_id=contract.id))

        for error in errors:
            flash(error, "danger")

    return render_template(
        "contract_form.html",
        contract=contract,
        customers=customers,
        suppliers=suppliers,
        mode="edit",
    )


@contracts_bp.route("/<int:contract_id>/positions/new", methods=["GET", "POST"])
@write_required
def new_position(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    position = ContractPosition(contract=contract, position_type=contract.contract_type, status="active")

    if request.method == "POST":
        errors = save_position_from_form(position)
        if not errors:
            db.session.add(position)
            db.session.commit()
            flash("Position wurde angelegt.", "success")
            return redirect(url_for("contracts.contract_detail", contract_id=contract.id))

        for error in errors:
            flash(error, "danger")

    return render_template("position_form.html", contract=contract, position=position, mode="new")


@contracts_bp.route("/positions/<int:position_id>/edit", methods=["GET", "POST"])
@write_required
def edit_position(position_id):
    position = ContractPosition.query.get_or_404(position_id)
    contract = position.contract

    if request.method == "POST":
        errors = save_position_from_form(position)
        if not errors:
            db.session.commit()
            flash("Position wurde gespeichert.", "success")
            return redirect(url_for("contracts.contract_detail", contract_id=contract.id))

        for error in errors:
            flash(error, "danger")

    return render_template("position_form.html", contract=contract, position=position, mode="edit")


@contracts_bp.route("/positions/<int:position_id>/versions/new", methods=["GET", "POST"])
@write_required
def new_version(position_id):
    position = ContractPosition.query.get_or_404(position_id)
    version = ContractPositionVersion(
        position_id=position.id,
        currency="EUR",
        recurrence="monthly",
        is_active=True,
    )

    if request.method == "POST":
        errors = save_version_from_form(version)
        if not errors:
            close_previous_versions(position, version.valid_from)
            db.session.add(version)
            db.session.commit()
            flash("Version wurde fortgeschrieben.", "success")
            return redirect(url_for("contracts.contract_detail", contract_id=position.contract.id))

        for error in errors:
            flash(error, "danger")

    latest = get_latest_version(position)
    return render_template(
        "version_form.html",
        position=position,
        version=version,
        latest=latest,
        mode="new",
    )


@contracts_bp.route("/versions/<int:version_id>/edit", methods=["GET", "POST"])
@write_required
def edit_version(version_id):
    version = ContractPositionVersion.query.get_or_404(version_id)
    position = version.position

    if request.method == "POST":
        errors = save_version_from_form(version, allow_valid_to=True)
        if not errors:
            db.session.commit()
            flash("Version wurde gespeichert.", "success")
            return redirect(url_for("contracts.contract_detail", contract_id=position.contract.id))

        for error in errors:
            flash(error, "danger")

    return render_template(
        "version_form.html",
        position=position,
        version=version,
        latest=None,
        mode="edit",
    )


def save_contract_from_form(contract):
    errors = []

    partner_type = request.form.get("partner_type", "customer")
    contract.customer_id = None
    contract.supplier_id = None

    if partner_type == "supplier":
        contract.supplier_id = parse_int(request.form.get("supplier_id"))
    else:
        contract.customer_id = parse_int(request.form.get("customer_id"))

    contract.contract_no = request.form.get("contract_no", "").strip() or None
    contract.title = request.form.get("title", "").strip()
    contract.contract_type = request.form.get("contract_type", "revenue")
    contract.status = request.form.get("status", "draft")
    contract.start_date = parse_date(request.form.get("start_date"))
    contract.end_date = parse_date(request.form.get("end_date"))
    contract.cancellation_date = parse_date(request.form.get("cancellation_date"))
    contract.renewal_type = request.form.get("renewal_type", "none")
    contract.responsible = request.form.get("responsible", "").strip() or None
    contract.description = request.form.get("description", "").strip() or None

    if contract.customer_id and contract.supplier_id:
        errors.append("Bitte entweder Kunde oder Lieferant auswaehlen, nicht beides.")
    elif contract.customer_id:
        if not Customer.query.get(contract.customer_id):
            errors.append("Bitte einen gueltigen Kunden auswaehlen.")
    elif contract.supplier_id:
        if not Supplier.query.get(contract.supplier_id):
            errors.append("Bitte einen gueltigen Lieferanten auswaehlen.")
    else:
        errors.append("Bitte Kunde oder Lieferant auswaehlen.")
    if not contract.title:
        errors.append("Bitte einen Vertragstitel eingeben.")
    if not contract.start_date:
        errors.append("Bitte ein Startdatum eingeben.")
    if contract.start_date and contract.end_date and contract.end_date < contract.start_date:
        errors.append("Das Enddatum darf nicht vor dem Startdatum liegen.")
    if contract.start_date and contract.cancellation_date and contract.cancellation_date < contract.start_date:
        errors.append("Das Kuendigungsdatum darf nicht vor dem Startdatum liegen.")
    if contract.renewal_type not in {"none", "manual", "automatic"}:
        errors.append("Bitte einen gueltigen Verlaengerungstyp auswaehlen.")

    return errors


def save_position_from_form(position):
    position.name = request.form.get("name", "").strip()
    position.position_type = request.form.get("position_type", "revenue")
    position.status = request.form.get("status", "active")
    position.sort_order = parse_int(request.form.get("sort_order")) or 0

    errors = []
    if not position.name:
        errors.append("Bitte einen Positionsnamen eingeben.")

    return errors


def save_version_from_form(version, allow_valid_to=False):
    errors = []

    version.valid_from = parse_date(request.form.get("valid_from"))
    version.valid_to = parse_date(request.form.get("valid_to")) if allow_valid_to else None
    version.amount = parse_decimal(request.form.get("amount"))
    version.currency = request.form.get("currency", "EUR").strip() or "EUR"
    version.account = request.form.get("account", "").strip() or None
    version.cost_center_1 = request.form.get("cost_center_1", "").strip() or None
    version.cost_center_2 = request.form.get("cost_center_2", "").strip() or None
    version.recurrence = request.form.get("recurrence", "monthly")
    version.billing_day = parse_int(request.form.get("billing_day"))
    version.is_active = request.form.get("is_active") == "on"
    version.note = request.form.get("note", "").strip() or None

    if not version.valid_from:
        errors.append("Bitte ein Gueltig-ab-Datum eingeben.")
    if version.amount is None:
        errors.append("Bitte einen gueltigen Betrag eingeben.")
    if version.valid_from and version.valid_to and version.valid_to < version.valid_from:
        errors.append("Gueltig bis darf nicht vor Gueltig ab liegen.")
    if version.billing_day is not None and not 1 <= version.billing_day <= 31:
        errors.append("Der Abrechnungstag muss zwischen 1 und 31 liegen.")
    if not allow_valid_to and version.valid_from:
        position_id = version.position_id or version.position.id
        existing = ContractPositionVersion.query.filter_by(
            position_id=position_id,
            valid_from=version.valid_from,
        ).first()
        if existing:
            errors.append("Es gibt bereits eine Version mit diesem Gueltig-ab-Datum.")

    return errors


def close_previous_versions(position, valid_from):
    previous_valid_to = valid_from - timedelta(days=1)

    for old_version in position.versions:
        if old_version.valid_from < valid_from and (
            old_version.valid_to is None or old_version.valid_to >= valid_from
        ):
            old_version.valid_to = previous_valid_to


def get_latest_version(position):
    if not position.versions:
        return None
    return sorted(position.versions, key=lambda item: item.valid_from, reverse=True)[0]


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_decimal(value):
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def parse_int(value):
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
