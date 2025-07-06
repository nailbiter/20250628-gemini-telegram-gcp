.PHONY: deploy build

DOCKER_IMAGE_VERSION = v13

build:
	docker build -t 20250628-gemini-telegram-gcp:$(DOCKER_IMAGE_VERSION) .
deploy:
	docker push 20250628-gemini-telegram-gcp:$(DOCKER_IMAGE_VERSION)
	gcloud run deploy gemini-telegram-gcp \
	--image=nailbiter/20250628-gemini-telegram-gcp:$(DOCKER_IMAGE_VERSION) \
	--set-env-vars=$SET_ENV_VARS \
	--set-secrets=TELEGRAM_BOT_TOKEN=20250628-telegram-token-alex-gemini-bot:latest,GEMINI_API_KEY=20250628-gemini-key:latest \
	--region=us-central1 \
	--project=$GCLOUD_PROJECT_ID 
	gcloud run services update-traffic gemini-telegram-gcp --to-latest
