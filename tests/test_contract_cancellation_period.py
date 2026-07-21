import os
import unittest
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app, db
from app.auth import hash_secret
from app.models import Contract, Customer, User


class ContractCancellationPeriodTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()
            db.session.add(User(
                username="writer",
                password_hash=hash_secret("writer-pass"),
                role="write",
                is_active=True,
            ))
            db.session.add(Customer(name="Testkunde", status="active"))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self):
        return self.client.post("/login", data={"username": "writer", "password": "writer-pass"})

    def add_contract(self, title, end_date, value, unit, status="active"):
        customer = Customer.query.filter_by(name="Testkunde").first()
        contract = Contract(
            customer=customer,
            title=title,
            contract_type="revenue",
            status=status,
            start_date=date(2026, 1, 1),
            end_date=end_date,
            cancellation_period_value=value,
            cancellation_period_unit=unit,
            renewal_type="none",
        )
        db.session.add(contract)
        db.session.commit()
        return contract

    def test_cancellation_deadline_and_label_are_calculated(self):
        with self.app.app_context():
            contract = self.add_contract("Monatsfrist", date(2026, 12, 31), 3, "months")
            self.assertEqual(contract.cancellation_period_label, "3 Monate")
            self.assertEqual(contract.cancellation_deadline, date(2026, 9, 30))

            week_contract = self.add_contract("Wochenfrist", date(2026, 12, 31), 2, "weeks")
            self.assertEqual(week_contract.cancellation_period_label, "2 Wochen")
            self.assertEqual(week_contract.cancellation_deadline, date(2026, 12, 17))

    def test_cancellation_period_is_saved_and_rendered(self):
        self.login()
        with self.app.app_context():
            customer_id = Customer.query.filter_by(name="Testkunde").first().id

        response = self.client.post("/contracts/new", data={
            "partner_type": "customer",
            "customer_id": str(customer_id),
            "title": "Vertrag mit Kuendigungsfrist",
            "contract_type": "revenue",
            "status": "active",
            "start_date": date(2026, 1, 1).isoformat(),
            "end_date": date(2026, 12, 31).isoformat(),
            "cancellation_period_value": "3",
            "cancellation_period_unit": "months",
            "renewal_type": "none",
        })
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            contract = Contract.query.filter_by(title="Vertrag mit Kuendigungsfrist").first()
            self.assertEqual(contract.cancellation_period_value, 3)
            self.assertEqual(contract.cancellation_period_unit, "months")
            contract_id = contract.id

        detail = self.client.get(f"/contracts/{contract_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"3 Monate", detail.data)
        self.assertIn(b"2026-09-30", detail.data)

    def test_cancellation_due_filter(self):
        self.login()
        with self.app.app_context():
            self.add_contract("Bald kuendbar", date(2026, 12, 31), 3, "months")
            self.add_contract("Spaeter kuendbar", date(2027, 12, 31), 3, "months")

            # Freeze the filter helper's date by monkey-patching the imported date class.
            from app.routes import contracts as contracts_route
            old_date = contracts_route.date

            class FrozenDate(date):
                @classmethod
                def today(cls):
                    return cls(2026, 8, 1)

            contracts_route.date = FrozenDate
            try:
                response = self.client.get("/contracts/?cancellation_due=90")
            finally:
                contracts_route.date = old_date

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bald kuendbar", response.data)
        self.assertNotIn(b"Spaeter kuendbar", response.data)


if __name__ == "__main__":
    unittest.main()
