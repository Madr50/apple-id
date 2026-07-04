# Appify Store Bot | متجر آبيفاي

A complete, enterprise-grade Telegram bot for automated Apple ID & iOS game dropshipping, targeting the Arab market. Built with Python, Aiogram 3.x, Pyrogram, and SQLAlchemy.

## Features

- **Professional Arabic UI** - Native Arabic interface with elegant design
- **Dynamic Image Branding** - Pillow-based watermarking and product image generation
- **Full Dropshipping Automation** - Pyrogram userbot bridges with @SourceBot
- **Complete Product Catalog** - Games, Apps, and Apple IDs with dynamic pricing
- **Order Management** - Full lifecycle from purchase to delivery
- **Referral System** - Built-in referral tracking with bonuses
- **Admin Panel** - Statistics, user management, broadcasts, order control
- **Channel Integration** - Generate formatted posts with deep links
- **Flask Keep-Alive** - Render.com compatible with health checks
- **Database Ready** - SQLite now, PostgreSQL migration-ready

## Architecture

```
appify-bot/
├── main.py              # Async entry point (Aiogram + Pyrogram + Flask)
├── config.py            # Centralized configuration & text templates
├── database.py          # SQLAlchemy async models & CRUD operations
├── server.py            # Flask keep-alive for Render.com
├── requirements.txt     # Python dependencies
├── Procfile            # Render.com deployment
├── .env.example        # Environment variable template
├── frontend/           # Aiogram handlers & UI
│   ├── __init__.py
│   ├── keyboards.py    # Reply & Inline keyboard builders
│   └── handlers.py     # All message & callback handlers
├── backend/            # Pyrogram automation
│   ├── __init__.py
│   └── sourcebot_bridge.py  # SourceBot automation & parsing
├── utils/              # Utilities
│   ├── __init__.py
│   └── image_watermark.py   # Pillow image processing
└── assets/             # Logo and branding assets
```

## Setup Instructions

### 1. Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
- `BOT_TOKEN` - Your Telegram bot token
- `ADMIN_IDS` - Your Telegram user ID
- `PYROGRAM_API_ID` - From my.telegram.org
- `PYROGRAM_API_HASH` - From my.telegram.org
- `PYROGRAM_SESSION_STRING` - Generated session string

### 2. Generate Pyrogram Session String (Headless)

```bash
python -c "
from pyrogram import Client
import asyncio

async def main():
    async with Client(
        'session_generator',
        api_id=YOUR_API_ID,
        api_hash='YOUR_API_HASH',
        in_memory=True
    ) as app:
        print('Session string:')
        print(await app.export_session_string())

asyncio.run(main())
"
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python main.py
```

### 5. Deploy to Render.com

1. Push code to GitHub
2. Connect repository to Render
3. Set environment variables in Render dashboard
4. Deploy with `Procfile`

## Bot Menu

- **🛒 المنتجات** - Browse products by category
- **📋 قائمة الأسعار** - Full price list
- **ℹ️ معلومات** - Bot information
- **📝 القوانين** - Terms of use
- **👤 حسابي** - User profile & referral
- **🛠 الدعم الفني** - Support

## Admin Commands

- **📊 الإحصائيات** - Full store statistics
- **👥 المستخدمين** - User management
- **📦 إدارة الطلبات** - Order management
- **📢 إشعار عام** - Broadcast to all users
- **🚫 حظر مستخدم** - Ban users
- **⚙️ إعدادات المتجر** - Store settings

## License

Private - For Appify Store use only.
