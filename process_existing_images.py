"""
Script to process existing product images.

This script processes all existing product images to have consistent sizing
and white backgrounds for better presentation.
"""
from app import create_app, db
from app.models import Product
from app.utils.image_processor import process_product_image
import os

def process_all_product_images():
    """Process all existing product images."""
    app = create_app()
    
    with app.app_context():
        products = Product.query.filter(Product.image.isnot(None)).all()
        upload_folder = os.path.join('app', 'static', 'uploads')
        
        print(f"Found {len(products)} products with images to process...")
        
        for product in products:
            if product.image:
                image_path = os.path.join(upload_folder, product.image)
                
                if os.path.exists(image_path):
                    try:
                        print(f"Processing: {product.name} ({product.image})")
                        process_product_image(image_path, size=(600, 600), background_color='white')
                        print(f"  ✓ Processed successfully")
                    except Exception as e:
                        print(f"  ✗ Error processing {product.image}: {e}")
                else:
                    print(f"  ⚠ Image file not found: {image_path}")
        
        print("\nImage processing complete!")

if __name__ == '__main__':
    process_all_product_images()


