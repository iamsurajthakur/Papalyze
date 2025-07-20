import os

class Config:
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///default.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail config
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")  
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") 
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")  


