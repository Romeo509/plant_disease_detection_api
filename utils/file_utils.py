"""
File handling utilities for plant condition detection API
"""
import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

# Supported file formats
SUPPORTED_FORMATS = {
    "png": ["image/png", "img"],
    "jpg": ["image/jpg", "img"],
    "jpeg": ["image/jpeg", "img"],
    "mp4": ["video/mp4", "video"],
}

UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)


def get_file_extension(filename):
    """Extract file extension from filename"""
    return filename.split(".")[-1].lower()


def is_supported_format(filename):
    """Check if file format is supported"""
    ext = get_file_extension(filename)
    return ext in SUPPORTED_FORMATS


def save_uploaded_file(file):
    """
    Save uploaded file and return path and extension
    Returns: tuple (file_path, extension)
    """
    ext = get_file_extension(file.filename)
    if not is_supported_format(file.filename):
        raise ValueError(f'{file.filename} format not supported')
    
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    return file_path, ext


def cleanup_file(file_path):
    """Safely remove uploaded file"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass  # Ignore cleanup errors