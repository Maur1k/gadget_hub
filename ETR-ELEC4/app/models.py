"""
Database models for the e-commerce application.

This module defines all database models including User, Category, Product,
Order, OrderItem, and CartItem models.
"""
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


@login_manager.user_loader
def load_user(id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(id))


class User(UserMixin, db.Model):
    """
    User model representing customers and administrators.
    
    Attributes:
        id: Primary key
        email: Unique email address
        username: Unique username
        password_hash: Hashed password
        is_admin: Boolean flag for admin privileges
        is_active_account: Boolean flag for account status
        created_at: Account creation timestamp
        orders: Relationship to Order model
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    orders = db.relationship('Order', backref='customer', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """
        Set user password by hashing it.
        
        Args:
            password: Plain text password to hash
        """
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Check if provided password matches the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    """
    Category model for organizing products.
    
    Attributes:
        id: Primary key
        name: Unique category name
        description: Category description
        products: Relationship to Product model
    """
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    """
    Product model representing items in the store.
    
    Attributes:
        id: Primary key
        name: Product name
        description: Product description
        price: Product price
        stock: Available stock quantity
        image: Product image filename
        category_id: Foreign key to Category
        is_active: Boolean flag for product availability
        created_at: Product creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    image = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def is_in_stock(self):
        """Check if product is in stock."""
        return self.stock > 0 and self.is_active
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Order(db.Model):
    """
    Order model representing customer orders.
    
    Status values: Pending, Approved, Shipped, Delivered, Declined
    Payment methods: COD (Cash on Delivery), Online
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        status: Order status
        decline_reason: Reason provided when order is declined
        payment_method: Payment method used
        payment_proof: Path to payment proof screenshot (for online payments)
        total_amount: Total order amount
        shipping_address: Delivery address
        created_at: Order creation timestamp
        updated_at: Last update timestamp
        items: Relationship to OrderItem model
    """
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), default='Pending', nullable=False, index=True)
    decline_reason = db.Column(db.Text)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_proof = db.Column(db.String(255))
    total_amount = db.Column(db.Float, default=0, nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def can_be_cancelled(self):
        """Check if order can be cancelled (only if pending)."""
        return self.status == 'Pending'
    
    def __repr__(self):
        return f'<Order {self.id} - {self.status}>'

class OrderItem(db.Model):
    """
    OrderItem model representing individual items in an order.
    
    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        product_id: Foreign key to Product
        product_name: Snapshot of product name at time of order
        quantity: Quantity ordered
        price: Snapshot of price at time of order
        product: Relationship to Product model
    """
    __tablename__ = 'order_item'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='SET NULL'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    product = db.relationship('Product')
    
    def subtotal(self):
        """Calculate subtotal for this order item."""
        return self.quantity * self.price
    
    def __repr__(self):
        return f'<OrderItem {self.product_name} x {self.quantity}>'

class CartItem(db.Model):
    """
    CartItem model representing items in user's shopping cart.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        product_id: Foreign key to Product
        quantity: Quantity in cart
        user: Relationship to User model
        product: Relationship to Product model
    """
    __tablename__ = 'cart_item'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    
    user = db.relationship('User', backref='cart_items')
    product = db.relationship('Product')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)
    
    def subtotal(self):
        """Calculate subtotal for this cart item."""
        if self.product:
            return self.quantity * self.product.price
        return 0
    
    def __repr__(self):
        return f'<CartItem User:{self.user_id} Product:{self.product_id} Qty:{self.quantity}>'

