.PHONY: deploy push build secrets

DOCKER_IMAGE_VERSION = v16
DOCKER_USER = nailbiter
DOCKER_IMAGE = 20250628-gemini-telegram-gcp

build:
	docker build -t $(DOCKER_USER)/$(DOCKER_IMAGE):$(DOCKER_IMAGE_VERSION) .
push:
	docker push $(DOCKER_USER)/$(DOCKER_IMAGE):$(DOCKER_IMAGE_VERSION)
deploy:
	gcloud run deploy gemini-telegram-gcp \
	--image=nailbiter/$(DOCKER_IMAGE):$(DOCKER_IMAGE_VERSION) \
	--set-env-vars=$(SET_ENV_VARS) \
	--set-secrets=TELEGRAM_BOT_TOKEN=20250628-telegram-token-alex-gemini-bot:latest,GEMINI_API_KEY=20250628-gemini-key:latest \
	--region=us-central1 \
	--project=$(GCLOUD_PROJECT_ID)
	gcloud run services update-traffic gemini-telegram-gcp --to-latest
secrets:
	gcloud secrets add-iam-policy-binding 20250628-gemini-key \
    --member=$(SERVICE_ACCOUNT) \
    --role="roles/secretmanager.secretAccessor" \
    --project=$(GCLOUD_PROJECT_ID)
