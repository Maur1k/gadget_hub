"""
Application configuration.

This module contains configuration settings for the Flask application.
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Configuration class for Flask application.
    
    Attributes:
        SECRET_KEY: Secret key for session management
        SQLALCHEMY_DATABASE_URI: Database connection URI
        SQLALCHEMY_TRACK_MODIFICATIONS: Disable SQLAlchemy event system
        UPLOAD_FOLDER: Path to upload directory
        MAX_CONTENT_LENGTH: Maximum file upload size (16MB)
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'ecommerce.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

