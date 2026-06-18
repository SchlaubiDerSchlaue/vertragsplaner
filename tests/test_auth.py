import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app, db
from app.auth import hash_secret, role_allows
from app.models import ApiToken, User


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()
            db.session.add(User(
                username="reader",
                password_hash=hash_secret("reader-pass"),
                role="read",
                is_active=True,
            ))
            db.session.add(User(
                username="writer",
                password_hash=hash_secret("writer-pass"),
                role="write",
                is_active=True,
            ))
            db.session.add(User(
                username="admin",
                password_hash=hash_secret("admin-pass"),
                role="admin",
                is_active=True,
            ))
            db.session.add(ApiToken(
                name="reader-token",
                token_hash=hash_secret("api-secret"),
                role="read",
                is_active=True,
            ))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.client.post("/login", data={"username": username, "password": password})

    def test_role_hierarchy(self):
        self.assertTrue(role_allows("admin", "write"))
        self.assertTrue(role_allows("write", "read"))
        self.assertFalse(role_allows("read", "write"))

    def test_login_success_and_failure(self):
        response = self.login("reader", "reader-pass")
        self.assertEqual(response.status_code, 302)

        response = self.login("reader", "wrong")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ungueltig", response.data)

    def test_web_requires_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_read_user_cannot_access_write_route(self):
        self.login("reader", "reader-pass")
        response = self.client.get("/customers/new")
        self.assertEqual(response.status_code, 403)

    def test_write_user_cannot_access_admin_route(self):
        self.login("writer", "writer-pass")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 403)

    def test_api_requires_valid_token(self):
        self.assertEqual(self.client.get("/api/v1/health").status_code, 401)
        self.assertEqual(
            self.client.get("/api/v1/health", headers={"Authorization": "Bearer wrong"}).status_code,
            401,
        )
        response = self.client.get("/api/v1/health", headers={"Authorization": "Bearer api-secret"})
        self.assertEqual(response.status_code, 200)

    def test_admin_can_delete_token(self):
        self.login("admin", "admin-pass")
        with self.app.app_context():
            token_id = ApiToken.query.filter_by(name="reader-token").first().id

        response = self.client.post(f"/admin/tokens/{token_id}/delete")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(ApiToken.query.filter_by(name="reader-token").first())

    def test_admin_can_delete_other_user_but_not_self(self):
        self.login("admin", "admin-pass")
        with self.app.app_context():
            reader_id = User.query.filter_by(username="reader").first().id
            admin_id = User.query.filter_by(username="admin").first().id

        response = self.client.post(f"/admin/users/{reader_id}/delete")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(username="reader").first())

        response = self.client.post(f"/admin/users/{admin_id}/delete")
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIsNotNone(User.query.filter_by(username="admin").first())


if __name__ == "__main__":
    unittest.main()
