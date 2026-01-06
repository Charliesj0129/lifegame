from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
OUTPUT_JPG = ASSETS_DIR / "rich_menu.jpg"
OUTPUT_PNG = ASSETS_DIR / "rich_menu.png"

WIDTH = 2500
HEIGHT = 1686
COLS = 4
ROWS = 3

LABELS = [
    "狀態",
    "任務",
    "背包",
    "商店",
    "合成",
    "首領",
    "攻擊",
    "簽到",
    "重新生成",
    "全部接受",
    "略過 Viper",
    "指令",
]


def _find_font() -> Path:
    candidates = [
        Path("/tmp/NotoSansCJKtc-Regular.otf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "找不到可用字型。請先下載："
        "curl -L -o /tmp/NotoSansCJKtc-Regular.otf "
        "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    )


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    font_path = _find_font()
    font = ImageFont.truetype(str(font_path), 72)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#0f1114")
    draw = ImageDraw.Draw(image)

    cell_w = WIDTH // COLS
    cell_h = HEIGHT // ROWS
    padding = 30
    radius = 36

    accent_colors = ["#3ddbd9", "#f5b85b", "#7cd992"]

    for index, label in enumerate(LABELS):
        row = index // COLS
        col = index % COLS
        x0 = col * cell_w + padding
        y0 = row * cell_h + padding
        x1 = (col + 1) * cell_w - padding
        y1 = (row + 1) * cell_h - padding

        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=radius,
            fill="#1a1f26",
            outline="#2c3540",
            width=4,
        )
        draw.rectangle([x0, y0, x0 + 12, y1], fill=accent_colors[row])

        text_box = draw.textbbox((0, 0), label, font=font)
        text_w = text_box[2] - text_box[0]
        text_h = text_box[3] - text_box[1]
        text_x = x0 + (x1 - x0 - text_w) / 2
        text_y = y0 + (y1 - y0 - text_h) / 2

        draw.text((text_x, text_y), label, font=font, fill="#f5f7fa")

    image.save(OUTPUT_PNG, optimize=True)
    image.save(OUTPUT_JPG, quality=92)


if __name__ == "__main__":
    main()
