from datetime import datetime
from functools import wraps
from secrets import token_urlsafe

from flask import flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import ApiToken, User

ROLES = ("read", "write", "admin")
ROLE_LEVELS = {"read": 10, "write": 20, "admin": 30}


def hash_secret(secret):
    return generate_password_hash(secret)


def verify_secret(secret_hash, secret):
    if not secret_hash or not secret:
        return False
    return check_password_hash(secret_hash, secret)


def normalize_role(role):
    return role if role in ROLES else "read"


def role_allows(actual_role, required_role):
    return ROLE_LEVELS.get(actual_role, 0) >= ROLE_LEVELS.get(required_role, 0)


def current_user():
    return getattr(g, "current_user", None)


def current_role():
    user = current_user()
    return user.role if user else None


def can_write():
    return role_allows(current_role(), "write")


def can_admin():
    return role_allows(current_role(), "admin")


def login_user(user):
    session.clear()
    session["user_id"] = user.id


def logout_user():
    session.clear()


def load_logged_in_user():
    g.current_user = None
    user_id = session.get("user_id")
    if user_id is None:
        return

    user = db.session.get(User, user_id)
    if user and user.is_active:
        g.current_user = user
    else:
        session.clear()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(required_role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if current_user() is None:
                return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
            if not role_allows(current_role(), required_role):
                return ("Zugriff verweigert.", 403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


write_required = role_required("write")
admin_required = role_required("admin")


def authenticate_api_token(raw_token):
    for api_token in ApiToken.query.filter_by(is_active=True).all():
        if verify_secret(api_token.token_hash, raw_token):
            api_token.last_used_at = datetime.utcnow()
            db.session.commit()
            return api_token
    return None


def create_api_token_secret():
    return token_urlsafe(32)
