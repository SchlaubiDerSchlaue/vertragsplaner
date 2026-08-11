"""
Audit logging for Vertragsplaner.

SQLAlchemy event listeners that automatically track data changes
for audit compliance (GoBD/Revisionssicherheit).
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import event
from sqlalchemy.orm import Session as SA_Session
from sqlalchemy.orm.attributes import get_history

from app.logging_config import get_audit_logger, log_audit

# Model name mapping for human-readable resource types
MODEL_NAMES = {
    "customer": "Kunde",
    "supplier": "Lieferant",
    "contract": "Vertrag",
    "contract_position": "Vertragsposition",
    "contract_position_version": "Positionsversion",
    "user": "Benutzer",
    "api_token": "API-Token",
}


def _get_table_name(model: Any) -> str:
    """Get the database table name from a model."""
    return getattr(model, "__tablename__", type(model).__name__.lower())


def _get_resource_type(model: Any) -> str:
    """Get the human-readable resource type."""
    table = _get_table_name(model)
    return MODEL_NAMES.get(table, table)


def _get_model_pk(model: Any) -> Optional[int]:
    """Get the primary key value of a model instance."""
    return getattr(model, "id", None)


def _serializable_value(value: Any) -> Any:
    """Convert a value to a JSON-serializable format."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        # date, time, etc.
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    # Fallback: convert to string
    try:
        return str(value)
    except Exception:
        return repr(value)


def _get_model_fields(model: Any) -> Dict[str, Any]:
    """Extract serializable field values from a model instance."""
    fields = {}
    mapper = model.__mapper__ if hasattr(model, "__mapper__") else None
    if mapper is None:
        return fields

    for column in mapper.column_attrs:
        key = column.key
        try:
            value = getattr(model, key, None)
            fields[key] = _serializable_value(value)
        except Exception:
            fields[key] = "<error reading value>"

    return fields


def _get_changed_fields(model: Any) -> Dict[str, Dict[str, Any]]:
    """
    Get changed fields using SQLAlchemy history.
    Returns dict with old_values and new_values.
    """
    old_values = {}
    new_values = {}

    mapper = model.__mapper__ if hasattr(model, "__mapper__") else None
    if mapper is None:
        return {"old_values": old_values, "new_values": new_values}

    for column in mapper.column_attrs:
        key = column.key
        try:
            history = get_history(model, key)
            if history.has_changes():
                # history.deleted contains old values, history.added contains new values
                if history.deleted:
                    old_values[key] = _serializable_value(history.deleted[0])
                if history.added:
                    new_values[key] = _serializable_value(history.added[0])
        except Exception:
            pass

    return {"old_values": old_values, "new_values": new_values}


def _extract_user_context(session: Any) -> Dict[str, Any]:
    """
    Try to extract user context from the current Flask request/session.
    This is set by the request logging middleware.
    """
    try:
        from flask import g, request
        context = {}

        # Web user context
        current_user = getattr(g, "current_user", None)
        if current_user:
            context["user_id"] = current_user.id
            context["username"] = current_user.username

        # API token context
        api_token = getattr(g, "api_token", None)
        if api_token:
            context["api_token_name"] = api_token.name

        # Request context
        if request:
            context["request_id"] = getattr(request, "request_id", None)
            context["ip_address"] = request.remote_addr

        return {k: v for k, v in context.items() if v is not None}
    except (RuntimeError, ImportError):
        # Outside of Flask request context
        return {}


def _log_action(action: str, model: Any, session: Any, **kwargs) -> None:
    """Central logging function for audit events."""
    resource_type = _get_resource_type(model)
    resource_id = _get_model_pk(model)
    user_context = _extract_user_context(session)

    log_audit(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_context.get("user_id"),
        username=user_context.get("username"),
        api_token_name=user_context.get("api_token_name"),
        request_id=user_context.get("request_id"),
        ip_address=user_context.get("ip_address"),
        **kwargs,
    )


@event.listens_for(SA_Session, "before_flush")
def audit_before_flush(session, flush_context, instances) -> None:
    """
    SQLAlchemy event listener that logs all INSERT, UPDATE, DELETE operations.
    Fires before the actual database write for full before/after tracking.
    """
    logger = get_audit_logger()

    # New objects (INSERT)
    for obj in session.new:
        resource_type = _get_resource_type(obj)
        resource_id = _get_model_pk(obj)

        _log_action(
            action="create",
            model=obj,
            session=session,
            new_values=_get_model_fields(obj),
            message=f"Erstellt: {resource_type}",
        )

    # Dirty objects (UPDATE)
    for obj in session.dirty:
        changes = _get_changed_fields(obj)
        if not changes["old_values"] and not changes["new_values"]:
            continue

        resource_type = _get_resource_type(obj)
        resource_id = _get_model_pk(obj)

        _log_action(
            action="update",
            model=obj,
            session=session,
            old_values=changes["old_values"],
            new_values=changes["new_values"],
            message=f"Geändert: {resource_type}",
        )

    # Deleted objects (DELETE)
    for obj in session.deleted:
        resource_type = _get_resource_type(obj)
        resource_id = _get_model_pk(obj)

        _log_action(
            action="delete",
            model=obj,
            session=session,
            old_values=_get_model_fields(obj),
            message=f"Gelöscht: {resource_type}",
        )


def init_audit_listeners(app: Any) -> None:
    """
    Initialize audit event listeners with the Flask app's database.
    Call this during app setup after the db is initialized.
    """
    from app import db

    # The event listener is registered at the Session class level,
    # so it automatically applies to all sessions using that class.
    # No additional setup needed - the decorator above handles it.

    app.logger.info("Audit event listeners initialized")
