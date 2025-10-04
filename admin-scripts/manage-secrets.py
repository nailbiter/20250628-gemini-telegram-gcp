#!/usr/bin/env python
"""===============================================================================

        FILE: /Users/nailbiter/Documents/forgithub/20250628-gemini-telegram-gcp/admin-scripts/manage-secrets.py

       USAGE: (not intended to be directly executed)

 DESCRIPTION: 

     OPTIONS: ---
REQUIREMENTS: ---
        BUGS: ---
       NOTES: ---
      AUTHOR: Alex Leontiev (alozz1991@gmail.com)
ORGANIZATION: 
     VERSION: ---
     CREATED: 2025-10-04T14:18:06.996816
    REVISION: ---

==============================================================================="""

import click

# from dotenv import load_dotenv
import os
from os import path
import logging

import os
import click
from dotenv import load_dotenv
from google.cloud import secretmanager
from google.api_core import exceptions

# Load environment variables from a .env file at script startup
load_dotenv()


@click.command(context_settings=dict(auto_envvar_prefix="SECRET_TOOL"))
@click.option(
    "--project-id",
    required=True,
    help="Your GCP project ID. Can be set via SECRET_TOOL_PROJECT_ID.",
)
@click.option("--secret-name", required=True, help="The name for your secret in GCP.")
@click.option(
    "--env-var",
    required=True,
    help="The name of the environment variable holding the secret value.",
)
@click.option(
    "--service-account",
    required=True,
    help="The service account to grant access to. Set via SECRET_TOOL_SERVICE_ACCOUNT.",
)
def add(project_id, secret_name, env_var, service_account):
    """
    Creates/updates a secret and grants the default service account access.
    """
    # Part 1: Read the secret value from the environment
    secret_value = os.getenv(env_var)
    if not secret_value:
        click.secho(
            f"❌ Error: Environment variable '{env_var}' not found or is empty.",
            fg="red",
        )
        return

    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}"
    secret_path = f"{parent}/secrets/{secret_name}"

    # Part 2: Create the secret container if it doesn't exist
    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_name,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        click.secho(f"✅ Secret '{secret_name}' created.", fg="green")
    except exceptions.AlreadyExists:
        click.secho(
            f"ℹ️ Secret '{secret_name}' already exists. Updating version and permissions.",
            fg="yellow",
        )
    except Exception as e:
        click.secho(f"❌ Error creating secret: {e}", fg="red")
        return

    # Part 3: Add the new secret version
    try:
        payload = secret_value.encode("UTF-8")
        response = client.add_secret_version(
            request={"parent": secret_path, "payload": {"data": payload}}
        )
        version_id = response.name.split("/")[-1]
        click.secho(
            f"✅ Added new version ({version_id}) for secret '{secret_name}'.",
            fg="green",
        )
    except Exception as e:
        click.secho(f"❌ Error adding secret version: {e}", fg="red")
        return

    # Part 4: Grant the service account access
    try:
        policy = client.get_iam_policy(request={"resource": secret_path})
        role = "roles/secretmanager.secretAccessor"
        binding = {"role": role, "members": [f"serviceAccount:{service_account}"]}

        if binding in policy.bindings:
            click.secho(
                f"ℹ️ Service account already has access to '{secret_name}'.",
                fg="yellow",
            )
            return

        policy.bindings.append(binding)
        client.set_iam_policy(request={"resource": secret_path, "policy": policy})
        click.secho(
            f"✅ Granted access for '{service_account}' to secret '{secret_name}'.",
            fg="green",
        )
    except Exception as e:
        click.secho(f"❌ An error occurred while setting IAM policy: {e}", fg="red")


if __name__ == "__main__":
    add()
