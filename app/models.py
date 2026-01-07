"""
Database models helper.

Since we are using Flask-Mysqldb, we use raw SQL in routes.
This module strictly provides the User class for Flask-Login compatibility.
"""
from app import mysql, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(id):
    """Load user by ID for Flask-Login."""
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM user WHERE id = %s", (int(id),))
    user_data = cursor.fetchone()
    cursor.close()
    
    if user_data:
        # Create User object from dictionary
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            is_admin=user_data['is_admin'],
            is_active_account=user_data['is_active_account']
        )
    return None


class User(UserMixin):
    """
    User class for Flask-Login compatibility.
    """
    def __init__(self, id, username, email, password_hash, is_admin, is_active_account, **kwargs):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = bool(is_admin)
        self.is_active_account = bool(is_active_account)
    
    def get_id(self):
        return str(self.id)
        
    def set_password(self, password):
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = generate_password_hash(password)
        # Note: Saving to DB must be done via SQL UPDATE in the controller
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


