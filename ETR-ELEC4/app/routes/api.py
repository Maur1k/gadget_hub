"""
API routes for JSON endpoints.

This module provides API endpoints for products, categories, cart count, and dashboard statistics.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Order, CartItem

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/products')
def get_products():
    """
    Get all active products as JSON.
    
    Returns:
        JSON array of product objects
    """
    try:
        products = Product.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'stock': p.stock,
            'category': p.category.name if p.category else None
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
        categories = Category.query.all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'product_count': c.products.count()
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
        count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'count': count})
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
        return jsonify({
            'total_orders': Order.query.count(),
            'pending_orders': Order.query.filter_by(status='Pending').count(),
            'total_products': Product.query.count(),
            'total_revenue': db.session.query(db.func.sum(Order.total_amount)).filter(
                Order.status.in_(['Approved', 'Shipped', 'Delivered'])
            ).scalar() or 0
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch dashboard statistics'}), 500

