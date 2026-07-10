import os
import unittest
from datetime import date
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from werkzeug.datastructures import FileStorage

from app import create_app, db
from app.auth import hash_secret
from app.database_backup import export_database_backup, import_database_backup
from app.models import ApiToken, Contract, ContractPosition, ContractPositionVersion, Customer, User


class DatabaseBackupTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_sample_data(self):
        customer = Customer(name="Testkunde", status="active")
        contract = Contract(
            customer=customer,
            title="Testvertrag",
            contract_type="revenue",
            status="active",
            start_date=date(2026, 1, 1),
        )
        position = ContractPosition(contract=contract, name="Monatlich", position_type="revenue")
        version = ContractPositionVersion(
            position=position,
            valid_from=date(2026, 1, 1),
            amount=Decimal("123.45"),
            currency="EUR",
            recurrence="monthly",
        )
        db.session.add_all([
            User(username="admin", password_hash=hash_secret("secret"), role="admin"),
            ApiToken(name="api", token_hash=hash_secret("token"), role="admin"),
            customer,
            contract,
            position,
            version,
        ])
        db.session.commit()

    def test_export_and_import_roundtrip_replaces_database(self):
        with self.app.app_context():
            self.create_sample_data()

            backup = export_database_backup()

            db.session.add(Customer(name="Wird ersetzt"))
            db.session.commit()
            backup.seek(0)
            imported = import_database_backup(FileStorage(stream=backup, filename="backup.json"))

            self.assertEqual(imported, 6)
            self.assertEqual(User.query.count(), 1)
            self.assertEqual(ApiToken.query.count(), 1)
            self.assertEqual(Customer.query.count(), 1)
            self.assertEqual(Customer.query.first().name, "Testkunde")
            self.assertEqual(ContractPositionVersion.query.first().amount, Decimal("123.45"))

    def test_contract_data_backup_excludes_and_preserves_users_and_tokens(self):
        with self.app.app_context():
            self.create_sample_data()

            backup = export_database_backup(include_auth=False)
            self.assertNotIn(b'"user"', backup.getvalue())
            self.assertNotIn(b'"api_token"', backup.getvalue())

            User.query.filter_by(username="admin").first().username = "existing-admin"
            ApiToken.query.filter_by(name="api").first().name = "existing-token"
            db.session.add(Customer(name="Wird ersetzt"))
            db.session.commit()

            backup.seek(0)
            imported = import_database_backup(FileStorage(stream=backup, filename="backup.json"))

            self.assertEqual(imported, 4)
            self.assertEqual(User.query.first().username, "existing-admin")
            self.assertEqual(ApiToken.query.first().name, "existing-token")
            self.assertEqual(Customer.query.count(), 1)
            self.assertEqual(Customer.query.first().name, "Testkunde")


if __name__ == "__main__":
    unittest.main()
