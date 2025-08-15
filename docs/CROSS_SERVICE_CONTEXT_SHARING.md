# Cross-Service Context Sharing Strategy

## Overview

This document outlines automated approaches to ensure that AI assistants working on other services (like core-service) always have up-to-date context about the content-service APIs and functionality.

## 🔄 **Automated Context Sharing Solutions**

### **Option 1: OpenAPI Specification (Recommended)**

**What it is**: Machine-readable API documentation that auto-updates

**Implementation**:
```bash
# Generate API specs automatically
cd statlas-content-service/scripts
python3 generate_api_spec.py

# Files created:
# - api-spec.json (machine-readable)
# - api-spec.yaml (human-readable)
```

**Usage in other services**:
- Place `api-spec.json` in the core-service repository
- AI assistant can read this file to understand all content-service endpoints
- Automatically stays in sync when you regenerate the spec

**Benefits**:
- ✅ Machine-readable format
- ✅ Standardized OpenAPI 3.0 format
- ✅ Can generate client SDKs automatically
- ✅ Works with Postman, Swagger UI, etc.

### **Option 2: Shared Documentation Repository**

**What it is**: Central docs repo that all services reference

**Implementation**:
```bash
# Create shared docs repo
mkdir statlas-platform-docs
cd statlas-platform-docs

# Structure:
# ├── services/
# │   ├── content-service/
# │   │   ├── api-endpoints.md
# │   │   ├── data-models.md
# │   │   └── integration-guide.md
# │   ├── core-service/
# │   └── web-app/
# └── shared/
#     ├── authentication.md
#     └── deployment.md
```

**Usage**:
- Each service includes relevant docs as git submodules
- AI assistant reads from shared documentation
- Updates propagate across all services

### **Option 3: Service Registry with Metadata**

**What it is**: Automated service discovery with API metadata

**Implementation**:
```json
{
  "services": {
    "content-service": {
      "url": "https://statlas-content-service-1064925383001.us-central1.run.app",
      "version": "1.0.0",
      "endpoints": {
        "countries_bulk": "/countries/bulk",
        "country_polygon": "/polygons/country/{id}",
        "continent_polygons": "/polygons/continent/{continent}",
        "world_polygons": "/polygons/world"
      },
      "last_updated": "2025-08-15T11:42:08Z"
    }
  }
}
```

### **Option 4: GitHub Actions Integration (Automated)**

**What it is**: Automatically sync documentation on code changes

**Implementation**:
```yaml
# .github/workflows/sync-docs.yml
name: Sync API Documentation
on:
  push:
    branches: [main]
    paths: ['main.go', 'docs/**']

jobs:
  sync-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate API Spec
        run: |
          cd scripts
          python3 generate_api_spec.py
          
      - name: Update Core Service
        uses: dmnemec/copy_file_to_another_repo_action@main
        env:
          API_TOKEN_GITHUB: ${{ secrets.API_TOKEN_GITHUB }}
        with:
          source_file: 'scripts/api-spec.json'
          destination_repo: 'sjrealholdings/statlas-core-service'
          destination_folder: 'docs/dependencies/'
          user_email: 'actions@github.com'
          user_name: 'GitHub Actions'
```

## 🎯 **Recommended Implementation**

### **Phase 1: Immediate (5 minutes)**

1. **Copy API spec to core-service**:
```bash
# In core-service repository
mkdir -p docs/dependencies/
cp ../statlas-content-service/scripts/api-spec.json docs/dependencies/content-service-api.json
```

2. **Add to core-service README**:
```markdown
## Service Dependencies

This service integrates with:
- **Content Service**: See [API spec](docs/dependencies/content-service-api.json)
```

### **Phase 2: Automation (15 minutes)**

1. **Add to content-service build process**:
```bash
# Add to Makefile
generate-docs:
	cd scripts && python3 generate_api_spec.py
	
# Add to deployment
deploy: generate-docs
	# ... existing deployment steps
```

2. **Create update script**:
```bash
#!/bin/bash
# scripts/update-dependent-services.sh
echo "Updating dependent services with latest API spec..."

# Update core-service
cp api-spec.json ../../statlas-core-service/docs/dependencies/content-service-api.json

# Update web-app  
cp api-spec.json ../../statlas-web-app/docs/dependencies/content-service-api.json

echo "✅ API specs updated in dependent services"
```

### **Phase 3: Full Automation (30 minutes)**

Set up GitHub Actions to automatically sync documentation across repositories.

## 📋 **Current Content Service Context**

### **Key Endpoints for Core Service**:

```json
{
  "bulk_countries": {
    "endpoint": "/countries/bulk",
    "purpose": "Enhanced country data with continent and territory info",
    "returns": "263 countries with sovereignty relationships"
  },
  "country_polygon": {
    "endpoint": "/polygons/country/{id}",
    "purpose": "Individual country polygon for mapping",
    "returns": "GeoJSON string with bounds"
  },
  "continent_polygons": {
    "endpoint": "/polygons/continent/{continent}",
    "purpose": "All countries in a continent for regional maps",
    "returns": "Array of country polygons"
  },
  "world_polygons": {
    "endpoint": "/polygons/world",
    "purpose": "All world countries for global map",
    "returns": "257 country polygons with continent data"
  }
}
```

### **Data Models**:
- **Country**: Enhanced with `continent`, `is_territory`, `sovereign_state_name`
- **Polygon**: GeoJSON string with bounds for efficient rendering
- **No Double-Counting**: Only queries `countries` collection

### **Authentication**: 
- Service-to-service bearer token required
- Same auth mechanism as other endpoints

## 🚀 **Next Steps**

1. **Immediate**: Copy `api-spec.json` to core-service
2. **Short-term**: Add API spec generation to build process  
3. **Long-term**: Set up automated cross-repo documentation sync

This ensures that whenever you make changes to content-service, the core-service AI assistant automatically has the latest context about available endpoints and data structures.
