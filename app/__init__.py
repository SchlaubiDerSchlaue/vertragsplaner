from flask import Flask
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

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(suppliers_bp, url_prefix="/suppliers")
    app.register_blueprint(contracts_bp, url_prefix="/contracts")
    app.register_blueprint(planning_bp, url_prefix="/planning")
    app.register_blueprint(imports_bp, url_prefix="/imports")
    app.register_blueprint(exports_bp, url_prefix="/exports")

    return app
