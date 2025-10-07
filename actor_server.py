# actor_server.py
import os
import logging
from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient
import pytz

# The shared `common` module is used here
from common import MONGO_COLL_NAME, TIME_CATS

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Initialize clients once
MONGO_URL = os.environ.get('MONGO_URL')
if not MONGO_URL:
    logging.warning("MONGO_URL not set. Database functionality disabled.")
    mongo_client = None
else:
    mongo_client = MongoClient(MONGO_URL)

@app.route("/", methods=["POST"])
def handle_callback():
    """
    Handles a callback_query payload forwarded from the dispatcher.
    Cloud Run has already verified the request is authenticated.
    """
    if not mongo_client:
        return "Internal Server Error: DB not configured", 500

    payload = request.get_json()
    if not payload:
        return "Bad Request: No JSON payload received", 400

    logging.info(f"Processing callback query: {payload}")
    
    try:
        message_id = payload['message']['message_id']
        category_index = int(payload['data'])
        category = TIME_CATS[category_index]
        
        time_coll = mongo_client[MONGO_COLL_NAME]["alex.time"]
        
        # Find the record created by the heartbeat service and update it
        result = time_coll.update_one(
            {"telegram_message_id": message_id},
            {
                "$set": {
                    "category": category,
                    "_last_modification_date": datetime.now(pytz.utc),
                }
            }
        )
        logging.info(f"DB update result: {result.matched_count} matched, {result.modified_count} modified.")

    except (KeyError, IndexError, ValueError) as e:
        logging.error(f"Error processing payload: {e}")
        return "Bad Request: Malformed payload", 400
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return "Internal Server Error", 500

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)