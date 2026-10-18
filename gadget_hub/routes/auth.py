"""
Authentication routes for user registration and login.

This module handles user registration, login, and logout functionality.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from gadget_hub import mysql
from gadget_hub.models import User
from werkzeug.security import generate_password_hash
import re
import pymysql.cursors

bp = Blueprint('auth', __name__, url_prefix='/auth')


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, ""


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    
    GET: Display login form
    POST: Process login credentials
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validate input
        if not email or not password:
            flash('Please provide both email and password', 'error')
            return render_template('auth/login.html')
        
        if not validate_email(email):
            flash('Invalid email format', 'error')
            return render_template('auth/login.html')
        
        # Find user by email
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        
        if user_data:
            # Check password
            # We create a temp user object to use check_password method, 
            # or just import check_password_hash. 
            # Since we have the User class, let's use it if we want, or just verify using the data.
            # User class expects all fields.
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                is_admin=user_data['is_admin'],
                is_active_account=user_data['is_active_account']
            )
            
            if user.check_password(password):
                # Check if account is active
                if not user.is_active_account:
                    flash('Your account has been deactivated. Please contact admin.', 'error')
                    return render_template('auth/login.html')
                
                # Login user
                login_user(user, remember=True)
                flash(f'Welcome back, {user.username}!', 'success')
                
                if user.is_admin:
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('customer.home'))
        
        flash('Invalid email or password', 'error')
        return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    
    GET: Display registration form
    POST: Process registration data
    """
    if current_user.is_authenticated:
        return redirect(url_for('customer.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate input fields
        if not email or not username or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        # Validate email format
        if not validate_email(email):
            flash('Invalid email format', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        # Validate username
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        if not username.replace('_', '').replace('-', '').isalnum():
            flash('Username can only contain letters, numbers, hyphens, and underscores', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        cursor = mysql.connection.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM user WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            flash('Email already registered. Please use a different email.', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        # Check if username already exists
        cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            flash('Username already taken. Please choose a different username.', 'error')
            return render_template('auth/register.html', email=email, username=username)
        
        # Create new user
        try:
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO user (email, username, password_hash) VALUES (%s, %s, %s)",
                (email, username, password_hash)
            )
            mysql.connection.commit()
            cursor.close()
            flash('Registration successful! Please login to continue.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Registration failed. Please try again.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    username = current_user.username
    logout_user()
    flash(f'You have been logged out. Goodbye, {username}!', 'info')
    return redirect(url_for('auth.login'))


