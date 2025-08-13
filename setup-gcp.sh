#!/bin/bash

# Setup script for statlas-content-service GCP resources
# Usage: ./setup-gcp.sh [PROJECT_ID]

set -e

PROJECT_ID=${1:-$GOOGLE_CLOUD_PROJECT}

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID not provided"
    echo "Usage: $0 PROJECT_ID"
    echo "   or: export GOOGLE_CLOUD_PROJECT=your-project-id && $0"
    exit 1
fi

echo "🚀 Setting up GCP resources for statlas-content-service"
echo "📋 Project ID: $PROJECT_ID"
echo ""

# Set the project
echo "📌 Setting active project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo "📦 Setting up Artifact Registry..."
if ! gcloud artifacts repositories describe statlas-services --location=us-central1 --project=$PROJECT_ID &>/dev/null; then
    echo "Creating Artifact Registry repository..."
    gcloud artifacts repositories create statlas-services \
        --repository-format=docker \
        --location=us-central1 \
        --project=$PROJECT_ID
else
    echo "Artifact Registry repository already exists"
fi

# Configure Docker authentication
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker us-central1-docker.pkg.dev

# Create statlas-content Firestore database
echo "🗄️  Setting up Firestore database..."
if ! gcloud firestore databases describe --database=statlas-content --project=$PROJECT_ID &>/dev/null; then
    echo "Creating statlas-content Firestore database..."
    gcloud firestore databases create \
        --database=statlas-content \
        --location=nam5 \
        --type=firestore-native \
        --project=$PROJECT_ID
    echo "✅ Database created successfully"
else
    echo "✅ statlas-content database already exists"
fi

# Grant necessary permissions
echo "🔐 Setting up IAM permissions..."

# Get the default compute service account
COMPUTE_SA="${PROJECT_ID}-compute@developer.gserviceaccount.com"

# Grant Cloud Build permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/cloudbuild.builds.builder" \
    --quiet

# Grant Firestore permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/datastore.user" \
    --quiet

# Grant Cloud Run permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/run.developer" \
    --quiet

# Grant Artifact Registry permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/artifactregistry.writer" \
    --quiet

echo ""
echo "✅ GCP setup complete!"
echo ""
echo "📋 Summary:"
echo "   • Project: $PROJECT_ID"
echo "   • Firestore database: statlas-content (nam5)"
echo "   • Artifact Registry: statlas-services (us-central1)"
echo "   • APIs enabled: Cloud Build, Cloud Run, Firestore"
echo ""
echo "🚀 Next steps:"
echo "   1. Deploy the service: make deploy"
echo "   2. Import sample data: make import-sample-data"
echo "   3. Test the endpoints: curl https://statlas-content-service-*.run.app/health"
echo ""
