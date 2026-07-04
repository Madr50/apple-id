"""
Appify Store Bot - Database Module
==================================
Async SQLAlchemy ORM with SQLite (PostgreSQL-ready).
Handles Users, Orders, Products, and Referrals with full CRUD operations.
"""

import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Float,
    DateTime, Boolean, Text, ForeignKey, select, func, desc
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, selectinload
from sqlalchemy.exc import IntegrityError

from config import DATABASE_PATH, PRODUCT_CATALOG, get_all_products

# ─── Database Engine & Session ────────────────────────────────────────────────
# Use aiosqlite for async SQLite support
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    """Telegram user model with profile and referral tracking."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    language_code = Column(String(10), default="ar")
    reg_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    referred_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    referral_count = Column(Integer, default=0)
    referral_earnings = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)
    orders_count = Column(Integer, default=0)

    # Relationships
    orders = relationship("Order", back_populates="user", lazy="selectin")
    referrals = relationship(
        "User",
        backref="referrer",
        remote_side=[telegram_id],
        foreign_keys=[referred_by],
        lazy="selectin"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "reg_date": self.reg_date.strftime("%Y-%m-%d") if self.reg_date else None,
            "is_banned": self.is_banned,
            "is_admin": self.is_admin,
            "referral_count": self.referral_count,
            "referral_earnings": self.referral_earnings,
            "total_spent": self.total_spent,
            "orders_count": self.orders_count,
        }


class Product(Base):
    """Product catalog model with dynamic pricing."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_key = Column(String(64), unique=True, nullable=False, index=True)
    category = Column(String(32), nullable=False)
    category_emoji = Column(String(8), nullable=False)
    category_name_ar = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    base_price_rub = Column(Integer, nullable=False)
    final_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    image_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="product", lazy="selectin")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_key": self.product_key,
            "category": self.category,
            "category_emoji": self.category_emoji,
            "category_name_ar": self.category_name_ar,
            "name": self.name,
            "base_price_rub": self.base_price_rub,
            "final_price": self.final_price,
            "is_active": self.is_active,
        }


class Order(Base):
    """Order model tracking purchase lifecycle."""
    __tablename__ = "orders"

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    status = Column(String(16), default=STATUS_PENDING)
    price_paid = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    apple_id = Column(String(256), nullable=True)
    apple_password = Column(String(256), nullable=True)
    source_order_response = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders", lazy="selectin")
    product = relationship("Product", back_populates="orders", lazy="selectin")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "product_name": self.product.name if self.product else None,
            "status": self.status,
            "price_paid": self.price_paid,
            "currency": self.currency,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M") if self.completed_at else None,
        }


class AdminLog(Base):
    """Admin action log for auditing."""
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, nullable=False)
    action = Column(String(64), nullable=False)
    target_user_id = Column(BigInteger, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ─── Database Initialization ──────────────────────────────────────────────────

async def init_db():
    """Initialize database tables and seed products."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_products()
    print("[DB] Database initialized and products seeded.")


async def seed_products():
    """Seed the database with initial product catalog."""
    async with AsyncSessionLocal() as session:
        # Check if products already exist
        result = await session.execute(select(Product))
        existing = result.scalars().all()
        if existing:
            print(f"[DB] {len(existing)} products already seeded.")
            return

        # Seed products from catalog
        for product_data in get_all_products():
            product = Product(
                product_key=product_data["id"],
                category=product_data["category"],
                category_emoji=product_data["category_emoji"],
                category_name_ar=product_data["category_name_ar"],
                name=product_data["name"],
                base_price_rub=product_data["base_price_rub"],
                final_price=product_data["final_price"],
                is_active=True,
            )
            session.add(product)

        await session.commit()
        print(f"[DB] Seeded {len(get_all_products())} products.")


# ─── CRUD Operations: Users ───────────────────────────────────────────────────

async def get_user(telegram_id: int) -> Optional[User]:
    """Get user by Telegram ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: str = "ar",
    referrer_id: Optional[int] = None,
) -> User:
    """Get existing user or create new one."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Update user info
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            await session.commit()
            return user

        # Check for referrer
        referred_by = None
        if referrer_id and referrer_id != telegram_id:
            ref_result = await session.execute(
                select(User).where(User.telegram_id == referrer_id)
            )
            referrer = ref_result.scalar_one_or_none()
            if referrer:
                referred_by = referrer_id
                referrer.referral_count += 1

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            referred_by=referred_by,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def ban_user(telegram_id: int) -> bool:
    """Ban a user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_banned = True
            await session.commit()
            return True
        return False


async def unban_user(telegram_id: int) -> bool:
    """Unban a user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.is_banned = False
            await session.commit()
            return True
        return False


async def get_all_users(limit: int = 100, offset: int = 0) -> List[User]:
    """Get all users with pagination."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).order_by(desc(User.reg_date)).limit(limit).offset(offset)
        )
        return result.scalars().all()


async def get_users_count() -> int:
    """Get total users count."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar()


# ─── CRUD Operations: Products ────────────────────────────────────────────────

async def get_all_products_db() -> List[Product]:
    """Get all active products."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.is_active == True).order_by(Product.category, Product.id)
        )
        return result.scalars().all()


async def get_product_by_key(product_key: str) -> Optional[Product]:
    """Get product by its unique key."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.product_key == product_key)
        )
        return result.scalar_one_or_none()


async def get_product_by_id(product_id: int) -> Optional[Product]:
    """Get product by database ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()


async def update_product_price(product_key: str, new_final_price: float) -> bool:
    """Update product final price."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.product_key == product_key)
        )
        product = result.scalar_one_or_none()
        if product:
            product.final_price = new_final_price
            await session.commit()
            return True
        return False


async def toggle_product_status(product_key: str) -> bool:
    """Toggle product active status."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(Product.product_key == product_key)
        )
        product = result.scalar_one_or_none()
        if product:
            product.is_active = not product.is_active
            await session.commit()
            return product.is_active
        return False


# ─── CRUD Operations: Orders ──────────────────────────────────────────────────

async def create_order(
    telegram_id: int,
    product_id: int,
    price_paid: float,
    currency: str = "USD",
) -> Optional[Order]:
    """Create a new order."""
    async with AsyncSessionLocal() as session:
        # Generate unique order ID
        import uuid
        order_id = f"APP{uuid.uuid4().hex[:8].upper()}"

        order = Order(
            order_id=order_id,
            user_id=telegram_id,
            product_id=product_id,
            price_paid=price_paid,
            currency=currency,
            status=Order.STATUS_PENDING,
        )
        session.add(order)

        # Update user orders count
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.orders_count += 1

        await session.commit()
        await session.refresh(order)
        return order


async def get_order(order_id: str) -> Optional[Order]:
    """Get order by order ID string."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()


async def get_user_orders(telegram_id: int, limit: int = 20) -> List[Order]:
    """Get user's orders."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.user_id == telegram_id)
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        return result.scalars().all()


async def update_order_status(
    order_id: str,
    status: str,
    apple_id: Optional[str] = None,
    apple_password: Optional[str] = None,
    source_response: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    """Update order status and optional credentials."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return False

        order.status = status

        if apple_id:
            order.apple_id = apple_id
        if apple_password:
            order.apple_password = apple_password
        if source_response:
            order.source_order_response = source_response
        if error_message:
            order.error_message = error_message

        if status == Order.STATUS_PAID:
            order.paid_at = datetime.datetime.utcnow()
        elif status == Order.STATUS_COMPLETED:
            order.completed_at = datetime.datetime.utcnow()

        await session.commit()
        return True


async def deliver_order(order_id: str, apple_id: str, password: str) -> bool:
    """Mark order as completed with credentials delivery."""
    success = await update_order_status(
        order_id=order_id,
        status=Order.STATUS_COMPLETED,
        apple_id=apple_id,
        apple_password=password,
    )
    if success:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Order).where(Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                # Update user total spent
                user_result = await session.execute(
                    select(User).where(User.telegram_id == order.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user.total_spent += order.price_paid
                await session.commit()
    return success


async def refund_order(order_id: str) -> bool:
    """Refund an order."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        if order and order.status != Order.STATUS_REFUNDED:
            order.status = Order.STATUS_REFUNDED
            order.refunded_at = datetime.datetime.utcnow()
            await session.commit()
            return True
        return False


async def get_orders_count() -> int:
    """Get total orders count."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Order.id)))
        return result.scalar()


async def get_today_orders_count() -> int:
    """Get today's orders count."""
    async with AsyncSessionLocal() as session:
        today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(Order.id)).where(Order.created_at >= today)
        )
        return result.scalar()


async def get_total_revenue() -> float:
    """Get total revenue from completed orders."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.sum(Order.price_paid)).where(
                Order.status == Order.STATUS_COMPLETED
            )
        )
        return result.scalar() or 0.0


async def get_recent_orders(limit: int = 20) -> List[Order]:
    """Get recent orders for admin panel."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order)
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        return result.scalars().all()


# ─── Admin Logs ───────────────────────────────────────────────────────────────

async def log_admin_action(
    admin_id: int,
    action: str,
    target_user_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    """Log admin action."""
    async with AsyncSessionLocal() as session:
        log = AdminLog(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            details=details,
        )
        session.add(log)
        await session.commit()


# ─── Statistics ───────────────────────────────────────────────────────────────

async def get_full_stats() -> Dict[str, Any]:
    """Get complete store statistics for admin panel."""
    return {
        "total_users": await get_users_count(),
        "total_orders": await get_orders_count(),
        "today_orders": await get_today_orders_count(),
        "total_revenue": await get_total_revenue(),
        "pending_orders": await get_orders_by_status_count(Order.STATUS_PENDING),
        "processing_orders": await get_orders_by_status_count(Order.STATUS_PROCESSING),
        "completed_orders": await get_orders_by_status_count(Order.STATUS_COMPLETED),
        "failed_orders": await get_orders_by_status_count(Order.STATUS_FAILED),
    }


async def get_orders_by_status_count(status: str) -> int:
    """Get count of orders by status."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Order.id)).where(Order.status == status)
        )
        return result.scalar()
