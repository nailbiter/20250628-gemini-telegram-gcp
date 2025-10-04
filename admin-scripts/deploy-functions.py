#!/usr/bin/env python3
"""===============================================================================

        FILE: /Users/nailbiter/Documents/forgithub/20250628-gemini-telegram-gcp/admin-scripts/deploy-functions.py

       USAGE: (not intended to be directly executed)

 DESCRIPTION: 

     OPTIONS: ---
REQUIREMENTS: ---
        BUGS: ---
       NOTES: ---
      AUTHOR: Alex Leontiev (alozz1991@gmail.com)
ORGANIZATION: 
     VERSION: ---
     CREATED: 2025-10-04T19:21:41.335383
    REVISION: ---

==============================================================================="""

import click
from dotenv import load_dotenv
import os
from os import path
import logging
from jinja2 import Template

load_dotenv()

"""
    gcloud run deploy time-react-service \
  --image gcr.io/api-project-424250507607/py-assistant-bot \
  --service-account "pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com" \
  --set-secrets="TELEGRAM_TOKEN=20250628-telegram-token-alex-gemini-bot:latest" \
  --set-env-vars="CHAT_ID=[YOUR_CHAT_ID]" \
  --region "us-east1" \
  --allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","time_react:app"
"""


@click.command()
def deploy_functions():
    pass


if __name__ == "__main__":
    fn = ".env"
    if path.isfile(fn):
        logging.warning(f"loading `{fn}`")
        load_dotenv(dotenv_path=fn)
    deploy_functions()
