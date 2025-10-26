# GEMINI.md

## Project Overview

This project is a Python-based application that integrates with Telegram and Gemini. It acts as a Telegram bot that uses the Gemini API to generate responses to user messages. The project also includes a scheduled "heartbeat" job that monitors user activity and stores it in a MongoDB database.

The application is built using FastAPI and is designed to be deployed as a containerized service on Google Cloud Run.

### Key Technologies:

*   **Backend:** Python, FastAPI
*   **AI:** Google Gemini
*   **Database:** MongoDB
*   **Deployment:** Docker, Google Cloud Run
*   **Messaging:** Telegram

## Building and Running

The project uses a `Makefile` to streamline the build and deployment process.

### Docker Build:

To build the Docker image for the application, run the following command:

```bash
make build
```

This will build a Docker image with the name `nailbiter/20250628-gemini-telegram-gcp:v16`.

### Running Locally:

To run the application locally for development, you can use `uvicorn`:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8080
```

### Deployment:

The application is designed to be deployed to Google Cloud Run. The `Makefile` provides a `deploy` command to simplify this process:

```bash
make deploy
```

This command will deploy the application to Google Cloud Run, set the necessary environment variables and secrets, and update the traffic to the latest revision.

## Development Conventions

*   The project uses a `requirements.txt` file to manage Python dependencies.
*   The application is containerized using Docker. There are two Dockerfiles available: `Dockerfile` and `Dockerfile.gemini`. `Dockerfile` uses a distroless image for a smaller footprint, while `Dockerfile.gemini` uses a standard Python slim image.
*   The application is configured using environment variables. Key environment variables include `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `MONGO_URL`, and `CHAT_ID`.
*   The project includes a `heartbeat.py` script that runs as a scheduled job to monitor user activity.
