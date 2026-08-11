"""
Logging configuration for Vertragsplaner.

Provides structured JSON logging with rotation and audit compliance features.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Default log directory (can be overridden via env)
LOG_DIR = Path(os.getenv("VERTRAGSPLANER_LOG_DIR", "logs"))
LOG_LEVEL = os.getenv("VERTRAGSPLANER_LOG_LEVEL", "INFO")
MAX_BYTES = int(os.getenv("VERTRAGSPLANER_LOG_MAX_BYTES", "10_000_000"))  # 10MB
BACKUP_COUNT = int(os.getenv("VERTRAGSPLANER_LOG_BACKUP_COUNT", "10"))


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Ensures audit compliance by including all required fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Add extra fields from record
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "username"):
            log_entry["username"] = record.username
        if hasattr(record, "api_token_name"):
            log_entry["api_token_name"] = record.api_token_name
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "resource_type"):
            log_entry["resource_type"] = record.resource_type
        if hasattr(record, "resource_id"):
            log_entry["resource_id"] = record.resource_id
        if hasattr(record, "changes"):
            log_entry["changes"] = record.changes
        if hasattr(record, "old_values"):
            log_entry["old_values"] = record.old_values
        if hasattr(record, "new_values"):
            log_entry["new_values"] = record.new_values
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "ip_address"):
            log_entry["ip_address"] = record.ip_address
        if hasattr(record, "user_agent"):
            log_entry["user_agent"] = record.user_agent
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        # Add any extra attributes from record
        for key, value in record.__dict__.items():
            if key not in {
                "timestamp", "level", "logger", "message", "source",
                "user_id", "username", "api_token_name", "action", "resource_type",
                "resource_id", "changes", "old_values", "new_values", "request_id",
                "method", "path", "ip_address", "user_agent", "status_code", "duration_ms",
                "name", "msg", "args", "levelno", "levelname", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "_cache"
            }:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class AuditFormatter(logging.Formatter):
    """
    Special formatter for audit logs - extra fields for GoBD/Revisionssicherheit.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base audit fields required for compliance
        audit_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "seq": getattr(record, "seq", None),  # Sequence number for tamper detection
            "hash": getattr(record, "prev_hash", None),  # Chain hash for tamper detection
        }

        # Who
        if hasattr(record, "user_id"):
            audit_entry["user_id"] = record.user_id
        if hasattr(record, "username"):
            audit_entry["username"] = record.username
        if hasattr(record, "api_token_name"):
            audit_entry["api_token_name"] = record.api_token_name

        # What
        audit_entry["action"] = getattr(record, "action", "unknown")
        audit_entry["resource_type"] = getattr(record, "resource_type", "unknown")
        audit_entry["resource_id"] = getattr(record, "resource_id", None)

        # Before/After values for data changes
        if hasattr(record, "old_values"):
            audit_entry["old_values"] = record.old_values
        if hasattr(record, "new_values"):
            audit_entry["new_values"] = record.new_values

        # Context
        if hasattr(record, "request_id"):
            audit_entry["request_id"] = record.request_id
        if hasattr(record, "ip_address"):
            audit_entry["ip_address"] = record.ip_address

        # Message
        audit_entry["message"] = record.getMessage()

        return json.dumps(audit_entry, ensure_ascii=False, default=str)


def setup_logging() -> None:
    """
    Configure logging for the application.
    Call this once during app initialization.
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates
    root_logger.handlers = []

    # Console handler (for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Application log (rotating)
    app_log_path = LOG_DIR / "app.log"
    app_handler = logging.handlers.RotatingFileHandler(
        app_log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(app_handler)

    # Error log (rotating) - only WARNING and above
    error_log_path = LOG_DIR / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # Audit log (separate, with special formatter)
    audit_log_path = LOG_DIR / "audit.log"
    audit_handler = logging.handlers.RotatingFileHandler(
        audit_log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(AuditFormatter())

    # Audit logger
    audit_logger = logging.getLogger("vertragsplaner.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.handlers = [audit_handler]
    audit_logger.propagate = False  # Don't duplicate to root

    # Access log (HTTP requests)
    access_log_path = LOG_DIR / "access.log"
    access_handler = logging.handlers.RotatingFileHandler(
        access_log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(JSONFormatter())

    access_logger = logging.getLogger("vertragsplaner.access")
    access_logger.setLevel(logging.INFO)
    access_logger.handlers = [access_handler]
    access_logger.propagate = False

    # Log startup
    logging.info("Logging initialized", extra={
        "log_dir": str(LOG_DIR),
        "log_level": LOG_LEVEL,
    })


def get_audit_logger() -> logging.Logger:
    """Get the audit logger for data change events."""
    return logging.getLogger("vertragsplaner.audit")


def get_access_logger() -> logging.Logger:
    """Get the access logger for HTTP requests."""
    return logging.getLogger("vertragsplaner.access")


# Convenience function for audit logging
def log_audit(
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    api_token_name: Optional[str] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """
    Log an audit event.

    Args:
        action: The action performed (create, update, delete, login, etc.)
        resource_type: The type of resource affected (customer, contract, etc.)
        resource_id: The ID of the affected resource
        old_values: Previous values (for updates/deletes)
        new_values: New values (for creates/updates)
        user_id: ID of the user who performed the action
        username: Username of the user
        api_token_name: Name of API token if used
        request_id: Request ID for correlation
        ip_address: Client IP address
        message: Optional human-readable message
    """
    logger = get_audit_logger()

    extra = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "old_values": old_values,
        "new_values": new_values,
        "user_id": user_id,
        "username": username,
        "api_token_name": api_token_name,
        "request_id": request_id,
        "ip_address": ip_address,
    }

    # Remove None values for cleaner logs
    extra = {k: v for k, v in extra.items() if v is not None}

    msg = message or f"{action} {resource_type}"
    if resource_id:
        msg += f" #{resource_id}"

    logger.info(msg, extra=extra)
