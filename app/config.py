import os
class Config:
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///default.db"  # fallback if .env not found
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
