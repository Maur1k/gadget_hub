"""
Initialize database with gadget store data.
Categories: Laptops, Smartphones, Tablets, Gaming Phones
Products: Apple, Samsung, Asus, Lenovo, etc.
"""
from app import create_app, db
from app.models import User, Category, Product, Order, OrderItem

def init_database():
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            email='admin@admin.com',
            username='admin',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create sample customer
        customer = User(
            email='customer@test.com',
            username='customer'
        )
        customer.set_password('customer123')
        db.session.add(customer)
        
        # Create gadget categories
        categories = [
            Category(name='Laptops', description='Gaming laptops, ultrabooks, and workstations'),
            Category(name='Smartphones', description='iPhones, Android phones, and flagship devices'),
            Category(name='Tablets', description='iPads, Android tablets, and drawing tablets'),
            Category(name='Gaming Phones', description='High-performance gaming smartphones'),
            Category(name='Accessories', description='Cases, chargers, and peripherals')
        ]
        for cat in categories:
            db.session.add(cat)
        
        db.session.commit()
        
        # Create gadget products
        products = [
            # Laptops (category_id=1)
            Product(
                name='MacBook Pro 14" M3 Pro',
                description='Apple M3 Pro chip, 18GB RAM, 512GB SSD, Liquid Retina XDR display',
                price=89999.00,
                stock=15,
                category_id=1
            ),
            Product(
                name='ASUS ROG Zephyrus G14',
                description='AMD Ryzen 9, RTX 4060, 16GB RAM, 1TB SSD, 14" QHD 165Hz',
                price=74999.00,
                stock=20,
                category_id=1
            ),
            Product(
                name='Lenovo ThinkPad X1 Carbon',
                description='Intel Core i7, 16GB RAM, 512GB SSD, 14" 2.8K OLED',
                price=82999.00,
                stock=12,
                category_id=1
            ),
            Product(
                name='Dell XPS 15',
                description='Intel Core i7-13700H, 32GB RAM, 1TB SSD, RTX 4050, 15.6" OLED',
                price=94999.00,
                stock=8,
                category_id=1
            ),
            
            # Smartphones (category_id=2)
            Product(
                name='iPhone 15 Pro Max',
                description='A17 Pro chip, 256GB, Titanium design, 48MP camera, Action button',
                price=74990.00,
                stock=25,
                category_id=2
            ),
            Product(
                name='iPhone 15 Pro',
                description='A17 Pro chip, 128GB, Titanium design, 48MP camera system',
                price=64990.00,
                stock=30,
                category_id=2
            ),
            Product(
                name='Samsung Galaxy S24 Ultra',
                description='Snapdragon 8 Gen 3, 256GB, 200MP camera, S Pen, AI features',
                price=69990.00,
                stock=20,
                category_id=2
            ),
            Product(
                name='Google Pixel 8 Pro',
                description='Tensor G3, 128GB, 50MP camera, 7 years of updates, AI photo editing',
                price=54990.00,
                stock=18,
                category_id=2
            ),
            
            # Tablets (category_id=3)
            Product(
                name='iPad Pro 12.9" M2',
                description='Apple M2 chip, 256GB, Liquid Retina XDR, Face ID, Thunderbolt',
                price=69990.00,
                stock=15,
                category_id=3
            ),
            Product(
                name='iPad Air 5th Gen',
                description='Apple M1 chip, 64GB, 10.9" Liquid Retina, Touch ID, USB-C',
                price=34990.00,
                stock=25,
                category_id=3
            ),
            Product(
                name='Samsung Galaxy Tab S9 Ultra',
                description='Snapdragon 8 Gen 2, 256GB, 14.6" AMOLED, S Pen included',
                price=64990.00,
                stock=12,
                category_id=3
            ),
            Product(
                name='iPad 10th Generation',
                description='A14 Bionic chip, 64GB, 10.9" Liquid Retina, USB-C',
                price=24990.00,
                stock=35,
                category_id=3
            ),
            
            # Gaming Phones (category_id=4)
            Product(
                name='ASUS ROG Phone 8 Pro',
                description='Snapdragon 8 Gen 3, 16GB RAM, 512GB, 165Hz AMOLED, AeroActive Cooler',
                price=59990.00,
                stock=10,
                category_id=4
            ),
            Product(
                name='Red Magic 9 Pro',
                description='Snapdragon 8 Gen 3, 16GB RAM, 512GB, 120Hz, Built-in cooling fan',
                price=44990.00,
                stock=15,
                category_id=4
            ),
            Product(
                name='Xiaomi Black Shark 5 Pro',
                description='Snapdragon 8 Gen 1, 12GB RAM, 256GB, 144Hz AMOLED, Magnetic triggers',
                price=34990.00,
                stock=20,
                category_id=4
            ),
            Product(
                name='Lenovo Legion Phone Duel 2',
                description='Snapdragon 888, 16GB RAM, 512GB, Dual cooling fans, Pop-up camera',
                price=29990.00,
                stock=8,
                category_id=4
            ),
            
            # Accessories (category_id=5)
            Product(
                name='Apple AirPods Pro 2nd Gen',
                description='Active Noise Cancellation, Adaptive Audio, USB-C, MagSafe case',
                price=14990.00,
                stock=50,
                category_id=5
            ),
            Product(
                name='Apple Magic Keyboard for iPad Pro',
                description='Backlit keys, trackpad, USB-C passthrough, floating design',
                price=17990.00,
                stock=20,
                category_id=5
            ),
            Product(
                name='Samsung Galaxy Buds2 Pro',
                description='24-bit Hi-Fi audio, ANC, 360 Audio, IPX7 water resistance',
                price=10990.00,
                stock=40,
                category_id=5
            ),
            Product(
                name='Anker 100W USB-C Charger',
                description='GaN II technology, 4 ports, foldable plug, fast charging',
                price=3990.00,
                stock=100,
                category_id=5
            ),
        ]
        
        for product in products:
            db.session.add(product)
        
        db.session.commit()
        
        # Create a sample order for testing
        order = Order(
            user_id=2,  # customer
            status='Pending',
            payment_method='Online',
            total_amount=139980.00,
            shipping_address='Unit 1234, Tower A, BGC, Taguig City, Metro Manila 1630'
        )
        db.session.add(order)
        db.session.commit()
        
        # Add items to the order
        item1 = OrderItem(
            order_id=order.id,
            product_id=5,
            product_name='iPhone 15 Pro Max',
            quantity=1,
            price=74990.00
        )
        item2 = OrderItem(
            order_id=order.id,
            product_id=10,
            product_name='iPad Air 5th Gen',
            quantity=1,
            price=34990.00
        )
        item3 = OrderItem(
            order_id=order.id,
            product_id=17,
            product_name='Apple AirPods Pro 2nd Gen',
            quantity=2,
            price=14990.00
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.commit()
        
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
        for cat in categories:
            print(f"  - {cat.name}: {cat.description}")
        print(f"\nProducts: {len(products)} gadgets added")
        print("  - 4 Laptops (MacBook, ROG, ThinkPad, XPS)")
        print("  - 4 Smartphones (iPhones, Samsung, Pixel)")
        print("  - 4 Tablets (iPads, Galaxy Tab)")
        print("  - 4 Gaming Phones (ROG, Red Magic, Black Shark, Legion)")
        print("  - 4 Accessories (AirPods, Keyboard, Buds, Charger)")
        print("\nSample order created with Apple products")
        print("\nRun the app with: python run.py")
        print("=" * 60)

if __name__ == '__main__':
    init_database()
