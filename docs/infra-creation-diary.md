## `2025-10-04`

### \#\# Step 1: Set Up the GCP Infrastructure

First, we create the shared service account for the entire bot. **Note: You only need to run this first command once for the whole project.**

**1. Create the Shared Service Account**
This account will act as the identity for all your bot's Cloud Run services.

```bash
gcloud iam service-accounts create pyassistantbot3-sa \
  --display-name="Shared Service Account for PyAssistantBot"
```

**2. Create a Pub/Sub Topic**
This topic remains specific to the heartbeat service.

```bash
gcloud pubsub topics create heartbeat-time-topic
```

**3. Create the Cloud Scheduler Job**
This job will publish a message to the topic every 30 minutes.

```bash
gcloud scheduler jobs create pubsub heartbeat-time-scheduler \
  --schedule="*/30 * * * *" \
  --topic="heartbeat-time-topic" \
  --message-body="tick" \
  --location="us-east1"
```

### granting access to secrets
```
gcloud secrets add-iam-policy-binding "20250628-telegram-token-alex-gemini-bot" \
  --member="serviceAccount:pyassistantbot3-sa@[YOUR_PROJECT_ID].iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### permissions
#### give me permissions to build
```
gcloud projects add-iam-policy-binding api-project-424250507607 \
  --member="user:alozz1991@gmail.com" \
  --role="roles/cloudbuild.editor"
```

#### give GCE SA permissions to GCS
```
gcloud projects add-iam-policy-binding api-project-424250507607 \
  --member="serviceAccount:424250507607@cloudbuild.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

```
gcloud projects add-iam-policy-binding api-project-424250507607 \
  --member="serviceAccount:424250507607-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"
```

### build
```
gcloud builds submit --tag gcr.io/api-project-424250507607/py-assistant-bot
```


### deploy

```
gcloud run deploy heartbeat-time-service \
  --image gcr.io/api-project-424250507607/py-assistant-bot \
  --service-account "pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com" \
  --eventarc-trigger-service-account "pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com" \
  --eventarc-trigger \
  --eventarc-trigger-event "google.cloud.pubsub.topic.v1.messagePublished" \
  --eventarc-trigger-event-filters "type=google.cloud.pubsub.topic.v1.messagePublished" \
  --eventarc-trigger-event-filters "topic=heartbeat-time-topic" \
  --set-secrets="TELEGRAM_TOKEN=20250628-telegram-token-alex-gemini-bot:latest,MONGO_URL=mongo-url-gaq:latest" \
  --set-env-vars="CHAT_ID=[YOUR_CHAT_ID]" \
  --region "us-east1" \
  --allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","heartbeat_time_main:app"
```

#### older way

```
	gcloud run deploy heartbeat-time-service \
  --image gcr.io/api-project-424250507607/py-assistant-bot \
  --service-account "pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com" \
  --set-secrets="TELEGRAM_TOKEN=20250628-telegram-token-alex-gemini-bot:latest,MONGO_URL=mongo-url-gaq:latest" \
  --set-env-vars="CHAT_ID=[YOUR_CHAT_ID]" \
  --region "us-east1" \
  --allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","heartbeat_time_main:app"
  ```
  
  ```
  gcloud eventarc triggers create heartbeat-time-trigger \
  --destination-run-service="heartbeat-time-service" \
  --destination-run-region="us-east1" \
  --location="us-east1" \
  --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
  --event-filters="topic=heartbeat-time-topic" \
  --service-account="pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com"
  ```

## `2025-10-05`


**2. Deploy the New Cloud Run Service**
This command creates the `heartbeat-habits-service`. Note the new service name and the new `--command` value.

```bash
gcloud run deploy heartbeat-habits-service \
  --image gcr.io/api-project-424250507607/py-assistant-bot \
  --service-account "pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com" \
  --set-secrets="TELEGRAM_TOKEN=20250628-telegram-token-alex-gemini-bot:latest,MONGO_URL=mongo-url-gaq:latest" \
  --set-env-vars="CHAT_ID=[YOUR_CHAT_ID]" \
  --region "us-east1" \
  --allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","heartbeat_habits_main:app"
```

**3. Create the Eventarc Trigger Manually**
Finally, this command connects your new scheduler (`heartbeat-habits-topic`) to your new service (`heartbeat-habits-service`).

```bash
gcloud eventarc triggers create heartbeat-habits-trigger \
  --destination-run-service="heartbeat-habits-service" \
  --destination-run-region="us-east1" \
  --location="us-east1" \
  --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
  --transport-topic="heartbeat-habits-topic" \
  --service-account="pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com"
```

Once these steps are complete, your second automated service will be live and running on the new serverless architecture.
