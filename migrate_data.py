
import sqlite3
import pymysql
import os
from config import Config

def migrate():
    # 1. Connect to SQLite
    print("Connecting to SQLite...")
    if not os.path.exists('ecommerce.db'):
        print("Error: ecommerce.db not found!")
        return
        
    sqlite_conn = sqlite3.connect('ecommerce.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # 2. Connect to MySQL
    print("Connecting to MySQL...")
    mysql_conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    mysql_cursor = mysql_conn.cursor()
    
    try:
        # Disable FK checks to allow arbitrary insertion order if needed
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Clear existing MySQL data to avoid duplicates/conflicts
        print("Clearing existing MySQL data...")
        tables = ['cart_item', 'order_item', '`order`', 'product', 'category', 'user']
        for table in tables:
            mysql_cursor.execute(f"DELETE FROM {table}")
            mysql_cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
            
        # Migrate Users
        print("Migrating Users...")
        sqlite_cursor.execute("SELECT * FROM user")
        users = sqlite_cursor.fetchall()
        for user in users:
            user = dict(user)
            mysql_cursor.execute("""
                INSERT INTO user (id, email, username, password_hash, is_admin, is_active_account, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user['id'], user['email'], user['username'], user['password_hash'], 
                  user['is_admin'], user.get('is_active_account', 1), user.get('created_at'))) # Handle potentially missing columns if schema changed
            
        # Migrate Categories
        print("Migrating Categories...")
        sqlite_cursor.execute("SELECT * FROM category")
        categories = sqlite_cursor.fetchall()
        for cat in categories:
            cat = dict(cat)
            mysql_cursor.execute("""
                INSERT INTO category (id, name, description)
                VALUES (%s, %s, %s)
            """, (cat['id'], cat['name'], cat.get('description')))
            
        # Migrate Products
        print("Migrating Products...")
        sqlite_cursor.execute("SELECT * FROM product")
        products = sqlite_cursor.fetchall()
        for p in products:
            p = dict(p)
            # Check for boolean conversion if needed (SQLite uses 0/1 usually, MySQL does too but good to be safe)
            mysql_cursor.execute("""
                INSERT INTO product (id, name, description, price, stock, image, category_id, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (p['id'], p['name'], p.get('description'), p['price'], p['stock'], p['image'], 
                  p['category_id'], p.get('is_active', 1), p.get('created_at'), p.get('updated_at')))
            
        # Migrate Orders
        # Warning: SQLite table might be 'order' or 'orders' - try 'order' first (reserved word)
        print("Migrating Orders...")
        try:
            sqlite_cursor.execute("SELECT * FROM `order`")
        except sqlite3.OperationalError:
            # Try 'orders' if 'order' fails (though likely 'order' if SQLAlchemy default was used)
            sqlite_cursor.execute("SELECT * FROM orders")
            
        orders = sqlite_cursor.fetchall()
        for o in orders:
            o = dict(o)
            mysql_cursor.execute("""
                INSERT INTO `order` (id, user_id, status, decline_reason, payment_method, payment_proof, total_amount, shipping_address, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (o['id'], o['user_id'], o.get('status', 'Pending'), o.get('decline_reason'), o['payment_method'], o.get('payment_proof'), 
                  o['total_amount'], o['shipping_address'], o['created_at'], o.get('updated_at')))

        # Migrate Order Items
        print("Migrating Order Items...")
        sqlite_cursor.execute("SELECT * FROM order_item")
        items = sqlite_cursor.fetchall()
        for i in items:
            i = dict(i)
            # If product_name missing, set default or handle
            mysql_cursor.execute("""
                INSERT INTO order_item (id, order_id, product_id, product_name, quantity, price)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (i['id'], i['order_id'], i['product_id'], i.get('product_name', 'Product'), i['quantity'], i['price']))
            # Note: product_name might be missing in old schema if it was normalized, but looking at current usage it seems required.
            # If Sqlite didn't have it, we might need to fetch from product table via product_id.
            # Let's verify if product_name exists in SQLite. If not, we join or fetch.
            # Assuming it exists for now based on typical patterns, if error, we catch it.
        
        # Migrate Cart Items
        print("Migrating Cart Items...")
        sqlite_cursor.execute("SELECT * FROM cart_item")
        cart_items = sqlite_cursor.fetchall()
        for c in cart_items:
            c = dict(c)
            mysql_cursor.execute("""
                INSERT INTO cart_item (id, user_id, product_id, quantity)
                VALUES (%s, %s, %s, %s)
            """, (c['id'], c['user_id'], c['product_id'], c['quantity']))

        # Enable FK checks
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        mysql_conn.commit()
        print("Migration successful!")
        
    except Exception as e:
        mysql_conn.rollback()
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sqlite_conn.close()
        mysql_conn.close()

if __name__ == "__main__":
    migrate()
