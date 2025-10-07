# actor_dispatcher.py
import os
import logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# The URL for the private service that handles time category updates.
# This will be set via an environment variable during deployment.
TIME_SERVER_URL = os.environ.get('TIME_SERVER_URL')

def get_id_token(audience_url):
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

@app.route("/", methods=["POST"])
def index():
    """Receives all updates from Telegram and dispatches them."""
    telegram_update = request.get_json()

    if not telegram_update:
        return "OK", 200 # Acknowledge empty requests

    # Check if the update is a button press (callback query)
    if 'callback_query' in telegram_update:
        if not TIME_SERVER_URL:
            logging.error("TIME_SERVER_URL is not configured.")
            return "Internal Server Error", 500

        logging.info("Dispatching callback query to time-category-server...")
        id_token = get_id_token(TIME_SERVER_URL)
        if not id_token:
            return "Internal Server Error", 500
            
        headers = {'Authorization': f'Bearer {id_token}'}
        try:
            # Forward the callback_query payload to the private server
            requests.post(
                TIME_SERVER_URL,
                headers=headers,
                json=telegram_update['callback_query']
            )
        except requests.exceptions.RequestException as e:
            logging.error(f"Error calling time-category-server: {e}")
            # We don't return an error to Telegram, just log it.
    
    # In the future, you can add more routing logic here.
    # elif 'message' in telegram_update and 'text' in telegram_update['message']:
    #     if telegram_update['message']['text'].startswith('/money'):
    #         # call money service...

    else:
        logging.info("Received an unhandled update type.")

    # Always return a 200 OK to Telegram immediately.
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)