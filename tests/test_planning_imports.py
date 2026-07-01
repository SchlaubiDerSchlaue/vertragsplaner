import csv
import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app, db
from app.imports import import_contract_rows
from app.models import Customer, Contract, ContractPosition, ContractPositionVersion
from app.planning import generate_planning_lines


class PlanningAndImportTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.session.remove()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def add_contract_with_version(self, status="active"):
        customer = Customer(name=f"Kunde {status}")
        contract = Contract(
            customer=customer,
            title=f"Vertrag {status}",
            contract_type="revenue",
            status=status,
            start_date=date(2026, 1, 1),
        )
        position = ContractPosition(
            contract=contract,
            name="Grundgebuehr",
            position_type="revenue",
            status="active",
        )
        version = ContractPositionVersion(
            position=position,
            valid_from=date(2026, 1, 1),
            amount=Decimal("100.00"),
            recurrence="monthly",
        )
        db.session.add_all([customer, contract, position, version])
        db.session.commit()
        return contract

    def test_cancelled_contract_is_excluded_from_planning(self):
        self.add_contract_with_version(status="active")
        self.add_contract_with_version(status="cancelled")

        lines = generate_planning_lines(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            include_revenue=True,
        )

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["contract_status"], "active")

    def test_import_closes_previous_version(self):
        customer = Customer(name="Importkunde")
        contract = Contract(
            customer=customer,
            title="Importvertrag",
            contract_type="revenue",
            status="active",
            start_date=date(2026, 1, 1),
        )
        position = ContractPosition(
            contract=contract,
            name="Lizenz",
            position_type="revenue",
            status="active",
        )
        old_version = ContractPositionVersion(
            position=position,
            valid_from=date(2026, 1, 1),
            amount=Decimal("100.00"),
            recurrence="monthly",
        )
        db.session.add_all([customer, contract, position, old_version])
        db.session.commit()

        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            with open(path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=[
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
                ])
                writer.writeheader()
                writer.writerow({
                    "customer_name": "Importkunde",
                    "contract_title": "Importvertrag",
                    "status": "active",
                    "position_name": "Lizenz",
                    "valid_from": "2026-04-01",
                    "amount": "120.00",
                    "account": "8400",
                    "cost_center_1": "CC1",
                    "cost_center_2": "CC2",
                    "recurrence": "monthly",
                })

            imported = import_contract_rows(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

        db.session.refresh(old_version)
        versions = ContractPositionVersion.query.order_by(ContractPositionVersion.valid_from).all()
        self.assertEqual(imported, 1)
        self.assertEqual(len(versions), 2)
        self.assertEqual(old_version.valid_to, date(2026, 3, 31))


if __name__ == "__main__":
    unittest.main()
