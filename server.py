# server.py
# PRODUCTION-READY Telegram Signal Server ⚡ (FIXED SYMBOL MATCH)

import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import time
import os
from typing import Dict

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================= FASTAPI SETUP =================
app = FastAPI(title="Telegram Signal Server ⚡")

signals: Dict[str, dict] = {}

# ================= SYMBOL NORMALIZER =================
def normalize_symbol(symbol: str) -> str:
    symbol = symbol.upper()

    for suffix in ["M", ".M", "C", ".C", "S", ".S", "PRO", ".PRO"]:
        if symbol.endswith(suffix):
            symbol = symbol.replace(suffix, "")

    return symbol

# ================= SIGNAL MODEL =================
class Signal(BaseModel):
    symbol: str
    signal: str
    sl: float = 0
    tp: float = 0

# ================= API ROUTES =================

@app.get("/")
def home():
    return {
        "status": "running",
        "message": "Telegram Signal Server is LIVE 🚀",
        "active_symbols": list(signals.keys())
    }

@app.get("/signal")
def get_signal(symbol: str):
    symbol = normalize_symbol(symbol)

    if symbol not in signals:
        return {
            "symbol": symbol,
            "signal": "none",
            "sl": 0,
            "tp": 0,
            "id": 0
        }

    return signals[symbol]

@app.get("/signals")
def get_all_signals():
    return signals

@app.post("/set")
def set_signal(signal: Signal):
    symbol = normalize_symbol(signal.symbol)

    signals[symbol] = {
        "symbol": symbol,
        "signal": signal.signal.lower(),
        "sl": signal.sl,
        "tp": signal.tp,
        "id": int(time.time())
    }

    print(f"📡 API Signal Set: {signals[symbol]}")
    return signals[symbol]

# ================= TELEGRAM BOT =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables")

raw_users = os.getenv("AUTHORIZED_USERS", "")

AUTHORIZED_USERS = (
    [int(x) for x in raw_users.split(",") if x.strip().isdigit()]
    if raw_users else []
)

telegram_app = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Unauthorized user")
        return

    text = update.message.text.upper().strip()
    parts = text.split()

    if len(parts) < 2:
        await update.message.reply_text("❌ Format: BUY XAUUSD SL=2300 TP=2400")
        return

    action = parts[0]
    raw_symbol = parts[1]

    symbol = normalize_symbol(raw_symbol)

    sl = 0
    tp = 0

    for part in parts[2:]:
        try:
            if "SL=" in part:
                sl = float(part.split("=")[1])
            elif "TP=" in part:
                tp = float(part.split("=")[1])
        except:
            pass

    signals[symbol] = {
        "symbol": symbol,
        "signal": action.lower(),
        "sl": sl,
        "tp": tp,
        "id": int(time.time())
    }

    print(f"📡 Telegram Signal: {signals[symbol]}")

    await update.message.reply_text(f"✅ {action} {symbol} received")

# ================= START TELEGRAM BOT =================

async def start_telegram():
    global telegram_app

    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()

@app.on_event("startup")
async def startup():
    asyncio.create_task(start_telegram())

# ================= MAIN =================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    print(f"⚡ Server running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
