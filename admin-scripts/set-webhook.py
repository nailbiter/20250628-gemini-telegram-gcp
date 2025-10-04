#!/usr/bin/env python

# set_webhook.py
import os
import click
import logging
import subprocess
import requests

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_command(cmd):
    """Helper function to run a command and return its output."""
    logging.info(f"> {cmd}")
    ec, out = subprocess.getstatusoutput(cmd)
    if ec != 0:
        logging.error(f"Command failed with exit code {ec}:\n{out}")
        raise RuntimeError(f"Command failed: {cmd}")
    return out.strip()


@click.command()
@click.option(
    "-n", "--service-name", required=True, help="The name of the Cloud Run service."
)
@click.option(
    "--secret-name",
    default="20250628-telegram-token-alex-gemini-bot",
    show_default=True,
    help="The name of the secret in Secret Manager holding the Telegram token.",
)
@click.option(
    "-P",
    "--project-id",
    required=True,
    envvar="GCLOUD_PROJECT",
    help="Your GCP project ID. Can be set via GCLOUD_PROJECT env var.",
)
def set_webhook(service_name, secret_name, project_id):
    """
    Finds a Cloud Run service, gets its URL and a secret from GCP, and sets the Telegram webhook.
    """
    try:
        # 1. Discover the service's region
        logging.info(f"Discovering region for service '{service_name}'...")
        find_region_cmd = (
            f'gcloud run services list --project="{project_id}" '
            f'--filter="metadata.name={service_name}" '
            f'''--format="value(metadata.labels.\\'cloud.googleapis.com/location\\')"'''
        )
        region = run_command(find_region_cmd)

        if not region:
            logging.error(
                f"Could not find service '{service_name}' in project '{project_id}'. Please check the name."
            )
            return
        if "\n" in region:
            logging.error(
                f"Found multiple services named '{service_name}' in different regions. Please specify the region manually."
            )
            return
        logging.info(f"Found service in region: {region}")

        # 2. Get the Telegram token securely from GCP Secret Manager
        logging.info(f"Fetching secret '{secret_name}'...")
        get_secret_cmd = f'gcloud secrets versions access latest --secret="{secret_name}" --project="{project_id}"'
        token = run_command(get_secret_cmd)

        if not token:
            logging.error("Fetched an empty value from Secret Manager.")
            return

        # 3. Get the Cloud Run service URL using the discovered region
        logging.info(f"Fetching URL for service...")
        get_url_cmd = f'gcloud run services describe {service_name} --region="{region}" --format="value(status.url)" --project="{project_id}"'
        service_url = run_command(get_url_cmd)
        logging.info(f"Service URL: {service_url}")

        # 4. Set the webhook by calling the Telegram API
        logging.info("Setting Telegram webhook...")
        webhook_url = f"https://api.telegram.org/bot{token}/setWebhook"
        response = requests.post(webhook_url, data={"url": service_url})
        response.raise_for_status()

        response_json = response.json()
        if response_json.get("ok"):
            logging.info("✅ Webhook was set successfully!")
            logging.info(f'Description: {response_json.get("description")}')
        else:
            logging.error(f"Failed to set webhook: {response_json}")

    except RuntimeError as e:
        logging.error(f"An error occurred during command execution: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while calling the Telegram API: {e}")


if __name__ == "__main__":
    set_webhook()
