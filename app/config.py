import os
from pathlib import Path
from datetime import timedelta
import logging
from urllib.parse import urlparse

class Config:
    _initialized = False
    def __init__(self):
        self.is_production = os.environ.get('RENDER', '').lower() in ('1', 'true', 'yes')
        self.base_dir = Path(__file__).parent.absolute()

        if self.is_production:
            # Use /tmp for all file operations on Render
            self.upload_folder = Path('/tmp/uploads')
            self.temp_folder = Path('/tmp/temp_analysis')
            self.reports_folder = Path('/tmp/reports')
            self.session_backup_folder = Path('/tmp/session_backup')
        else:
            # Use project-relative paths locally
            self.upload_folder = self.base_dir / 'uploaded_files'
            self.temp_folder = self.base_dir / 'temp_analysis'
            self.reports_folder = self.base_dir / 'reports'
            self.session_backup_folder = self.base_dir / 'session_backup'

    def ensure_directories(self):
        if Config._initialized:
            return
        for folder in [self.upload_folder, self.temp_folder, self.reports_folder, self.session_backup_folder]:
            folder.mkdir(parents=True, exist_ok=True)
            if self.is_production:
                os.chmod(str(folder), 0o755)
        Config._initialized = True

    def get_upload_path(self, filename=None):
        if filename:
            return self.upload_folder / filename
        return self.upload_folder

    def get_temp_path(self, filename=None):
        if filename:
            return self.temp_folder / filename
        return self.temp_folder

    def get_session_backup_path(self, session_id):
        return self.session_backup_folder / f"session_{session_id}.json"

    def cleanup_temp_files(self):
        import shutil
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder)
            self.temp_folder.mkdir(parents=True, exist_ok=True)

    def cleanup_old_session_backups(self, max_age_hours=24):
        import time
        if not self.session_backup_folder.exists():
            return

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        for backup_file in self.session_backup_folder.glob("session_*.json"):
            try:
                file_age = current_time - backup_file.stat().st_mtime
                if file_age > max_age_seconds:
                    backup_file.unlink()
            except Exception:
                pass

    # Flask Configuration
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")

    # Enhanced Database Configuration with connection pooling and SSL fixes
    
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        # Fix for psycopg2 compatibility
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = database_url or "sqlite:///default.db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database engine options for better connection handling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections every 5 minutes
        'pool_timeout': 20,     # Timeout for getting connection from pool
        'max_overflow': 10,     # Maximum overflow connections
        'echo': False,          # Set to True for SQL debugging
    }
    
    # Additional database options for production
    if os.environ.get('RENDER'):
        SQLALCHEMY_ENGINE_OPTIONS.update({
            'connect_args': {
                'sslmode': 'require',
                'options': '-c statement_timeout=30000'  # 30 second timeout
            }
        })

    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = bool(os.environ.get('RENDER'))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_TYPE = 'filesystem'  # Optional: requires Flask-Session if used

    # Flask-Mail Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

    # Analysis Configuration
    ANALYSIS_TIMEOUT = 300  # 5 minutes timeout for analysis
    MAX_FILES_PER_UPLOAD = 10

    # Logging Configuration
    LOG_LEVEL = 'INFO' if os.environ.get('RENDER') else 'DEBUG'

    @classmethod
    def init_app(cls, app):
        # Create an instance to access instance methods
        config_instance = cls()
        config_instance.ensure_directories()
        config_instance.cleanup_old_session_backups()

        if config_instance.is_production:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s %(levelname)s %(name)s %(message)s'
            )
        else:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s %(levelname)s %(name)s %(threadName)s %(message)s'
            )

# Create global config instance
config = Config()

# Environment-specific configurations
class DevelopmentConfig(Config):
    def __init__(self):
        super().__init__()
    
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    def __init__(self):
        super().__init__()
        # Override with production-specific database URL processing
        database_url = os.getenv("DATABASE_URL")
        if database_url and database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        self.SQLALCHEMY_DATABASE_URI = database_url or "sqlite:///default.db"
    
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    WTF_CSRF_ENABLED = True
    
    # Production-specific database settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 20,
        'pool_size': 10,
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
    }

class TestingConfig(Config):
    def __init__(self):
        super().__init__()
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    TESTING = True
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}