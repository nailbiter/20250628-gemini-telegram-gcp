# time_react.py (now with dispatcher logic)
import os
import logging
import requests  # Make sure 'requests' is in your requirements.txt
import telegram
from fastapi import FastAPI, Request, Response
from pymongo import MongoClient
from datetime import datetime
import typing
import common  # Assuming your common module is accessible

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
CHAT_ID = os.environ.get("CHAT_ID")
# --- NEW: URL for the private service that will handle other commands ---
ACTOR_SERVER_URL = os.environ.get("ACTOR_SERVER_URL")

# --- Initialization ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
app = FastAPI()

# Initialize Telegram Bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
# Initialize MongoDB Client
mongo_client = MongoClient(MONGO_URL) if MONGO_URL else None


# --- NEW: Dispatcher function ---
def get_id_token(audience_url: str) -> typing.Optional[str]:
    """Fetches a Google-signed ID token for the given audience URL."""
    token_url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience_url}"
    token_headers = {"Metadata-Flavor": "Google"}
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
            return "OK"  # Acknowledge the request even if we can't process it

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
                {
                    "$set": {
                        "category": time_category,
                        "_last_modification_date": common.to_utc_datetime(),
                    }
                },
            )
            await bot.delete_message(chat_id, message_id)
            await bot.send_message(chat_id=chat_id, text=f"Got: {time_category}")
        else:
            logging.warning(
                f"Ignoring callback for message_id {message_id} (already processed or not found)."
            )

    # --- NEW: Else, dispatch it to a generic actor server ---
    # 2. For any other message type, forward it to the private actor server.
    else:
        await process_message(update_json)

    return "OK"


# def process_message(update_json: dict) -> None:
#     if not ACTOR_SERVER_URL:
#         logging.info(
#             "Received an unhandled update, but no ACTOR_SERVER_URL is configured. Doing nothing."
#         )
#         return "OK"

#     logging.info(f"Dispatching update to actor server at {ACTOR_SERVER_URL}...")
#     id_token = get_id_token(ACTOR_SERVER_URL)
#     if not id_token:
#         return "OK"  # Fail silently to Telegram, but log the error.

#     headers = {"Authorization": f"Bearer {id_token}"}
#     try:
#         # Forward the entire Telegram update payload
#         requests.post(ACTOR_SERVER_URL, headers=headers, json=update_json)
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Error calling actor server: {e}")
# import logging
# import requests
# import typing
# import telegram  # Assuming telegram library is imported elsewhere

# Assume mongo_client, bot, get_id_token are defined globally or passed as arguments
# Assume get_help() function will be provided elsewhere


async def handle_no_match(update_json: dict) -> None:
    """Sends a 'no match' message back to the user."""
    try:
        chat_id = update_json.get("message", {}).get("chat", {}).get("id")
        if chat_id and bot:
            await bot.send_message(
                chat_id=chat_id, text="Sorry, I don't understand that command."
            )
        else:
            logging.warning(
                "Could not send 'no match' message: chat_id or bot not available."
            )
    except Exception as e:
        logging.error(f"Error in handle_no_match: {e}", exc_info=True)


async def process_message(update_json: dict) -> None:
    """
    Processes incoming messages, matching prefixes from MongoDB to dispatch
    to the appropriate Cloud Run service.
    """
    if not mongo_client:
        logging.error("Mongo client not configured. Cannot process message.")
        return

    # Extract message details safely
    message = update_json.get("message")

    if not message:
        logging.info("Update does not contain a message object.")
        return

    message_text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    if not message_text or not chat_id:
        logging.info("Message object is missing text or chat ID.")
        return

    message_text = message_text.strip()
    logging.debug(f"message: {message_text}")

    # 2. Fetch routing rules from MongoDB
    try:
        hooks_coll = mongo_client["logistics"]["cloud-run-hooks-gcp"]
        # Fetch all hooks at once
        hooks = list(hooks_coll.find({}, {"prefix": 1, "url": 1}))
        if not hooks:
            logging.warning("No routing hooks found in MongoDB.")
            await handle_no_match(update_json)
            return
    except Exception as e:
        logging.error(f"Failed to fetch routing hooks from MongoDB: {e}", exc_info=True)
        # Optionally send an error message back to the user
        # await bot.send_message(chat_id=chat_id, text="Error accessing routing configuration.")
        return

    # 1. Special case: /help command
    if message_text.strip() == "/help":
        try:
            # --- User will provide this function ---
            help_text = get_help(hooks)
            # -------------------------------------
            if bot:
                await bot.send_message(chat_id=chat_id, text=help_text)
        except NameError:
            logging.error("get_help() function is not defined.")
            if bot:
                await bot.send_message(
                    chat_id=chat_id, text="Help information is currently unavailable."
                )
        except Exception as e:
            logging.error(f"Error handling /help command: {e}", exc_info=True)
        return  # Stop further processing

    # 3. Find the longest matching prefix
    best_match_hook = None
    longest_match_len = -1

    for hook in hooks:
        prefix = hook.get("prefix")
        if prefix and message_text.startswith(prefix):
            if len(prefix) > longest_match_len:
                longest_match_len = len(prefix)
                best_match_hook = hook

    # 4. Dispatch or handle no match
    if best_match_hook:
        target_url = best_match_hook.get("url")
        if not target_url:
            logging.error(
                f"Matched hook for prefix '{best_match_hook.get('prefix')}' has no URL."
            )
            await handle_no_match(update_json)  # Fallback if URL is missing
            return

        logging.info(
            f"Dispatching message starting with '{best_match_hook.get('prefix')}' to {target_url}..."
        )
        id_token = get_id_token(target_url)
        if not id_token:
            # Error already logged by get_id_token
            # Optionally send an error message back to the user
            # await bot.send_message(chat_id=chat_id, text="Error obtaining authentication token.")
            return

        headers = {"Authorization": f"Bearer {id_token}"}
        try:
            # Forward the entire original Telegram update payload
            response = requests.post(target_url, headers=headers, json=update_json)
            response.raise_for_status()  # Check for HTTP errors from the target service
            logging.info(
                f"Successfully dispatched to {target_url}. Status: {response.status_code}"
            )
        except requests.exceptions.RequestException as e:
            logging.error(f"Error calling target service {target_url}: {e}")
            # Optionally send an error message back to the user
            # await bot.send_message(chat_id=chat_id, text="There was an error processing your command.")
    else:
        # No prefix matched
        logging.info(f"No matching prefix found for message: '{message_text}'")
        await handle_no_match(update_json)


def get_help(hooks: list[dict]) -> str:
    ## FIXME: change to DEBUG once stable
    logging.info(hooks)
    return "help stub"


# --- Ensure the main webhook calls the async function correctly ---
# You need to update the main telegram_webhook function like this:

# @app.post("/")
# async def telegram_webhook(request: Request):
#     # ... (existing code to decode update) ...
#
#     if update.callback_query:
#         # ... (existing callback handling logic) ...
#     else:
#         # --- CHANGED: Await the async function ---
#         await process_message(update_json)
#
#     return "OK"
