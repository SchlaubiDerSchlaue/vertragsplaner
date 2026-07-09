import os
import unittest
from datetime import date
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app, db
from app.models import Contract, ContractPosition, ContractPositionVersion, Customer
from app.planning import contract_effective_end_date, contract_is_valid, generate_planning_lines, last_day_of_month


class ContractTermPlanningTestCase(unittest.TestCase):
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

    def add_contract(self, *, status="active", end_date=None, cancellation_date=None, renewal_type="none"):
        customer = Customer(name="Testkunde", status="active")
        contract = Contract(
            customer=customer,
            title="Testvertrag",
            contract_type="revenue",
            status=status,
            start_date=date(2026, 1, 1),
            end_date=end_date,
            cancellation_date=cancellation_date,
            renewal_type=renewal_type,
        )
        position = ContractPosition(
            contract=contract,
            name="Monatliche Position",
            position_type="revenue",
            status="active",
        )
        version = ContractPositionVersion(
            position=position,
            valid_from=date(2026, 1, 1),
            amount=Decimal("100.00"),
            currency="EUR",
            recurrence="monthly",
            is_active=True,
        )
        db.session.add_all([customer, contract, position, version])
        db.session.commit()
        return contract

    def planned_months(self):
        lines = generate_planning_lines(date(2026, 6, 1), date(2026, 8, 31))
        return [line["month"] for line in lines]

    def test_manual_or_no_renewal_ends_after_end_date(self):
        with self.app.app_context():
            self.add_contract(end_date=date(2026, 6, 30), renewal_type="manual")
            self.assertEqual(self.planned_months(), ["2026-06"])

    def test_automatic_renewal_continues_past_end_date_without_cancellation(self):
        with self.app.app_context():
            contract = self.add_contract(end_date=date(2026, 6, 30), renewal_type="automatic")

            self.assertIsNone(contract_effective_end_date(contract))
            self.assertEqual(self.planned_months(), ["2026-06", "2026-07", "2026-08"])

    def test_cancellation_date_stops_automatic_renewal(self):
        with self.app.app_context():
            contract = self.add_contract(
                end_date=date(2026, 6, 30),
                cancellation_date=date(2026, 7, 15),
                renewal_type="automatic",
            )

            self.assertEqual(contract_effective_end_date(contract), date(2026, 7, 15))
            self.assertEqual(self.planned_months(), ["2026-06", "2026-07"])

    def test_cancelled_status_is_planned_until_effective_end(self):
        with self.app.app_context():
            contract = self.add_contract(
                status="cancelled",
                end_date=date(2026, 7, 31),
                renewal_type="none",
            )

            self.assertTrue(contract_is_valid(contract, date(2026, 7, 1), last_day_of_month(date(2026, 7, 1))))
            self.assertFalse(contract_is_valid(contract, date(2026, 8, 1), last_day_of_month(date(2026, 8, 1))))
            self.assertEqual(self.planned_months(), ["2026-06", "2026-07"])


if __name__ == "__main__":
    unittest.main()
