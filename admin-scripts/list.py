#!/usr/bin/env python3

## note: run
# ```
# gcloud auth application-default revoke
# gcloud auth application-default login
# ```
# if does not work

import click
import logging
import subprocess
import json

import tqdm
from google.cloud import run_v2
from google.api_core import exceptions
import pandas as pd


# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@click.group()
def list_():
    pass


REGIONS = ["us-east1", "us-central1"]


@list_.command()
@click.option(
    "--project-id",
    required=True,
    envvar="GCLOUD_PROJECT",
    help="Your GCP project ID. Can be set via GCLOUD_PROJECT env var.",
)
@click.option("--annotate/--no-annotate", "-A/ ")
@click.option(
    "--region",
    "-r",
    "regions",
    multiple=True,
    required=True,
    type=click.Choice(REGIONS),
    help="GCP region to check. Can be specified multiple times (e.g., --region us-east1 --region us-central1).",
)
def images(project_id, annotate, regions):
    df_images = get_images(project_id)
    if annotate:
        assert len(regions) > 0
        df_services = get_services(project_id, regions, is_loud=False)
        df_images["is_in_use"] = (
            df_images["version"]
            .str.removeprefix("sha256:")
            .isin(df_services["Digest sha256"])
        )
        logging.info(df_images["is_in_use"].value_counts())

    df_images.to_parquet("/tmp/df_images.prq")
    click.echo(df_images)


def get_images(project_id: str) -> pd.DataFrame:
    cmd = (
        f"gcloud artifacts docker images list us-docker.pkg.dev/{project_id}/gcr.io "
        "--sort-by=~createTime "
        f'--format="json" --project {project_id}'
    )
    ec, out = subprocess.getstatusoutput(cmd)
    assert ec == 0, (cmd, ec, out)

    out = out.split("\n\n")[-1]
    try:
        out = json.loads(out)
    except json.decoder.JSONDecodeError as jde:
        logging.error(jde)
        logging.error(out)
    df_images = pd.DataFrame(out)
    return df_images


@list_.command()
@click.option(
    "--project-id",
    required=True,
    envvar="GCLOUD_PROJECT",
    help="Your GCP project ID. Can be set via GCLOUD_PROJECT env var.",
)
@click.option(
    "--region",
    "-r",
    "regions",
    multiple=True,
    required=True,
    type=click.Choice(REGIONS),
    help="GCP region to check. Can be specified multiple times (e.g., --region us-east1 --region us-central1).",
)
def services(project_id, regions):
    """
    Lists Cloud Run services, URLs, active image, and image digest
    for a given GCP project in the specified regions.
    """
    try:
        # Iterate through the regions provided on the command line
        df_services = get_services(project_id, regions)
        df_services.to_parquet("/tmp/df_services.prq")
        click.echo(df_services.to_string())
    except exceptions.PermissionDenied:
        logging.error(
            "Permission denied. Ensure the Cloud Run Admin API is enabled and you have the 'Cloud Run Viewer' role."
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)


def get_services(
    project_id: str, regions: list[str], is_loud: bool = True
) -> pd.DataFrame:
    services_client = run_v2.ServicesClient()
    # --- NEW: Client for fetching revision details ---
    revisions_client = run_v2.RevisionsClient()
    # -----------------------------------------------
    all_services_data = []  # Store tuples of (service, revision)

    services = []
    for loc in regions:
        # get_services(loc)
        logging.info(f"Checking for services in region: {loc}...")
        parent = f"projects/{project_id}/locations/{loc}"

        try:
            # List the services in the current region
            list_request = run_v2.ListServicesRequest(parent=parent)
            for service in tqdm.tqdm(
                services_client.list_services(request=list_request),
                desc="list_services",
            ):
                latest_revision_name = service.latest_ready_revision
                revision_detail = None
                if latest_revision_name:
                    try:
                        # --- NEW: Fetch the specific revision details ---
                        revision_request = run_v2.GetRevisionRequest(
                            name=latest_revision_name
                        )
                        revision_detail = revisions_client.get_revision(
                            request=revision_request
                        )
                        # -----------------------------------------------
                    except exceptions.NotFound:
                        logging.warning(
                            f"Could not find revision {latest_revision_name} for service {service.name.split('/')[-1]}."
                        )
                    except exceptions.PermissionDenied:
                        logging.warning(
                            f"Permission denied to get revision details for service {service.name.split('/')[-1]}."
                        )

                all_services_data.append((service, revision_detail))

        except exceptions.PermissionDenied:
            logging.warning(f"Permission denied to list services in {loc}. Skipping.")
            continue

    if not all_services_data:
        logging.info("No services found in the specified regions.")
        return

    if is_loud:
        click.echo("\n--- Deployed Cloud Run Services ---")
    for service, revision in all_services_data:
        name = service.name.split("/")[-1]
        region_name = service.name.split("/")[-3]
        url = service.uri

        # Get image name from the service template (as fallback or reference)
        template_image = "N/A"
        if (
            service.template
            and service.template.containers
            and len(service.template.containers) > 0
        ):
            template_image = service.template.containers[0].image

        # --- NEW: Get image digest from the fetched revision ---
        image_digest = "N/A"
        # The actual running image digest is in the revision details
        if revision and revision.containers and len(revision.containers) > 0:
            # The image name in revision might include the digest already
            # e.g., gcr.io/proj/img@sha256:abc...
            # Or sometimes just the tag is shown, digest needs separate query (less common now)
            full_image_name = revision.containers[0].image
            if "@sha256:" in full_image_name:
                image_digest = full_image_name.split("@sha256:")[-1]
            else:
                # Fallback if digest isn't in the main image string
                # This might require another API call in rare cases,
                # but usually the digest is part of the image name in the Revision object.
                image_digest = "(Digest not directly available in image name)"
        # --------------------------------------------------------

        # click.echo(f"  - Service: {name}")
        # click.echo(f"    Region:  {region_name}")
        # click.echo(f"    URL:     {url}")
        # click.echo(
        #     f"    Image:   {template_image}"
        # )  # Shows image name:tag used for deployment
        # # --- NEW: Print the digest ---
        # click.echo(
        #     f"    Digest:  sha256:{image_digest}"
        # )  # Shows the exact running image hash
        # # ---------------------------
        # click.echo("-" * 35)
        services.append(
            {
                "Service": name,
                "Region": region_name,
                "URL": url,
                "Image": template_image,
                "Digest sha256": image_digest,
            }
        )
    df_services = pd.DataFrame(services)
    return df_services
    # click.echo(df_services.to_string())


if __name__ == "__main__":
    list_()
