"""
Appify Store Bot - Keyboard Builders
====================================
Reply and Inline keyboard factories for the Telegram bot UI.
All text is in native Arabic with professional layout.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from config import PRODUCT_CATALOG, CHANNEL_LINK, BOT_USERNAME


# ─── Reply Keyboards (Main Menu) ──────────────────────────────────────────────

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the persistent main menu with properly arranged buttons."""
    builder = ReplyKeyboardBuilder()

    # Row 1: Products + Price List
    builder.row(
        KeyboardButton(text="🛒 المنتجات"),
        KeyboardButton(text="📋 قائمة الأسعار"),
    )
    # Row 2: Info + Rules
    builder.row(
        KeyboardButton(text="ℹ️ معلومات"),
        KeyboardButton(text="📝 القوانين"),
    )
    # Row 3: Profile + Support
    builder.row(
        KeyboardButton(text="👤 حسابي"),
        KeyboardButton(text="🛠 الدعم الفني"),
    )

    return builder.as_markup(resize_keyboard=True, persistent=True)


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Admin extended menu with management buttons."""
    builder = ReplyKeyboardBuilder()

    # Row 1
    builder.row(
        KeyboardButton(text="📊 الإحصائيات"),
        KeyboardButton(text="👥 المستخدمين"),
    )
    # Row 2
    builder.row(
        KeyboardButton(text="📦 إدارة الطلبات"),
        KeyboardButton(text="⚙️ إعدادات المتجر"),
    )
    # Row 3
    builder.row(
        KeyboardButton(text="📢 إشعار عام"),
        KeyboardButton(text="🚫 حظر مستخدم"),
    )
    # Row 4: Back to main menu
    builder.row(
        KeyboardButton(text="🔙 القائمة الرئيسية"),
    )

    return builder.as_markup(resize_keyboard=True, persistent=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel/Back keyboard for dialogs."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ إلغاء"))
    return builder.as_markup(resize_keyboard=True)


# ─── Inline Keyboards ─────────────────────────────────────────────────────────

def get_categories_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for product categories."""
    builder = InlineKeyboardBuilder()

    for cat_key, category in PRODUCT_CATALOG.items():
        builder.button(
            text=f"{category['emoji']} {category['name_ar']}",
            callback_data=f"category:{cat_key}"
        )

    builder.button(
        text="🔙 رجوع",
        callback_data="menu:main"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_products_inline_keyboard(category_key: str) -> InlineKeyboardMarkup:
    """Inline keyboard for products in a category."""
    from config import calculate_final_price

    builder = InlineKeyboardBuilder()
    category = PRODUCT_CATALOG.get(category_key)

    if category:
        for prod_key, product in category["items"].items():
            final_price = calculate_final_price(product["base_price_rub"])
            builder.button(
                text=f"{product['name']} — {final_price}$",
                callback_data=f"product:{prod_key}"
            )

    builder.button(
        text="🔙 رجوع للأقسام",
        callback_data="menu:categories"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_product_detail_keyboard(product_key: str, category_key: str) -> InlineKeyboardMarkup:
    """Inline keyboard for product detail view with purchase option."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🛒 شراء الآن",
        callback_data=f"buy:{product_key}"
    )
    builder.button(
        text="🛒 شراء (حسابك في البوت)",
        callback_data=f"buy_wallet:{product_key}"
    )
    builder.button(
        text="📤 مشاركة للقناة",
        callback_data=f"share_channel:{product_key}"
    )
    builder.button(
        text="🔙 رجوع",
        callback_data=f"category:{category_key}"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_payment_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Payment confirmation keyboard."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ تأكيد الدفع",
        callback_data=f"payment:confirm:{order_id}"
    )
    builder.button(
        text="❌ إلغاء الطلب",
        callback_data=f"payment:cancel:{order_id}"
    )
    builder.adjust(2)
    return builder.as_markup()


def get_profile_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for user profile section."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📜 سجل الطلبات",
        callback_data=f"profile:orders:{user_id}"
    )
    builder.button(
        text="🎁 نظام الإحالة",
        callback_data=f"profile:referral:{user_id}"
    )
    builder.button(
        text="💰 شحن الرصيد",
        callback_data=f"profile:deposit:{user_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_order_history_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for order history with pagination."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔙 رجوع للحساب",
        callback_data=f"profile:main:{telegram_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_referral_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for referral section."""
    builder = InlineKeyboardBuilder()

    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref{telegram_id}"

    builder.button(
        text="🔗 نسخ رابط الإحالة",
        url=f"https://t.me/share/url?url={referral_link}&text=انضم%20إلى%20متجر%20Appify%20Store!"
    )
    builder.button(
        text="🔙 رجوع للحساب",
        callback_data=f"profile:main:{telegram_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for support section."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📩 مراسلة الدعم",
        url=f"https://t.me/{BOT_USERNAME}"
    )
    builder.button(
        text="📢 قناتنا",
        url=CHANNEL_LINK
    )
    builder.button(
        text="🔙 رجوع",
        callback_data="menu:main"
    )
    builder.adjust(1)
    return builder.as_markup()


def get_channel_post_keyboard(product_key: str) -> InlineKeyboardMarkup:
    """Inline keyboard for channel post with deep link."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🛒 شراء الآن",
        url=f"https://t.me/{BOT_USERNAME}?start=buy_{product_key}"
    )
    builder.button(
        text="📢 قناة المتجر",
        url=CHANNEL_LINK
    )
    builder.adjust(2)
    return builder.as_markup()


def get_admin_actions_keyboard(target_user_id: int) -> InlineKeyboardMarkup:
    """Admin actions keyboard for user management."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🚫 حظر",
        callback_data=f"admin:ban:{target_user_id}"
    )
    builder.button(
        text="✅ فك الحظر",
        callback_data=f"admin:unban:{target_user_id}"
    )
    builder.button(
        text="📜 طلباته",
        callback_data=f"admin:orders:{target_user_id}"
    )
    builder.button(
        text="🔙 رجوع",
        callback_data="admin:users"
    )
    builder.adjust(3, 1)
    return builder.as_markup()


def get_order_action_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Admin order action keyboard."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ توصيل يدوي",
        callback_data=f"order:deliver:{order_id}"
    )
    builder.button(
        text="❌ رفض واسترداد",
        callback_data=f"order:refund:{order_id}"
    )
    builder.button(
        text="🔙 رجوع",
        callback_data="admin:orders"
    )
    builder.adjust(2, 1)
    return builder.as_markup()
