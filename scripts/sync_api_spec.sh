#!/bin/bash

# sync_api_spec.sh
# Automatically sync API specification to dependent services

set -e

echo "🔄 Syncing API specification to dependent services..."

# Configuration
CONTENT_SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_SPEC_FILE="$CONTENT_SERVICE_DIR/scripts/api-spec.json"

# Check if API spec exists
if [ ! -f "$API_SPEC_FILE" ]; then
    echo "❌ API spec not found. Generating it first..."
    cd "$CONTENT_SERVICE_DIR/scripts"
    python3 generate_api_spec.py
fi

# Function to sync to a service
sync_to_service() {
    local service_name=$1
    local service_path=$2
    
    if [ -d "$service_path" ]; then
        echo "📁 Syncing to $service_name..."
        
        # Create dependencies directory if it doesn't exist
        mkdir -p "$service_path/docs/dependencies"
        
        # Copy API spec
        cp "$API_SPEC_FILE" "$service_path/docs/dependencies/content-service-api.json"
        
        # Update timestamp file
        echo "$(date -Iseconds)" > "$service_path/docs/dependencies/content-service-api-updated.txt"
        
        echo "✅ $service_name updated successfully"
    else
        echo "⚠️  $service_name not found at $service_path (skipping)"
    fi
}

# Sync to core-service
CORE_SERVICE_PATH="../statlas-core-service"
sync_to_service "Core Service" "$CORE_SERVICE_PATH"

# Sync to web-app
WEB_APP_PATH="../statlas-web-app"
sync_to_service "Web App" "$WEB_APP_PATH"

# Sync to any other services (add as needed)
# ADMIN_SERVICE_PATH="../statlas-admin-service"
# sync_to_service "Admin Service" "$ADMIN_SERVICE_PATH"

echo ""
echo "🎉 API specification sync complete!"
echo ""
echo "📋 Next steps for dependent services:"
echo "   1. Commit the updated API spec files"
echo "   2. Tell AI assistants to read docs/dependencies/content-service-api.json"
echo "   3. Use the API spec for integration and testing"
echo ""
echo "🔗 API spec location in dependent services:"
echo "   docs/dependencies/content-service-api.json"
