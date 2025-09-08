"""Plant Disease Detection API - Main Application

A Flask-based API for detecting plant diseases using AI vision models.
Refactored for better maintainability with modular architecture.
"""
import os
from pathlib import Path
from flask import Flask
from config import Config
from routes.main_routes import main_bp


def create_app(config_class=Config):
    """Application factory pattern for creating Flask app"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure upload directory exists
    upload_folder = Path(app.config.get('UPLOAD_FOLDER', 'uploads'))
    upload_folder.mkdir(exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    
    return app


# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
