import os


DEFAULT_SECRET_KEY = "dev-secret-key"


def env_value(name, default=None):
    value = os.getenv(name, default)
    if isinstance(value, str):
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
    return value


class Config:
    SECRET_KEY = env_value("SECRET_KEY", DEFAULT_SECRET_KEY)
    if env_value("FLASK_ENV") == "production" and SECRET_KEY == DEFAULT_SECRET_KEY:
        raise RuntimeError("SECRET_KEY muss in Produktion gesetzt werden.")
    SQLALCHEMY_DATABASE_URI = env_value(
        "DATABASE_URL",
        "sqlite:///contract_planning.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
