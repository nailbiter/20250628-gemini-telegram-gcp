# habits.py
import os
import logging
from datetime import datetime, timedelta
from telegram import Bot  # Keep this import
from pymongo import MongoClient, UpdateOne
import pandas as pd
from croniter import croniter
import pytz
import asyncio  # <-- Add asyncio import

from common import MONGO_COLL_NAME, TimerContextManager, TARGET_TIMEZONE


class HabitsJob:
    def __init__(self):
        self._token = os.environ["TELEGRAM_TOKEN"]
        self._chat_id = os.environ["CHAT_ID"]
        self._mongo_url = os.environ["MONGO_URL"]
        self._bot = Bot(token=self._token)
        self._mongo_client = MongoClient(self._mongo_url)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._habits_punch_coll = self._mongo_client[MONGO_COLL_NAME][
            "alex.habitspunch2"
        ]

    # <-- CHANGED: Mark run() as an async function
    async def run(self):
        # ... (all the logic to calculate habits remains the same) ...
        _now_utc = datetime.now(pytz.utc)
        target_tz = pytz.timezone(TARGET_TIMEZONE)
        self._logger.info(f"Habits job running at {_now_utc.isoformat()} UTC")

        # [ The entire block of code for calculating 'punches_to_create' is unchanged ]

        habits_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits"]
        habits_df = pd.DataFrame(list(habits_coll.find({"enabled": True})))
        anchor_dates = self._get_anchor_dates()
        punches_to_create = []
        default_base_utc = datetime(2021, 12, 14, tzinfo=pytz.utc)
        utc_tz = pytz.utc
        for habit in habits_df.to_dict(orient="records"):
            base_utc = anchor_dates.get(habit["name"], default_base_utc)
            base_target_naive = base_utc.astimezone(target_tz).replace(tzinfo=None)
            it = croniter(habit["cronline"], base_target_naive)
            while (
                due_date_target_naive := it.get_next(datetime)
            ) <= _now_utc.astimezone(target_tz).replace(tzinfo=None):
                due_date_utc = target_tz.localize(due_date_target_naive).astimezone(
                    utc_tz
                )
                punches_to_create.append(
                    {
                        "name": habit["name"],
                        "date": due_date_utc,
                        "due": due_date_utc
                        + timedelta(minutes=habit.get("delaymin", 0)),
                        "onFailed": habit.get("onFailed"),
                        "info": habit.get("info"),
                    }
                )

        self._logger.info(f"{len(punches_to_create)} punches")
        if punches_to_create:
            with TimerContextManager("bulk_write habits"):
                operations = [
                    UpdateOne(
                        {"name": p["name"], "date": p["date"]}, {"$set": p}, upsert=True
                    )
                    for p in punches_to_create
                ]
                result = self._habits_punch_coll.bulk_write(operations)
                self._logger.info(f"{result.upserted_count} habits created.")

                summary_df = pd.DataFrame(punches_to_create)[["name", "due"]]
                summary_df["due"] = (
                    pd.to_datetime(summary_df["due"])
                    .dt.tz_convert(target_tz)
                    .dt.strftime("%Y-%m-%d %H:%M")
                )

                tz_name_for_display = TARGET_TIMEZONE.split("/")[-1].replace("_", " ")
                message = f"New habits generated ({tz_name_for_display} Time):\n```{summary_df.to_string(index=False)}```"

                # <-- CHANGED: Use 'await' to call the async function
                await self._send_message(message, parse_mode="Markdown")

            self._update_anchor_dates(habits_df["name"].unique(), _now_utc)

        with TimerContextManager("sanitize mongo"):
            self._sanitize_mongo(_now_utc)

    # ... (the other synchronous methods are unchanged) ...
    def _get_anchor_dates(self):
        # ...
        anchor_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits_anchors"]
        return {r["name"]: r["date"] for r in anchor_coll.find()}

    def _update_anchor_dates(self, habit_names, anchor_date):
        # ...
        anchor_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits_anchors"]
        operations = [
            UpdateOne({"name": name}, {"$set": {"date": anchor_date}}, upsert=True)
            for name in habit_names
        ]
        if operations:
            anchor_coll.bulk_write(operations)

    def _sanitize_mongo(self, now_time):
        # ...
        result = self._habits_punch_coll.update_many(
            {"due": {"$lt": now_time}, "status": {"$exists": False}},
            {"$set": {"status": "FAILED"}},
        )
        if result.modified_count > 0:
            self._logger.info(f"Marked {result.modified_count} habits as FAILED.")

    # <-- CHANGED: Mark _send_message as an async function and use 'await'
    async def _send_message(self, text, **kwargs):
        await self._bot.send_message(chat_id=self._chat_id, text=text, **kwargs)
