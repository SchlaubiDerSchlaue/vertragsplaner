import argparse
import getpass

from app import create_app, db
from app.auth import hash_secret, normalize_role
from app.models import User


def main():
    parser = argparse.ArgumentParser(description="Admin-Benutzer erstellen oder aktualisieren.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password")
    parser.add_argument("--role", choices=["read", "write", "admin"], default="admin")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Passwort: ")
    if not password:
        raise SystemExit("Passwort darf nicht leer sein.")

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User.query.filter_by(username=args.username).first()
        if user is None:
            user = User(username=args.username)
            db.session.add(user)

        user.password_hash = hash_secret(password)
        user.role = normalize_role(args.role)
        user.is_active = True
        db.session.commit()
        print(f"Benutzer '{user.username}' wurde mit Rolle '{user.role}' gespeichert.")


if __name__ == "__main__":
    main()
