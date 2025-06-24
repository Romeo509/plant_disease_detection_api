import os

class Config:
    """Configuration class for the Flask application"""
    
    # NVIDIA API Configuration
    NVIDIA_API_KEY = "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"
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Security
    SECRET_KEY = os.urandom(24)
    
    # Supported file types
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4'}
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        pass