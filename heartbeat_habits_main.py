# heartbeat_habits_main.py
import os
import logging
from flask import Flask, request
from habits import HabitsJob
import asyncio  # <-- Add asyncio import

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)


@app.route("/", methods=["POST"])
def index():
    logging.info("Trigger received, starting habits job.")
    try:
        job = HabitsJob()
        # <-- CHANGED: Use asyncio.run() to execute the async function
        asyncio.run(job.run())
        return "OK", 200
    except Exception as e:
        logging.error(f"Job failed: {e}", exc_info=True)
        return "Job execution failed", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
