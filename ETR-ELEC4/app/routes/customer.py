"""
Customer routes for browsing products, managing cart, and placing orders.

This module handles all customer-facing functionality including:
- Product browsing and searching
- Shopping cart management
- Checkout and payment processing
- Order tracking
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Order, OrderItem, CartItem
from datetime import datetime
import os

bp = Blueprint('customer', __name__)

@bp.route('/')
def home():
    products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.all()
    return render_template('customer/home.html', products=products, categories=categories)

@bp.route('/products')
def products():
    category_id = request.args.get('category')
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    
    return render_template('customer/products.html', 
                          products=products, 
                          categories=categories,
                          current_category=category_id,
                          search=search)

@bp.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('customer/product_detail.html', product=product)

@bp.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items if item.product)
    return render_template('customer/cart.html', cart_items=cart_items, total=total)

@bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """
    Add product to shopping cart.
    
    Args:
        product_id: ID of the product to add
    """
    product = Product.query.get_or_404(product_id)
    
    # Check if product is active
    if not product.is_active:
        flash('This product is currently unavailable', 'error')
        return redirect(url_for('customer.product_detail', id=product_id))
    
    # Validate quantity
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity <= 0:
            flash('Quantity must be greater than 0', 'error')
            return redirect(url_for('customer.product_detail', id=product_id))
    except (ValueError, TypeError):
        flash('Invalid quantity', 'error')
        return redirect(url_for('customer.product_detail', id=product_id))
    
    # Check stock availability
    existing_cart_item = CartItem.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id
    ).first()
    
    current_quantity = existing_cart_item.quantity if existing_cart_item else 0
    total_quantity = current_quantity + quantity
    
    if total_quantity > product.stock:
        flash(f'Not enough stock available. Only {product.stock} items in stock.', 'error')
        return redirect(url_for('customer.product_detail', id=product_id))
    
    # Add or update cart item
    try:
        if existing_cart_item:
            existing_cart_item.quantity = total_quantity
        else:
            cart_item = CartItem(
                user_id=current_user.id, 
                product_id=product_id, 
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        flash(f'{product.name} added to cart successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to add item to cart. Please try again.', 'error')
    
    return redirect(url_for('customer.cart'))

@bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    """
    Update quantity of item in cart.
    
    Args:
        item_id: ID of the cart item to update
    """
    cart_item = CartItem.query.get_or_404(item_id)
    
    # Verify ownership
    if cart_item.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('customer.cart'))
    
    # Validate quantity
    try:
        quantity = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        flash('Invalid quantity', 'error')
        return redirect(url_for('customer.cart'))
    
    # Remove item if quantity is 0 or less
    if quantity <= 0:
        try:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Item removed from cart', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Failed to update cart. Please try again.', 'error')
        return redirect(url_for('customer.cart'))
    
    # Check stock availability
    if not cart_item.product:
        flash('Product no longer exists', 'error')
        db.session.delete(cart_item)
        db.session.commit()
        return redirect(url_for('customer.cart'))
    
    if quantity > cart_item.product.stock:
        flash(f'Not enough stock. Only {cart_item.product.stock} items available.', 'error')
        return redirect(url_for('customer.cart'))
    
    # Update quantity
    try:
        cart_item.quantity = quantity
        db.session.commit()
        flash('Cart updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to update cart. Please try again.', 'error')
    
    return redirect(url_for('customer.cart'))

@bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('Unauthorized', 'error')
        return redirect(url_for('customer.cart'))
    
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart', 'success')
    return redirect(url_for('customer.cart'))

@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """
    Handle checkout process.
    
    GET: Display checkout form
    POST: Process order creation
    """
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty. Add items before checkout.', 'error')
        return redirect(url_for('customer.cart'))
    
    # Calculate total and validate items
    total = 0
    valid_items = []
    for item in cart_items:
        if not item.product:
            # Remove invalid items
            db.session.delete(item)
            continue
        if not item.product.is_active:
            flash(f'{item.product.name} is no longer available', 'error')
            db.session.delete(item)
            continue
        if item.quantity > item.product.stock:
            flash(f'Not enough stock for {item.product.name}. Available: {item.product.stock}', 'error')
            return redirect(url_for('customer.cart'))
        total += item.product.price * item.quantity
        valid_items.append(item)
    
    if not valid_items:
        db.session.commit()
        flash('No valid items in cart', 'error')
        return redirect(url_for('customer.cart'))
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        shipping_address = request.form.get('shipping_address', '').strip()
        
        # Validate form data
        if not payment_method or payment_method not in ['COD', 'Online']:
            flash('Please select a valid payment method', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
        
        if not shipping_address:
            flash('Please provide a shipping address', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
        
        if len(shipping_address) < 10:
            flash('Shipping address must be at least 10 characters long', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
        
        # Re-validate stock before creating order
        for item in valid_items:
            product = Product.query.get(item.product_id)
            if item.quantity > product.stock:
                flash(f'Not enough stock for {product.name}. Available: {product.stock}', 'error')
                return redirect(url_for('customer.cart'))
        
        # Create order
        try:
            order = Order(
                user_id=current_user.id,
                payment_method=payment_method,
                shipping_address=shipping_address,
                total_amount=total
            )
            
            # Handle payment proof for online payment
            if payment_method == 'Online':
                if 'payment_proof' not in request.files:
                    flash('Please upload payment proof for online payment', 'error')
                    return render_template('customer/checkout.html', cart_items=valid_items, total=total)
                
                file = request.files['payment_proof']
                if not file or not file.filename:
                    flash('Please upload a valid payment proof image', 'error')
                    return render_template('customer/checkout.html', cart_items=valid_items, total=total)
                
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext not in allowed_extensions:
                    flash('Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, WEBP)', 'error')
                    return render_template('customer/checkout.html', cart_items=valid_items, total=total)
                
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"payment_{datetime.now().timestamp()}_{file.filename}")
                filepath = os.path.join('app', 'static', 'uploads', filename)
                file.save(filepath)
                order.payment_proof = filename
            
            db.session.add(order)
            db.session.flush()
            
            # Add order items and reduce stock
            for item in valid_items:
                product = Product.query.get(item.product_id)
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_name=product.name,
                    quantity=item.quantity,
                    price=product.price
                )
                db.session.add(order_item)
                product.stock -= item.quantity
            
            # Clear cart
            CartItem.query.filter_by(user_id=current_user.id).delete()
            
            db.session.commit()
            flash('Order placed successfully! Your order is now pending approval.', 'success')
            return redirect(url_for('customer.order_detail', id=order.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to place order. Please try again.', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
    
    return render_template('customer/checkout.html', cart_items=valid_items, total=total)

@bp.route('/orders')
@login_required
def orders():
    """
    Display all orders for the current user.
    
    Shows order history with status tracking (Pending, Shipped, Delivered).
    """
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=orders)


@bp.route('/orders/<int:id>')
@login_required
def order_detail(id):
    """
    Display detailed information for a specific order.
    
    Args:
        id: Order ID
        
    Customers can view order status: Pending, Shipped, Delivered
    """
    order = Order.query.get_or_404(id)
    
    # Verify ownership (unless admin)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access to this order', 'error')
        return redirect(url_for('customer.orders'))
    
    return render_template('customer/order_detail.html', order=order)

