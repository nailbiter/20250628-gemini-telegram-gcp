import os
import logging
from fastapi import FastAPI, Request, Response
import telegram
from telegram.request import HTTPXRequest
import google.generativeai as genai

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Use the GEMINI_MODEL environment variable, with a fallback to the latest flash model
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")

# --- Initialization ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize FastAPI app
app = FastAPI()

bot = None
if TELEGRAM_BOT_TOKEN:
    # Configure a custom request object for the bot
    # Use HTTP/1.1 and a larger connection pool for better stability in serverless environments.
    request_handler = HTTPXRequest(http_version="1.1", connection_pool_size=10)
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request_handler)
else:
    logging.warning("TELEGRAM_BOT_TOKEN environment variable not set.")

gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # --- FIX: Use the configured model name ---
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logging.info(f"Initialized Gemini model: {GEMINI_MODEL_NAME}")
    except Exception as e:
        logging.error(f"Failed to configure Gemini: {e}")
else:
    logging.warning("GEMINI_API_KEY environment variable not set.")


# --- Webhook Endpoint ---
@app.post("/")
async def telegram_webhook(request: Request) -> str:
    """
    This function handles incoming updates from the Telegram webhook.
    """
    logging.info(f"request: {request}")

    if not bot or not gemini_model:
        logging.error("Service is not configured correctly. Missing API keys.")
        return Response(content="Service not configured", status_code=500)

    try:
        update_json = await request.json()
        logging.info(f"request_json: {update_json}")
        update = telegram.Update.de_json(update_json, bot)
    except Exception as e:
        logging.error(f"Could not decode Telegram update: {e}")
        return Response(content="Invalid request", status_code=400)

    if not update.message or not update.message.text:
        logging.info("Received an update without a text message.")
        return "OK"

    chat_id = update.message.chat.id
    logging.info(f"chat_id={chat_id}")
    should_be_chat_id = os.environ.get("SHOULD_BE_CHAT_ID")
    logging.info(f"should be chat_id={should_be_chat_id}")
    assert should_be_chat_id is None or str(should_be_chat_id) == str(chat_id)
    user_text = update.message.text
    logging.info(f"Received message from chat_id {chat_id}: '{user_text}'")

    try:
        logging.info(f"Generating content with Gemini model '{GEMINI_MODEL_NAME}'...")
        response = gemini_model.generate_content(user_text)
        gemini_response_text = response.text

        await bot.send_message(chat_id=chat_id, text=gemini_response_text)
        logging.info(f"Successfully sent Gemini response to chat_id {chat_id}")

    except Exception as e:
        logging.error(
            f"Error processing with Gemini or sending reply: {e}", exc_info=True
        )
        # We don't try to send another message on failure here, to avoid cascading errors.

    # Always return a 200 OK to Telegram to acknowledge receipt of the update
    return "OK"


# For local development: uvicorn app:app --reload --host 0.0.0.0 --port 8080
