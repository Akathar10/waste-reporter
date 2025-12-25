from PIL import Image
import os

path = r"d:\waste reporter\static\images\broom_cursor.png"

try:
    img = Image.open(path)
    print(f"Original size: {img.size}")
    
    # Resize to 32x32 for maximum compatibility
    img = img.resize((32, 32), Image.Resampling.LANCZOS)
    
    img.save(path)
    print(f"Resized to: {img.size}")
except Exception as e:
    print(f"Error: {e}")
