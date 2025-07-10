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