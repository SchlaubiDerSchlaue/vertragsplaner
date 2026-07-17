import os
import unittest
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app, db
from app.auth import hash_secret
from app.models import Contract, Customer, User


class ContractLinksTestCase(unittest.TestCase):
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

    def test_contract_links_are_saved_and_rendered(self):
        self.login()
        with self.app.app_context():
            customer_id = Customer.query.filter_by(name="Testkunde").first().id

        response = self.client.post("/contracts/new", data={
            "partner_type": "customer",
            "customer_id": str(customer_id),
            "contract_no": "V-1",
            "title": "Vertrag mit Links",
            "contract_type": "revenue",
            "status": "active",
            "start_date": date(2026, 1, 1).isoformat(),
            "renewal_type": "none",
            "responsible": "Claudia",
            "contract_link": "example.com/vertrag",
            "invoice_link": "https://example.com/rechnungen",
        })
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            contract = Contract.query.filter_by(title="Vertrag mit Links").first()
            self.assertEqual(contract.contract_link, "https://example.com/vertrag")
            self.assertEqual(contract.invoice_link, "https://example.com/rechnungen")
            contract_id = contract.id

        detail = self.client.get(f"/contracts/{contract_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"https://example.com/vertrag", detail.data)
        self.assertIn(b"https://example.com/rechnungen", detail.data)

        overview = self.client.get("/contracts/")
        self.assertEqual(overview.status_code, 200)
        self.assertIn(b"https://example.com/vertrag", overview.data)
        self.assertIn(b"https://example.com/rechnungen", overview.data)


if __name__ == "__main__":
    unittest.main()
