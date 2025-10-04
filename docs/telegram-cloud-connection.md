Excellent, you're ready for the final connection. To "connect" your service to Telegram, you need to tell Telegram the public URL of your `time-react-service`. This is done by setting a **webhook**.

Here's the step-by-step process.

-----

### \#\#\# Step 1: Get Your Cloud Run Service URL

First, you need the unique public URL that Google assigned to your new service.

You can get this easily with a `gcloud` command. Make sure to specify the correct region.

```bash
gcloud run services describe time-react-service --region="us-east1" --format="value(status.url)"
```

This command will print out a URL that looks something like this:
`https://time-react-service-xxxxxxxxxx-ue.a.run.app`

Copy this URL. This is where Telegram will send all updates.

-----

### \#\#\# Step 2: Set the Telegram Webhook

Now, you'll make a single web request to the Telegram Bot API to register your URL. You can do this with a simple `curl` command in your terminal.

You will need two pieces of information:

1.  **Your Telegram Bot Token**: The one stored in the `20250628-telegram-token-alex-gemini-bot` secret.
2.  **Your Service URL**: The URL you just copied from the previous step.

Construct and run the following `curl` command, replacing the placeholders:

```bash
curl "https://api.telegram.org/bot[YOUR_TELEGRAM_TOKEN]/setWebhook?url=[YOUR_CLOUD_RUN_URL]"
```

**Example:**

```bash
curl "https://api.telegram.org/bot12345:abcdefg-hijklmnop/setWebhook?url=https://time-react-service-xxxxxxxxxx-ue.a.run.app"
```

If the command is successful, Telegram will respond with:
`{"ok":true,"result":true,"description":"Webhook was set"}`

-----

### \#\#\# Step 3: Test It\!

That's it\! Your bot is now connected.

To test the entire flow:

1.  Go to your Telegram chat.
2.  Press any of the category buttons from the message sent by your `heartbeat-time-service`.
3.  Telegram will now send an update to your `time-react-service`.
4.  Your service will execute the `time_react.py` script and send "hi" back to your chat.

You can also check the **Logs** tab for the `time-react-service` in the Cloud Run console to see the incoming request from Telegram.