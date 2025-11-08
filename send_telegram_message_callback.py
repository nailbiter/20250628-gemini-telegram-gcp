# actor_server.py
import os
import logging
import asyncio
from fastapi import FastAPI, Request, Response
from _actor import add_money, add_note, sleepstart, sleepend
import functools
from pymongo import MongoClient
from common.telegram_help_utils import TelegramBotWrapper

# --- Initialization ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
app = FastAPI()

# TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# bot = telegram.Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

MONGO_URL = os.environ.get("MONGO_URL")
mongo_client = MongoClient(MONGO_URL) if MONGO_URL else None

COMMANDS = {
    "/money": add_money,
    "/note": add_note,
    "/sleepstart": sleepstart,
    "/sleepend": sleepend,
}


# --- Webhook Endpoint ---
@app.post("/")
async def handle_callback(request: Request):
    """
    Handles a callback_query payload forwarded from the dispatcher
    and echoes the original message text.
    """
    try:
        payload = await request.json()
    except Exception:
        return Response(content="Invalid JSON payload", status_code=400)

    my_bot = TelegramBotWrapper(
        {"pyas2": "PYAS2_TELEGRAM_TOKEN"}.get(payload.get("channel"), "TELEGRAM_TOKEN")
    )
    my_bot.chat_id = int(os.environ.get("CHAT_ID"))

    if not my_bot.is_able_to_work:
        logging.error("TELEGRAM_TOKEN not configured.")
        return Response(content="Service not configured", status_code=500)

    logging.info(f"Processing forwarded payload: {payload}")

    try:
        # Extract the necessary info from the callback_query payload
        original_text = payload["message"]["text"]

        text = original_text.strip()
        logging.info(f"text: {text}")
        await my_bot.send_message(text)
        # cmd, *_ = text.split()
        # logging.info(f"cmd: `{cmd}`")

        # is_matched: bool = False
        # for k, cb in COMMANDS.items():
        #     if k == cmd:
        #         await cb(
        #             text.removeprefix(cmd).strip(),
        #             # send_message=functools.partial(bot.send_message, chat_id=chat_id),
        #             send_message_cb=my_bot.send_message,
        #             mongo_client=mongo_client,
        #         )
        #         is_matched = True
        #         break

        # if not is_matched:
        #     # Formulate the echo message
        #     echo_text = f"Button press received from message: '{original_text}'"

        #     # Send the echo message back to the chat
        #     await bot.send_message(chat_id=chat_id, text=echo_text)

    except (KeyError, IndexError) as e:
        logging.error(f"Error processing payload, missing key: {e}")
        # Don't return an error to the dispatcher, just log it.
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

    # Always return a 200 OK to the calling dispatcher service.
    return "OK"
