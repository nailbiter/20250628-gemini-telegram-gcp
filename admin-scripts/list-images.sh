#!/bin/sh

gcloud artifacts docker images list us-docker.pkg.dev/$GCLOUD_PROJECT/gcr.io \
  --sort-by=~createTime \
  --format="json" --project $GCLOUD_PROJECT
