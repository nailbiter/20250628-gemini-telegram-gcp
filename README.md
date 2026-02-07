## deployment

## build

```
gcloud builds submit --tag gcr.io/$GCLOUD_PROJECT/py-assistant-bot
```

## deploy

(works from new Mac or Cloud Shell)

### actor experimental

```
./admin-scripts/deploy-functions.py -n time-react-service-experimental -s actor_server_experimental.py -C uvicorn
```

## housekeeping

### cleanup

to see what will be removed use

```
./admin-scripts/list.py images -r us-east1 -AP
```

add `-F` for force
