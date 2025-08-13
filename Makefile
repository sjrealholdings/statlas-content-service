# Makefile for statlas-content-service

# Variables
PROJECT_ID ?= statlas-467715
SERVICE_NAME = statlas-content-service
REGION = us-central1
IMAGE_URI = $(REGION)-docker.pkg.dev/$(PROJECT_ID)/statlas-services/$(SERVICE_NAME):latest

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build        - Build the Go application"
	@echo "  test         - Run tests"
	@echo "  docker-build - Build Docker image locally"
	@echo "  docker-run   - Run Docker container locally"
	@echo "  deploy       - Deploy to Google Cloud Run"
	@echo "  setup-gcp    - Set up GCP project and services"
	@echo "  clean        - Clean build artifacts"

# Build the Go application
.PHONY: build
build:
	go build -o bin/main .

# Run tests
.PHONY: test
test:
	go test ./...

# Build Docker image locally
.PHONY: docker-build
docker-build:
	docker build -t $(SERVICE_NAME) .

# Run Docker container locally
.PHONY: docker-run
docker-run:
	docker run --rm \
		-p 8083:8083 \
		-e GOOGLE_CLOUD_PROJECT="$(PROJECT_ID)" \
		-e GOOGLE_APPLICATION_CREDENTIALS="/creds/service-account.json" \
		-v $(HOME)/.config/gcloud/application_default_credentials.json:/creds/service-account.json:ro \
		$(SERVICE_NAME)

# Deploy to Google Cloud Run
.PHONY: deploy
deploy:
	@echo "Deploying $(SERVICE_NAME) to project $(PROJECT_ID)..."
	# Build and push using Cloud Build
	gcloud builds submit --tag $(IMAGE_URI) --project $(PROJECT_ID)
	
	# Deploy to Cloud Run
	gcloud run deploy $(SERVICE_NAME) \
		--image $(IMAGE_URI) \
		--platform managed \
		--region $(REGION) \
		--set-env-vars GOOGLE_CLOUD_PROJECT=$(PROJECT_ID),CORS_ALLOWED_ORIGIN="https://statlas-web-app-aleilqeyua-uc.a.run.app" \
		--port 8083 \
		--memory 1Gi \
		--cpu 1 \
		--max-instances 10 \
		--allow-unauthenticated \
		--project $(PROJECT_ID)
	
	@echo "Deployment complete!"
	@echo "Service URL: https://$(SERVICE_NAME)-aleilqeyua-uc.a.run.app"

# Set up GCP project and services
.PHONY: setup-gcp
setup-gcp:
	@echo "Setting up GCP project $(PROJECT_ID)..."
	./setup-gcp.sh $(PROJECT_ID)

# Clean build artifacts
.PHONY: clean
clean:
	rm -rf bin/
	docker rmi $(SERVICE_NAME) 2>/dev/null || true

# Development helpers
.PHONY: run
run:
	go run main.go

.PHONY: fmt
fmt:
	go fmt ./...

.PHONY: vet
vet:
	go vet ./...

.PHONY: mod-tidy
mod-tidy:
	go mod tidy

# Database setup
.PHONY: setup-database
setup-database:
	@echo "Setting up statlas-content Firestore database..."
	gcloud firestore databases create --database=statlas-content --location=nam5 --type=firestore-native --project=$(PROJECT_ID)
	@echo "Database setup complete!"

# Import sample data
.PHONY: import-sample-data
import-sample-data:
	@echo "Importing sample content data..."
	python3 scripts/import_sample_countries.py --project-id $(PROJECT_ID)
	python3 scripts/import_sample_landmarks.py --project-id $(PROJECT_ID)
	@echo "Sample data import complete!"
