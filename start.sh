#!/bin/bash
# Appify Store Bot - Quick Start Script
# ======================================

echo "╔══════════════════════════════════════════════╗"
echo "║       Appify Store Bot - Launcher            ║"
echo "║         متجر آبيفاي - تشغيل البوت             ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

echo "✅ Python version: $(python3 --version)"

# Check/create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "📝 Creating from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env with your credentials before running again."
    echo ""
    exit 1
fi

# Start bot
echo ""
echo "🚀 Starting Appify Store Bot..."
echo "═══════════════════════════════════════════════"
python3 main.py
