import os
import logging
from flask import Flask, request
import telegram
import google.generativeai as genai

# --- Configuration ---
# These will be set as environment variables in your Cloud Run service.
# It is strongly recommended to source these from Google Secret Manager.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Initialization ---
# Configure logging for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram Bot and Gemini Model safely
bot = None
if TELEGRAM_BOT_TOKEN:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
else:
    logging.warning("TELEGRAM_BOT_TOKEN environment variable not set. Bot will not be able to send messages.")

gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        logging.error(f"Failed to configure Gemini: {e}")
else:
    logging.warning("GEMINI_API_KEY environment variable not set. Gemini features will be disabled.")


# --- Webhook Endpoint ---
@app.route('/', methods=['POST'])
def telegram_webhook():
    """
    This function handles incoming updates from the Telegram webhook.
    """
    if not bot or not gemini_model:
        logging.error("Service is not configured correctly. Missing API keys.")
        return "Service not configured", 500

    try:
        update_json = request.get_json(force=True)
        update = telegram.Update.de_json(update_json, bot)
    except Exception as e:
        logging.error(f"Could not decode Telegram update: {e}")
        return "Invalid request", 400

    if not update.message or not update.message.text:
        logging.info("Received an update without a text message.")
        return "OK", 200

    chat_id = update.message.chat.id
    user_text = update.message.text
    logging.info(f"Received message from chat_id {chat_id}: '{user_text}'")

    try:
        # Send text to Gemini model for content generation
        logging.info("Generating content with Gemini...")
        response = gemini_model.generate_content(user_text)
        gemini_response_text = response.text
        
        # Send Gemini's response back to the user via Telegram
        bot.send_message(chat_id=chat_id, text=gemini_response_text)
        logging.info(f"Successfully sent Gemini response to chat_id {chat_id}")

    except Exception as e:
        logging.error(f"Error processing with Gemini or sending reply: {e}", exc_info=True)
        # Send a generic error message back to the user
        try:
            bot.send_message(chat_id=chat_id, text="Sorry, I encountered an error. Please try again later.")
        except Exception as telegram_e:
            logging.error(f"Failed to send error message to Telegram: {telegram_e}")
            
    # Always return a 200 OK to Telegram to acknowledge receipt of the update
    return "OK", 200

# This part is for local development and won't be used in Cloud Run (Gunicorn will run the app).
if __name__ == "__main__":
    if not bot or not gemini_model:
        print("ERROR: TELEGRAM_BOT_TOKEN and GEMINI_API_KEY must be set as environment variables to run.")
    else:
        # Use debug=False for local testing to better simulate production
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
