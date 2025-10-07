Of course. Let's build the final, reactive part of your bot: the `actor` module. We will split it into a public "dispatcher" and a private "server" (worker) as planned.

Here are the two full Python files and the detailed, step-by-step deployment instructions, written without any sensitive information so you can safely commit them to your public repository.

-----

### \#\#\# Step 1: Add the New Code

Place the following two files in the root of your project directory alongside your other scripts.

**1. `actor_dispatcher.py` (The Public Webhook)**
This service is the new front door for your bot. It receives all updates from Telegram, inspects them, and routes them to the correct private worker service. For now, it only knows how to route button presses (`callback_query`) to our `actor-server`.

```python
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
```

**2. `actor_server.py` (The Private Worker)**
This service contains the actual business logic. It receives the forwarded payload from the dispatcher and updates the database. It is private and can only be called by other services within your GCP project that have the correct permissions.

```python
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
```

-----

### \#\#\# Step 2: Deployment Instructions

Follow these steps in order to deploy the two new services and connect them.

**1. Re-Build the Generic Docker Image**
Since you've added new source files, you must re-build the image to include them.

```bash
gcloud builds submit --tag gcr.io/[YOUR_PROJECT_ID]/py-assistant-bot
```

**2. Deploy the Private "Server"**
This service contains your business logic. We deploy it first so we can get its unique URL.

```bash
gcloud run deploy time-category-server \
  --image gcr.io/[YOUR_PROJECT_ID]/py-assistant-bot \
  --service-account "[YOUR_SERVICE_ACCOUNT_EMAIL]" \
  --set-secrets="MONGO_URL=mongo-url-gaq:latest" \
  --region "us-east1" \
  --no-allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","actor_server:app"
```

  * **Note:** `--no-allow-unauthenticated` is critical. It makes the service private.

**3. Get the Server's URL**
After the deployment succeeds, get the unique URL of the private service you just created.

```bash
gcloud run services describe time-category-server \
  --region="us-east1" \
  --format="value(status.url)"
```

Copy the URL that is printed. It will look like `https://time-category-server-....a.run.app`.

**4. Deploy the Public "Dispatcher"**
Now, deploy the public-facing dispatcher and give it the server's URL as an environment variable.

```bash
gcloud run deploy actor-dispatcher \
  --image gcr.io/[YOUR_PROJECT_ID]/py-assistant-bot \
  --service-account "[YOUR_SERVICE_ACCOUNT_EMAIL]" \
  --set-env-vars="TIME_SERVER_URL=[THE_SERVER_URL_YOU_COPIED]" \
  --region "us-east1" \
  --allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","actor_dispatcher:app"
```

**5. Grant "Invoker" Permissions**
Tell GCP that the dispatcher is allowed to call the private server.

```bash
gcloud run services add-iam-policy-binding time-category-server \
  --member="serviceAccount:[YOUR_SERVICE_ACCOUNT_EMAIL]" \
  --role="roles/run.invoker" \
  --region="us-east1"
```

**6. Update the Telegram Webhook**
Finally, point your Telegram bot to the new public dispatcher service using the `set_webhook.py` script.

```bash
python set_webhook.py \
  --service-name="actor-dispatcher" \
  --project-id="[YOUR_PROJECT_ID]"
```

Your new, fully refactored actor architecture is now live\! When you press a button, Telegram will call the dispatcher, which will securely call the private server, which will then update your database.