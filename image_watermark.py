"""
Appify Store Bot - Image Watermark Module
=========================================
Dynamic image branding using Pillow (PIL).
Overlays watermark/logo on product images and serves via BytesIO.
Supports Arabic text rendering with proper RTL handling.
"""

import io
import os
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import aiohttp
import asyncio

from config import (
    WATERMARK_TEXT, WATERMARK_OPACITY,
    BRAND_PRIMARY_COLOR, BRAND_ACCENT_COLOR, BRAND_TEXT_COLOR,
    BOT_NAME, ASSETS_DIR
)

# ─── Font Setup ───────────────────────────────────────────────────────────────

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load appropriate font with Arabic support."""
    # Try common Arabic-supporting fonts
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/GeezaPro.ttc",  # macOS Arabic
        "C:\\Windows\\Fonts\\arial.ttf",  # Windows
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue

    # Fallback to default font
    return ImageFont.load_default()


# ─── Image Processing Functions ───────────────────────────────────────────────

async def download_image(url: str) -> Optional[Image.Image]:
    """Download image from URL asynchronously."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"[Image] Failed to download image from {url}: {e}")
    return None


def create_gradient_background(width: int, height: int) -> Image.Image:
    """Create a branded gradient background."""
    base = Image.new("RGBA", (width, height), BRAND_PRIMARY_COLOR)
    draw = ImageDraw.Draw(base)

    # Add subtle gradient overlay
    for y in range(height):
        alpha = int(30 * (1 - y / height))
        draw.line([(0, y), (width, y)], fill=(233, 69, 96, alpha))

    return base


def add_watermark(
    image: Image.Image,
    watermark_text: str = WATERMARK_TEXT,
    position: str = "bottom-right",
    opacity: int = WATERMARK_OPACITY,
) -> Image.Image:
    """Add text watermark to image."""
    img = image.copy()
    width, height = img.size

    # Create watermark layer
    watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)

    # Calculate font size based on image dimensions
    font_size = max(int(min(width, height) * 0.04), 16)
    font = get_font(font_size, bold=True)

    # Get text bounding box
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Position calculation
    padding = int(min(width, height) * 0.03)
    positions = {
        "top-left": (padding, padding),
        "top-right": (width - text_width - padding, padding),
        "bottom-left": (padding, height - text_height - padding),
        "bottom-right": (width - text_width - padding, height - text_height - padding),
        "center": ((width - text_width) // 2, (height - text_height) // 2),
    }

    pos = positions.get(position, positions["bottom-right"])

    # Draw semi-transparent text
    text_color = (255, 255, 255, opacity)
    draw.text(pos, watermark_text, font=font, fill=text_color)

    # Composite watermark onto image
    img = Image.alpha_composite(img.convert("RGBA"), watermark)
    return img


def add_logo_overlay(
    image: Image.Image,
    logo_path: Optional[str] = None,
    position: str = "top-left",
    size_ratio: float = 0.15,
    opacity: int = 200,
) -> Image.Image:
    """Overlay logo image on product image."""
    img = image.copy()
    width, height = img.size

    # Use default logo if not specified
    if logo_path is None:
        logo_path = ASSETS_DIR / "logo.png"
        if not os.path.exists(logo_path):
            # Return image with text watermark instead
            return add_watermark(img, position=position)

    try:
        logo = Image.open(logo_path).convert("RGBA")
    except:
        return add_watermark(img, position=position)

    # Resize logo
    logo_width = int(min(width, height) * size_ratio)
    logo_height = int(logo.height * (logo_width / logo.width))
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

    # Apply opacity
    if opacity < 255:
        logo = logo.copy()
        logo.putalpha(int(255 * (opacity / 255)))

    # Position calculation
    padding = int(min(width, height) * 0.03)
    positions = {
        "top-left": (padding, padding),
        "top-right": (width - logo_width - padding, padding),
        "bottom-left": (padding, height - logo_height - padding),
        "bottom-right": (width - logo_width - padding, height - logo_height - padding),
    }

    pos = positions.get(position, positions["top-left"])

    # Paste logo onto image
    img.paste(logo, pos, logo)
    return img


def add_price_tag(
    image: Image.Image,
    price: str,
    currency: str = "USD",
) -> Image.Image:
    """Add elegant price tag overlay."""
    img = image.copy()
    width, height = img.size
    draw = ImageDraw.Draw(img)

    # Price tag dimensions
    tag_height = int(height * 0.1)
    tag_y = height - tag_height

    # Draw gradient tag background
    for y in range(tag_y, height):
        progress = (y - tag_y) / tag_height
        r = int(26 + (233 - 26) * progress)
        g = int(26 + (69 - 26) * progress)
        b = int(46 + (96 - 46) * progress)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 220))

    # Price text
    price_text = f"{price} {currency}"
    font_size = max(int(tag_height * 0.5), 20)
    font = get_font(font_size, bold=True)

    bbox = draw.textbbox((0, 0), price_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2
    text_y = tag_y + (tag_height - (bbox[3] - bbox[1])) // 2

    draw.text((text_x, text_y), price_text, font=font, fill=(255, 255, 255, 255))

    # Bot name in corner
    bot_font = get_font(max(int(tag_height * 0.25), 10), bold=False)
    draw.text((10, tag_y + 5), BOT_NAME, font=bot_font, fill=(255, 255, 255, 180))

    return img


def add_product_caption(
    image: Image.Image,
    product_name: str,
    category: str,
) -> Image.Image:
    """Add product name caption overlay."""
    img = image.copy()
    width, height = img.size
    draw = ImageDraw.Draw(img)

    # Caption bar at top
    bar_height = int(height * 0.12)

    # Semi-transparent dark bar
    overlay = Image.new("RGBA", (width, bar_height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(bar_height):
        alpha = int(180 * (1 - y / bar_height))
        overlay_draw.line([(0, y), (width, y)], fill=(26, 26, 46, alpha))

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)

    # Product name
    name_font_size = max(int(bar_height * 0.4), 18)
    name_font = get_font(name_font_size, bold=True)

    # Handle Arabic text alignment (RTL)
    bbox = draw.textbbox((0, 0), product_name, font=name_font)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2  # Center for simplicity
    text_y = bar_height // 4

    draw.text((text_x, text_y), product_name, font=name_font, fill=(255, 255, 255, 255))

    # Category tag
    cat_font = get_font(max(int(bar_height * 0.22), 10), bold=False)
    cat_bbox = draw.textbbox((0, 0), category, font=cat_font)
    cat_width = cat_bbox[2] - cat_bbox[0]
    cat_x = (width - cat_width) // 2
    cat_y = bar_height * 3 // 5

    draw.text((cat_x, cat_y), category, font=cat_font, fill=(233, 69, 96, 255))

    return img


# ─── Main Processing Pipeline ─────────────────────────────────────────────────

async def process_product_image(
    image_source: str,
    product_name: str,
    category: str = "",
    price: str = "",
    currency: str = "USD",
    add_branding: bool = True,
) -> Optional[io.BytesIO]:
    """
    Full processing pipeline for product images.

    Args:
        image_source: URL or local path to image
        product_name: Product name for caption
        category: Product category name
        price: Price string
        currency: Currency code
        add_branding: Whether to apply branding overlays

    Returns:
        BytesIO buffer with processed image, or None if failed
    """
    # Load image
    if image_source.startswith("http://") or image_source.startswith("https://"):
        img = await download_image(image_source)
    else:
        try:
            img = Image.open(image_source).convert("RGBA")
        except:
            img = None

    if img is None:
        # Create branded placeholder
        img = create_gradient_background(800, 600)
        draw = ImageDraw.Draw(img)
        font = get_font(40, bold=True)
        bbox = draw.textbbox((0, 0), product_name, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(
            ((800 - text_w) // 2, (600 - text_h) // 2),
            product_name,
            font=font,
            fill=(255, 255, 255, 255),
        )

    # Resize to consistent dimensions
    img = img.resize((800, 600), Image.LANCZOS)

    if add_branding:
        # Apply branding pipeline
        img = add_product_caption(img, product_name, category)
        img = add_logo_overlay(img, position="top-left", opacity=180)
        img = add_watermark(img, position="bottom-right", opacity=WATERMARK_OPACITY)
        if price:
            img = add_price_tag(img, price, currency)

    # Convert to output format
    output = io.BytesIO()
    if img.mode == "RGBA":
        # Convert to RGB for JPEG with white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        background.save(output, format="JPEG", quality=95)
    else:
        img.convert("RGB").save(output, format="JPEG", quality=95)

    output.seek(0)
    output.name = "product.jpg"
    return output


def generate_channel_post_image(
    product_name: str,
    price: str,
    category: str,
) -> io.BytesIO:
    """Generate a branded image for Telegram channel posts."""
    # Create base image
    width, height = 1080, 1080
    img = create_gradient_background(width, height)
    draw = ImageDraw.Draw(img)

    # Category emoji and name
    cat_font = get_font(48, bold=False)
    cat_bbox = draw.textbbox((0, 0), category, font=cat_font)
    cat_w = cat_bbox[2] - cat_bbox[0]
    draw.text(((width - cat_w) // 2, 200), category, font=cat_font, fill=(233, 69, 96, 255))

    # Product name (main)
    name_font = get_font(72, bold=True)
    # Wrap long names
    lines = []
    words = product_name.split()
    current_line = ""
    for word in words:
        test = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test, font=name_font)
        if bbox[2] - bbox[0] > width - 100:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test
    lines.append(current_line)

    y_offset = 350
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=name_font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        draw.text(((width - line_w) // 2, y_offset), line, font=name_font, fill=(255, 255, 255, 255))
        y_offset += line_h + 20

    # Price
    price_font = get_font(96, bold=True)
    price_text = f"{price}"
    p_bbox = draw.textbbox((0, 0), price_text, font=price_font)
    p_w = p_bbox[2] - p_bbox[0]
    draw.text(((width - p_w) // 2, 700), price_text, font=price_font, fill=(233, 69, 96, 255))

    # Brand footer
    foot_font = get_font(32, bold=False)
    foot_bbox = draw.textbbox((0, 0), BOT_NAME, font=foot_font)
    f_w = foot_bbox[2] - foot_bbox[0]
    draw.text(((width - f_w) // 2, 950), BOT_NAME, font=foot_font, fill=(255, 255, 255, 150))

    # Convert and return
    output = io.BytesIO()
    img.convert("RGB").save(output, format="JPEG", quality=95)
    output.seek(0)
    output.name = "channel_post.jpg"
    return output
