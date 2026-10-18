"""
Flask application factory.

This module initializes the Flask application, database, and login manager.
It also registers all blueprints for the application.
"""
from flask import Flask
# from flask_mysqldb import MySQL  # Removed due to compilation issues on Windows
import pymysql
from flask import g, current_app
from flask_login import LoginManager
from config import Config
import os

class MySQL:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

    @property
    def connection(self):
        if 'mysql_db' not in g:
            g.mysql_db = pymysql.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
        return g.mysql_db

    def teardown(self, exception):
        db = g.pop('mysql_db', None)
        if db is not None:
            db.close()

# Initialize extensions
mysql = MySQL()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    """
    Application factory function.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)
    
    # Initialize extensions
    mysql.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints
    from gadget_hub.routes import auth, admin, customer, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(customer.bp)
    app.register_blueprint(api.bp)
    
    return app

