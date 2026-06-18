from flask import Blueprint, flash, redirect, render_template, request, url_for
from app import db
from app.auth import write_required
from app.models import Supplier
from app.routes.listing import active_filters, apply_sort, get_list_params

suppliers_bp = Blueprint("suppliers", __name__)


@suppliers_bp.route("/")
def list_suppliers():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sort, direction = get_list_params("name")

    query = Supplier.query
    if q:
        search = f"%{q}%"
        query = query.filter(
            db.or_(
                Supplier.supplier_no.ilike(search),
                Supplier.name.ilike(search),
                Supplier.contact_name.ilike(search),
                Supplier.email.ilike(search),
                Supplier.city.ilike(search),
            )
        )
    if status:
        query = query.filter(Supplier.status == status)

    sort_map = {
        "supplier_no": Supplier.supplier_no,
        "name": Supplier.name,
        "status": Supplier.status,
        "email": Supplier.email,
        "city": Supplier.city,
        "created_at": Supplier.created_at,
    }
    suppliers = apply_sort(query, sort, direction, sort_map, "name").all()
    statuses = [row[0] for row in db.session.query(Supplier.status).distinct().order_by(Supplier.status).all() if row[0]]

    return render_template(
        "suppliers.html",
        suppliers=suppliers,
        filters={"q": q, "status": status},
        sort=sort,
        direction=direction,
        sort_filters=active_filters(q=q, status=status),
        statuses=statuses,
    )


@suppliers_bp.route("/new", methods=["GET", "POST"])
@write_required
def new_supplier():
    supplier = Supplier(status="active")

    if request.method == "POST":
        errors = save_supplier_from_form(supplier)
        if not errors:
            db.session.add(supplier)
            db.session.commit()
            flash("Lieferant wurde angelegt.", "success")
            return redirect(url_for("suppliers.list_suppliers"))

        for error in errors:
            flash(error, "danger")

    return render_template("supplier_form.html", supplier=supplier, mode="new")


@suppliers_bp.route("/<int:supplier_id>/edit", methods=["GET", "POST"])
@write_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    if request.method == "POST":
        errors = save_supplier_from_form(supplier)
        if not errors:
            db.session.commit()
            flash("Lieferant wurde gespeichert.", "success")
            return redirect(url_for("suppliers.list_suppliers"))

        for error in errors:
            flash(error, "danger")

    return render_template("supplier_form.html", supplier=supplier, mode="edit")


def save_supplier_from_form(supplier):
    supplier.supplier_no = request.form.get("supplier_no", "").strip() or None
    supplier.name = request.form.get("name", "").strip()
    supplier.status = request.form.get("status", "active")
    supplier.contact_name = request.form.get("contact_name", "").strip() or None
    supplier.email = request.form.get("email", "").strip() or None
    supplier.street = request.form.get("street", "").strip() or None
    supplier.postal_code = request.form.get("postal_code", "").strip() or None
    supplier.city = request.form.get("city", "").strip() or None
    supplier.country = request.form.get("country", "").strip() or None
    supplier.notes = request.form.get("notes", "").strip() or None

    errors = []
    if not supplier.name:
        errors.append("Bitte einen Lieferantennamen eingeben.")

    existing = Supplier.query.filter(Supplier.name == supplier.name).first()
    if existing and existing.id != supplier.id:
        errors.append("Ein Lieferant mit diesem Namen existiert bereits.")

    return errors
