"""
Appify Store Bot - SourceBot Automation Bridge
===============================================
Pyrogram Userbot that automates purchases from @SourceBot.
Handles communication, response parsing, and error recovery.
"""

import asyncio
import re
import time
from typing import Optional, Tuple, Dict, Any

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    FloodWait, UserIsBlocked, PeerIdInvalid,
    UsernameNotOccupied, TimeoutError as PyrogramTimeout
)

from config import (
    PYROGRAM_API_ID, PYROGRAM_API_HASH, PYROGRAM_SESSION_STRING,
    SOURCE_BOT_USERNAME, ADMIN_IDS
)
from database import (
    get_order, update_order_status, deliver_order, create_order
)

# ─── Pyrogram Client ──────────────────────────────────────────────────────────

pyro_client: Optional[Client] = None

# ─── Regex Patterns for Parsing SourceBot Responses ───────────────────────────

# Pattern to extract Apple ID (email format)
APPLE_ID_PATTERN = re.compile(
    r'(?:Apple\s*ID[\s:]*|Логин[\s:]*|Айди[\s:]*|ID[\s:]*)\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    re.IGNORECASE
)

# Pattern to extract Password
PASSWORD_PATTERN = re.compile(
    r'(?:Password[\s:]*|Пароль[\s:]*|Pass[\s:]*|Пароль[\s:]*)\s*[:\-]?\s*(\S+)',
    re.IGNORECASE
)

# Pattern to detect "Out of Stock"
OUT_OF_STOCK_PATTERNS = [
    re.compile(r'нет\s+в\s+наличии', re.IGNORECASE),
    re.compile(r'out\s+of\s+stock', re.IGNORECASE),
    re.compile(r'закончил(?:ся|ись|ось)', re.IGNORECASE),
    re.compile(r'не\s+доступен', re.IGNORECASE),
    re.compile(r'not\s+available', re.IGNORECASE),
    re.compile(r'отсутствует', re.IGNORECASE),
]

# Pattern to detect insufficient funds
NO_FUNDS_PATTERNS = [
    re.compile(r'недостаточно\s+(?:средств|баланса)', re.IGNORECASE),
    re.compile(r'insufficient\s+funds', re.IGNORECASE),
    re.compile(r'не\s+хватает', re.IGNORECASE),
    re.compile(r'баланс\s+низкий', re.IGNORECASE),
]

# Pattern to detect successful purchase
SUCCESS_PATTERNS = [
    re.compile(r'(?:покупка\s+успешна|успешно|готово|выполнено|success|done)', re.IGNORECASE),
    re.compile(r'ваш\s+(?:заказ|покупка)', re.IGNORECASE),
    re.compile(r'данные\s+для\s+входа', re.IGNORECASE),
]

# Pattern to detect error/failure
ERROR_PATTERNS = [
    re.compile(r'(?:ошибка|error|fail|не удалось|не\s+вышло)', re.IGNORECASE),
]


# ─── Response Parser ──────────────────────────────────────────────────────────

class SourceBotResponse:
    """Parsed response from SourceBot."""

    STATUS_SUCCESS = "success"
    STATUS_OUT_OF_STOCK = "out_of_stock"
    STATUS_NO_FUNDS = "no_funds"
    STATUS_ERROR = "error"
    STATUS_UNKNOWN = "unknown"
    STATUS_TIMEOUT = "timeout"

    def __init__(self, raw_text: str = ""):
        self.raw_text = raw_text
        self.apple_id: Optional[str] = None
        self.password: Optional[str] = None
        self.status = self.STATUS_UNKNOWN
        self.is_success = False
        self.error_message: Optional[str] = None
        self._parse()

    def _parse(self) -> None:
        """Parse the raw response text."""
        if not self.raw_text:
            return

        text = self.raw_text

        # Check for out of stock
        for pattern in OUT_OF_STOCK_PATTERNS:
            if pattern.search(text):
                self.status = self.STATUS_OUT_OF_STOCK
                self.error_message = "المنتج غير متوفر حالياً في المصدر"
                return

        # Check for insufficient funds
        for pattern in NO_FUNDS_PATTERNS:
            if pattern.search(text):
                self.status = self.STATUS_NO_FUNDS
                self.error_message = "رصيد المصدر غير كافٍ - يرجى إبلاغ الإدارة"
                return

        # Check for error
        for pattern in ERROR_PATTERNS:
            if pattern.search(text):
                self.status = self.STATUS_ERROR
                self.error_message = "حدث خطأ أثناء المعالجة في المصدر"
                return

        # Try to extract Apple ID and Password
        id_match = APPLE_ID_PATTERN.search(text)
        pass_match = PASSWORD_PATTERN.search(text)

        if id_match and pass_match:
            self.apple_id = id_match.group(1).strip()
            self.password = pass_match.group(1).strip()
            self.status = self.STATUS_SUCCESS
            self.is_success = True
            return

        # Check for success indicators even without credentials
        for pattern in SUCCESS_PATTERNS:
            if pattern.search(text):
                self.status = self.STATUS_SUCCESS
                self.is_success = True
                return

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "is_success": self.is_success,
            "apple_id": self.apple_id,
            "password": self.password,
            "error_message": self.error_message,
            "raw_preview": self.raw_text[:200] if self.raw_text else "",
        }


# ─── SourceBot Bridge ─────────────────────────────────────────────────────────

class SourceBotBridge:
    """
    Bridge to automate purchases from @SourceBot.
    Uses Pyrogram userbot to send messages and parse responses.
    """

    def __init__(self):
        self.client: Optional[Client] = None
        self.pending_purchases: Dict[str, asyncio.Future] = {}
        self.response_timeout = 60  # seconds
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize the Pyrogram client."""
        if self.initialized:
            return True

        if not all([PYROGRAM_API_ID, PYROGRAM_API_HASH, PYROGRAM_SESSION_STRING]):
            print("[SourceBot] Pyrogram credentials not configured. Bridge disabled.")
            return False

        try:
            self.client = Client(
                name="appify_bridge",
                api_id=PYROGRAM_API_ID,
                api_hash=PYROGRAM_API_HASH,
                session_string=PYROGRAM_SESSION_STRING,
                in_memory=True,
                no_updates=False,
            )

            await self.client.start()

            # Register message handler for SourceBot responses
            @self.client.on_message(
                filters.private & filters.user(SOURCE_BOT_USERNAME)
            )
            async def handle_sourcebot_response(client, message: Message):
                await self._handle_response(message)

            self.initialized = True
            print("[SourceBot] Bridge initialized successfully.")
            return True

        except Exception as e:
            print(f"[SourceBot] Failed to initialize: {e}")
            self.initialized = False
            return False

    async def shutdown(self):
        """Shutdown the Pyrogram client."""
        if self.client:
            try:
                await self.client.stop()
            except:
                pass
        self.initialized = False

    async def _handle_response(self, message: Message):
        """Handle incoming messages from SourceBot."""
        text = message.text or message.caption or ""

        # Try to match with pending purchases
        # We use a simple approach - match by order context
        # In production, you'd want more sophisticated matching

        for order_id, future in list(self.pending_purchases.items()):
            if not future.done():
                response = SourceBotResponse(text)
                future.set_result(response)
                del self.pending_purchases[order_id]
                break

    async def _wait_for_response(self, order_id: str) -> SourceBotResponse:
        """Wait for SourceBot response with timeout."""
        future = asyncio.Future()
        self.pending_purchases[order_id] = future

        try:
            response = await asyncio.wait_for(
                future,
                timeout=self.response_timeout
            )
            return response
        except asyncio.TimeoutError:
            return SourceBotResponse()
        finally:
            self.pending_purchases.pop(order_id, None)

    async def purchase(
        self,
        order_id: str,
        product_name: str,
        product_code: Optional[str] = None,
    ) -> SourceBotResponse:
        """
        Execute purchase from SourceBot.

        Args:
            order_id: Our internal order ID
            product_name: Product name as known by SourceBot
            product_code: Optional product code/ID

        Returns:
            SourceBotResponse with parsed result
        """
        if not self.initialized or not self.client:
            return SourceBotResponse()

        try:
            # Step 1: Send /start or initial command to SourceBot
            # This depends on how @SourceBot works - adjust accordingly
            await self.client.send_message(
                chat_id=SOURCE_BOT_USERNAME,
                text="/start",
            )

            await asyncio.sleep(2)

            # Step 2: Send product selection
            # Adjust message format based on @SourceBot's expected format
            purchase_message = product_code or product_name
            await self.client.send_message(
                chat_id=SOURCE_BOT_USERNAME,
                text=purchase_message,
            )

            # Step 3: Wait for response
            response = await self._wait_for_response(order_id)

            # Step 4: Handle any follow-up interactions
            if response.status == SourceBotResponse.STATUS_SUCCESS:
                # May need to confirm payment
                await self.client.send_message(
                    chat_id=SOURCE_BOT_USERNAME,
                    text="✅",
                )

                # Wait for final response with credentials
                final_response = await self._wait_for_response(f"{order_id}_final")
                if final_response.apple_id:
                    response = final_response

            return response

        except FloodWait as e:
            wait_time = e.value
            print(f"[SourceBot] FloodWait: sleeping {wait_time}s")
            await asyncio.sleep(wait_time)
            return SourceBotResponse()

        except (UserIsBlocked, PeerIdInvalid, UsernameNotOccupied) as e:
            print(f"[SourceBot] Cannot reach SourceBot: {e}")
            return SourceBotResponse()

        except Exception as e:
            print(f"[SourceBot] Purchase error: {e}")
            return SourceBotResponse()

    async def check_balance(self) -> Optional[float]:
        """Check remaining balance with SourceBot."""
        if not self.initialized or not self.client:
            return None

        try:
            # Send balance check command
            # Adjust based on @SourceBot's command format
            await self.client.send_message(
                chat_id=SOURCE_BOT_USERNAME,
                text="/balance",
            )

            response = await self._wait_for_response("balance_check")

            # Try to extract balance amount
            balance_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(?:₽|RUB|руб)')
            match = balance_pattern.search(response.raw_text)
            if match:
                return float(match.group(1))

            return None

        except Exception as e:
            print(f"[SourceBot] Balance check error: {e}")
            return None


# ─── Singleton Instance ───────────────────────────────────────────────────────

_bridge: Optional[SourceBotBridge] = None


def get_bridge() -> SourceBotBridge:
    """Get or create SourceBot bridge singleton."""
    global _bridge
    if _bridge is None:
        _bridge = SourceBotBridge()
    return _bridge


# ─── Automation Orchestrator ──────────────────────────────────────────────────

class OrderAutomation:
    """
    Orchestrates the full order lifecycle from payment to delivery.
    Bridges frontend orders with SourceBot automation.
    """

    def __init__(self):
        self.bridge = get_bridge()
        self.active_orders: Dict[str, asyncio.Task] = {}

    async def initialize(self):
        """Initialize automation components."""
        await self.bridge.initialize()

    async def process_order(self, order_id: str, bot=None):
        """
        Process a paid order through SourceBot automation.

        Flow:
        1. Get order details from database
        2. Map product to SourceBot format
        3. Execute purchase via Pyrogram
        4. Parse response and deliver to customer
        5. Handle errors gracefully
        """
        from database import get_order, update_order_status, deliver_order

        order = await get_order(order_id)
        if not order:
            print(f"[Automation] Order {order_id} not found")
            return

        # Update status to processing
        await update_order_status(order_id, "processing")

        # Map product to SourceBot format
        product_mapping = self._get_sourcebot_product_code(order.product.name)

        # Execute purchase
        response = await self.bridge.purchase(
            order_id=order_id,
            product_name=order.product.name,
            product_code=product_mapping,
        )

        # Handle response
        if response.is_success and response.apple_id and response.password:
            # Deliver to customer
            await deliver_order(
                order_id=order_id,
                apple_id=response.apple_id,
                password=response.password,
            )

            # Notify customer
            if bot:
                try:
                    from config import TextTemplates
                    delivery_text = TextTemplates.DELIVERY_MESSAGE.format(
                        product_name=order.product.name,
                        order_id=order_id,
                        apple_id=response.apple_id,
                        password=response.password,
                    )
                    await bot.send_message(
                        chat_id=order.user_id,
                        text=delivery_text,
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    print(f"[Automation] Failed to notify customer: {e}")

        elif response.status == SourceBotResponse.STATUS_OUT_OF_STOCK:
            await update_order_status(
                order_id=order_id,
                status="failed",
                error_message="المنتج غير متوفر في المصدر",
            )
            # Notify admins
            if bot:
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"⚠️ **نفاد مخزون!**\n\n"
                            f"المنتج: {order.product.name}\n"
                            f"الطلب: `{order_id}`",
                            parse_mode="Markdown",
                        )
                    except:
                        pass

        elif response.status == SourceBotResponse.STATUS_NO_FUNDS:
            await update_order_status(
                order_id=order_id,
                status="failed",
                error_message="رصيد المصدر غير كافٍ",
            )
            # Urgent admin notification
            if bot:
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"🚨 **تنبيه عاجل: رصيد المصدر منخفض!**\n\n"
                            f"الطلب: `{order_id}`\n"
                            f"يرجى شحن رصيد @SourceBot فوراً!",
                            parse_mode="Markdown",
                        )
                    except:
                        pass

        else:
            # Generic error
            await update_order_status(
                order_id=order_id,
                status="failed",
                error_message=response.error_message or "خطأ غير معروف",
            )

    def _get_sourcebot_product_code(self, product_name: str) -> str:
        """
        Map our product names to @SourceBot's expected format.
        Customize this based on how @SourceBot accepts orders.
        """
        # This is a mapping - adjust based on actual SourceBot behavior
        mapping = {
            "Minecraft": "Minecraft",
            "Terraria": "Terraria",
            "Geometry Dash": "Geometry Dash",
            "GTA: San Andreas": "GTA San Andreas",
            "Red Dead Redemption": "Red Dead Redemption",
            "Все FNaF'ы": "FNAF",
            "Subnautica + Below Zero": "Subnautica",
            "Dead Cells": "Dead Cells",
            "Tomb Raider": "Tomb Raider",
            "Удалённые игры из РФ": "Removed Games RU",
            "LumaFusion": "LumaFusion",
            "FL Studio": "FL Studio Mobile",
            "Procreate + PE": "Procreate",
            "Procreate Dreams": "Procreate Dreams",
            "Procam": "ProCam",
            "Nomad Sculpt": "Nomad Sculpt",
            "Things 3": "Things 3",
            "AnkiMobile Flashcards": "AnkiMobile",
            "Apple ID США": "Apple ID USA",
            "Apple ID Турция": "Apple ID Turkey",
            "Apple ID Россия": "Apple ID Russia",
            "Apple ID c Minecraft": "Apple ID + Minecraft",
        }
        return mapping.get(product_name, product_name)

    async def shutdown(self):
        """Cancel all active order tasks."""
        for task in self.active_orders.values():
            task.cancel()
        self.active_orders.clear()
        await self.bridge.shutdown()


# ─── Convenience Functions ────────────────────────────────────────────────────

async def init_automation() -> bool:
    """Initialize the automation system."""
    automation = OrderAutomation()
    success = await automation.initialize()
    if success:
        print("[Automation] Order automation initialized.")
    return success


async def process_paid_order(order_id: str, bot=None):
    """Process a paid order through automation."""
    automation = OrderAutomation()
    await automation.process_order(order_id, bot)


async def shutdown_automation():
    """Shutdown automation system."""
    bridge = get_bridge()
    await bridge.shutdown()
