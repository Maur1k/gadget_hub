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
        MYSQL_HOST: Database hostname
        MYSQL_USER: Database username
        MYSQL_PASSWORD: Database password
        MYSQL_DB: Database name
        MYSQL_CURSORCLASS: Cursor class (DictCursor)
        UPLOAD_FOLDER: Path to upload directory
        MAX_CONTENT_LENGTH: Maximum file upload size (16MB)
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'ecommerce'
    MYSQL_CURSORCLASS = 'DictCursor'
    UPLOAD_FOLDER = os.path.join(basedir, 'gadget_hub', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
