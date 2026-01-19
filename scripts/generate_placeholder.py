from PIL import Image, ImageDraw, ImageFont
import os


def create_rich_menu_image():
    width = 2500
    height = 1686
    color = (20, 30, 20)  # Dark Green
    text_color = (100, 255, 100)  # Bright Green

    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)

    # Grid 4x3
    cols = 4
    rows = 3
    cell_w = width // cols
    cell_h = height // rows

    labels = [
        "狀態 (Status)",
        "任務 (Quests)",
        "背包 (Bag)",
        "商店 (Shop)",
        "合成 (Craft)",
        "首領 (Boss)",
        "攻擊 (Attack)",
        "簽到 (Checkin)",
        "重骰 (Reroll)",
        "全接 (Accept)",
        "略過 (Skip)",
        "指令 (Help)",
    ]

    for idx, label in enumerate(labels):
        row = idx // cols
        col = idx % cols
        x = col * cell_w
        y = row * cell_h

        # Border
        draw.rectangle([x, y, x + cell_w, y + cell_h], outline=text_color, width=5)

        # Text (Centered)
        # Load default font if possible, or simple calculation
        # PIL default font is tiny, but sufficient for placeholder
        # We'll just draw text

        # Approximate center
        text_x = x + 50
        text_y = y + cell_h // 2 - 20
        draw.text((text_x, text_y), label, fill=text_color)

    output_path = "assets/rich_menu.jpg"
    img.save(output_path, "JPEG", quality=80)
    print(f"Generated {output_path}")


if __name__ == "__main__":
    create_rich_menu_image()
