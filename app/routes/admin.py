"""
Admin routes for managing products, orders, users, and generating reports.

This module handles all administrative functionality including:
- Product and category management
- Order processing (approve, decline, ship, deliver)
- Sales report generation (daily/weekly/monthly)
- User management (password reset, activate/deactivate accounts)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import mysql
from app.models import User
from functools import wraps
from datetime import datetime, timedelta
import os

bp = Blueprint('admin', __name__, url_prefix='/admin')


# Helper classes for template compatibility
class ProductsWrapper:
    """Wrapper to mimic SQLAlchemy relationship with count() method."""
    def __init__(self, count):
        self._count = count
    def count(self):
        return self._count


class OrdersWrapper:
    """Wrapper to mimic SQLAlchemy relationship with count() method."""
    def __init__(self, count):
        self._count = count
    def count(self):
        return self._count


def admin_required(f):
    """Decorator to ensure only admin users can access the route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Dashboard
@bp.route('/')
@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    cursor = mysql.connection.cursor()
    
    # Stats
    cursor.execute("SELECT COUNT(*) as count FROM `order`")
    total_orders = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM product")
    total_products = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM user WHERE is_admin = 0")
    total_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(total_amount) as revenue FROM `order` WHERE status IN ('Approved', 'Shipped', 'Delivered')")
    result = cursor.fetchone()
    total_revenue = result['revenue'] if result and result['revenue'] else 0
    
    # Recent orders (with customer info)
    cursor.execute("""
        SELECT o.*, u.username, u.email 
        FROM `order` o 
        JOIN user u ON o.user_id = u.id 
        ORDER BY o.created_at DESC LIMIT 5
    """)
    recent_orders_raw = cursor.fetchall()
    recent_orders = []
    if recent_orders_raw:
        for row in recent_orders_raw:
            # Convert Row to dict and add customer dict for template compatibility
            order_dict = dict(row)
            order_dict['customer'] = {'username': order_dict['username'], 'email': order_dict['email']}
            recent_orders.append(order_dict)
    
    # Top products (with category info)
    cursor.execute("""
        SELECT p.*, c.name as category_name 
        FROM product p 
        LEFT JOIN category c ON p.category_id = c.id 
        ORDER BY p.id DESC LIMIT 5
    """)
    top_products_raw = cursor.fetchall()
    top_products = []
    if top_products_raw:
        for row in top_products_raw:
            # Convert Row to dict for template compatibility
            product_dict = dict(row)
            product_dict['category'] = {'name': product_dict['category_name']} if product_dict.get('category_name') else None
            top_products.append(product_dict)
    
    # Pending orders count
    cursor.execute("SELECT COUNT(*) as count FROM `order` WHERE status = 'Pending'")
    pending_orders = cursor.fetchone()['count']
    
    cursor.close()
    
    return render_template('admin/dashboard.html',
                          total_orders=total_orders,
                          total_products=total_products,
                          total_users=total_users,
                          total_revenue=total_revenue,
                          recent_orders=recent_orders,
                          top_products=top_products,
                          pending_orders=pending_orders)

# Product Management
@bp.route('/products')
@login_required
@admin_required
def products():
    cursor = mysql.connection.cursor()
    
    # Get products with category info
    cursor.execute("""
        SELECT p.*, c.name as category_name 
        FROM product p 
        LEFT JOIN category c ON p.category_id = c.id 
        ORDER BY p.created_at DESC
    """)
    products_raw = cursor.fetchall()
    products = []
    if products_raw:
        for row in products_raw:
            # Convert Row to dict for template compatibility
            product_dict = dict(row)
            product_dict['category'] = {'name': product_dict['category_name']} if product_dict.get('category_name') else None
            products.append(product_dict)
            
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/products.html', products=products, categories=categories)

@bp.route('/products/add', methods=['POST'])
@login_required
@admin_required
def add_product():
    """
    Add a new product.
    
    Admin can add products with name, description, price, stock, category, and image.
    """
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    # Validate required fields
    if not name:
        flash('Product name is required', 'error')
        return redirect(url_for('admin.products'))
    
    # Validate price
    try:
        price = float(request.form.get('price', 0))
        if price <= 0:
            flash('Price must be greater than 0', 'error')
            return redirect(url_for('admin.products'))
    except (ValueError, TypeError):
        flash('Invalid price format', 'error')
        return redirect(url_for('admin.products'))
    
    # Validate stock
    try:
        stock = int(request.form.get('stock', 0))
        if stock < 0:
            flash('Stock cannot be negative', 'error')
            return redirect(url_for('admin.products'))
    except (ValueError, TypeError):
        flash('Invalid stock format', 'error')
        return redirect(url_for('admin.products'))
    
    # Validate category if provided
    category_id = request.form.get('category_id')
    cursor = mysql.connection.cursor()
    
    if category_id:
        try:
            category_id = int(category_id)
            cursor.execute("SELECT id FROM category WHERE id = %s", (category_id,))
            if not cursor.fetchone():
                flash('Invalid category selected', 'error')
                return redirect(url_for('admin.products'))
        except (ValueError, TypeError):
            flash('Invalid category', 'error')
            return redirect(url_for('admin.products'))
    else:
        category_id = None
    
    image_filename = None
    
    try:
        # Handle image upload with processing
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext not in allowed_extensions:
                    flash('Invalid image format. Use PNG, JPG, JPEG, GIF, or WEBP', 'error')
                    return redirect(url_for('admin.products'))
                
                # Process and save image with consistent sizing and white background
                from app.utils.image_processor import process_and_save_upload
                upload_folder = os.path.join('app', 'static', 'uploads')
                image_filename = process_and_save_upload(file, upload_folder)
        
        cursor.execute("""
            INSERT INTO product (name, description, price, stock, image, category_id, is_active, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (name, description, price, stock, image_filename, category_id, 1))
        
        mysql.connection.commit()
        flash(f'Product "{name}" added successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to add product. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.products'))

@bp.route('/products/edit/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_product(id):
    """
    Edit an existing product.
    
    Args:
        id: Product ID
        
    Admin can edit product details including name, description, price, stock, category, and image.
    """
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM product WHERE id = %s", (id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        flash('Product not found', 'error')
        return redirect(url_for('admin.products'))
        
    name = request.form.get('name', '').strip()
    
    # Validate required fields
    if not name:
        flash('Product name is required', 'error')
        return redirect(url_for('admin.products'))
    
    # Validate price
    try:
        price = float(request.form.get('price', 0))
        if price <= 0:
            flash('Price must be greater than 0', 'error')
            return redirect(url_for('admin.products'))
    except (ValueError, TypeError):
        flash('Invalid price format', 'error')
        return redirect(url_for('admin.products'))
    
    # Validate stock
    try:
        stock = int(request.form.get('stock', 0))
        if stock < 0:
            flash('Stock cannot be negative', 'error')
            return redirect(url_for('admin.products'))
    except (ValueError, TypeError):
        flash('Invalid stock format', 'error')
        return redirect(url_for('admin.products'))
    
    # Validate category if provided
    category_id = request.form.get('category_id')
    if category_id:
        try:
            category_id = int(category_id)
            cursor.execute("SELECT id FROM category WHERE id = %s", (category_id,))
            if not cursor.fetchone():
                category_id = None
        except (ValueError, TypeError):
            category_id = None
    else:
        category_id = None
    
    is_active = 1 if request.form.get('is_active') == 'on' else 0
    image_filename = product['image']
    
    try:
        # Handle image upload with processing
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext in allowed_extensions:
                    # Process and save image with consistent sizing and white background
                    from app.utils.image_processor import process_and_save_upload
                    upload_folder = os.path.join('app', 'static', 'uploads')
                    image_filename = process_and_save_upload(file, upload_folder)
                    # Note: We keep the old file on disk (or could delete it)
                else:
                    flash('Invalid image format. Use PNG, JPG, JPEG, GIF, or WEBP', 'error')
        
        description = request.form.get('description', '').strip()
        
        cursor.execute("""
            UPDATE product 
            SET name=%s, description=%s, price=%s, stock=%s, category_id=%s, is_active=%s, image=%s, updated_at=NOW()
            WHERE id=%s
        """, (name, description, price, stock, category_id, is_active, image_filename, id))
        
        mysql.connection.commit()
        flash(f'Product "{name}" updated successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to update product. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.products'))

@bp.route('/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    """
    Delete a product.
    
    Args:
        id: Product ID
        
    Admin can delete products.
    """
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT name FROM product WHERE id = %s", (id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        flash('Product not found', 'error')
        return redirect(url_for('admin.products'))
        
    product_name = product['name']
    
    try:
        cursor.execute("DELETE FROM product WHERE id = %s", (id,))
        mysql.connection.commit()
        flash(f'Product "{product_name}" deleted successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to delete product. It may be referenced in existing orders.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.products'))

# Category Management
@bp.route('/categories')
@login_required
@admin_required
def categories():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT c.*, COUNT(p.id) as product_count 
        FROM category c 
        LEFT JOIN product p ON c.id = p.category_id 
        GROUP BY c.id
        ORDER BY c.name
    """)
    categories_raw = cursor.fetchall()
    # Convert to plain dicts and add products relationship-like structure for template
    categories = []
    for cat in categories_raw:
        cat_dict = dict(cat)
        cat_dict['products'] = ProductsWrapper(cat_dict['product_count'])
        categories.append(cat_dict)
    cursor.close()
    return render_template('admin/categories.html', categories=categories)

@bp.route('/categories/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    """
    Add a new category.
    
    Admin can add categories to organize products.
    """
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Category name is required', 'error')
        return redirect(url_for('admin.categories'))
    
    cursor = mysql.connection.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM category WHERE name = %s", (name,))
    if cursor.fetchone():
        cursor.close()
        flash('Category already exists', 'error')
        return redirect(url_for('admin.categories'))
    
    try:
        cursor.execute("INSERT INTO category (name, description) VALUES (%s, %s)", (name, description))
        mysql.connection.commit()
        flash(f'Category "{name}" added successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to add category. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.categories'))

@bp.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_category(id):
    cursor = mysql.connection.cursor()
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    try:
        cursor.execute("UPDATE category SET name = %s, description = %s WHERE id = %s", (name, description, id))
        mysql.connection.commit()
        flash('Category updated successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to update category', 'error')
    finally:
        cursor.close()
        
    return redirect(url_for('admin.categories'))

@bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM category WHERE id = %s", (id,))
        mysql.connection.commit()
        flash('Category deleted successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to delete category (it may be in use)', 'error')
    finally:
        cursor.close()
        
    return redirect(url_for('admin.categories'))

# ============================================================================
# FEATURE 1: PROCESS CUSTOMER ORDERS
# Admin can view, approve, decline orders. If declined, provide reason for customers to know.
# ============================================================================
# Order Management
# VIEW ORDERS - Admin can view all orders
@bp.route('/orders')
@login_required
@admin_required
def orders():
    status_filter = request.args.get('status', '')
    cursor = mysql.connection.cursor()
    
    query = """
        SELECT o.*, u.username, u.email 
        FROM `order` o 
        JOIN user u ON o.user_id = u.id
    """
    
    if status_filter:
        query += " WHERE o.status = %s"
        query += " ORDER BY o.created_at DESC"
        cursor.execute(query, (status_filter,))
    else:
        query += " ORDER BY o.created_at DESC"
        cursor.execute(query)
        
    orders_raw = cursor.fetchall()
    orders = []
    
    if orders_raw:
        for row in orders_raw:
            row['customer'] = {'username': row['username'], 'email': row['email']}
            orders.append(row)
            
    cursor.close()
    return render_template('admin/orders.html', orders=orders, current_status=status_filter)

# VIEW ORDER DETAILS
@bp.route('/orders/<int:id>')
@login_required
@admin_required
def order_detail(id):
    cursor = mysql.connection.cursor()
    
    # Get order with customer info
    cursor.execute("""
        SELECT o.*, u.username, u.email, u.id as user_id
        FROM `order` o 
        JOIN user u ON o.user_id = u.id
        WHERE o.id = %s
    """, (id,))
    order_data = cursor.fetchone()
    
    if not order_data:
        cursor.close()
        flash('Order not found', 'error')
        return redirect(url_for('admin.orders'))
        
    # Get order items with product info
    cursor.execute("""
        SELECT oi.*, p.name as product_name, p.image as product_image
        FROM order_item oi
        LEFT JOIN product p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (id,))
    items_raw = cursor.fetchall()
    
    # Structure data for template
    order = order_data
    order['customer'] = {'username': order['username'], 'email': order['email'], 'id': order['user_id']}
    
    # Helper to mimic SQLAlchemy relationship access if strictly needed, 
    # but best to pass items separately or attached to order dict
    order['items'] = []
    if items_raw:
        for item in items_raw:
            item['product'] = {'name': item['product_name'], 'image': item['product_image']}
            order['items'].append(item)
            
    cursor.close()
    return render_template('admin/order_detail.html', order=order)

# APPROVE ORDER - Admin can approve orders
@bp.route('/orders/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_order(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            UPDATE `order` 
            SET status = 'Approved', decline_reason = NULL, updated_at = NOW() 
            WHERE id = %s
        """, (id,))
        mysql.connection.commit()
        flash('Order approved', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to approve order', 'error')
    finally:
        cursor.close()
    return redirect(url_for('admin.orders'))

@bp.route('/orders/<int:id>/ship', methods=['POST'])
@login_required
@admin_required
def ship_order(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE `order` SET status = 'Shipped', updated_at = NOW() WHERE id = %s", (id,))
        mysql.connection.commit()
        flash('Order marked as shipped', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to update order status', 'error')
    finally:
        cursor.close()
    return redirect(url_for('admin.orders'))

@bp.route('/orders/<int:id>/deliver', methods=['POST'])
@login_required
@admin_required
def deliver_order(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE `order` SET status = 'Delivered', updated_at = NOW() WHERE id = %s", (id,))
        mysql.connection.commit()
        flash('Order marked as delivered', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to update order status', 'error')
    finally:
        cursor.close()
    return redirect(url_for('admin.orders'))

# DECLINE ORDER - Admin can decline orders and provide reason for customers to know
@bp.route('/orders/<int:id>/decline', methods=['POST'])
@login_required
@admin_required
def decline_order(id):
    """
    Decline an order and provide reason for customers.
    """
    cursor = mysql.connection.cursor()
    
    # Get current status
    cursor.execute("SELECT status FROM `order` WHERE id = %s", (id,))
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        flash('Order not found', 'error')
        return redirect(url_for('admin.orders'))
    
    if order['status'] == 'Declined':
        cursor.close()
        flash('Order is already declined', 'error')
        return redirect(url_for('admin.order_detail', id=id))
    
    if order['status'] in ['Shipped', 'Delivered']:
        cursor.close()
        flash('Cannot decline an order that has already been shipped or delivered', 'error')
        return redirect(url_for('admin.order_detail', id=id))
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        reason = 'No reason provided'
    
    try:
        # Get order items to restore stock
        cursor.execute("SELECT product_id, quantity FROM order_item WHERE order_id = %s", (id,))
        items = cursor.fetchall()
        
        # Restore stock
        for item in items:
            if item['product_id']:
                cursor.execute("UPDATE product SET stock = stock + %s WHERE id = %s", 
                              (item['quantity'], item['product_id']))
        
        # Update order status
        cursor.execute("""
            UPDATE `order` 
            SET status = 'Declined', decline_reason = %s, updated_at = NOW() 
            WHERE id = %s
        """, (reason, id))
        
        mysql.connection.commit()
        flash(f'Order declined. Reason: {reason}', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to decline order. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.orders'))

# ============================================================================
# FEATURE 2: GENERATE SALES REPORTS
# Admin can view daily/weekly/monthly sales reports.
# ============================================================================
# Sales Reports
# VIEW SALES REPORTS - Admin can view daily/weekly/monthly sales reports
# Sales Reports
# VIEW SALES REPORTS - Admin can view daily/weekly/monthly sales reports
@bp.route('/reports')
@login_required
@admin_required
def reports():
    period = request.args.get('period', 'daily')
    
    today = datetime.utcnow().date()
    
    if period == 'daily':
        start_date = today
        end_date = today + timedelta(days=1)
    elif period == 'weekly':
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=1)
    else:  # monthly
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)
    
    cursor = mysql.connection.cursor()
    
    # Get relevant orders
    cursor.execute("""
        SELECT * FROM `order` 
        WHERE created_at >= %s AND created_at < %s
        AND status IN ('Approved', 'Shipped', 'Delivered')
        ORDER BY created_at DESC
    """, (start_date, end_date))
    orders_raw = cursor.fetchall()
    orders = []
    if orders_raw:
        for row in orders_raw:
            orders.append(row)
            
    total_revenue = sum(o['total_amount'] for o in orders)
    total_orders = len(orders)
    
    # Get detailed order data for report table
    cursor.execute("""
        SELECT o.id as order_id, o.created_at as `date`, o.status,
               u.username as customer_name,
               p.name as product_name, 
               oi.quantity, oi.price, (oi.quantity * oi.price) as total
        FROM `order` o
        JOIN user u ON o.user_id = u.id
        JOIN order_item oi ON o.id = oi.order_id
        JOIN product p ON oi.product_id = p.id
        WHERE o.created_at >= %s AND o.created_at < %s
        AND o.status IN ('Approved', 'Shipped', 'Delivered')
        ORDER BY o.created_at DESC
    """, (start_date, end_date))
    
    items_raw = cursor.fetchall()
    order_data = []
    if items_raw:
        for item in items_raw:
            order_data.append({
                'order_id': item['order_id'],
                'date': item['date'],
                'product': item['product_name'],
                'quantity': item['quantity'],
                'price': item['price'],
                'total': item['total'],
                'status': item['status']
            })
            
    cursor.close()
    
    return render_template('admin/reports.html',
                          period=period,
                          orders=orders,
                          order_data=order_data,
                          total_revenue=total_revenue,
                          total_orders=total_orders, 
                          start_date=start_date,
                          end_date=today)

# ============================================================================
# FEATURE 3: MANAGE USERS
# The admin can reset customer password, deactivate/activate accounts.
# ============================================================================
# User Management
# VIEW USERS
@bp.route('/users')
@login_required
@admin_required
def users():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT u.*, COUNT(o.id) as order_count 
        FROM user u 
        LEFT JOIN `order` o ON u.id = o.user_id 
        WHERE u.is_admin = 0 
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """)
    users_raw = cursor.fetchall()
    # Convert to plain dicts and add orders relationship-like structure for template
    users = []
    for user in users_raw:
        user_dict = dict(user)
        user_dict['orders'] = OrdersWrapper(user_dict['order_count'])
        users.append(user_dict)
    cursor.close()
    return render_template('admin/users.html', users=users)

# ACTIVATE/DEACTIVATE ACCOUNTS - Admin can deactivate/activate customer accounts
@bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT is_admin, is_active_account, username FROM user WHERE id = %s", (id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
        
    if user['is_admin']:
        cursor.close()
        flash('Cannot modify admin status', 'error')
        return redirect(url_for('admin.users'))
    
    new_status = 0 if user['is_active_account'] else 1
    
    try:
        cursor.execute("UPDATE user SET is_active_account = %s WHERE id = %s", (new_status, id))
        mysql.connection.commit()
        status_text = 'activated' if new_status else 'deactivated'
        flash(f"User {user['username']} {status_text}", 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to update user status', 'error')
    finally:
        cursor.close()
        
    return redirect(url_for('admin.users'))

# RESET PASSWORD - Admin can reset customer password
@bp.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT is_admin, username FROM user WHERE id = %s", (id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    if user['is_admin']:
        cursor.close()
        flash('Cannot reset admin password through this interface', 'error')
        return redirect(url_for('admin.users'))
    
    new_password = request.form.get('new_password', '').strip()
    
    # Validate password strength
    if len(new_password) < 6:
        cursor.close()
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('admin.users'))
    
    from werkzeug.security import generate_password_hash
    
    try:
        password_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE user SET password_hash = %s WHERE id = %s", (password_hash, id))
        mysql.connection.commit()
        flash(f"Password reset for {user['username']}. New password: {new_password}", 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to reset password. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin.users'))

