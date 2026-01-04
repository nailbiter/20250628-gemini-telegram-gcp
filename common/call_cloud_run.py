"""===============================================================================

        FILE: /Users/nailbiter/Documents/forgithub/20250628-gemini-telegram-gcp/common/call_cloud_run.py

       USAGE: (not intended to be directly executed)

 DESCRIPTION: 

     OPTIONS: ---
REQUIREMENTS: ---
        BUGS: ---
       NOTES: ---
      AUTHOR: Alex Leontiev (alozz1991@gmail.com)
ORGANIZATION: 
     VERSION: ---
     CREATED: 2026-01-04T18:03:06.635863
    REVISION: ---

==============================================================================="""
import logging
import typing
import os
import tempfile
import typing
from datetime import datetime

# import nbconvert
# import papermill
import requests

# from fastapi import FastAPI, HTTPException, Response
# from google.cloud import storage


def get_id_token(audience_url: str) -> typing.Optional[str]:
    """Fetches a Google-signed ID token for the given audience URL."""
    token_url = f"http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience_url}"
    token_headers = {"Metadata-Flavor": "Google"}
    try:
        token_response = requests.get(token_url, headers=token_headers)
        token_response.raise_for_status()  # Raise an exception for bad status codes
        return token_response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch ID token for {audience_url}: {e}")
        return None


def call_cloud_run(url: str, text: typing.Optional[str] = None) -> dict:
    logging.info(f"Calling notification service at {url}...")
    id_token = get_id_token(url)

    # message_text = f"{public_url} #weeklyReport"
    # if not github_notebook_used:
    #     message_text += f" (Note: Used local notebook due to: {fallback_reason})"
    # else:
    #     message_text += " (Note: Used latest notebook from GitHub)"

    if not id_token:
        logging.error("Could not get ID token. Skipping notification.")
        # Still return success, as the main task (report gen) worked
        return {
            "status": "failure",
            "reason": "cannot generate id",
        }

    try:
        headers = {"Authorization": f"Bearer {id_token}"}
        payload = {"message": {"text": text}} if text is not None else {}

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Check for HTTP errors

        logging.info(
            f"Notification service called successfully. Status: {response.status_code}"
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to call notification service: {e}")
        # Log the error but don't fail the whole job
        return {
            "status": "failure",
            "reason": "cannot call function",
        }

    return {
        "status": "success",
    }
