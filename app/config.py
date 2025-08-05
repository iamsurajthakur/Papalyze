import os
from pathlib import Path

class Config:
    def __init__(self):
        self.is_production = bool(os.environ.get('RENDER'))
        self.base_dir = Path(__file__).parent.absolute()
        
        if self.is_production:
            # Use /tmp for all file operations on Render
            self.upload_folder = Path('/tmp/uploads')
            self.temp_folder = Path('/tmp/temp_analysis')
            self.reports_folder = Path('/tmp/reports')
        else:
            # Use project-relative paths locally
            self.upload_folder = self.base_dir / 'uploaded_files'
            self.temp_folder = self.base_dir / 'temp_analysis'  
            self.reports_folder = self.base_dir / 'reports'
        
        # Ensure all directories exist
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create all necessary directories"""
        for folder in [self.upload_folder, self.temp_folder, self.reports_folder]:
            folder.mkdir(parents=True, exist_ok=True)
    
    def get_upload_path(self, filename=None):
        """Get upload path, optionally with filename"""
        if filename:
            return self.upload_folder / filename
        return self.upload_folder
    
    def get_temp_path(self, filename=None):
        """Get temp path, optionally with filename"""
        if filename:
            return self.temp_folder / filename
        return self.temp_folder
    
    def cleanup_temp_files(self):
        """Clean up temporary files (important for Render's ephemeral filesystem)"""
        import shutil
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder)
            self.temp_folder.mkdir(parents=True, exist_ok=True)
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

    def cleanup_temp_files(self):
        """Clean up temporary files (important for Render's ephemeral filesystem)"""
        import shutil
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder)
            self.temp_folder.mkdir(parents=True, exist_ok=True)


config = Config()
