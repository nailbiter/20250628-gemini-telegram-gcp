# habits.py
import os
import logging
from datetime import datetime, timedelta
from telegram import Bot
from pymongo import MongoClient, UpdateOne
import pandas as pd
from croniter import croniter
import pytz  # <-- CHANGED: Import pytz for timezone handling

from common import MONGO_COLL_NAME, TimerContextManager


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

    def run(self):
        # <-- CHANGED: Get the current time as a timezone-aware UTC datetime
        _now = datetime.now(pytz.utc)
        self._logger.info(f"Habits job running at {_now.isoformat()}")

        habits_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits"]
        habits_df = pd.DataFrame(list(habits_coll.find({"enabled": True})))
        anchor_dates = self._get_anchor_dates()

        punches_to_create = []
        # <-- CHANGED: Make the default base datetime timezone-aware (UTC)
        default_base = datetime(2021, 12, 14, tzinfo=pytz.utc)

        for habit in habits_df.to_dict(orient="records"):
            # Anchor dates from Mongo are already UTC-aware
            base = anchor_dates.get(habit["name"], default_base)
            # croniter will now produce timezone-aware UTC datetimes
            it = croniter(habit["cronline"], base)
            while (due_date := it.get_next(datetime)) <= _now:
                punches_to_create.append(
                    {
                        "name": habit["name"],
                        "date": due_date,  # This is a UTC-aware datetime
                        "due": due_date
                        + timedelta(minutes=habit.get("delaymin", 0)),  # Also UTC-aware
                        "onFailed": habit.get("onFailed"),
                        "info": habit.get("info"),
                    }
                )

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

                # --- Send summary message to Telegram ---
                summary_df = pd.DataFrame(punches_to_create)[["name", "due"]]

                # <-- CHANGED: Convert UTC 'due' time to JST for display
                jst_tz = pytz.timezone("Asia/Tokyo")
                summary_df["due"] = (
                    pd.to_datetime(summary_df["due"])
                    .dt.tz_convert(jst_tz)
                    .dt.strftime("%Y-%m-%d %H:%M")
                )

                message = f"New habits generated (JST):\n```{summary_df.to_string(index=False)}```"
                self._send_message(message, parse_mode="Markdown")

            # Update anchor dates with the current UTC time
            self._update_anchor_dates(habits_df["name"].unique(), _now)

        with TimerContextManager("sanitize mongo"):
            self._sanitize_mongo(_now)  # Pass the UTC-aware time

    def _get_anchor_dates(self):
        anchor_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits_anchors"]
        # pymongo > 3.10 automatically returns timezone-aware UTC datetimes
        return {r["name"]: r["date"] for r in anchor_coll.find()}

    def _update_anchor_dates(self, habit_names, anchor_date):
        anchor_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits_anchors"]
        operations = [
            UpdateOne(
                {"name": name},
                {"$set": {"date": anchor_date}},  # anchor_date is already UTC-aware
                upsert=True,
            )
            for name in habit_names
        ]
        if operations:
            anchor_coll.bulk_write(operations)

    def _sanitize_mongo(self, now_time):
        # now_time is already a UTC-aware datetime, so the comparison is correct
        result = self._habits_punch_coll.update_many(
            {"due": {"$lt": now_time}, "status": {"$exists": False}},
            {"$set": {"status": "FAILED"}},
        )
        if result.modified_count > 0:
            self._logger.info(f"Marked {result.modified_count} habits as FAILED.")

    def _send_message(self, text, **kwargs):
        self._bot.send_message(chat_id=self._chat_id, text=text, **kwargs)
