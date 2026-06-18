from flask import Flask, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

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
        load_logged_in_user()

        if request.endpoint in {None, "auth.login", "static"}:
            return None
        if request.path.startswith("/api/v1"):
            return None
        if current_user() is None:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return None

    @app.context_processor
    def inject_auth_helpers():
        return {
            "current_user": current_user,
            "can_write": can_write,
            "can_admin": can_admin,
        }

    return app
