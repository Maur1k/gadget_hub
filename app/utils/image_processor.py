"""
Image processing utility for product images.

This module handles image resizing, background removal/whitening,
and optimization for consistent product display.
"""
from PIL import Image
import os
from werkzeug.utils import secure_filename


def process_product_image(image_path, output_path=None, size=(600, 600), background_color='white'):
    """
    Process product image: resize, center, and apply white background.
    
    Args:
        image_path: Path to the source image file
        output_path: Path to save processed image (if None, overwrites original)
        size: Tuple of (width, height) for output size (default: 600x600)
        background_color: Background color ('white', 'transparent', or hex color)
        
    Returns:
        str: Path to processed image
    """
    try:
        # Open and process image
        img = Image.open(image_path)
        
        # Convert RGBA if needed
        if img.mode == 'RGBA':
            # Create white background
            bg_color = (255, 255, 255) if background_color == 'white' or background_color == 'transparent' else background_color
            background = Image.new('RGB', img.size, bg_color)
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calculate dimensions to maintain aspect ratio and fit within size
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Create new image with white background
        bg_color = (255, 255, 255) if background_color == 'white' or background_color == 'transparent' else background_color
        new_img = Image.new('RGB', size, bg_color)
        
        # Calculate position to center the image
        x_offset = (size[0] - img.size[0]) // 2
        y_offset = (size[1] - img.size[1]) // 2
        
        # Paste resized image onto white background
        new_img.paste(img, (x_offset, y_offset))
        
        # Save processed image
        if output_path is None:
            output_path = image_path
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Save with high quality
        new_img.save(output_path, 'JPEG', quality=90, optimize=True)
        
        return output_path
        
    except Exception as e:
        print(f"Error processing image: {e}")
        # Return original path if processing fails
        return image_path


def remove_background_simple(image_path, output_path=None, threshold=240):
    """
    Simple background removal by making white/light pixels transparent.
    
    Args:
        image_path: Path to source image
        output_path: Path to save processed image
        threshold: Brightness threshold (0-255) for background removal
        
    Returns:
        str: Path to processed image
    """
    try:
        img = Image.open(image_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Get image data
        data = img.getdata()
        
        # Create new image data with transparency
        new_data = []
        for item in data:
            # Calculate brightness
            if img.mode == 'RGBA':
                r, g, b, a = item
            else:
                r, g, b = item[:3]
                a = 255
            
            brightness = (r + g + b) / 3
            
            # Make light pixels transparent
            if brightness > threshold:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        
        # Update image with new data
        img.putdata(new_data)
        
        # Resize to standard size while maintaining aspect ratio
        img.thumbnail((600, 600), Image.Resampling.LANCZOS)
        
        # Create new image with transparent background
        new_img = Image.new('RGBA', (600, 600), (255, 255, 255, 0))
        
        # Center the image
        x_offset = (600 - img.size[0]) // 2
        y_offset = (600 - img.size[1]) // 2
        
        new_img.paste(img, (x_offset, y_offset), img)
        
        # Save as PNG to preserve transparency
        if output_path is None:
            # Change extension to PNG
            output_path = os.path.splitext(image_path)[0] + '.png'
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        new_img.save(output_path, 'PNG', optimize=True)
        
        return output_path
        
    except Exception as e:
        print(f"Error removing background: {e}")
        return image_path


def process_and_save_upload(file, upload_folder, filename=None):
    """
    Process uploaded image file and save it.
    
    Args:
        file: FileStorage object from Flask
        upload_folder: Directory to save the file
        filename: Optional custom filename
        
    Returns:
        str: Filename of saved and processed image
    """
    from datetime import datetime
    
    if filename is None:
        timestamp = datetime.now().timestamp()
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        filename = f"{timestamp}_{name}{ext}"
    
    filepath = os.path.join(upload_folder, filename)
    
    # Save original first
    file.save(filepath)
    
    # Process the image: resize, center, white background
    processed_path = process_product_image(filepath, size=(600, 600), background_color='white')
    
    # Return the processed filename
    return os.path.basename(processed_path)

