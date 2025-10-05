# habits.py
import os
import logging
from datetime import datetime, timedelta
from telegram.ext import Updater
from pymongo import MongoClient, UpdateOne
import pandas as pd
from croniter import croniter

from common import MONGO_COLL_NAME, to_utc_datetime, TimerContextManager

class HabitsJob:
    def __init__(self):
        # Config from environment variables
        self._token = os.environ['TELEGRAM_TOKEN']
        self._chat_id = os.environ['CHAT_ID']
        self._mongo_url = os.environ['MONGO_URL']

        # Setup clients
        self._bot = Updater(self._token, use_context=True).bot
        self._mongo_client = MongoClient(self._mongo_url)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._habits_punch_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habitspunch2"]

    def run(self):
        _now = datetime.now()
        self._logger.info(f"Habits job running at {_now.isoformat()}")

        # Get enabled habits and last-run anchors
        habits_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits"]
        habits_df = pd.DataFrame(list(habits_coll.find({"enabled": True})))
        anchor_dates = self._get_anchor_dates()

        # Calculate all habit occurrences since the last run
        punches_to_create = []
        for habit in habits_df.to_dict(orient="records"):
            base = anchor_dates.get(habit["name"], datetime(2021, 12, 14))
            it = croniter(habit["cronline"], base)
            while (due_date := it.get_next(datetime)) <= _now:
                punches_to_create.append({
                    "name": habit["name"],
                    "date": due_date,
                    "due": due_date + timedelta(minutes=habit.get("delaymin", 0)),
                    "onFailed": habit.get("onFailed"),
                    "info": habit.get("info")
                })
        
        # Upsert new habits using a single, efficient bulk write operation
        if punches_to_create:
            with TimerContextManager("bulk_write habits"):
                operations = [
                    UpdateOne(
                        {"name": p["name"], "date": p["date"]},
                        {"$set": p},
                        upsert=True
                    ) for p in punches_to_create
                ]
                result = self._habits_punch_coll.bulk_write(operations)
                self._logger.info(f"{result.upserted_count} habits created.")
                
                # Send summary message to Telegram
                summary_df = pd.DataFrame(punches_to_create)[["name", "due"]]
                summary_df["due"] = summary_df["due"].dt.strftime("%Y-%m-%d %H:%M")
                message = f"New habits generated:\n```{summary_df.to_string(index=False)}```"
                self._send_message(message, parse_mode="Markdown")

            # Update anchor dates to now for all processed habits
            self._update_anchor_dates(habits_df["name"].unique(), _now)

        # Mark any past-due habits as FAILED
        with TimerContextManager("sanitize mongo"):
            self._sanitize_mongo(_now)

    def _get_anchor_dates(self):
        anchor_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits_anchors"]
        return {r["name"]: r["date"] for r in anchor_coll.find()}

    def _update_anchor_dates(self, habit_names, anchor_date):
        anchor_coll = self._mongo_client[MONGO_COLL_NAME]["alex.habits_anchors"]
        operations = [
            UpdateOne(
                {"name": name},
                {"$set": {"date": anchor_date}},
                upsert=True
            ) for name in habit_names
        ]
        if operations:
            anchor_coll.bulk_write(operations)

    def _sanitize_mongo(self, now_time):
        # Find habits that are past their due date but have no status
        result = self._habits_punch_coll.update_many(
            {
                "due": {"$lt": now_time},
                "status": {"$exists": False}
            },
            {"$set": {"status": "FAILED"}}
        )
        if result.modified_count > 0:
            self._logger.info(f"Marked {result.modified_count} habits as FAILED.")
    
    def _send_message(self, text, **kwargs):
        self._bot.send_message(chat_id=self._chat_id, text=text, **kwargs)