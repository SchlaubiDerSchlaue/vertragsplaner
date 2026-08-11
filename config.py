import os


def env_value(name, default=None):
    value = os.getenv(name, default)
    if isinstance(value, str):
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
    return value


class Config:
    SECRET_KEY = env_value("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = env_value(
        "DATABASE_URL",
        "sqlite:///contract_planning.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Logging configuration
    # Override via environment variables:
    #   VERTRAGSPLANER_LOG_DIR       - Log directory (default: logs/)
    #   VERTRAGSPLANER_LOG_LEVEL     - Log level: DEBUG/INFO/WARNING/ERROR (default: INFO)
    #   VERTRAGSPLANER_LOG_MAX_BYTES - Max size per log file in bytes (default: 10000000)
    #   VERTRAGSPLANER_LOG_BACKUP_COUNT - Number of rotated backup files (default: 10)
    LOG_DIR = env_value("VERTRAGSPLANER_LOG_DIR", "logs")
    LOG_LEVEL = env_value("VERTRAGSPLANER_LOG_LEVEL", "INFO")
