"""
Appify Store Bot - Configuration Module
=====================================
Secure environment-based configuration for the dropshipping bot.
All sensitive values are loaded from environment variables.
"""

import os
from pathlib import Path

# ─── Base Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "data" / "appify.db"
ASSETS_DIR = BASE_DIR / "assets"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for dir_path in [DATABASE_PATH.parent, ASSETS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ─── Bot Credentials ──────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8848866254:AAFUKRg-W8ZHKCW_KkYgRzcn4EIdaIsfxiU")
BOT_ID = int(os.getenv("BOT_ID", "8989271393"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "AppifyStore_bot")
BOT_NAME = os.getenv("BOT_NAME", "Appify Store | متجر آبيفاي")

# ─── Admin Configuration ──────────────────────────────────────────────────────
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
# Add your admin Telegram ID here for full control
# Example: ADMIN_IDS = [123456789]

# ─── Telegram Channel ─────────────────────────────────────────────────────────
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "AppifyStore0")
CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME}"

# ─── Pyrogram Userbot (SourceBot Automation) ──────────────────────────────────
PYROGRAM_API_ID = int(os.getenv("PYROGRAM_API_ID", "0"))
PYROGRAM_API_HASH = os.getenv("PYROGRAM_API_HASH", "")
PYROGRAM_SESSION_STRING = os.getenv("PYROGRAM_SESSION_STRING", "")
SOURCE_BOT_USERNAME = os.getenv("SOURCE_BOT_USERNAME", "SourceBot")

# ─── Pricing Configuration ────────────────────────────────────────────────────
PROFIT_MARGIN_PERCENT = float(os.getenv("PROFIT_MARGIN_PERCENT", "25"))  # 25% markup
CURRENCY_DISPLAY = os.getenv("CURRENCY_DISPLAY", "USD")  # Display currency
EXCHANGE_RATE_RUB_TO_USD = float(os.getenv("EXCHANGE_RATE_RUB_TO_USD", "0.011"))

# ─── Flask Keep-Alive Server ──────────────────────────────────────────────────
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "8080"))

# ─── Bot Behavior ─────────────────────────────────────────────────────────────
ORDER_TIMEOUT_SECONDS = int(os.getenv("ORDER_TIMEOUT_SECONDS", "300"))  # 5 min
MAX_CONCURRENT_ORDERS = int(os.getenv("MAX_CONCURRENT_ORDERS", "10"))
PAYMENT_TIMEOUT_MINUTES = int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "15"))

# ─── Referral System ──────────────────────────────────────────────────────────
REFERRAL_BONUS_PERCENT = float(os.getenv("REFERRAL_BONUS_PERCENT", "5"))

# ─── Watermark / Branding ─────────────────────────────────────────────────────
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "Appify Store")
WATERMARK_OPACITY = int(os.getenv("WATERMARK_OPACITY", "80"))
BRAND_PRIMARY_COLOR = os.getenv("BRAND_PRIMARY_COLOR", "#1A1A2E")
BRAND_ACCENT_COLOR = os.getenv("BRAND_ACCENT_COLOR", "#E94560")
BRAND_TEXT_COLOR = os.getenv("BRAND_TEXT_COLOR", "#FFFFFF")

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── Validate Critical Config ─────────────────────────────────────────────────
def validate_config():
    """Validate that all critical configuration values are set."""
    critical_vars = {
        "BOT_TOKEN": BOT_TOKEN,
        "PYROGRAM_API_ID": PYROGRAM_API_ID,
        "PYROGRAM_API_HASH": PYROGRAM_API_HASH,
        "PYROGRAM_SESSION_STRING": PYROGRAM_SESSION_STRING,
    }
    missing = [name for name, value in critical_vars.items() if not value or value == 0]
    if missing:
        print(f"[WARNING] Missing critical environment variables: {', '.join(missing)}")
        print("[INFO] Bot will start in limited mode without Pyrogram automation.")
    return len(missing) == 0

# ─── Product Categories & Base Prices (RUB) ───────────────────────────────────
PRODUCT_CATALOG = {
    "games": {
        "emoji": "🎮",
        "name_ar": "الألعاب",
        "items": {
            "minecraft": {"name": "Minecraft", "base_price_rub": 100},
            "terraria": {"name": "Terraria", "base_price_rub": 100},
            "geometry_dash": {"name": "Geometry Dash", "base_price_rub": 100},
            "gta_sa": {"name": "GTA: San Andreas", "base_price_rub": 100},
            "red_dead": {"name": "Red Dead Redemption", "base_price_rub": 299},
            "fnaf_all": {"name": "Все FNaF'ы", "base_price_rub": 299},
            "subnautica": {"name": "Subnautica + Below Zero", "base_price_rub": 149},
            "dead_cells": {"name": "Dead Cells", "base_price_rub": 149},
            "tomb_raider": {"name": "Tomb Raider", "base_price_rub": 199},
            "removed_games": {"name": "Удалённые игры из РФ", "base_price_rub": 100},
        }
    },
    "apps": {
        "emoji": "📷",
        "name_ar": "التطبيقات",
        "items": {
            "lumafusion": {"name": "LumaFusion", "base_price_rub": 229},
            "fl_studio": {"name": "FL Studio", "base_price_rub": 199},
            "procreate": {"name": "Procreate + PE", "base_price_rub": 199},
            "procreate_dreams": {"name": "Procreate Dreams", "base_price_rub": 199},
            "procam": {"name": "Procam", "base_price_rub": 149},
            "nomad_sculpt": {"name": "Nomad Sculpt", "base_price_rub": 199},
            "things3": {"name": "Things 3", "base_price_rub": 199},
            "anki": {"name": "AnkiMobile Flashcards", "base_price_rub": 229},
        }
    },
    "apple_ids": {
        "emoji": "🍎",
        "name_ar": "حسابات Apple ID",
        "items": {
            "id_usa": {"name": "Apple ID США", "base_price_rub": 299},
            "id_turkey": {"name": "Apple ID Турция", "base_price_rub": 299},
            "id_russia": {"name": "Apple ID Россия", "base_price_rub": 299},
            "id_minecraft": {"name": "Apple ID c Minecraft", "base_price_rub": 949},
        }
    }
}


def calculate_final_price(base_price_rub: int) -> float:
    """
    Calculate final price with profit margin.
    Converts RUB to display currency and adds markup.
    """
    base_in_currency = base_price_rub * EXCHANGE_RATE_RUB_TO_USD
    final_price = base_in_currency * (1 + PROFIT_MARGIN_PERCENT / 100)
    return round(final_price, 2)


def get_all_products():
    """Get flat list of all products with calculated prices."""
    products = []
    for cat_key, category in PRODUCT_CATALOG.items():
        for prod_key, product in category["items"].items():
            products.append({
                "id": prod_key,
                "category": cat_key,
                "category_emoji": category["emoji"],
                "category_name_ar": category["name_ar"],
                "name": product["name"],
                "base_price_rub": product["base_price_rub"],
                "final_price": calculate_final_price(product["base_price_rub"]),
            })
    return products


# ─── Arabic Text Templates ────────────────────────────────────────────────────
class TextTemplates:
    """Centralized Arabic text templates for consistent messaging."""

    WELCOME_MESSAGE = """
👋 **أهلاً وسهلاً بك في {bot_name}!**

🛍️ **متجرك الموثوق لشراء Apple IDs والألعاب والتطبيقات**

📱 نوفر لك حسابات Apple ID جاهزة مع ألعاب iOS مدفوعة مسبقاً
⚡ توصيل فوري آمن وموثوق
💰 أسعار تنافسية مع ضمان الجودة

🔰 **للبدء، اختر من القائمة أدناه:**
"""

    RULES_MESSAGE = """
📝 **قوانين وشروط الاستخدام:**

🤔 **ماذا يحدث عند المخالفة؟**
1) البند الأول: في حال المخالفة، يحق لنا رفض تقديم الخدمة وتقييد وصولك للحساب المشترى.
2) البند الثاني: أفعال غير مستحسنة قد تضر بالحساب.

🚫 **البند الأول (ممنوع منعاً باتاً):**
1.1: يمنع مشاركة أو إعادة بيع الحساب لأطراف أخرى.
1.2: يمنع تسجيل الدخول للحساب من (الإعدادات / iCloud). الدخول مسموح فقط عبر App Store.
1.3: يمنع تغيير أي بيانات في الحساب (المنطقة، الاسم، الإيميل الاحتياطي، كلمة المرور).
1.4: يمنع تسجيل الدخول لموقع Apple الرسمي باستخدام الحساب (فقط App Store).

❌ **البند الثاني (غير مستحسن):**
2.1: لا يُنصح بالدخول للحساب بعد مرور 24 ساعة من لحظة الشراء.
2.2: لا يُنصح بإدخال كلمة المرور بشكل خاطئ أكثر من 3 مرات (تواصل مع الدعم فوراً).
2.3: لا يُنصح بمحاولة شراء ألعاب مدفوعة أخرى على الحساب.
2.4: لا يُنصح باستخدام الحساب كحسابك الأساسي.
2.5: لا يُنصح بتسجيل الدخول في أي مكان عدا App Store (مثل: iTunes Store, Apple TV).
2.6: لا يُنصح بشراء أي شيء مدفوع أو تفعيل بطاقات هدايا (Gift Cards) على الحساب (لن تتمكن من صرفها).
"""

    INFO_MESSAGE = """
ℹ️ **معلومات عن المتجر:**

🏪 **{bot_name}** - وجهتك الأولى لشراء Apple IDs والألعاب

✅ **مميزاتنا:**
• توصيل فوري آمن
• ضمان كامل على جميع المنتجات
• دعم فني على مدار الساعة
• أسعار تنافسية
• نظام إحالة مجزي

📢 **قناتنا:** {channel_link}
🤖 **البوت:** @{bot_username}

💬 **للاستفسارات:** @AppifyStore0
"""

    SUPPORT_MESSAGE = """
🛠 **الدعم الفني:**

📩 **للتواصل مع فريق الدعم:**
• وصف مشكلتك بالتفصيل
• أرفق لقطة شاشة إن أمكن
• سيتم الرد عليك في أقرب وقت

⚡ **قناة الدعم:** {channel_link}
"""

    ORDER_CONFIRMATION = """
✅ **تم تأكيد طلبك بنجاح!**

🆔 **رقم الطلب:** `{order_id}`
📦 **المنتج:** {product_name}
💰 **السعر:** {price} {currency}
📅 **التاريخ:** {date}

⏳ **جاري معالجة طلبك...**
سيتم إرسال بيانات الحساب فوراً عند اكتمال المعاملة.
"""

    DELIVERY_MESSAGE = """
🎉 **تم توصيل طلبك!**

📦 **المنتج:** {product_name}
🆔 **رقم الطلب:** `{order_id}`

📧 **Apple ID:** `{apple_id}`
🔑 **Password:** `{password}`

⚠️ **تعليمات مهمة:**
• سجل الدخول فقط عبر App Store
• لا تحاول تسجيل الدخول عبر iCloud
• لا تقم بتغيير أي بيانات الحساب
• اقرأ قوانين الاستخدام بالكامل

📖 **لقراءة القوانين:** اضغط على 📝 القوانين
"""

    PROFILE_TEMPLATE = """
👤 **حسابي:**

🆔 **المعرف:** `{user_id}`
👤 **الاسم:** {name}
📅 **تاريخ التسجيل:** {reg_date}
📊 **عدد الطلبات:** {orders_count}
💰 **إجمالي المشتريات:** {total_spent} {currency}
🎁 **الإحالات:** {referrals_count}

💎 **العضوية:** {membership}
"""

    REFERRAL_MESSAGE = """
🎁 **نظام الإحالة:**

🔗 **رابط الإحالة الخاص بك:**
`{referral_link}`

💰 **لكل صديق يشتري عبر رابطك، تحصل على {bonus_percent}% من قيمة مشترياته!**

📊 **إحصائيات إحالاتك:**
• عدد الإحالات: {referrals_count}
• إجمالي الأرباح: {total_earnings} {currency}

📢 شارك الرابط مع أصدقائك وابدأ بالربح الآن!
"""

    PRICE_LIST_HEADER = """
📋 **قائمة الأسعار:**

"""

    NO_ORDERS_MESSAGE = """
📭 **لا يوجد لديك طلبات حالياً.**

🛒 ابدأ التسوق الآن من قسم المنتجات!
"""

    ORDER_HISTORY_HEADER = """
📜 **سجل طلباتك:**

"""

    ADMIN_STATS = """
📊 **إحصائيات المتجر:**

👥 **إجمالي المستخدمين:** {total_users}
📦 **إجمالي الطلبات:** {total_orders}
💰 **إجمالي المبيعات:** {total_revenue} {currency}
📅 **طلبات اليوم:** {today_orders}
"""
