import os
import logging
import asyncio
from flask import Flask, request
import telegram
import google.generativeai as genai
from a2wsgi import WSGIMiddleware  # <--- Import the translator
from telegram.request import HTTPXRequest

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Initialization ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize the core Flask app
flask_app = Flask(__name__)

# This is the app Gunicorn will talk to now. It wraps the Flask app for ASGI compatibility.
app = WSGIMiddleware(flask_app)  # <--- Wrap the app here

bot = None
if TELEGRAM_BOT_TOKEN:
    # Initialize the Bot with a higher connection pool size for async
    request_handler = HTTPXRequest(
        http_version="1.1", connection_pool_size=20  # Increase pool size from default
    )
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request_handler)
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
else:
    logging.warning("TELEGRAM_BOT_TOKEN environment variable not set.")

gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")
        )
    except Exception as e:
        logging.error(f"Failed to configure Gemini: {e}")
else:
    logging.warning("GEMINI_API_KEY environment variable not set.")


# --- Webhook Endpoint (Now Asynchronous) ---
@flask_app.route("/", methods=["POST"])
async def telegram_webhook():  # <--- Changed to `async def`
    """
    This function handles incoming updates from the Telegram webhook asynchronously.
    """
    if not bot or not gemini_model:
        logging.error("Service is not configured correctly. Missing API keys.")
        return "Service not configured", 500

    try:
        update_json = request.get_json(force=True)
        update = telegram.Update.de_json(update_json, bot)
    except Exception as e:
        logging.error(f"Could not decode Telegram update: {e}")
        return "Invalid request", 400

    if not update.message or not update.message.text:
        logging.info("Received an update without a text message.")
        return "OK", 200

    chat_id = update.message.chat.id
    user_text = update.message.text
    logging.info(f"Received message from chat_id {chat_id}: '{user_text}'")

    try:
        logging.info("Generating content with Gemini...")
        response = gemini_model.generate_content(user_text)
        gemini_response_text = response.text

        # Use `await` to correctly call the asynchronous send_message function
        await bot.send_message(
            chat_id=chat_id, text=gemini_response_text
        )  # <--- Added `await`
        logging.info(f"Successfully sent Gemini response to chat_id {chat_id}")

    except Exception as e:
        logging.error(
            f"Error processing with Gemini or sending reply: {e}", exc_info=True
        )
        try:
            # Also await the error message call
            await bot.send_message(
                chat_id=chat_id,
                text="Sorry, I encountered an error. Please try again later.",
            )  # <--- Added `await`
        except Exception as telegram_e:
            logging.error(f"Failed to send error message to Telegram: {telegram_e}")

    return "OK", 200


# Local development runner (not used in Cloud Run)
if __name__ == "__main__":
    # Note: Running async Flask apps directly is complex.
    # It's better to test using a proper ASGI server like `uvicorn`.
    # Example: uvicorn app:app --host 0.0.0.0 --port 8080
    print(
        "To run locally, use an ASGI server like uvicorn: 'uvicorn app:app --host 0.0.0.0 --port 8080'"
    )
