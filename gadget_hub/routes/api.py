"""
API routes for JSON endpoints.

This module provides API endpoints for products, categories, cart count, and dashboard statistics.
"""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from gadget_hub import mysql
import pymysql.cursors

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/products')
def get_products():
    """
    Get all active products as JSON.
    
    Returns:
        JSON array of product objects
    """
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT p.*, c.name as category_name 
            FROM product p 
            LEFT JOIN category c ON p.category_id = c.id 
            WHERE p.is_active = 1
        """)
        products = cursor.fetchall()
        cursor.close()
        
        return jsonify([{
            'id': p['id'],
            'name': p['name'],
            'price': p['price'],
            'stock': p['stock'],
            'category': p['category_name']
        } for p in products])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch products'}), 500

@bp.route('/categories')
def get_categories():
    """
    Get all categories as JSON.
    
    Returns:
        JSON array of category objects with product counts
    """
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT c.id, c.name, COUNT(p.id) as product_count 
            FROM category c 
            LEFT JOIN product p ON c.id = p.category_id 
            GROUP BY c.id, c.name
        """)
        categories = cursor.fetchall()
        cursor.close()
        
        return jsonify([{
            'id': c['id'],
            'name': c['name'],
            'product_count': c['product_count']
        } for c in categories])
    except Exception as e:
        return jsonify({'error': 'Failed to fetch categories'}), 500

@bp.route('/cart/count')
@login_required
def cart_count():
    """
    Get current user's cart item count.
    
    Returns:
        JSON object with cart count
    """
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM cart_item WHERE user_id = %s", (current_user.id,))
        result = cursor.fetchone()
        cursor.close()
        return jsonify({'count': result['count']})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch cart count'}), 500

@bp.route('/dashboard/stats')
@login_required
def dashboard_stats():
    """
    Get admin dashboard statistics.
    
    Returns:
        JSON object with dashboard statistics (orders, products, revenue)
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM `order`")
        total_orders = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM `order` WHERE status = 'Pending'")
        pending_orders = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM product")
        total_products = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT SUM(total_amount) as revenue 
            FROM `order` 
            WHERE status IN ('Approved', 'Shipped', 'Delivered')
        """)
        result = cursor.fetchone()
        total_revenue = result['revenue'] if result and result['revenue'] else 0
        
        cursor.close()
        
        return jsonify({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_products': total_products,
            'total_revenue': total_revenue
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch dashboard statistics'}), 500
