from flask import Blueprint, flash, redirect, render_template, request, url_for
from app import db
from app.auth import write_required
from app.models import Customer
from app.routes.listing import active_filters, apply_sort, get_list_params

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/")
def list_customers():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sort, direction = get_list_params("name")

    query = Customer.query
    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                Customer.customer_no.ilike(search),
                Customer.name.ilike(search),
                Customer.contact_name.ilike(search),
                Customer.email.ilike(search),
                Customer.city.ilike(search),
            )
        )
    if status:
        query = query.filter(Customer.status == status)

    sort_map = {
        "customer_no": Customer.customer_no,
        "name": Customer.name,
        "status": Customer.status,
        "email": Customer.email,
        "city": Customer.city,
        "created_at": Customer.created_at,
    }
    customers = apply_sort(query, sort, direction, sort_map, "name").all()
    statuses = [row[0] for row in db.session.query(Customer.status).distinct().order_by(Customer.status).all() if row[0]]

    return render_template(
        "customers.html",
        customers=customers,
        filters={"q": q, "status": status},
        sort=sort,
        direction=direction,
        sort_filters=active_filters(q=q, status=status),
        statuses=statuses,
    )


@customers_bp.route("/new", methods=["GET", "POST"])
@write_required
def new_customer():
    customer = Customer(status="active")

    if request.method == "POST":
        errors = save_customer_from_form(customer)
        if not errors:
            db.session.add(customer)
            db.session.commit()
            flash("Kunde wurde angelegt.", "success")
            return redirect(url_for("customers.list_customers"))

        for error in errors:
            flash(error, "danger")

    return render_template("customer_form.html", customer=customer, mode="new")


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@write_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if request.method == "POST":
        errors = save_customer_from_form(customer)
        if not errors:
            db.session.commit()
            flash("Kunde wurde gespeichert.", "success")
            return redirect(url_for("customers.list_customers"))

        for error in errors:
            flash(error, "danger")

    return render_template("customer_form.html", customer=customer, mode="edit")


def save_customer_from_form(customer):
    customer.customer_no = request.form.get("customer_no", "").strip() or None
    customer.name = request.form.get("name", "").strip()
    customer.status = request.form.get("status", "active")
    customer.contact_name = request.form.get("contact_name", "").strip() or None
    customer.email = request.form.get("email", "").strip() or None
    customer.street = request.form.get("street", "").strip() or None
    customer.postal_code = request.form.get("postal_code", "").strip() or None
    customer.city = request.form.get("city", "").strip() or None
    customer.country = request.form.get("country", "").strip() or None
    customer.notes = request.form.get("notes", "").strip() or None

    errors = []
    if not customer.name:
        errors.append("Bitte einen Kundennamen eingeben.")

    existing = Customer.query.filter(Customer.name == customer.name).first()
    if existing and existing.id != customer.id:
        errors.append("Ein Kunde mit diesem Namen existiert bereits.")

    return errors
