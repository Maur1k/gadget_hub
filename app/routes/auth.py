"""
Authentication routes for user registration and login.

This module handles user registration, login, and logout functionality.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
import re

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
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html')
        
        # Check if account is active
        if not user.is_active_account:
            flash('Your account has been deactivated. Please contact admin.', 'error')
            return render_template('auth/login.html')
        
        # Login user
        login_user(user, remember=True)
        flash(f'Welcome back, {user.username}!', 'success')
        
        # Redirect to next page or appropriate dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.home'))
    
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
        if not email or not username or not password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        # Validate email format
        if not validate_email(email):
            flash('Invalid email format', 'error')
            return render_template('auth/register.html')
        
        # Validate username
        if len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
            return render_template('auth/register.html')
        
        if not username.replace('_', '').replace('-', '').isalnum():
            flash('Username can only contain letters, numbers, hyphens, and underscores', 'error')
            return render_template('auth/register.html')
        
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('auth/register.html')
        
        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'error')
            return render_template('auth/register.html')
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose a different username.', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        try:
            user = User(email=email, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login to continue.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
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

