# time_react.py (now with dispatcher logic)
import os
import logging
import requests # Make sure 'requests' is in your requirements.txt
import telegram
from fastapi import FastAPI, Request, Response
from pymongo import MongoClient
from datetime import datetime
import typing
import common # Assuming your common module is accessible

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
CHAT_ID = os.environ.get("CHAT_ID")
# --- NEW: URL for the private service that will handle other commands ---
ACTOR_SERVER_URL = os.environ.get('ACTOR_SERVER_URL')

# --- Initialization ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = FastAPI()

# Initialize Telegram Bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
# Initialize MongoDB Client
mongo_client = MongoClient(MONGO_URL) if MONGO_URL else None

# --- NEW: Dispatcher function ---
def get_id_token(audience_url: str) -> typing.Optional[str]:
    """Fetches a Google-signed ID token for the given audience URL."""
    token_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience_url}'
    token_headers = {'Metadata-Flavor': 'Google'}
    try:
        token_response = requests.get(token_url, headers=token_headers)
        token_response.raise_for_status()
        return token_response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch ID token: {e}")
        return None

# --- Webhook Endpoint ---
@app.post("/")
async def telegram_webhook(request: Request):
    """
    This function handles all incoming updates from the Telegram webhook.
    """
    if not bot:
        logging.error("Service is not configured correctly. Missing TELEGRAM_TOKEN.")
        return Response(content="Service not configured", status_code=500)

    try:
        update_json = await request.json()
        logging.info(f"Received update: {update_json}")
        update = telegram.Update.de_json(update_json, bot)
    except Exception as e:
        logging.error(f"Could not decode Telegram update: {e}")
        return Response(content="Invalid request", status_code=400)

    # --- ROUTING LOGIC ---

    # 1. If it's a callback query (button press), handle it here.
    if update.callback_query:
        if not mongo_client:
            logging.error("Mongo client not configured, cannot process callback.")
            return "OK" # Acknowledge the request even if we can't process it

        chat_id = update.callback_query.message.chat.id
        # Filter to only respond to your chat
        if CHAT_ID and str(chat_id) != str(CHAT_ID):
            logging.warning(f"Callback from unauthorized chat ID: {chat_id}")
            return "OK"
        
        message_id = update.callback_query.message.message_id
        data = int(update.callback_query.data)
        
        time_coll = mongo_client["logistics"]["alex.time"]
        msg = time_coll.find_one({"telegram_message_id": message_id})

        if msg and msg.get("category") is None:
            time_category = common.TIME_CATS[data]
            time_coll.update_one(
                {"telegram_message_id": message_id},
                {"$set": {"category": time_category, "_last_modification_date": common.to_utc_datetime()}}
            )
            await bot.delete_message(chat_id, message_id)
            await bot.send_message(chat_id=chat_id, text=f"Got: {time_category}")
        else:
            logging.warning(f"Ignoring callback for message_id {message_id} (already processed or not found).")
    
    # --- NEW: Else, dispatch it to a generic actor server ---
    # 2. For any other message type, forward it to the private actor server.
    else:
        if not ACTOR_SERVER_URL:
            logging.info("Received an unhandled update, but no ACTOR_SERVER_URL is configured. Doing nothing.")
            return "OK"

        logging.info(f"Dispatching update to actor server at {ACTOR_SERVER_URL}...")
        id_token = get_id_token(ACTOR_SERVER_URL)
        if not id_token:
            return "OK" # Fail silently to Telegram, but log the error.
        
        headers = {'Authorization': f'Bearer {id_token}'}
        try:
            # Forward the entire Telegram update payload
            requests.post(ACTOR_SERVER_URL, headers=headers, json=update_json)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error calling actor server: {e}")

    return "OK"