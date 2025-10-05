import os
import logging
from fastapi import FastAPI, Request, Response
import telegram
from telegram.request import HTTPXRequest
import typing
import common
from pymongo import MongoClient
from datetime import datetime, timedelta

# import google.generativeai as genai

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# # Use the GEMINI_MODEL environment variable, with a fallback to the latest flash model
# GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")

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

# gemini_model = None
# if GEMINI_API_KEY:
#     try:
#         genai.configure(api_key=GEMINI_API_KEY)
#         # --- FIX: Use the configured model name ---
#         gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
#         logging.info(f"Initialized Gemini model: {GEMINI_MODEL_NAME}")
#     except Exception as e:
#         logging.error(f"Failed to configure Gemini: {e}")
# else:
#     logging.warning("GEMINI_API_KEY environment variable not set.")
gemini_model = 1


async def time_react(request: Request, bot: telegram.Bot) -> typing.Any:
    try:
        update_json = await request.json()
        logging.info(f"request_json: {update_json}")
        update = telegram.Update.de_json(update_json, bot)
    except Exception as e:
        logging.error(f"Could not decode Telegram update: {e}")
        return Response(content="Invalid request", status_code=400)

    # if not update.message or not update.message.text:
    #     logging.info("Received an update without a text message.")
    #     return "OK"
    if not update.message:
        logging.info("Received an update without a message.")
        return "OK"

    chat_id = update.message.chat.id
    logging.info(f"chat_id={chat_id}")
    should_be_chat_id = os.environ.get("CHAT_ID")
    logging.info(f"should be chat_id={should_be_chat_id}")
    if not (should_be_chat_id is None or str(should_be_chat_id) == str(chat_id)):
        logging.info(f"{should_be_chat_id}!={chat_id}")
        return "OK"

    message_id = update.callback_query.message.message_id
    data = int(update.callback_query.data)

    mongo_client = MongoClient(os.environ["MONGO_URL"])
    mongo_coll = self._mongo_client["logistics"]["alex.time"]
    msg = mongo_coll.find_one({"telegram_message_id": message_id})
    if msg is None:
        logging.error(f"could not find keyboard for message_id={message_id} ==> ignore")
        return "OK"
    elif msg["category"] is not None:
        logging.warning(
            f"already have saved state \"{msg['category']}\" for message_id={message_id} ==> ignore"
        )
        return "OK"
    time_category = common.TIME_CATS[data]
    logging.info(time_category)
    # FIXME: use `sanitize_mongo` of `heartbeat_time`
    mongo_coll.update_one(
        {"telegram_message_id": message_id},
        {
            "$set": {
                "category": time_category,
                "_last_modification_date": _common.to_utc_datetime(),
            }
        },
    )

    try:
        _now = datetime.now()
        await bot.delete_message(chat_id, message_id)
        await bot.send_message(
            chat_id=chat_id,
            text=f"""
    got: {time_category}
    remaining time to live: {str(datetime(1991+70,12,24)-_now)} 
        """.strip(),
        )

    except Exception as e:
        logging.error(
            f"Error processing with Gemini or sending reply: {e}", exc_info=True
        )
        # We don't try to send another message on failure here, to avoid cascading errors.

    # # Always return a 200 OK to Telegram to acknowledge receipt of the update
    return "OK"


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
    res = await time_react(request, bot)
    return res


# For local development: uvicorn app:app --reload --host 0.0.0.0 --port 8080


# # time_react.py
# import os
# import logging
# from flask import Flask, request
# from telegram import Bot

# # Configure logging
# logging.basicConfig(level=logging.INFO)

# app = Flask(__name__)

# # Initialize the bot once when the service starts
# # This is more efficient than creating it on every request
# TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# CHAT_ID = os.environ.get("CHAT_ID")

# if not TELEGRAM_TOKEN:
#     logging.warning(
#         "TELEGRAM_TOKEN environment variable not set. Bot functionality will be disabled."
#     )
#     bot = None
# else:
#     bot = Bot(token=TELEGRAM_TOKEN)


# @app.route("/", methods=["POST"])
# def index():
#     """
#     This endpoint will be called by the Telegram webhook.
#     """
#     # We can inspect the incoming data from Telegram later.
#     # update = request.get_json()
#     # logging.info(f"Received update: {update}")

#     if bot and CHAT_ID:
#         try:
#             logging.info(f"Sending 'hi' to chat ID: {CHAT_ID}")
#             bot.send_message(chat_id=CHAT_ID, text="hi")
#         except Exception as e:
#             logging.error(f"Failed to send message: {e}")
#             return "Error sending message", 500
#     else:
#         logging.error("TELEGRAM_TOKEN or CHAT_ID not configured.")
#         return "Bot not configured", 500

#     return "OK", 200


# if __name__ == "__main__":
#     # This part is for local testing if needed.
#     # Cloud Run will use a production Gunicorn server.
#     port = int(os.environ.get("PORT", 8080))
#     app.run(host="0.0.0.0", port=port)
