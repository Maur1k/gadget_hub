"""
Admin routes for managing products, orders, users, and generating reports.

This module handles all administrative functionality including:
- Product and category management
- Order processing (approve, decline, ship, deliver)
- Sales report generation (daily/weekly/monthly with PDF export)
- User management (password reset, activate/deactivate accounts)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app import db
from app.models import User, Product, Category, Order, OrderItem
from functools import wraps
from datetime import datetime, timedelta
from io import BytesIO
import os

bp = Blueprint('admin', __name__, url_prefix='/admin')


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
    # Stats
    total_orders = Order.query.count()
    total_products = Product.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.status.in_(['Approved', 'Shipped', 'Delivered'])
    ).scalar() or 0
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Top products
    top_products = Product.query.order_by(Product.id.desc()).limit(5).all()
    
    # Pending orders count
    pending_orders = Order.query.filter_by(status='Pending').count()
    
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
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
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
    if category_id:
        try:
            category_id = int(category_id)
            if not Category.query.get(category_id):
                flash('Invalid category selected', 'error')
                return redirect(url_for('admin.products'))
        except (ValueError, TypeError):
            flash('Invalid category', 'error')
            return redirect(url_for('admin.products'))
    else:
        category_id = None
    
    try:
        product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id
        )
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext not in allowed_extensions:
                    flash('Invalid image format. Use PNG, JPG, JPEG, GIF, or WEBP', 'error')
                    return redirect(url_for('admin.products'))
                
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                filepath = os.path.join('app', 'static', 'uploads', filename)
                file.save(filepath)
                product.image = filename
        
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{name}" added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to add product. Please try again.', 'error')
    
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
    product = Product.query.get_or_404(id)
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
            if not Category.query.get(category_id):
                category_id = None
        except (ValueError, TypeError):
            category_id = None
    else:
        category_id = None
    
    try:
        product.name = name
        product.description = request.form.get('description', '').strip()
        product.price = price
        product.stock = stock
        product.category_id = category_id
        product.is_active = request.form.get('is_active') == 'on'
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext in allowed_extensions:
                    from werkzeug.utils import secure_filename
                    filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
                    filepath = os.path.join('app', 'static', 'uploads', filename)
                    file.save(filepath)
                    product.image = filename
                else:
                    flash('Invalid image format. Use PNG, JPG, JPEG, GIF, or WEBP', 'error')
        
        db.session.commit()
        flash(f'Product "{name}" updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to update product. Please try again.', 'error')
    
    return redirect(url_for('admin.products'))

@bp.route('/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    """
    Delete a product.
    
    Args:
        id: Product ID
        
    Admin can delete products. This will also remove associated cart items.
    """
    product = Product.query.get_or_404(id)
    product_name = product.name
    
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{product_name}" deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete product. It may be referenced in existing orders.', 'error')
    
    return redirect(url_for('admin.products'))

# Category Management
@bp.route('/categories')
@login_required
@admin_required
def categories():
    categories = Category.query.all()
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
    
    if Category.query.filter_by(name=name).first():
        flash('Category already exists', 'error')
        return redirect(url_for('admin.categories'))
    
    try:
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{name}" added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to add category. Please try again.', 'error')
    
    return redirect(url_for('admin.categories'))

@bp.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    category.name = request.form.get('name')
    category.description = request.form.get('description')
    db.session.commit()
    flash('Category updated successfully', 'success')
    return redirect(url_for('admin.categories'))

@bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully', 'success')
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
    if status_filter:
        orders = Order.query.filter_by(status=status_filter).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders, current_status=status_filter)

# VIEW ORDER DETAILS
@bp.route('/orders/<int:id>')
@login_required
@admin_required
def order_detail(id):
    order = Order.query.get_or_404(id)
    return render_template('admin/order_detail.html', order=order)

# APPROVE ORDER - Admin can approve orders
@bp.route('/orders/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'Approved'
    order.decline_reason = None
    db.session.commit()
    flash('Order approved', 'success')
    return redirect(url_for('admin.orders'))

@bp.route('/orders/<int:id>/ship', methods=['POST'])
@login_required
@admin_required
def ship_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'Shipped'
    db.session.commit()
    flash('Order marked as shipped', 'success')
    return redirect(url_for('admin.orders'))

@bp.route('/orders/<int:id>/deliver', methods=['POST'])
@login_required
@admin_required
def deliver_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'Delivered'
    db.session.commit()
    flash('Order marked as delivered', 'success')
    return redirect(url_for('admin.orders'))

# DECLINE ORDER - Admin can decline orders and provide reason for customers to know
# DECLINE ORDER - Admin can decline orders and provide reason for customers to know
@bp.route('/orders/<int:id>/decline', methods=['POST'])
@login_required
@admin_required
def decline_order(id):
    """
    Decline an order and provide reason for customers.
    
    Args:
        id: Order ID
        
    When declined, the reason is stored so customers can see why their order was declined.
    Stock is restored for declined orders.
    """
    order = Order.query.get_or_404(id)
    
    # Validate order can be declined
    if order.status == 'Declined':
        flash('Order is already declined', 'error')
        return redirect(url_for('admin.order_detail', id=id))
    
    if order.status in ['Shipped', 'Delivered']:
        flash('Cannot decline an order that has already been shipped or delivered', 'error')
        return redirect(url_for('admin.order_detail', id=id))
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        reason = 'No reason provided'
    
    try:
        order.status = 'Declined'
        order.decline_reason = reason
        
        # Restore stock for declined orders
        for item in order.items:
            if item.product:
                item.product.stock += item.quantity
        
        db.session.commit()
        flash(f'Order #{order.id} declined. Reason: {reason}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to decline order. Please try again.', 'error')
    
    return redirect(url_for('admin.orders'))

# ============================================================================
# FEATURE 2: GENERATE SALES REPORTS
# Admin can view daily/weekly/monthly sales reports. Can be generated into pdf or doc file (optional)
# ============================================================================
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
    
    orders = Order.query.filter(
        Order.created_at >= datetime.combine(start_date, datetime.min.time()),
        Order.created_at < datetime.combine(end_date, datetime.min.time()),
        Order.status.in_(['Approved', 'Shipped', 'Delivered'])
    ).all()
    
    total_revenue = sum(o.total_amount for o in orders)
    total_orders = len(orders)
    
    # Get order items with product info for report
    order_data = []
    for order in orders:
        for item in order.items:
            order_data.append({
                'order_id': order.id,
                'date': order.created_at,
                'product': item.product_name,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.quantity * item.price,
                'status': order.status
            })
    
    return render_template('admin/reports.html',
                          period=period,
                          orders=orders,
                          order_data=order_data,
                          total_revenue=total_revenue,
                          total_orders=total_orders,
                          start_date=start_date,
                          end_date=today)

# DOWNLOAD REPORT - Generate sales reports into PDF file (optional)
@bp.route('/reports/download')
@login_required
@admin_required
def download_report():
    period = request.args.get('period', 'daily')
    
    today = datetime.utcnow().date()
    
    if period == 'daily':
        start_date = today
    elif period == 'weekly':
        start_date = today - timedelta(days=7)
    else:
        start_date = today - timedelta(days=30)
    
    orders = Order.query.filter(
        Order.created_at >= datetime.combine(start_date, datetime.min.time()),
        Order.status.in_(['Approved', 'Shipped', 'Delivered'])
    ).all()
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"Sales Report - {period.capitalize()}", styles['Heading1']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"Period: {start_date} to {today}", styles['Normal']))
        elements.append(Paragraph(" ", styles['Normal']))
        
        data = [['Order ID', 'Date', 'Customer', 'Total', 'Status']]
        total_revenue = 0
        for order in orders:
            data.append([
                str(order.id),
                order.created_at.strftime('%Y-%m-%d'),
                order.customer.username,
                f"${order.total_amount:.2f}",
                order.status
            ])
            total_revenue += order.total_amount
        
        data.append(['', '', 'TOTAL', f"${total_revenue:.2f}", ''])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'sales_report_{period}_{today}.pdf',
            mimetype='application/pdf'
        )
    except ImportError:
        flash('PDF generation requires reportlab library', 'error')
        return redirect(url_for('admin.reports'))

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
    users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

# ACTIVATE/DEACTIVATE ACCOUNTS - Admin can deactivate/activate customer accounts
@bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    if user.is_admin:
        flash('Cannot modify admin status', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_active_account = not user.is_active_account
    db.session.commit()
    status = 'activated' if user.is_active_account else 'deactivated'
    flash(f'User {user.username} {status}', 'success')
    return redirect(url_for('admin.users'))

# RESET PASSWORD - Admin can reset customer password
# RESET PASSWORD - Admin can reset customer password
@bp.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(id):
    """
    Reset customer password.
    
    Args:
        id: User ID
        
    Admin can reset customer passwords. If no password provided, uses default.
    """
    user = User.query.get_or_404(id)
    
    if user.is_admin:
        flash('Cannot reset admin password through this interface', 'error')
        return redirect(url_for('admin.users'))
    
    new_password = request.form.get('new_password', '').strip()
    
    # Use default password if none provided
    if not new_password:
        new_password = 'password123'
    
    # Validate password strength
    if len(new_password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password reset for {user.username}. New password: {new_password}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to reset password. Please try again.', 'error')
    
    return redirect(url_for('admin.users'))

