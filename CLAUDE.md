# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-service Telegram bot platform backed by Google Gemini AI, deployed on Google Cloud Run. The bot handles conversational AI responses, time/activity tracking, expense logging, sleep state management, and habit reminders. A dispatcher routes Telegram messages to specialized Cloud Run services based on prefix matching stored in MongoDB.

## Build and Deployment

```bash
# Build Docker image
make build

# Push to Docker Hub
make push

# Deploy main service to Cloud Run
make deploy

# Deploy a specialized Cloud Run service
./admin-scripts/deploy-functions.py -n <service-name> -s <script>.py -C uvicorn

# Example: deploy experimental actor server
./admin-scripts/deploy-functions.py -n time-react-service-experimental -s actor_server_experimental.py -C uvicorn

# Run locally for development
uvicorn app:app --reload --host 0.0.0.0 --port 8080
uvicorn time_react:app --reload --host 0.0.0.0 --port 8080

# Housekeeping: preview images to clean up
./admin-scripts/list.py images -r us-east1 -AP
# Add -F to force deletion
```

## Environment Variables

Required secrets (managed via GCP Secret Manager):
- `TELEGRAM_TOKEN` / `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `GEMINI_API_KEY` — Google Gemini API key
- `MONGO_URL` — MongoDB Atlas connection string

Required env vars:
- `CHAT_ID` — Authorized Telegram chat ID (messages from other chats are rejected)
- `ACTOR_SERVER_URL` — URL of the actor/dispatcher service (used by `time_react.py`)
- `GCLOUD_PROJECT` / `GCLOUD_PROJECT_ID` — GCP project ID

Local secrets file: `.env.secrets` (not committed).

## Architecture

### Entry Points

| File | Role |
|---|---|
| `time_react.py` | **Primary webhook handler** — routes callback queries (time tracking) and dispatches text messages to Cloud Run services via MongoDB prefix rules |
| `app.py` | Gemini-Telegram bridge — receives messages, calls Gemini API, returns responses |
| `actor_server.py` | FastAPI service handling `/money`, `/note`, `/sleepstart`, `/sleepend` |
| `actor_server_experimental.py` | Experimental variant of actor server |
| `heartbeat_time_main.py` | Scheduled job — sends activity category keyboards every 30 min |
| `heartbeat_habits_main.py` | Scheduled job — checks habit cron schedules and sends reminders |

### Dispatcher Pattern (`time_react.py`)

Incoming Telegram updates are routed based on update type:
1. **Callback query** (button press) → handled locally in `time_react.py`, updates `logistics.alex.time` in MongoDB with the selected time category, then deletes the keyboard message
2. **Text message** → fetches routing rules from MongoDB collection `logistics.cloud-run-hooks-gcp` (prefix → URL mappings), finds longest matching prefix, calls the target Cloud Run service with a Google-signed ID token
3. **`/help`** → lists available prefixes from MongoDB hooks

### Service-to-Service Auth

Cloud Run services use Google metadata server ID tokens for authentication. `get_id_token(audience_url)` in `time_react.py` and `common/call_cloud_run.py` fetch tokens from the GCP metadata server. Services are deployed with `--no-allow-unauthenticated` by default.

### MongoDB Collections (`logistics` database)

| Collection | Purpose |
|---|---|
| `alex.time` | Activity tracking records; each record has a `telegram_message_id` and `category` |
| `alex.sleepingtimes` | Sleep/wake records with `startsleep`/`endsleep` and `category` |
| `cloud-run-hooks-gcp` | Routing table: `{prefix, url}` documents |

### Shared Utilities (`common/`)

- `common/__init__.py` — `TIME_CATS` list (12 activity categories), `to_utc_datetime()`, `parse_cmdline_datetime()`, `get_sleeping_state()`, `split_long_text()`
- `common/call_cloud_run.py` — Helpers for calling Cloud Run services with auth
- `common/simple_math_eval.py` — Math expression evaluator for money amounts

### Scheduled Jobs

`heartbeat.py` (`HeartbeatJob`) and `habits.py` (`HabitsJob`) are run via Cloud Scheduler → Pub/Sub → Cloud Run. `heartbeat_time_main.py` and `heartbeat_habits_main.py` are the respective entry points.

## Dockerfile Notes

Two Dockerfiles:
- `Dockerfile` — multi-stage build, distroless final image, runs `time_react:app` via gunicorn+uvicorn workers
- `Dockerfile.gemini` — standard Python slim image

GCP Container Registry build: `gcloud builds submit --tag gcr.io/$GCLOUD_PROJECT/py-assistant-bot`

## Admin Scripts

All scripts in `admin-scripts/` use Click CLI and load `.env.secrets`:
- `deploy-functions.py` — deploy any `.py` FastAPI app as a Cloud Run service
- `manage-secrets.py` — manage GCP Secret Manager secrets
- `set-telegram-webhook.py` — configure the Telegram webhook URL
- `list.py` — list/clean up Docker images in GCP Container Registry
