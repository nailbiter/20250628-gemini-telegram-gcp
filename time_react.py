# time_react.py
import os
import logging
from flask import Flask, request
from telegram import Bot

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Initialize the bot once when the service starts
# This is more efficient than creating it on every request
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN:
    logging.warning(
        "TELEGRAM_TOKEN environment variable not set. Bot functionality will be disabled."
    )
    bot = None
else:
    bot = Bot(token=TELEGRAM_TOKEN)


@app.route("/", methods=["POST"])
def index():
    """
    This endpoint will be called by the Telegram webhook.
    """
    # We can inspect the incoming data from Telegram later.
    # update = request.get_json()
    # logging.info(f"Received update: {update}")

    if bot and CHAT_ID:
        try:
            logging.info(f"Sending 'hi' to chat ID: {CHAT_ID}")
            bot.send_message(chat_id=CHAT_ID, text="hi")
        except Exception as e:
            logging.error(f"Failed to send message: {e}")
            return "Error sending message", 500
    else:
        logging.error("TELEGRAM_TOKEN or CHAT_ID not configured.")
        return "Bot not configured", 500

    return "OK", 200


if __name__ == "__main__":
    # This part is for local testing if needed.
    # Cloud Run will use a production Gunicorn server.
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
