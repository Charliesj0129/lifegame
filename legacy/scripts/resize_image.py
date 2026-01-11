from PIL import Image
import sys
import glob


def resize_images(pattern, width=2500, height=1686):
    files = glob.glob(pattern)
    if not files:
        print(f"No files found for {pattern}")
        return

    for f in files:
        try:
            img = Image.open(f)
            # Resize
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            # Convert to RGB (remove alpha)
            rgb_img = img.convert("RGB")
            # Save as JPEG with quality control
            new_filename = f.rsplit(".", 1)[0] + ".jpg"
            rgb_img.save(new_filename, "JPEG", optimize=True, quality=70)
            print(f"✅ Resized & Compressed {f} -> {new_filename}")
        except Exception as e:
            print(f"❌ Failed to resize {f}: {e}")


if __name__ == "__main__":
    import sys

    # Pattern
    pattern = sys.argv[1]
    resize_images(pattern)
