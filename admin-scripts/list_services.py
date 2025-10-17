#!/usr/bin/env python
# list_services.py
import click
import logging
import subprocess
import json

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_command(cmd):
    """Helper function to run a command and return its output."""
    logging.info(f"> {cmd}")
    try:
        # Using check_output to capture stdout and raise an exception on non-zero exit codes
        result = subprocess.check_output(
            cmd, shell=True, stderr=subprocess.PIPE, text=True
        )
        return result.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}:\n{e.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")


@click.command()
@click.option(
    "--project-id",
    required=True,
    envvar="GCLOUD_PROJECT",
    help="Your GCP project ID. Can be set via GCLOUD_PROJECT env var.",
)
def list_services(project_id):
    """
    Lists all Cloud Run services and their URLs for a given GCP project.
    """
    try:
        logging.info(f"Fetching services for project '{project_id}'...")
        # The --format="json" flag returns machine-readable output
        list_cmd = f'gcloud run services list --project="{project_id}" --format="json"'

        services_json_str = run_command(list_cmd)

        if not services_json_str:
            logging.info("No services found in this project.")
            return

        services = json.loads(services_json_str)

        if not services:
            logging.info("No services found in this project.")
            return

        click.echo("\n--- Deployed Cloud Run Services ---")
        # Format the output for readability
        for service in services:
            name = service.get("metadata", {}).get("name", "N/A")
            region = (
                service.get("metadata", {})
                .get("labels", {})
                .get("cloud.googleapis.com/location", "N/A")
            )
            url = service.get("status", {}).get("url", "N/A")

            click.echo(f"  - Service: {name}")
            click.echo(f"    Region:  {region}")
            click.echo(f"    URL:     {url}")
            click.echo("-" * 35)

    except RuntimeError:
        logging.error(
            "Failed to list services. Please check your gcloud authentication and permissions."
        )
    except json.JSONDecodeError:
        logging.error(
            "Failed to parse the output from gcloud. The command may have changed."
        )


if __name__ == "__main__":
    list_services()
