"""
Appify Store Bot - Frontend Handlers
====================================
Aiogram 3.x message and callback handlers for the Telegram bot.
All user-facing text is in native, professional Arabic.
"""

import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    BOT_NAME, BOT_USERNAME, CHANNEL_LINK,
    TextTemplates, PRODUCT_CATALOG, calculate_final_price,
    ADMIN_IDS
)
from database import (
    get_or_create_user, get_user, get_all_products_db,
    get_product_by_key, get_product_by_id,
    create_order, get_user_orders, get_order, deliver_order,
    get_full_stats, ban_user, unban_user,
    log_admin_action, update_order_status
)
from frontend.keyboards import *
from utils.image_watermark import process_product_image, generate_channel_post_image

router = Router()


# ─── FSM States ───────────────────────────────────────────────────────────────

class DepositState(StatesGroup):
    waiting_amount = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


class SupportState(StatesGroup):
    waiting_message = State()


# ─── Helper Functions ─────────────────────────────────────────────────────────

def is_admin(telegram_id: int) -> bool:
    """Check if user is admin."""
    return telegram_id in ADMIN_IDS


def escape_markdown(text: str) -> str:
    """Escape markdown special characters."""
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars:
        text = text.replace(char, f'\\{char}')
    return text


# ─── Start & Main Menu ────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - register user and show welcome."""
    await state.clear()

    # Parse referral or deep link
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    referrer_id = None
    product_key = None

    if args:
        if args.startswith("ref"):
            try:
                referrer_id = int(args[3:])
            except ValueError:
                pass
        elif args.startswith("buy_"):
            product_key = args[4:]
        elif args.isdigit():
            referrer_id = int(args)

    # Register or get user
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code or "ar",
        referrer_id=referrer_id,
    )

    if user.is_banned:
        await message.answer(
            "🚫 **تم حظرك من استخدام البوت.**\n\n"
            "للاستفسار، تواصل مع الإدارة.",
            parse_mode="Markdown"
        )
        return

    # If deep link to product
    if product_key:
        product = await get_product_by_key(product_key)
        if product:
            await show_product_detail(message, product)
            return

    # Show welcome message
    welcome_text = TextTemplates.WELCOME_MESSAGE.format(
        bot_name=BOT_NAME,
        channel_link=CHANNEL_LINK,
        bot_username=BOT_USERNAME,
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
        disable_web_page_preview=True,
    )


@router.message(F.text == "🔙 القائمة الرئيسية")
@router.message(F.text == "/menu")
async def show_main_menu(message: Message, state: FSMContext):
    """Show main menu."""
    await state.clear()
    user = await get_user(message.from_user.id)

    if user and user.is_banned:
        await message.answer("🚫 تم حظرك من البوت.", parse_mode="Markdown")
        return

    welcome_text = TextTemplates.WELCOME_MESSAGE.format(
        bot_name=BOT_NAME,
        channel_link=CHANNEL_LINK,
        bot_username=BOT_USERNAME,
    )

    keyboard = get_main_menu_keyboard()
    if user and user.is_admin:
        keyboard = get_admin_menu_keyboard()

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# ─── Products Section ─────────────────────────────────────────────────────────

@router.message(F.text == "🛒 المنتجات")
async def show_categories(message: Message):
    """Show product categories."""
    user = await get_user(message.from_user.id)
    if not user or user.is_banned:
        return

    await message.answer(
        "🛒 **قائمة الأقسام:**\n\n"
        "اختر القسم الذي تريد تصفح منتجاته:",
        parse_mode="Markdown",
        reply_markup=get_categories_inline_keyboard(),
    )


@router.callback_query(F.data.startswith("category:"))
async def callback_category(callback: CallbackQuery):
    """Handle category selection."""
    category_key = callback.data.split(":")[1]
    category = PRODUCT_CATALOG.get(category_key)

    if not category:
        await callback.answer("❌ القسم غير موجود", show_alert=True)
        return

    products_kb = get_products_inline_keyboard(category_key)
    await callback.message.edit_text(
        f"{category['emoji']} **قسم {category['name_ar']}:**\n\n"
        f"اختر المنتج لعرض التفاصيل:",
        parse_mode="Markdown",
        reply_markup=products_kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("product:"))
async def callback_product(callback: CallbackQuery):
    """Show product details."""
    product_key = callback.data.split(":")[1]
    product = await get_product_by_key(product_key)

    if not product:
        await callback.answer("❌ المنتج غير موجود", show_alert=True)
        return

    await show_product_detail(callback.message, product, edit=True)
    await callback.answer()


async def show_product_detail(message_or_callback, product, edit: bool = False):
    """Display product detail with image and purchase options."""
    final_price = product.final_price

    # Try to generate branded image
    try:
        image_buffer = await process_product_image(
            image_source=product.image_url or "",
            product_name=product.name,
            category=f"{product.category_emoji} {product.category_name_ar}",
            price=str(final_price),
            currency="USD",
        )
    except:
        image_buffer = None

    # Build caption
    caption = (
        f"{product.category_emoji} **{product.name}**\n"
        f"📂 **القسم:** {product.category_name_ar}\n"
        f"💰 **السعر:** `{final_price}` $ USD\n\n"
        f"🛒 اضغط **شراء الآن** لإتمام عملية الشراء"
    )

    keyboard = get_product_detail_keyboard(product.product_key, product.category)

    if image_buffer:
        if edit and hasattr(message_or_callback, 'edit_media'):
            from aiogram.types import InputMediaPhoto
            try:
                await message_or_callback.edit_media(
                    media=InputMediaPhoto(
                        media=image_buffer,
                        caption=caption,
                        parse_mode="Markdown",
                    ),
                    reply_markup=keyboard,
                )
                return
            except:
                pass
        await message_or_callback.answer_photo(
            photo=image_buffer,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        text = caption + "\n\n*(صورة المنتج غير متوفرة حالياً)*"
        if edit and hasattr(message_or_callback, 'edit_text'):
            try:
                await message_or_callback.edit_text(
                    text, parse_mode="Markdown", reply_markup=keyboard
                )
            except:
                await message_or_callback.answer(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await message_or_callback.answer(text, parse_mode="Markdown", reply_markup=keyboard)


# ─── Purchase Flow ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy:"))
async def callback_buy(callback: CallbackQuery):
    """Initiate purchase flow."""
    product_key = callback.data.split(":")[1]
    product = await get_product_by_key(product_key)

    if not product:
        await callback.answer("❌ المنتج غير متوفر", show_alert=True)
        return

    # Create order
    order = await create_order(
        telegram_id=callback.from_user.id,
        product_id=product.id,
        price_paid=product.final_price,
        currency="USD",
    )

    if not order:
        await callback.answer("❌ حدث خطأ في إنشاء الطلب", show_alert=True)
        return

    confirm_text = TextTemplates.ORDER_CONFIRMATION.format(
        order_id=order.order_id,
        product_name=product.name,
        price=product.final_price,
        currency="USD",
        date=order.created_at.strftime("%Y-%m-%d %H:%M"),
    )

    await callback.message.edit_text(
        confirm_text,
        parse_mode="Markdown",
        reply_markup=get_payment_keyboard(order.order_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payment:confirm:"))
async def callback_payment_confirm(callback: CallbackQuery, bot: Bot):
    """Handle payment confirmation."""
    order_id = callback.data.split(":")[2]
    order = await get_order(order_id)

    if not order:
        await callback.answer("❌ الطلب غير موجود", show_alert=True)
        return

    if order.user_id != callback.from_user.id:
        await callback.answer("❌ هذا الطلب ليس لك", show_alert=True)
        return

    # Update status to processing
    await update_order_status(order_id, "processing")

    await callback.message.edit_text(
        f"⏳ **جاري معالجة طلبك...**\n\n"
        f"🆔 رقم الطلب: `{order_id}`\n"
        f"📦 سيتم التوصيل خلال لحظات\n\n"
        f"⏳ يرجى الانتظار...",
        parse_mode="Markdown",
    )

    # Notify admins about new order
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 **طلب جديد!**\n\n"
                f"🆔 الطلب: `{order_id}`\n"
                f"👤 المستخدم: {callback.from_user.id}\n"
                f"📦 المنتج: {order.product.name if order.product else 'غير معروف'}\n"
                f"💰 السعر: {order.price_paid}$",
                parse_mode="Markdown",
            )
        except:
            pass

    # Here you would trigger the Pyrogram automation
    # For now, we'll simulate with a manual delivery option for admins

    await callback.answer("✅ تم تأكيد الدفع!", show_alert=True)


@router.callback_query(F.data.startswith("payment:cancel:"))
async def callback_payment_cancel(callback: CallbackQuery):
    """Handle order cancellation."""
    order_id = callback.data.split(":")[2]
    order = await get_order(order_id)

    if not order:
        await callback.answer("❌ الطلب غير موجود", show_alert=True)
        return

    if order.user_id != callback.from_user.id:
        await callback.answer("❌ هذا الطلب ليس لك", show_alert=True)
        return

    await update_order_status(order_id, "failed", error_message="Cancelled by user")

    await callback.message.edit_text(
        "❌ **تم إلغاء الطلب.**\n\n"
        "يمكنك إعادة المحاولة في أي وقت.",
        parse_mode="Markdown",
        reply_markup=get_categories_inline_keyboard(),
    )
    await callback.answer()


# ─── Price List ───────────────────────────────────────────────────────────────

@router.message(F.text == "📋 قائمة الأسعار")
async def show_price_list(message: Message):
    """Show formatted price list."""
    user = await get_user(message.from_user.id)
    if not user or user.is_banned:
        return

    products = await get_all_products_db()

    text = TextTemplates.PRICE_LIST_HEADER

    current_category = ""
    for product in products:
        if product.category != current_category:
            current_category = product.category
            text += f"\n{product.category_emoji} **{product.category_name_ar}:**\n"
            text += "─" * 20 + "\n"

        text += f"• {product.name} — `{product.final_price}` $USD\n"

    text += f"\n💡 **للشراء:** اذهب إلى 🛒 المنتجات"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


# ─── Rules Section ────────────────────────────────────────────────────────────

@router.message(F.text == "📝 القوانين")
async def show_rules(message: Message):
    """Display rules and terms of use."""
    user = await get_user(message.from_user.id)
    if not user or user.is_banned:
        return

    await message.answer(
        TextTemplates.RULES_MESSAGE,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )


# ─── Info Section ─────────────────────────────────────────────────────────────

@router.message(F.text == "ℹ️ معلومات")
async def show_info(message: Message):
    """Display bot information."""
    user = await get_user(message.from_user.id)
    if not user or user.is_banned:
        return

    info_text = TextTemplates.INFO_MESSAGE.format(
        bot_name=BOT_NAME,
        channel_link=CHANNEL_LINK,
        bot_username=BOT_USERNAME,
    )

    await message.answer(
        info_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
        disable_web_page_preview=True,
    )


# ─── Profile Section ──────────────────────────────────────────────────────────

@router.message(F.text == "👤 حسابي")
async def show_profile(message: Message):
    """Display user profile."""
    user = await get_user(message.from_user.id)

    if not user:
        await message.answer("⚠️ لم يتم العثور على حسابك. ابدأ بالأمر /start")
        return

    if user.is_banned:
        await message.answer("🚫 تم حظرك من البوت.")
        return

    membership = "💎 أدمن" if user.is_admin else "⭐ عادي"

    profile_text = TextTemplates.PROFILE_TEMPLATE.format(
        user_id=user.telegram_id,
        name=escape_markdown(user.first_name or "مستخدم"),
        reg_date=user.reg_date.strftime("%Y-%m-%d") if user.reg_date else "غير معروف",
        orders_count=user.orders_count,
        total_spent=user.total_spent,
        currency="USD",
        referrals_count=user.referral_count,
        membership=membership,
    )

    await message.answer(
        profile_text,
        parse_mode="Markdown",
        reply_markup=get_profile_inline_keyboard(user.telegram_id),
    )


@router.callback_query(F.data.startswith("profile:main:"))
async def callback_profile_main(callback: CallbackQuery):
    """Return to profile main view."""
    # Reuse show_profile logic
    await show_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("profile:orders:"))
async def callback_profile_orders(callback: CallbackQuery):
    """Show user's order history."""
    telegram_id = int(callback.data.split(":")[2])

    if callback.from_user.id != telegram_id and not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح", show_alert=True)
        return

    orders = await get_user_orders(telegram_id)

    if not orders:
        text = TextTemplates.NO_ORDERS_MESSAGE
    else:
        text = TextTemplates.ORDER_HISTORY_HEADER
        for order in orders[:10]:
            status_emoji = {
                "pending": "⏳",
                "paid": "💰",
                "processing": "⚙️",
                "completed": "✅",
                "failed": "❌",
                "refunded": "↩️",
            }.get(order.status, "❓")

            text += (
                f"{status_emoji} **طلب #{order.order_id}**\n"
                f"📦 {order.product.name if order.product else 'غير معروف'}\n"
                f"💰 {order.price_paid}$ | {order.created_at.strftime('%Y-%m-%d')}\n"
                f"─" * 15 + "\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_order_history_keyboard(telegram_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:referral:"))
async def callback_profile_referral(callback: CallbackQuery):
    """Show referral system info."""
    telegram_id = int(callback.data.split(":")[2])

    if callback.from_user.id != telegram_id and not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح", show_alert=True)
        return

    user = await get_user(telegram_id)
    if not user:
        await callback.answer("❌ المستخدم غير موجود", show_alert=True)
        return

    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref{telegram_id}"

    text = TextTemplates.REFERRAL_MESSAGE.format(
        referral_link=referral_link,
        bonus_percent="5",
        referrals_count=user.referral_count,
        total_earnings=user.referral_earnings,
        currency="USD",
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_referral_keyboard(telegram_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:deposit:"))
async def callback_profile_deposit(callback: CallbackQuery, state: FSMContext):
    """Handle balance deposit request."""
    await callback.message.edit_text(
        "💰 **شحن الرصيد**\n\n"
        "⚠️ هذه الميزة قيد التطوير.\n"
        "يرجى التواصل مع الدعم لشحن الرصيد يدوياً.",
        parse_mode="Markdown",
        reply_markup=get_support_keyboard(),
    )
    await callback.answer()


# ─── Support Section ──────────────────────────────────────────────────────────

@router.message(F.text == "🛠 الدعم الفني")
async def show_support(message: Message):
    """Display support information."""
    user = await get_user(message.from_user.id)
    if not user or user.is_banned:
        return

    support_text = TextTemplates.SUPPORT_MESSAGE.format(
        channel_link=CHANNEL_LINK,
    )

    await message.answer(
        support_text,
        parse_mode="Markdown",
        reply_markup=get_support_keyboard(),
    )


# ─── Menu Callbacks ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:main")
async def callback_menu_main(callback: CallbackQuery):
    """Return to main menu from inline."""
    welcome_text = TextTemplates.WELCOME_MESSAGE.format(
        bot_name=BOT_NAME,
        channel_link=CHANNEL_LINK,
        bot_username=BOT_USERNAME,
    )

    try:
        await callback.message.edit_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_categories_inline_keyboard(),
        )
    except:
        await callback.message.answer(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "menu:categories")
async def callback_menu_categories(callback: CallbackQuery):
    """Return to categories list."""
    await callback.message.edit_text(
        "🛒 **قائمة الأقسام:**\n\n"
        "اختر القسم الذي تريد تصفح منتجاته:",
        parse_mode="Markdown",
        reply_markup=get_categories_inline_keyboard(),
    )
    await callback.answer()


# ─── Channel Post Generation ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("share_channel:"))
async def callback_share_channel(callback: CallbackQuery):
    """Generate a channel post preview for a product."""
    product_key = callback.data.split(":")[1]
    product = await get_product_by_key(product_key)

    if not product:
        await callback.answer("❌ المنتج غير موجود", show_alert=True)
        return

    # Generate channel post image
    image_buffer = generate_channel_post_image(
        product_name=product.name,
        price=str(product.final_price),
        category=f"{product.category_emoji} {product.category_name_ar}",
    )

    deep_link = f"https://t.me/{BOT_USERNAME}?start=buy_{product_key}"

    caption = (
        f"{product.category_emoji} **{product.name}**\n\n"
        f"💰 **السعر:** `{product.final_price}` $USD\n"
        f"📂 **القسم:** {product.category_name_ar}\n\n"
        f"✅ توصيل فوري\n"
        f"✅ ضمان كامل\n\n"
        f"🛒 **للشراء:** [اضغط هنا]({deep_link})\n\n"
        f"📢 {CHANNEL_LINK}"
    )

    await callback.message.answer_photo(
        photo=image_buffer,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=get_channel_post_keyboard(product_key),
    )

    await callback.answer("✅ تم إنشاء المنشور!")


# ─── Admin Handlers ───────────────────────────────────────────────────────────

@router.message(F.text == "📊 الإحصائيات")
async def admin_stats(message: Message):
    """Show admin statistics panel."""
    if not is_admin(message.from_user.id):
        return

    stats = await get_full_stats()

    stats_text = TextTemplates.ADMIN_STATS.format(
        total_users=stats["total_users"],
        total_orders=stats["total_orders"],
        total_revenue=stats["total_revenue"],
        today_orders=stats["today_orders"],
        currency="USD",
    )

    stats_text += (
        f"\n📊 **حالة الطلبات:**\n"
        f"⏳ قيد الانتظار: {stats['pending_orders']}\n"
        f"⚙️ قيد المعالجة: {stats['processing_orders']}\n"
        f"✅ مكتملة: {stats['completed_orders']}\n"
        f"❌ فاشلة: {stats['failed_orders']}\n"
    )

    await message.answer(
        stats_text,
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard(),
    )

    await log_admin_action(
        admin_id=message.from_user.id,
        action="view_stats",
    )


@router.message(F.text == "👥 المستخدمين")
async def admin_users(message: Message):
    """Show recent users list."""
    if not is_admin(message.from_user.id):
        return

    from database import get_all_users
    users = await get_all_users(limit=20)

    if not users:
        await message.answer("📭 لا يوجد مستخدمون.")
        return

    text = "👥 **المستخدمون:**\n\n"
    for user in users:
        status = "🚫" if user.is_banned else "✅"
        name = escape_markdown(user.first_name or "مستخدم")
        text += (
            f"{status} `{user.telegram_id}` | {name}\n"
            f"📊 طلبات: {user.orders_count} | مشتريات: {user.total_spent}$\n"
            f"─" * 15 + "\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(F.text == "📦 إدارة الطلبات")
async def admin_orders(message: Message):
    """Show pending/processing orders for admin."""
    if not is_admin(message.from_user.id):
        return

    from database import get_recent_orders
    orders = await get_recent_orders(limit=20)

    if not orders:
        await message.answer("📭 لا يوجد طلبات.")
        return

    text = "📦 **الطلبات:**\n\n"
    for order in orders:
        status_emoji = {
            "pending": "⏳",
            "paid": "💰",
            "processing": "⚙️",
            "completed": "✅",
            "failed": "❌",
            "refunded": "↩️",
        }.get(order.status, "❓")

        text += (
            f"{status_emoji} **#{order.order_id}** | {order.price_paid}$\n"
            f"👤 `{order.user_id}` | 📦 {order.product.name if order.product else '؟'}\n"
            f"📅 {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"─" * 15 + "\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.message(F.text == "📢 إشعار عام")
async def admin_broadcast_start(message: Message, state: FSMContext):
    """Start broadcast flow."""
    if not is_admin(message.from_user.id):
        return

    await state.set_state(BroadcastState.waiting_message)
    await message.answer(
        "📢 **إرسال إشعار عام**\n\n"
        "أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:\n\n"
        "(أرسل ❌ إلغاء للتراجع)",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(BroadcastState.waiting_message)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    """Send broadcast to all users."""
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer("❌ تم الإلغاء.", reply_markup=get_admin_menu_keyboard())
        return

    await state.clear()

    # Get all users
    from database import get_all_users
    users = await get_all_users(limit=10000)

    sent = 0
    failed = 0

    status_msg = await message.answer(
        f"⏳ جاري الإرسال... (0/{len(users)})",
        reply_markup=get_admin_menu_keyboard(),
    )

    for user in users:
        try:
            await bot.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"⏳ جاري الإرسال... ({sent + failed}/{len(users)})\n"
                    f"✅ نجح: {sent} | ❌ فشل: {failed}"
                )
            except:
                pass

    await status_msg.edit_text(
        f"✅ **تم الإرسال!**\n\n"
        f"📊 الإحصائيات:\n"
        f"✅ نجح: {sent}\n"
        f"❌ فشل: {failed}\n"
        f"📊 المجموع: {len(users)}"
    )

    await log_admin_action(
        admin_id=message.from_user.id,
        action="broadcast",
        details=f"Sent to {sent} users, failed {failed}",
    )


@router.message(F.text == "🚫 حظر مستخدم")
async def admin_ban_start(message: Message, state: FSMContext):
    """Start ban user flow."""
    if not is_admin(message.from_user.id):
        return

    await state.set_state(SupportState.waiting_message)
    await state.update_data(action="ban")
    await message.answer(
        "🚫 **حظر مستخدم**\n\n"
        "أرسل آيدي المستخدم (Telegram ID) لحظره:\n\n"
        "(أرسل ❌ إلغاء للتراجع)",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(F.text == "⚙️ إعدادات المتجر")
async def admin_settings(message: Message):
    """Show store settings."""
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "⚙️ **إعدادات المتجر**\n\n"
        "🔧 الخيارات المتاحة:\n\n"
        "• تعديل الأسعار\n"
        "• تفعيل/تعطيل منتجات\n"
        "• إدارة الأقسام\n\n"
        "⚠️ هذه الميزات قيد التطوير.",
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard(),
    )


# ─── Admin Callbacks ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:ban:"))
async def callback_admin_ban(callback: CallbackQuery):
    """Ban user from admin action."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح", show_alert=True)
        return

    target_id = int(callback.data.split(":")[2])
    success = await ban_user(target_id)

    if success:
        await callback.answer(f"✅ تم حظر المستخدم {target_id}", show_alert=True)
        await log_admin_action(callback.from_user.id, "ban_user", target_id)
    else:
        await callback.answer("❌ المستخدم غير موجود", show_alert=True)


@router.callback_query(F.data.startswith("admin:unban:"))
async def callback_admin_unban(callback: CallbackQuery):
    """Unban user from admin action."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح", show_alert=True)
        return

    target_id = int(callback.data.split(":")[2])
    success = await unban_user(target_id)

    if success:
        await callback.answer(f"✅ تم فك حظر المستخدم {target_id}", show_alert=True)
        await log_admin_action(callback.from_user.id, "unban_user", target_id)
    else:
        await callback.answer("❌ المستخدم غير موجود", show_alert=True)


@router.callback_query(F.data.startswith("order:deliver:"))
async def callback_order_deliver(callback: CallbackQuery):
    """Manual order delivery by admin."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح", show_alert=True)
        return

    order_id = callback.data.split(":")[2]
    await callback.message.answer(
        f"📦 **توصيل يدوي للطلب {order_id}**\n\n"
        "أرسل بيانات الحساب بالصيغة التالية:\n"
        "```\nAppleID: email@example.com\nPassword: password123\n```",
        parse_mode="Markdown",
    )

    # Store pending delivery in state would need FSM - simplified here
    await callback.answer("📋 أرسل البيانات في رسالة منفصلة")


@router.callback_query(F.data.startswith("order:refund:"))
async def callback_order_refund(callback: CallbackQuery):
    """Refund order by admin."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ غير مصرح", show_alert=True)
        return

    from database import refund_order
    order_id = callback.data.split(":")[2]
    success = await refund_order(order_id)

    if success:
        await callback.answer(f"✅ تم استرداد الطلب {order_id}", show_alert=True)
        await log_admin_action(callback.from_user.id, "refund_order", details=order_id)
    else:
        await callback.answer("❌ الطلب غير موجود أو مسترد مسبقاً", show_alert=True)


# ─── Error Handler ────────────────────────────────────────────────────────────

@router.errors()
async def error_handler(update, exception):
    """Handle errors gracefully."""
    print(f"[Error] {type(exception).__name__}: {exception}")
    # Don't crash - log and continue
