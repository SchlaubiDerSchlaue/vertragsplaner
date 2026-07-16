import pandas as pd
from app import db
from app.models import Customer, Supplier, Contract, ContractPosition, ContractPositionVersion


def read_import_file(file_path):
    suffix = str(file_path).lower()

    if suffix.endswith(".csv"):
        return pd.read_csv(file_path, sep=None, engine="python")

    if suffix.endswith(".xlsx"):
        return pd.read_excel(file_path)

    raise ValueError("Nur CSV- und Excel-Dateien werden unterstützt.")


def clean_value(value, default=None):
    if pd.isna(value):
        return default
    return value


def import_contract_rows(file_path):
    df = read_import_file(file_path)

    required_columns = [
        "customer_name",
        "contract_title",
        "status",
        "position_name",
        "valid_from",
        "amount",
        "account",
        "cost_center_1",
        "cost_center_2",
        "recurrence",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Fehlende Spalten: {', '.join(missing)}")

    imported = 0

    for _, row in df.iterrows():
        partner_type = str(clean_value(row.get("partner_type"), "customer")).strip().lower()
        customer_name = str(clean_value(row.get("customer_name"), "")).strip()
        supplier_name = str(clean_value(row.get("supplier_name"), customer_name)).strip()
        contract_title = str(row["contract_title"]).strip()
        position_name = str(row["position_name"]).strip()

        customer = None
        supplier = None

        if partner_type == "supplier":
            supplier = Supplier.query.filter_by(name=supplier_name).first()

            if not supplier:
                supplier = Supplier(
                    name=supplier_name,
                    supplier_no=clean_value(row.get("supplier_no")),
                )
                db.session.add(supplier)
                db.session.flush()
        else:
            customer = Customer.query.filter_by(name=customer_name).first()

            if not customer:
                customer = Customer(
                    name=customer_name,
                    customer_no=clean_value(row.get("customer_no")),
                )
                db.session.add(customer)
                db.session.flush()

        contract_filter = {"title": contract_title}
        if supplier:
            contract_filter["supplier_id"] = supplier.id
        else:
            contract_filter["customer_id"] = customer.id

        contract = Contract.query.filter_by(**contract_filter).first()

        valid_from = pd.to_datetime(row["valid_from"]).date()

        if not contract:
            contract_start_raw = clean_value(row.get("contract_start"))
            contract_end_raw = clean_value(row.get("contract_end"))

            contract = Contract(
                customer_id=customer.id if customer else None,
                supplier_id=supplier.id if supplier else None,
                contract_no=clean_value(row.get("contract_no")),
                title=contract_title,
                status=clean_value(row.get("status"), "active"),
                contract_type=clean_value(row.get("contract_type"), "cost" if supplier else "revenue"),
                start_date=pd.to_datetime(contract_start_raw).date() if contract_start_raw else valid_from,
                end_date=pd.to_datetime(contract_end_raw).date() if contract_end_raw else None,
                contract_link=clean_value(row.get("contract_link")),
                invoice_link=clean_value(row.get("invoice_link")),
            )
            db.session.add(contract)
            db.session.flush()

        position = ContractPosition.query.filter_by(
            contract_id=contract.id,
            name=position_name
        ).first()

        if not position:
            position = ContractPosition(
                contract_id=contract.id,
                name=position_name,
                position_type=clean_value(
                    row.get("position_type"),
                    clean_value(row.get("contract_type"), "revenue")
                ),
            )
            db.session.add(position)
            db.session.flush()

        version = ContractPositionVersion(
            position_id=position.id,
            valid_from=valid_from,
            amount=row["amount"],
            currency=clean_value(row.get("currency"), "EUR"),
            account=str(clean_value(row.get("account"), "")),
            cost_center_1=str(clean_value(row.get("cost_center_1"), "")),
            cost_center_2=str(clean_value(row.get("cost_center_2"), "")),
            recurrence=clean_value(row.get("recurrence"), "monthly"),
        )

        db.session.add(version)
        imported += 1

    db.session.commit()
    return imported
