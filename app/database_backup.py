from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
import json

from sqlalchemy import delete

from app import db
from app.models import ApiToken, Contract, ContractPosition, ContractPositionVersion, Customer, Supplier, User

BACKUP_VERSION = 1
BACKUP_MODELS = [User, ApiToken, Customer, Supplier, Contract, ContractPosition, ContractPositionVersion]
DELETE_ORDER = [ContractPositionVersion, ContractPosition, Contract, Customer, Supplier, ApiToken, User]


def _serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _deserialize_value(column, value):
    if value is None:
        return None

    python_type = column.type.python_type
    if python_type is datetime:
        return datetime.fromisoformat(value)
    if python_type is date:
        return date.fromisoformat(value)
    if python_type is Decimal:
        return Decimal(str(value))
    if python_type is bool:
        return bool(value)
    return value


def export_database_backup():
    data = {
        "version": BACKUP_VERSION,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "tables": {},
    }

    for model in BACKUP_MODELS:
        rows = []
        columns = model.__table__.columns
        for item in model.query.order_by(model.id).all():
            rows.append({column.name: _serialize_value(getattr(item, column.name)) for column in columns})
        data["tables"][model.__tablename__] = rows

    output = BytesIO()
    output.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    output.seek(0)
    return output


def import_database_backup(file_storage):
    try:
        payload = json.load(file_storage.stream)
    except json.JSONDecodeError as exc:
        raise ValueError("Die Sicherungsdatei ist keine gültige JSON-Datei.") from exc

    if payload.get("version") != BACKUP_VERSION or not isinstance(payload.get("tables"), dict):
        raise ValueError("Die Sicherungsdatei hat ein unbekanntes Format.")

    tables = payload["tables"]

    for model in BACKUP_MODELS:
        if model.__tablename__ not in tables:
            raise ValueError(f"Tabelle fehlt in Sicherung: {model.__tablename__}")

    try:
        for model in DELETE_ORDER:
            db.session.execute(delete(model))

        imported = 0
        for model in BACKUP_MODELS:
            columns = {column.name: column for column in model.__table__.columns}
            for row in tables[model.__tablename__]:
                unknown = set(row) - set(columns)
                if unknown:
                    raise ValueError(
                        f"Unbekannte Spalten in {model.__tablename__}: {', '.join(sorted(unknown))}"
                    )
                item = model(**{
                    name: _deserialize_value(columns[name], value)
                    for name, value in row.items()
                })
                db.session.add(item)
                imported += 1

        db.session.commit()
        return imported
    except Exception:
        db.session.rollback()
        raise
