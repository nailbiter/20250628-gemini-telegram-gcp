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

CMD = Template(
    """
    gcloud run deploy {{service_name}} \
  --image gcr.io/api-project-424250507607/py-assistant-bot \
  --service-account "pyassistantbot3-sa@api-project-424250507607.iam.gserviceaccount.com" \
  --set-secrets="TELEGRAM_TOKEN=20250628-telegram-token-alex-gemini-bot:latest,MONGO_URL=mongo-url-gaq:latest" \
  --set-env-vars="CHAT_ID={{chat_id}}" \
  --region "us-east1" \
  --allow-unauthenticated \
  --command="gunicorn","--bind","0.0.0.0:8080","--workers","1","--threads","8","--timeout","0","time_react:app"
"""
)


def _render_cmd(*args, **kwargs) -> str:
    return (
        CMD.render(*args, **kwargs)
        .replace("\\", " ")
        .replace("\n", " ")
        .replace("  ", " ")
    )


@click.command()
@click.option("-s", "--script", type=click.Path(), required=True)
@click.option("-n", "--service-name", required=True)
@click.option("-C", "--chat_id", required=True, type=int, envvar="CHAT_ID")
def deploy_functions(script, chat_id, service_name):
    cmd = _render_cmd(
        script=script.removesuffix(".py"), chat_id=chat_id, service_name=service_name
    )
    logging.warning(f"> {cmd}")
    ec, out = subprocess.getstatusoutput(cmd)
    assert ec == 0, (cmd, ec, out)


if __name__ == "__main__":
    fn = ".env"
    if path.isfile(fn):
        logging.warning(f"loading `{fn}`")
        load_dotenv(dotenv_path=fn)
    deploy_functions()
