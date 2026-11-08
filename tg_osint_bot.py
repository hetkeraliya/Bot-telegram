# lang: python | file: tg_osint_bot.py
import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_URL   = "https://aerosend.bond/tgtonum.php"
API_KEY   = "crazy"
TRIES     = 5
DELAY     = 1.5
TIMEOUT   = 10


def search(tg_id: str) -> dict | None:
    for attempt in range(1, TRIES + 1):
        try:
            resp = requests.get(
                API_URL,
                params={"key": API_KEY, "num": tg_id},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return data
        except Exception:
            pass
        if attempt < TRIES:
            time.sleep(DELAY)
    return None


def fmt(data: dict | None, tg_id: str) -> str:
    if not data:
        return f"✗ No result for `{tg_id}` — unlinked or invalid."
    return "\n".join([
        "🔍 *Telegram OSINT Result*",
        "",
        f"• *TG ID:* `{data.get('tg_id', tg_id)}`",
        f"• *Mobile:* `{data.get('mobile', 'N/A')}`",
        f"• *Country Code:* `{data.get('country_code', 'N/A')}`",
        f"• *Country:* `{data.get('country', 'N/A')}`",
    ])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🔧 *TG OSINT Bot*\n\nSend me a numeric Telegram user ID and I'll resolve the linked number.\n\nExample: `123456789`",
        parse_mode="Markdown",
    )


async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text(
            "✗ Send a numeric ID only.\nExample: `123456789`",
            parse_mode="Markdown",
        )
        return
    msg = await update.message.reply_text("⏳ Querying…")
    result = search(text)
    await msg.edit_text(fmt(result, text), parse_mode="Markdown")


class Health(BaseHTTPRequestHandler):
    def do_GET(self):           # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def run_health(port: int = 8080) -> None:
    HTTPServer(("0.0.0.0", port), Health).serve_forever()


async def bot_main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("bot polling…")
    async with app:
        await app.start()
        await app.updater.start_polling()
        # run forever until killed
        await asyncio.Event().wait()


def main() -> None:
    # health thread
    t = threading.Thread(target=run_health, daemon=True)
    t.start()
    print("health server up on :8080")

    # explicit event loop — fixes Python 3.14 regression
    asyncio.run(bot_main())


if __name__ == "__main__":
    main()
