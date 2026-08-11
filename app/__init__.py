from flask import Flask, g, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

from app.logging_config import setup_logging, get_access_logger
from app.audit import init_audit_listeners

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Initialize logging before database
    setup_logging()

    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize audit listeners after db
    init_audit_listeners(app)

    from app.routes.dashboard import dashboard_bp
    from app.routes.customers import customers_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.contracts import contracts_bp
    from app.routes.planning import planning_bp
    from app.routes.imports import imports_bp
    from app.routes.exports import exports_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.auth import can_admin, can_write, current_user, load_logged_in_user

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(suppliers_bp, url_prefix="/suppliers")
    app.register_blueprint(contracts_bp, url_prefix="/contracts")
    app.register_blueprint(planning_bp, url_prefix="/planning")
    app.register_blueprint(imports_bp, url_prefix="/imports")
    app.register_blueprint(exports_bp, url_prefix="/exports")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.before_request
    def require_web_login():
        # Generate request ID for correlation across logs
        import uuid
        import time
        request.request_id = str(uuid.uuid4())[:8]
        request._start_time = time.time()

        load_logged_in_user()

        if request.endpoint in {None, "auth.login", "static"}:
            return None
        if request.path.startswith("/api/v1"):
            return None
        if current_user() is None:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return None

    @app.after_request
    def log_access(response):
        """Log all HTTP requests for audit trail."""
        access_logger = get_access_logger()

        # Get user context
        user_id = None
        username = None
        api_token_name = None
        current_user_obj = current_user()
        if current_user_obj:
            user_id = current_user_obj.id
            username = current_user_obj.username
        elif hasattr(g, "api_token"):
            api_token_name = g.api_token.name

        # Calculate duration
        duration_ms = None
        if hasattr(request, "_start_time"):
            import time
            duration_ms = round((time.time() - request._start_time) * 1000, 3)

        access_logger.info(
            f"{request.method} {request.path}",
            extra={
                "request_id": getattr(request, "request_id", None),
                "method": request.method,
                "path": request.path,
                "ip_address": request.remote_addr,
                "user_agent": request.user_agent.string if request.user_agent else None,
                "user_id": user_id,
                "username": username,
                "api_token_name": api_token_name,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.context_processor
    def inject_auth_helpers():
        return {
            "current_user": current_user,
            "can_write": can_write,
            "can_admin": can_admin,
        }

    # Log startup
    app.logger.info("Vertragsplaner application started")

    return app
