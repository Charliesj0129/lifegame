from PIL import Image
import os

path = "assets/rich_menu.png"
if os.path.exists(path):
    img = Image.open(path)
    print(f"Original size: {img.size}")
    # Resize to standard full size 2500x1686
    # Note: If aspect ratio is different, this might stretch.
    # Ideally we crop or paste into center, but stretching is fine for now to fix the error.
    new_img = img.resize((2500, 1686), Image.Resampling.LANCZOS)
    # Convert to RGB (remove alpha) for JPEG
    rgb_img = new_img.convert('RGB')
    rgb_img.save("assets/rich_menu.jpg", optimize=True, quality=85)
    print(f"Resized and saved as JPEG: {rgb_img.size}")
else:
    print("Image not found")
