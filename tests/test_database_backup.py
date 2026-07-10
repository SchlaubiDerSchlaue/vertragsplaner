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
from app.models import Contract, ContractPosition, ContractPositionVersion, Customer, User


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

    def test_export_and_import_roundtrip_replaces_database(self):
        with self.app.app_context():
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
                customer,
                contract,
                position,
                version,
            ])
            db.session.commit()

            backup = export_database_backup()

            db.session.add(Customer(name="Wird ersetzt"))
            db.session.commit()
            backup.seek(0)
            imported = import_database_backup(FileStorage(stream=backup, filename="backup.json"))

            self.assertEqual(imported, 5)
            self.assertEqual(Customer.query.count(), 1)
            self.assertEqual(Customer.query.first().name, "Testkunde")
            self.assertEqual(ContractPositionVersion.query.first().amount, Decimal("123.45"))


if __name__ == "__main__":
    unittest.main()
