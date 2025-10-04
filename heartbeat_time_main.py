# heartbeat_time_main.py
import os
import logging
from flask import Flask, request
from heartbeat import HeartbeatJob

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route("/", methods=["POST"])
def index():
    # The trigger from Pub/Sub via Eventarc is a POST request
    logging.info("Trigger received, starting heartbeat-time job.")
    try:
        job = HeartbeatJob()
        job.run()
        return "OK", 200
    except Exception as e:
        logging.error(f"Job failed: {e}")
        return "Job execution failed", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)