"""
Initialize database with gadget store data using raw SQL.
Categories: Laptops, Smartphones, Tablets, Gaming Phones
Products: Apple, Samsung, Asus, Lenovo, etc.
"""
from gadget_hub import create_app, mysql
from gadget_hub.models import User
from werkzeug.security import generate_password_hash

def init_database():
    app = create_app()
    
    with app.app_context():
        cursor = mysql.connection.cursor()
        
        try:
            # Clear existing data (in reverse order due to foreign keys)
            cursor.execute("DELETE FROM order_item")
            cursor.execute("DELETE FROM `order`")
            cursor.execute("DELETE FROM cart_item")
            cursor.execute("DELETE FROM product")
            cursor.execute("DELETE FROM category")
            cursor.execute("DELETE FROM user")
            
            # Create admin user
            admin_password_hash = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO user (email, username, password_hash, is_admin, is_active_account)
                VALUES (%s, %s, %s, %s, %s)
            """, ('admin@admin.com', 'admin', admin_password_hash, 1, 1))
            
            # Create sample customer
            customer_password_hash = generate_password_hash('customer123')
            cursor.execute("""
                INSERT INTO user (email, username, password_hash, is_admin, is_active_account)
                VALUES (%s, %s, %s, %s, %s)
            """, ('customer@test.com', 'customer', customer_password_hash, 0, 1))
            
            # Create gadget categories
            categories_data = [
                ('Laptops', 'Gaming laptops, ultrabooks, and workstations'),
                ('Smartphones', 'iPhones, Android phones, and flagship devices'),
                ('Tablets', 'iPads, Android tablets, and drawing tablets'),
                ('Gaming Phones', 'High-performance gaming smartphones'),
                ('Accessories', 'Cases, chargers, and peripherals')
            ]
            
            for name, description in categories_data:
                cursor.execute("""
                    INSERT INTO category (name, description)
                    VALUES (%s, %s)
                """, (name, description))
            
            # Get category IDs for products (assuming order: 1=Laptops, 2=Smartphones, etc.)
            cursor.execute("SELECT id, name FROM category ORDER BY id")
            categories = {cat['name']: cat['id'] for cat in cursor.fetchall()}
            
            # Create gadget products
            products_data = [
                # Laptops (category_id=1)
                ('MacBook Pro 14" M3 Pro', 'Apple M3 Pro chip, 18GB RAM, 512GB SSD, Liquid Retina XDR display', 89999.00, 15, categories['Laptops']),
                ('ASUS ROG Zephyrus G14', 'AMD Ryzen 9, RTX 4060, 16GB RAM, 1TB SSD, 14" QHD 165Hz', 74999.00, 20, categories['Laptops']),
                ('Lenovo ThinkPad X1 Carbon', 'Intel Core i7, 16GB RAM, 512GB SSD, 14" 2.8K OLED', 82999.00, 12, categories['Laptops']),
                ('Dell XPS 15', 'Intel Core i7-13700H, 32GB RAM, 1TB SSD, RTX 4050, 15.6" OLED', 94999.00, 8, categories['Laptops']),
                
                # Smartphones (category_id=2)
                ('iPhone 15 Pro Max', 'A17 Pro chip, 256GB, Titanium design, 48MP camera, Action button', 74990.00, 25, categories['Smartphones']),
                ('iPhone 15 Pro', 'A17 Pro chip, 128GB, Titanium design, 48MP camera system', 64990.00, 30, categories['Smartphones']),
                ('Samsung Galaxy S24 Ultra', 'Snapdragon 8 Gen 3, 256GB, 200MP camera, S Pen, AI features', 69990.00, 20, categories['Smartphones']),
                ('Google Pixel 8 Pro', 'Tensor G3, 128GB, 50MP camera, 7 years of updates, AI photo editing', 54990.00, 18, categories['Smartphones']),
                
                # Tablets (category_id=3)
                ('iPad Pro 12.9" M2', 'Apple M2 chip, 256GB, Liquid Retina XDR, Face ID, Thunderbolt', 69990.00, 15, categories['Tablets']),
                ('iPad Air 5th Gen', 'Apple M1 chip, 64GB, 10.9" Liquid Retina, Touch ID, USB-C', 34990.00, 25, categories['Tablets']),
                ('Samsung Galaxy Tab S9 Ultra', 'Snapdragon 8 Gen 2, 256GB, 14.6" AMOLED, S Pen included', 64990.00, 12, categories['Tablets']),
                ('iPad 10th Generation', 'A14 Bionic chip, 64GB, 10.9" Liquid Retina, USB-C', 24990.00, 35, categories['Tablets']),
                
                # Gaming Phones (category_id=4)
                ('ASUS ROG Phone 8 Pro', 'Snapdragon 8 Gen 3, 16GB RAM, 512GB, 165Hz AMOLED, AeroActive Cooler', 59990.00, 10, categories['Gaming Phones']),
                ('Red Magic 9 Pro', 'Snapdragon 8 Gen 3, 16GB RAM, 512GB, 120Hz, Built-in cooling fan', 44990.00, 15, categories['Gaming Phones']),
                ('Xiaomi Black Shark 5 Pro', 'Snapdragon 8 Gen 1, 12GB RAM, 256GB, 144Hz AMOLED, Magnetic triggers', 34990.00, 20, categories['Gaming Phones']),
                ('Lenovo Legion Phone Duel 2', 'Snapdragon 888, 16GB RAM, 512GB, Dual cooling fans, Pop-up camera', 29990.00, 8, categories['Gaming Phones']),
                
                # Accessories (category_id=5)
                ('Apple AirPods Pro 2nd Gen', 'Active Noise Cancellation, Adaptive Audio, USB-C, MagSafe case', 14990.00, 50, categories['Accessories']),
                ('Apple Magic Keyboard for iPad Pro', 'Backlit keys, trackpad, USB-C passthrough, floating design', 17990.00, 20, categories['Accessories']),
                ('Samsung Galaxy Buds2 Pro', '24-bit Hi-Fi audio, ANC, 360 Audio, IPX7 water resistance', 10990.00, 40, categories['Accessories']),
                ('Anker 100W USB-C Charger', 'GaN II technology, 4 ports, foldable plug, fast charging', 3990.00, 100, categories['Accessories']),
            ]
            
            for name, description, price, stock, category_id in products_data:
                cursor.execute("""
                    INSERT INTO product (name, description, price, stock, category_id, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (name, description, price, stock, category_id, 1))
            
            # Get product IDs for order items
            cursor.execute("SELECT id, name FROM product ORDER BY id")
            products = {prod['name']: prod['id'] for prod in cursor.fetchall()}
            
            # Get customer user ID (should be 2, but get it dynamically)
            cursor.execute("SELECT id FROM user WHERE username = 'customer'")
            customer_id = cursor.fetchone()['id']
            
            # Create a sample order for testing
            cursor.execute("""
                INSERT INTO `order` (user_id, status, payment_method, total_amount, shipping_address, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, (customer_id, 'Pending', 'Online', 139980.00, 'Unit 1234, Tower A, BGC, Taguig City, Metro Manila 1630'))
            order_id = cursor.lastrowid
            
            # Add items to the order
            order_items = [
                (order_id, products['iPhone 15 Pro Max'], 'iPhone 15 Pro Max', 1, 74990.00),
                (order_id, products['iPad Air 5th Gen'], 'iPad Air 5th Gen', 1, 34990.00),
                (order_id, products['Apple AirPods Pro 2nd Gen'], 'Apple AirPods Pro 2nd Gen', 2, 14990.00),
            ]
            
            for order_id_val, product_id, product_name, quantity, price in order_items:
                cursor.execute("""
                    INSERT INTO order_item (order_id, product_id, product_name, quantity, price)
                    VALUES (%s, %s, %s, %s, %s)
                """, (order_id_val, product_id, product_name, quantity, price))
            
            mysql.connection.commit()
            cursor.close()
            
            print("=" * 60)
            print("MJC GADGET HUB Database Initialized!")
            print("=" * 60)
            print("\nAdmin Account:")
            print("  Email: admin@admin.com")
            print("  Password: admin123")
            print("\nCustomer Account:")
            print("  Email: customer@test.com")
            print("  Password: customer123")
            print("\nGadget Categories:")
            for name, description in categories_data:
                print(f"  - {name}: {description}")
            print(f"\nProducts: {len(products_data)} gadgets added")
            print("  - 4 Laptops (MacBook, ROG, ThinkPad, XPS)")
            print("  - 4 Smartphones (iPhones, Samsung, Pixel)")
            print("  - 4 Tablets (iPads, Galaxy Tab)")
            print("  - 4 Gaming Phones (ROG, Red Magic, Black Shark, Legion)")
            print("  - 4 Accessories (AirPods, Keyboard, Buds, Charger)")
            print("\nSample order created with Apple products")
            print("\nRun the app with: python run.py")
            print("=" * 60)
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            print(f"Error initializing database: {e}")
            raise

if __name__ == '__main__':
    init_database()
