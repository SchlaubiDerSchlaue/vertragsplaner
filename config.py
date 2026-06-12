import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///contract_planning.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
