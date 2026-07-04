"""
Appify Store Bot - Flask Keep-Alive Server
==========================================
Lightweight Flask server for Render.com health checks.
Runs concurrently with the Telegram bot via asyncio.
"""

import asyncio
import threading
import time
from flask import Flask, jsonify

from config import FLASK_HOST, FLASK_PORT
from database import get_full_stats

# ─── Flask App ────────────────────────────────────────────────────────────────

app = Flask(__name__)

# Bot status tracking
bot_status = {
    "status": "initializing",
    "started_at": time.time(),
    "last_ping": time.time(),
    "version": "1.0.0",
    "name": "Appify Store Bot",
}


@app.route("/")
def index():
    """Root endpoint - bot status page."""
    uptime = time.time() - bot_status["started_at"]
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)

    return jsonify({
        "name": bot_status["name"],
        "version": bot_status["version"],
        "status": bot_status["status"],
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "last_ping": bot_status["last_ping"],
    })


@app.route("/health")
def health_check():
    """Health check endpoint for Render.com."""
    return jsonify({
        "status": "healthy" if bot_status["status"] == "running" else "degraded",
        "timestamp": time.time(),
    }), 200


@app.route("/stats")
def stats():
    """Public stats endpoint."""
    try:
        # We can't use async here directly in Flask, return basic stats
        return jsonify({
            "status": "ok",
            "bot_status": bot_status["status"],
            "uptime_seconds": time.time() - bot_status["started_at"],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def update_status(status: str):
    """Update bot status from the main process."""
    bot_status["status"] = status
    bot_status["last_ping"] = time.time()


def ping():
    """Update last ping timestamp."""
    bot_status["last_ping"] = time.time()


# ─── Async Runner ─────────────────────────────────────────────────────────────

def run_flask_app():
    """Run Flask app in a separate thread."""
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


async def start_keepalive_server():
    """Start the Flask keep-alive server in a background thread."""
    loop = asyncio.get_event_loop()

    # Run Flask in executor (background thread)
    await loop.run_in_executor(None, run_flask_app)
