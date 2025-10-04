## 2025-10-04

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
  --message-body="tick"
```
