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
from app import mysql
# from app.models import Product # Removed
from datetime import datetime
import os
import pymysql.cursors

bp = Blueprint('customer', __name__)

@bp.route('/')
def home():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM product 
        WHERE is_active = 1 
        ORDER BY created_at DESC LIMIT 8
    """)
    products = cursor.fetchall()
    
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()
    
    cursor.close()
    return render_template('customer/home.html', products=products, categories=categories)

@bp.route('/products')
def products():
    category_id = request.args.get('category')
    search = request.args.get('search', '')
    
    cursor = mysql.connection.cursor()
    
    query = "SELECT p.*, c.name as category_name FROM product p LEFT JOIN category c ON p.category_id = c.id WHERE p.is_active = 1"
    params = []
    
    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)
    
    if search:
        query += " AND p.name LIKE %s"
        params.append(f'%{search}%')
    
    query += " ORDER BY p.created_at DESC"
    
    cursor.execute(query, tuple(params))
    products = cursor.fetchall()
    
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()
    
    cursor.close()
    
    return render_template('customer/products.html', 
                          products=products, 
                          categories=categories,
                          current_category=int(category_id) if category_id and category_id.isdigit() else None,
                          search=search)

@bp.route('/product/<int:id>')
def product_detail(id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT p.*, c.name as category_name 
        FROM product p 
        LEFT JOIN category c ON p.category_id = c.id 
        WHERE p.id = %s
    """, (id,))
    product = cursor.fetchone()
    cursor.close()
    
    if not product:
        return render_template('errors/404.html'), 404
        
    # Ensure nested dictionary if template uses dot notation for category
    # Although DictCursor returns dict, accessing 'p.category.name' in template requires 'category' key
    if product.get('category_name'):
        product['category'] = {'name': product['category_name']}
    else:
        product['category'] = None
        
    return render_template('customer/product_detail.html', product=product)

@bp.route('/cart')
@login_required
def cart():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT ci.*, p.name as product_name, p.price as product_price, p.stock as product_stock, p.image as product_image, p.is_active as product_active
        FROM cart_item ci
        LEFT JOIN product p ON ci.product_id = p.id
        WHERE ci.user_id = %s
    """, (current_user.id,))
    items_raw = cursor.fetchall()
    
    cart_items = []
    total = 0
    if items_raw:
        for row in items_raw:
            # Structure for template compatibility
            # Provide dictionary access that mimics object structure if possible, or update template
            # For now, we'll create a structure that allows item['product']['name'] if we pass it as dict
            # or we might need to update the template to use item.product.name if it expects objects, 
            # but usually Jinja handles dict["key"] or object.key interchangeably if we are careful.
            # However, existing template likely uses dot notation. 
            # Ideally we'd update template or use a wrapper class, but simpler to construct dicts and update template usage or ensure strict dict usage.
            # Let's verify template usage later. For now, we build a robust dict.
            
            item = {
                'id': row['id'],
                'user_id': row['user_id'],
                'product_id': row['product_id'],
                'quantity': row['quantity'],
                'product': {
                    'id': row['product_id'],
                    'name': row['product_name'],
                    'price': row['product_price'],
                    'stock': row['product_stock'],
                    'image': row['product_image'],
                    'is_active': row['product_active']
                } if row['product_name'] else None
            }
            if item['product']:
                total += item['product']['price'] * item['quantity']
            cart_items.append(item)
            
    cursor.close()
    return render_template('customer/cart.html', cart_items=cart_items, total=total)

@bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """
    Add product to shopping cart.
    """
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM product WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        return render_template('errors/404.html'), 404
    
    # Check if product is active
    if not product['is_active']:
        cursor.close()
        flash('This product is currently unavailable', 'error')
        return redirect(url_for('customer.product_detail', id=product_id))
    
    # Validate quantity
    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity <= 0:
            cursor.close()
            flash('Quantity must be greater than 0', 'error')
            return redirect(url_for('customer.product_detail', id=product_id))
    except (ValueError, TypeError):
        cursor.close()
        flash('Invalid quantity', 'error')
        return redirect(url_for('customer.product_detail', id=product_id))
    
    # Check stock availability (check existing cart quantity + new quantity)
    cursor.execute("SELECT * FROM cart_item WHERE user_id = %s AND product_id = %s", (current_user.id, product_id))
    existing_cart_item = cursor.fetchone()
    
    current_quantity = existing_cart_item['quantity'] if existing_cart_item else 0
    total_quantity = current_quantity + quantity
    
    if total_quantity > product['stock']:
        cursor.close()
        flash(f"Not enough stock available. Only {product['stock']} items in stock.", 'error')
        return redirect(url_for('customer.product_detail', id=product_id))
    
    try:
        if existing_cart_item:
            cursor.execute("UPDATE cart_item SET quantity = %s WHERE id = %s", (total_quantity, existing_cart_item['id']))
        else:
            cursor.execute("INSERT INTO cart_item (user_id, product_id, quantity) VALUES (%s, %s, %s)", 
                          (current_user.id, product_id, quantity))
        
        mysql.connection.commit()
        flash(f"{product['name']} added to cart successfully!", 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to add item to cart. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('customer.cart'))

@bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    """
    Update quantity of item in cart.
    """
    cursor = mysql.connection.cursor()
    
    # Fetch cart item with product info
    cursor.execute("""
        SELECT ci.*, p.stock as product_stock, p.id as product_id
        FROM cart_item ci
        LEFT JOIN product p ON ci.product_id = p.id
        WHERE ci.id = %s
    """, (item_id,))
    cart_item = cursor.fetchone()
    
    # Verify ownership and existence
    if not cart_item or cart_item['user_id'] != current_user.id:
        cursor.close()
        flash('Unauthorized access or item not found', 'error')
        return redirect(url_for('customer.cart'))
    
    # Validate quantity
    try:
        quantity = int(request.form.get('quantity', 1))
    except (ValueError, TypeError):
        cursor.close()
        flash('Invalid quantity', 'error')
        return redirect(url_for('customer.cart'))
    
    # Remove item if quantity is 0 or less
    if quantity <= 0:
        try:
            cursor.execute("DELETE FROM cart_item WHERE id = %s", (item_id,))
            mysql.connection.commit()
            flash('Item removed from cart', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash('Failed to update cart. Please try again.', 'error')
        finally:
            cursor.close()
        return redirect(url_for('customer.cart'))
    
    # Check if product exists
    if not cart_item['product_id']:
        try:
            cursor.execute("DELETE FROM cart_item WHERE id = %s", (item_id,))
            mysql.connection.commit()
            flash('Product no longer exists', 'error')
        except:
            mysql.connection.rollback()
        finally:
            cursor.close()
        return redirect(url_for('customer.cart'))
    
    # Check stock
    if quantity > cart_item['product_stock']:
        cursor.close()
        flash(f"Not enough stock. Only {cart_item['product_stock']} items available.", 'error')
        return redirect(url_for('customer.cart'))
    
    # Update quantity
    try:
        cursor.execute("UPDATE cart_item SET quantity = %s WHERE id = %s", (quantity, item_id))
        mysql.connection.commit()
        flash('Cart updated successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to update cart. Please try again.', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('customer.cart'))

@bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cursor = mysql.connection.cursor()
    
    # Verify existence and ownership first
    cursor.execute("SELECT user_id FROM cart_item WHERE id = %s", (item_id,))
    cart_item = cursor.fetchone()
    
    if not cart_item or cart_item['user_id'] != current_user.id:
        cursor.close()
        flash('Unauthorized or item not found', 'error')
        return redirect(url_for('customer.cart'))
    
    try:
        cursor.execute("DELETE FROM cart_item WHERE id = %s", (item_id,))
        mysql.connection.commit()
        flash('Item removed from cart', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Failed to remove item', 'error')
    finally:
        cursor.close()
        
    return redirect(url_for('customer.cart'))

@bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """
    Handle checkout process.
    
    GET: Display checkout form
    POST: Process order creation
    """
    cursor = mysql.connection.cursor()
    
    # helper to get cart items
    def get_cart_items(uid):
        cursor.execute("""
            SELECT ci.*, p.name, p.price, p.stock, p.is_active, p.id as product_id
            FROM cart_item ci
            LEFT JOIN product p ON ci.product_id = p.id
            WHERE ci.user_id = %s
        """, (uid,))
        return cursor.fetchall()

    cart_items_raw = get_cart_items(current_user.id)
    
    if not cart_items_raw:
        cursor.close()
        flash('Your cart is empty. Add items before checkout.', 'error')
        return redirect(url_for('customer.cart'))
        
    # Process cart items for template and validation
    # Calculate total and validate items
    valid_items = []
    total = 0
    
    # We need to handle item validation and cleanup (delete invalid items)
    # Since we are iterating, we can collect IDs to delete
    items_to_delete = []
    
    for item in cart_items_raw:
        # Check if product exists (product_id from join would be NULL if not)
        if not item['product_id']:
            items_to_delete.append(item['id'])
            continue
            
        if not item['is_active']:
            flash(f"{item['name']} is no longer available", 'error')
            items_to_delete.append(item['id'])
            continue
            
        if item['quantity'] > item['stock']:
            flash(f"Not enough stock for {item['name']}. Available: {item['stock']}", 'error')
            cursor.close()
            return redirect(url_for('customer.cart'))
            
        # Structure item for template
        valid_item_struct = {
            'product_id': item['product_id'],
            'quantity': item['quantity'],
            'product': {
                'name': item['name'],
                'price': item['price'],
                'stock': item['stock']
            }
        }
        valid_items.append(valid_item_struct)
        total += item['price'] * item['quantity']
        
    # Perform cleanup of invalid items
    if items_to_delete:
        for iid in items_to_delete:
            cursor.execute("DELETE FROM cart_item WHERE id = %s", (iid,))
        mysql.connection.commit()
        
        # If we removed items but still have some, or maybe we removed all?
        # If we modified cart, maybe nice to redirect to cart to show updated state?
        # But existing logic just continued if valid_items remained.
        # But here we are modifying state in GET/POST.
        if not valid_items:
            cursor.close()
            flash('No valid items in cart', 'error')
            return redirect(url_for('customer.cart'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        shipping_address = request.form.get('shipping_address', '').strip()
        
        # Validate form data
        if not payment_method or payment_method not in ['COD', 'Online']:
            cursor.close()
            flash('Please select a valid payment method', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
        
        if not shipping_address:
            cursor.close()
            flash('Please provide a shipping address', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
        
        if len(shipping_address) < 10:
            cursor.close()
            flash('Shipping address must be at least 10 characters long', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
        
        # Re-validate stock before creating order (race condition check)
        for item in cart_items_raw:
             if item['product_id']: # Only check valid products
                cursor.execute("SELECT stock, name FROM product WHERE id = %s", (item['product_id'],))
                current_stock_data = cursor.fetchone()
                if item['quantity'] > current_stock_data['stock']:
                    cursor.close()
                    flash(f"Not enough stock for {current_stock_data['name']}. Available: {current_stock_data['stock']}", 'error')
                    return redirect(url_for('customer.cart'))

        payment_proof_filename = None
        # Handle payment proof for online payment
        if payment_method == 'Online':
            if 'payment_proof' not in request.files:
                cursor.close()
                flash('Please upload payment proof for online payment', 'error')
                return render_template('customer/checkout.html', cart_items=valid_items, total=total)
            
            file = request.files['payment_proof']
            if not file or not file.filename:
                cursor.close()
                flash('Please upload a valid payment proof image', 'error')
                return render_template('customer/checkout.html', cart_items=valid_items, total=total)
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if file_ext not in allowed_extensions:
                cursor.close()
                flash('Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, WEBP)', 'error')
                return render_template('customer/checkout.html', cart_items=valid_items, total=total)
            
            from werkzeug.utils import secure_filename
            filename = secure_filename(f"payment_{datetime.now().timestamp()}_{file.filename}")
            filepath = os.path.join('app', 'static', 'uploads', filename)
            file.save(filepath)
            payment_proof_filename = filename
            
        # Create order in transaction
        try:
            # Insert Order
            cursor.execute("""
                INSERT INTO `order` (user_id, total_amount, status, payment_method, shipping_address, payment_proof, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (current_user.id, total, 'Pending', payment_method, shipping_address, payment_proof_filename))
            order_id = cursor.lastrowid
            
            # Insert Order Items and Update Stock
            for item in cart_items_raw:
                if item['product_id']: # Skip invalid
                    cursor.execute("""
                        INSERT INTO order_item (order_id, product_id, product_name, quantity, price)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (order_id, item['product_id'], item['name'], item['quantity'], item['price']))
                    
                    cursor.execute("""
                        UPDATE product SET stock = stock - %s WHERE id = %s
                    """, (item['quantity'], item['product_id']))
            
            # Clear Cart
            cursor.execute("DELETE FROM cart_item WHERE user_id = %s", (current_user.id,))
            
            mysql.connection.commit()
            flash('Order placed successfully! Your order is now pending approval.', 'success')
            cursor.close()
            return redirect(url_for('customer.order_detail', id=order_id))
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Failed to place order. Please try again.', 'error')
            return render_template('customer/checkout.html', cart_items=valid_items, total=total)
            
    cursor.close()
    return render_template('customer/checkout.html', cart_items=valid_items, total=total)

@bp.route('/orders')
@login_required
def orders():
    """
    Display all orders for the current user.
    """
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM `order` 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    """, (current_user.id,))
    orders = cursor.fetchall()
    cursor.close()
    return render_template('customer/orders.html', orders=orders)

@bp.route('/orders/<int:id>')
@login_required
def order_detail(id):
    """
    Display detailed information for a specific order.
    """
    cursor = mysql.connection.cursor()
    
    # Get order
    cursor.execute("SELECT * FROM `order` WHERE id = %s", (id,))
    order_data = cursor.fetchone()
    
    if not order_data:
        cursor.close()
        return render_template('errors/404.html'), 404

    # Verify ownership (unless admin)
    if order_data['user_id'] != current_user.id and not current_user.is_admin:
        cursor.close()
        flash('Unauthorized access to this order', 'error')
        return redirect(url_for('customer.orders'))
        
    # Get order items
    cursor.execute("""
        SELECT oi.*, p.image as product_image 
        FROM order_item oi 
        LEFT JOIN product p ON oi.product_id = p.id
        WHERE order_id = %s
    """, (id,))
    items_raw = cursor.fetchall()
    
    # Structure for template - create a new dict to avoid conflicts with built-in methods
    order = dict(order_data)  # Convert Row to plain dict
    order['items'] = []
    if items_raw:
        for item in items_raw:
            # Template expects item.product.image structure
            item_dict = dict(item)  # Convert Row to plain dict
            item_dict['product'] = {'image': item_dict['product_image']} if item_dict.get('product_image') else None
            order['items'].append(item_dict)
            
    cursor.close()
    return render_template('customer/order_detail.html', order=order)

