# heartbeat.py
import os
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater
from pymongo import MongoClient
import pandas as pd
from telegram.error import TimedOut

# Assuming your _common file is now in a 'common' package
from common import get_sleeping_state, MONGO_COLL_NAME, TIME_CATS, to_utc_datetime


class HeartbeatJob:
    def __init__(self):
        # Configuration is now read from environment variables
        self._token = os.environ["TELEGRAM_TOKEN"]
        self._chat_id = os.environ["CHAT_ID"]
        self._mongo_url = os.environ["MONGO_URL"]

        # Set up clients
        self._bot = Updater(self._token, use_context=True).bot
        self._mongo_client = MongoClient(self._mongo_url)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._keyboard = TIME_CATS
        self._columns = 2

    def run(self):
        """The main logic of the job."""
        _now = datetime.now()
        self._logger.warning(f"Heartbeat job running at {_now.isoformat()}")

        sleeping_state = get_sleeping_state(self._mongo_client)
        self._logger.warning(f"Sleeping state: {sleeping_state}")

        message_id = "FAILURE"
        try:
            if sleeping_state is None:
                mess = self._send_keyboard("北鼻，你在幹什麼？")
                message_id = mess.message_id
            else:
                is_no_bother, cat = sleeping_state
                if not is_no_bother:
                    self._send_message(f"Current state: {cat}")
        except TimedOut as e:
            self._logger.error(f"Telegram timed out: {e}")

        self._sanitize_mongo(
            imputation_state="useless" if sleeping_state is None else sleeping_state[1]
        )

        # Log the event to MongoDB
        res = self._mongo_client[MONGO_COLL_NAME]["alex.time"].insert_one(
            {
                "date": _now,
                "category": None,
                "telegram_message_id": message_id,
            }
        )
        self._logger.warning(f"Inserted record ID: {res.inserted_id}")

    def _send_keyboard(self, text):
        keyboard = [
            [
                InlineKeyboardButton(self._keyboard[i + j], callback_data=str(i + j))
                for j in range(self._columns)
                if i + j < len(self._keyboard)
            ]
            for i in range(0, len(self._keyboard), self._columns)
        ]
        return self._bot.send_message(
            chat_id=self._chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    def _send_message(self, text):
        return self._bot.send_message(chat_id=self._chat_id, text=text)

    def _sanitize_mongo(self, imputation_state):
        self._logger.warning(f"Sanitizing with imputation state: {imputation_state}")
        mongo_coll = self._mongo_client[MONGO_COLL_NAME]["alex.time"]

        # Use update_many for efficiency
        result = mongo_coll.update_many(
            {"category": None},
            {
                "$set": {
                    "category": imputation_state,
                    "_last_modification_date": to_utc_datetime(),
                },
            },
        )
        if result.modified_count > 0:
            self._logger.warning(f"Sanitized {result.modified_count} records.")
