#!/usr/bin/env python3

## note: run
# ```
# gcloud auth application-default revoke
# gcloud auth application-default login
# ```
# if does not work

import click
import logging
from google.cloud import run_v2
from google.api_core import exceptions

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@click.command()
@click.option(
    "--project-id",
    required=True,
    envvar="GCLOUD_PROJECT",
    help="Your GCP project ID. Can be set via GCLOUD_PROJECT env var.",
)
@click.option(
    "--region",
    multiple=True,
    required=True,
    help="GCP region to check. Can be specified multiple times (e.g., --region us-east1 --region us-central1).",
)
def list_services(project_id, region):
    """
    Lists all Cloud Run services and their URLs for a given GCP project in the specified regions.
    """
    try:
        client = run_v2.ServicesClient()
        all_services = []

        # Iterate through the regions provided on the command line
        for loc in region:
            logging.info(f"Checking for services in region: {loc}...")
            parent = f"projects/{project_id}/locations/{loc}"

            try:
                # List the services in the current region
                list_request = run_v2.ListServicesRequest(parent=parent)
                for service in client.list_services(request=list_request):
                    all_services.append(service)
            except exceptions.PermissionDenied:
                logging.warning(
                    f"Permission denied to list services in {loc}. Skipping."
                )
                continue

        if not all_services:
            logging.info("No services found in the specified regions.")
            return

        click.echo("\n--- Deployed Cloud Run Services ---")
        for service in all_services:
            name = service.name.split("/")[-1]
            region_name = service.name.split("/")[-3]  # Get region from the full name
            url = service.uri

            click.echo(f"  - Service: {name}")
            click.echo(f"    Region:  {region_name}")
            click.echo(f"    URL:     {url}")
            click.echo("-" * 35)

    except exceptions.PermissionDenied:
        logging.error(
            "Permission denied. Ensure the Cloud Run Admin API is enabled and you have the 'Cloud Run Viewer' role."
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    list_services()
