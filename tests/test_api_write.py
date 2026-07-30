import os
import unittest
from datetime import date
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app, db
from app.auth import hash_secret
from app.models import (
    ApiToken,
    Contract,
    ContractPosition,
    ContractPositionVersion,
    Customer,
    Supplier,
)


class ApiWriteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()
            db.session.add_all([
                ApiToken(
                    name="reader-token",
                    token_hash=hash_secret("read-secret"),
                    role="read",
                    is_active=True,
                ),
                ApiToken(
                    name="writer-token",
                    token_hash=hash_secret("write-secret"),
                    role="write",
                    is_active=True,
                ),
                Customer(name="Bestandskunde", status="active"),
                Supplier(name="Bestandslieferant", status="active"),
            ])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def headers(self, token="write-secret"):
        return {"Authorization": f"Bearer {token}"}

    def test_read_token_cannot_write(self):
        response = self.client.post(
            "/api/v1/customers",
            headers=self.headers("read-secret"),
            json={"name": "Verbotener Kunde"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"]["code"], "forbidden")

    def test_create_and_patch_customer(self):
        response = self.client.post(
            "/api/v1/customers",
            headers=self.headers(),
            json={
                "customer_no": "K-100",
                "name": "API Kunde",
                "email": "api@example.test",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("/api/v1/customers/", response.headers["Location"])
        customer = response.get_json()["data"]
        self.assertEqual(customer["status"], "active")

        response = self.client.patch(
            f"/api/v1/customers/{customer['id']}",
            headers=self.headers(),
            json={"city": "Kiel", "status": "inactive"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["city"], "Kiel")
        self.assertEqual(response.get_json()["data"]["status"], "inactive")

        detail = self.client.get(
            f"/api/v1/customers/{customer['id']}", headers=self.headers("read-secret")
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["data"]["name"], "API Kunde")

    def test_duplicate_partner_name_is_rejected(self):
        response = self.client.post(
            "/api/v1/customers",
            headers=self.headers(),
            json={"name": "Bestandskunde"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.get_json()["error"]["details"])

    def test_create_and_patch_supplier(self):
        response = self.client.post(
            "/api/v1/suppliers",
            headers=self.headers(),
            json={"supplier_no": "L-100", "name": "API Lieferant"},
        )
        self.assertEqual(response.status_code, 201)
        supplier = response.get_json()["data"]

        response = self.client.patch(
            f"/api/v1/suppliers/{supplier['id']}",
            headers=self.headers(),
            json={"contact_name": "Frau Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["contact_name"], "Frau Test")

    def test_full_contract_position_and_version_write_flow(self):
        with self.app.app_context():
            customer_id = Customer.query.filter_by(name="Bestandskunde").first().id

        contract_response = self.client.post(
            "/api/v1/contracts",
            headers=self.headers(),
            json={
                "partner_type": "customer",
                "partner_id": customer_id,
                "contract_no": "V-API-1",
                "title": "API Vertrag",
                "contract_type": "revenue",
                "status": "active",
                "start_date": "2026-01-01",
                "cancellation_period_value": 3,
                "cancellation_period_unit": "months",
                "renewal_type": "automatic",
                "contract_link": "example.com/vertrag",
            },
        )
        self.assertEqual(contract_response.status_code, 201)
        contract = contract_response.get_json()["data"]
        self.assertEqual(contract["contract_link"], "https://example.com/vertrag")
        self.assertEqual(contract["partner"]["type"], "customer")

        patch_response = self.client.patch(
            f"/api/v1/contracts/{contract['id']}",
            headers=self.headers(),
            json={"responsible": "Claudia", "end_date": "2026-12-31"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.get_json()["data"]["responsible"], "Claudia")

        position_response = self.client.post(
            f"/api/v1/contracts/{contract['id']}/positions",
            headers=self.headers(),
            json={"name": "Grundgebühr", "sort_order": 10},
        )
        self.assertEqual(position_response.status_code, 201)
        position = position_response.get_json()["data"]
        self.assertEqual(position["position_type"], "revenue")

        version_response = self.client.post(
            f"/api/v1/positions/{position['id']}/versions",
            headers=self.headers(),
            json={
                "valid_from": "2026-01-01",
                "amount": "100.50",
                "currency": "eur",
                "recurrence": "monthly",
                "billing_day": 1,
            },
        )
        self.assertEqual(version_response.status_code, 201)
        first_version = version_response.get_json()["data"]
        self.assertEqual(first_version["amount"], "100.50")
        self.assertEqual(first_version["currency"], "EUR")
        self.assertTrue(first_version["is_active"])

        second_response = self.client.post(
            f"/api/v1/positions/{position['id']}/versions",
            headers=self.headers(),
            json={"valid_from": "2026-07-01", "amount": 120, "currency": "EUR"},
        )
        self.assertEqual(second_response.status_code, 201)
        second_version = second_response.get_json()["data"]

        with self.app.app_context():
            versions = ContractPositionVersion.query.order_by(
                ContractPositionVersion.valid_from
            ).all()
            self.assertEqual(versions[0].valid_to, date(2026, 6, 30))
            self.assertEqual(versions[1].amount, Decimal("120.00"))

        update_response = self.client.patch(
            f"/api/v1/versions/{second_version['id']}",
            headers=self.headers(),
            json={"amount": "125.25", "is_active": False},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.get_json()["data"]["amount"], "125.25")
        self.assertFalse(update_response.get_json()["data"]["is_active"])

    def test_validation_unknown_fields_and_content_type(self):
        no_json = self.client.post(
            "/api/v1/customers",
            headers=self.headers(),
            data="name=Test",
        )
        self.assertEqual(no_json.status_code, 415)

        unknown = self.client.post(
            "/api/v1/customers",
            headers=self.headers(),
            json={"name": "Test", "is_admin": True},
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.get_json()["error"]["code"], "unknown_fields")

        bad_contract = self.client.post(
            "/api/v1/contracts",
            headers=self.headers(),
            json={
                "partner_type": "customer",
                "partner_id": 99999,
                "title": "Fehlerhaft",
                "start_date": "2026-02-30",
                "contract_type": "other",
            },
        )
        self.assertEqual(bad_contract.status_code, 400)
        details = bad_contract.get_json()["error"]["details"]
        self.assertIn("partner_id", details)
        self.assertIn("start_date", details)
        self.assertIn("contract_type", details)

    def test_patch_cannot_null_required_fields(self):
        with self.app.app_context():
            customer = Customer.query.filter_by(name="Bestandskunde").first()
            customer_id = customer.id
            contract = Contract(
                customer=customer,
                title="Pflichtfelder",
                contract_type="revenue",
                status="active",
                start_date=date(2026, 1, 1),
                renewal_type="none",
            )
            db.session.add(contract)
            db.session.commit()
            contract_id = contract.id

        customer_response = self.client.patch(
            f"/api/v1/customers/{customer_id}",
            headers=self.headers(),
            json={"name": None},
        )
        self.assertEqual(customer_response.status_code, 400)
        self.assertIn("name", customer_response.get_json()["error"]["details"])

        contract_response = self.client.patch(
            f"/api/v1/contracts/{contract_id}",
            headers=self.headers(),
            json={"start_date": None},
        )
        self.assertEqual(contract_response.status_code, 400)
        self.assertIn("start_date", contract_response.get_json()["error"]["details"])

        partner_response = self.client.patch(
            f"/api/v1/contracts/{contract_id}",
            headers=self.headers(),
            json={"partner_type": "supplier"},
        )
        self.assertEqual(partner_response.status_code, 400)
        self.assertIn("partner_id", partner_response.get_json()["error"]["details"])

    def test_delete_is_not_available(self):
        response = self.client.delete(
            "/api/v1/customers/1",
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["error"]["code"], "method_not_allowed")


if __name__ == "__main__":
    unittest.main()
