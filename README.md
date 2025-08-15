# statlas-content-service

A comprehensive HTTP service for managing geographic reference data, landmarks, points of interest, and administrative boundaries, backed by Google Cloud Firestore.

## Overview

The Statlas Content Service provides structured geographic and cultural content that enriches the core grid system with meaningful context:

- **Geographic Reference Data**: Countries, states, cities with official names, codes, and boundaries
- **Landmarks & Monuments**: Famous locations with precise coordinates and achievement integration
- **Points of Interest**: Restaurants (including Michelin), museums, cultural attractions
- **Administrative Boundaries**: Polygon definitions for countries, cities, parks, and special areas
- **Multi-language Support**: Localized content with translations
- **Achievement Integration**: Landmark-based achievements with points and rarity systems

- Listens on port `8083`
- Stores content in Firestore database `statlas-content`
- Collections: `countries/`, `states/`, `cities/`, `landmarks/`, `boundaries/`, `restaurants/`, etc.
- Endpoints:
  - `GET /countries` — list all countries with flags and basic info
  - `GET /countries/bulk` — enhanced bulk country data with continent, territory info (for Core Service)
  - `GET /landmarks` — search landmarks with filters
  - `GET /landmarks/nearby` — find landmarks near coordinates
  - `GET /boundaries/containing` — find boundaries containing a point
  - `POST /boundaries/batch-lookup` — bulk boundary queries (for Core Service)
  - `GET /achievements/definitions` — get all achievement definitions
  - `GET /health` — health check

## Requirements

- Go 1.24+
- Google Cloud project with Firestore enabled
- Service Account with Firestore permissions (e.g., roles/datastore.user)

## Environment variables

- `GOOGLE_CLOUD_PROJECT` — your GCP project ID
- `GOOGLE_APPLICATION_CREDENTIALS` — absolute path to your service account JSON credentials (not needed on Cloud Run)
- `SERVICE_SECRET` — shared secret for service-to-service authentication (optional for local dev)
- `CORS_ALLOWED_ORIGIN` — allowed origin for CORS requests (optional, defaults to production web app)
- `CDN_BASE_URL` — base URL for content assets (flags, images) (optional, defaults to placeholder)

Example:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"  # Local only
export SERVICE_SECRET="your-shared-secret-here"  # For service auth
export CORS_ALLOWED_ORIGIN="https://your-web-app-domain.com"  # Optional
export CDN_BASE_URL="https://cdn.statlas.com"  # Optional
```

## Run locally

```bash
go run main.go
```

Health check:

```bash
curl http://localhost:8083/health
# -> OK
```

## API

### CORS Support

The service includes CORS middleware for web application integration:
- **Preflight requests**: OPTIONS requests handled automatically with 200 OK
- **Allowed origins**: Configurable via `CORS_ALLOWED_ORIGIN` environment variable
- **Authentication**: OPTIONS requests bypass authentication, actual requests require `X-Service-Auth`
- **Headers**: Supports `Content-Type`, `Authorization`, and `X-Service-Auth` headers
- **Production default**: `https://statlas-web-app-aleilqeyua-uc.a.run.app`

### Geographic Reference Data

Get all countries:

```bash
curl -H "X-Service-Auth: your-shared-secret-here" \
  http://localhost:8083/countries
```

Response (200):

```json
{
  "countries": [
    {
      "id": "usa",
      "name": "United States",
      "iso_alpha2": "US",
      "iso_alpha3": "USA", 
      "flag_url": "https://cdn.statlas.com/flags/usa.svg",
      "flag_emoji": "🇺🇸",
      "capital": "Washington, D.C.",
      "population": 331893745,
      "area_km2": 9833517,
      "landmarks_count": 1247
    }
  ]
}
```

Get country details:

```bash
curl -H "X-Service-Auth: your-shared-secret-here" \
  http://localhost:8083/countries/usa
```

### Landmarks & Points of Interest

Search landmarks:

```bash
curl -H "X-Service-Auth: your-shared-secret-here" \
  "http://localhost:8083/landmarks?country=usa&type=monument&limit=10"
```

Get landmarks near coordinates:

```bash
curl -H "X-Service-Auth: your-shared-secret-here" \
  "http://localhost:8083/landmarks/nearby?lat=40.7128&lon=-74.0060&radius=1000"
```

Response (200):

```json
{
  "landmarks": [
    {
      "id": "statue_of_liberty",
      "name": "Statue of Liberty",
      "type": "monument",
      "coordinates": {
        "lat": 40.6892494,
        "lon": -74.0445004
      },
      "precision_radius_meters": 30,
      "distance_meters": 2847,
      "achievement": {
        "id": "statue_of_liberty_visitor",
        "title": "Lady Liberty",
        "points": 50,
        "rarity": "uncommon"
      },
      "visiting_info": {
        "hours": {"monday": {"open": "08:30", "close": "18:00"}},
        "admission": {"adult_price": {"amount": 23.50, "currency": "USD"}}
      }
    }
  ]
}
```

### Boundaries & Geographic Features

Find boundaries containing a point:

```bash
curl -H "X-Service-Auth: your-shared-secret-here" \
  "http://localhost:8083/boundaries/containing?lat=40.7128&lon=-74.0060"
```

Response (200):

```json
{
  "boundaries": [
    {
      "id": "usa",
      "name": "United States", 
      "type": "country",
      "level": 0,
      "resolution_requirement": "1km"
    },
    {
      "id": "ny_usa",
      "name": "New York",
      "type": "state", 
      "level": 1,
      "resolution_requirement": "100m"
    },
    {
      "id": "manhattan_core",
      "name": "Manhattan",
      "type": "borough",
      "level": 3,
      "resolution_requirement": "100m"
    }
  ]
}
```

### Bulk Integration APIs

Batch boundary lookup (for Core Service integration):

```bash
curl -X POST http://localhost:8083/boundaries/batch-lookup \
  -H "Content-Type: application/json" \
  -H "X-Service-Auth: your-shared-secret-here" \
  -d '{
    "points": [
      {"lat": 40.7128, "lon": -74.0060, "square_id": "sq_manhattan_123"},
      {"lat": 48.8566, "lon": 2.3522, "square_id": "sq_paris_456"}
    ]
  }'
```

Response (200):

```json
{
  "results": [
    {
      "square_id": "sq_manhattan_123",
      "boundary_tags": ["usa", "new_york", "nyc", "manhattan"],
      "resolution": "100m",
      "landmarks_nearby": ["statue_of_liberty", "empire_state_building"]
    },
    {
      "square_id": "sq_paris_456",
      "boundary_tags": ["france", "ile_de_france", "paris"], 
      "resolution": "100m",
      "landmarks_nearby": ["eiffel_tower", "louvre"]
    }
  ]
}
```

### Achievement System

Get all achievement definitions:

```bash
curl -H "X-Service-Auth: your-shared-secret-here" \
  http://localhost:8083/achievements/definitions
```

Response (200):

```json
{
  "achievements": [
    {
      "id": "statue_of_liberty_visitor",
      "title": "Lady Liberty",
      "description": "Visit the iconic Statue of Liberty",
      "points": 50,
      "rarity": "uncommon",
      "category": "landmarks",
      "landmark_id": "statue_of_liberty",
      "precision_radius_meters": 30,
      "unlock_message": "You've visited one of America's most iconic symbols!"
    }
  ]
}
```

## Docker

Build:

```bash
docker build -t statlas-content-service .
```

Run:

```bash
docker run --rm \
  -p 8083:8083 \
  -e GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT" \
  -e GOOGLE_APPLICATION_CREDENTIALS="/creds/service-account.json" \
  -v /absolute/path/to/service-account.json:/creds/service-account.json:ro \
  statlas-content-service
```

## Testing

```bash
go test ./...
```

## Deployment

For detailed deployment instructions to Google Cloud Run, see [DEPLOY.md](./DEPLOY.md).

### First-time setup:
```bash
# Run once to set up your GCP project
export PROJECT_ID="your-gcp-project-id"
./setup-gcp.sh
```

### Quick deployment:
```bash
export PROJECT_ID="your-gcp-project-id"
PROJECT_ID=$PROJECT_ID make deploy
```

## Data Management

### Content Population

The service provides scripts and tools for populating content:

```bash
# Install Python dependencies for data scripts
pip install -r requirements.txt

# Import world countries with flags and basic data
python3 scripts/import_countries.py --project-id your-project-id

# Import major world landmarks
python3 scripts/import_landmarks.py --project-id your-project-id

# Import Michelin restaurant data
python3 scripts/import_michelin_restaurants.py --project-id your-project-id

# Import administrative boundaries
python3 scripts/import_boundaries.py --project-id your-project-id
```

### Content Sources

- **Countries**: Based on ISO 3166-1 standard with UN demographic data
- **Landmarks**: Curated from UNESCO, TripAdvisor, and Wikipedia
- **Restaurants**: Michelin Guide official data and OpenStreetMap
- **Boundaries**: OpenStreetMap and Natural Earth datasets
- **Administrative Boundaries**: GADM (Global Administrative Areas) dataset
- **Flags**: Public domain SVG flags from appropriate sources

### Administrative Boundary Coverage

The service provides **9-tier hierarchical administrative boundaries**:

#### ✅ **Natural Earth Data (Global Coverage)**
- **Sovereign States** (e.g., France and territories)
- **Countries** (e.g., Greenland separate from Denmark)  
- **Map Units** (e.g., England, Wales, Scotland, Northern Ireland)
- **Map Subunits** (e.g., mainland France vs. Corsica)

#### ✅ **GADM Data (170+ Countries)**
- **Admin Level 1** (States, Provinces, Regions)
- **Admin Level 2** (Counties, Districts)
- **Admin Level 3** (Municipalities, Cities)
- **Admin Level 4** (Wards, Villages)
- **Admin Level 5** (Neighborhoods, Sectors)

#### ⚠️ **GADM Limitations**
**22 countries excluded** due to Firestore geometry size limits:
- Large countries: Russia, Canada, USA, China, Brazil, Australia, India
- Desert nations: Algeria, Sudan, Libya, Chad, Niger, Angola
- See [`docs/EXCLUDED_COUNTRIES_GADM.md`](docs/EXCLUDED_COUNTRIES_GADM.md) for complete list

**Impact**: Users in excluded countries get Natural Earth boundaries only (no sub-national administrative data).

## Implementation notes

- **Multi-language Support**: All text fields support translations via `translations/` collection
- **Achievement Integration**: Landmarks automatically generate achievement definitions
- **Geospatial Queries**: Uses Firestore composite indexes for efficient location-based queries
- **Content Versioning**: All entities track `created_at` and `updated_at` for change management
- **Service Authentication**: Requires `X-Service-Auth` header with shared secret for all endpoints except health
- **CDN Integration**: Images and assets served via configurable CDN for optimal performance

## Security

### Authentication & Authorization

- **Service-to-Service Authentication**: All endpoints (except health) require the `X-Service-Auth` header
- **Cloud Run IAM**: Service access restricted to authenticated users only
- **Strong Secrets**: Uses cryptographically secure random secrets

### Data Protection

- **Input Validation**: All coordinates and IDs validated for proper formats
- **Path Validation**: URL parameters sanitized and validated
- **Error Handling**: Secure error responses without information leakage
- **Content Moderation**: All user-generated content (reviews, descriptions) subject to moderation

## Troubleshooting

### Common Issues

1. **Missing Content**: If landmark or boundary data is missing, check data import scripts
2. **Geospatial Queries**: Ensure Firestore composite indexes are created for location queries
3. **CDN Assets**: Verify `CDN_BASE_URL` is set correctly for image and flag URLs
4. **Achievement Integration**: Check that landmark achievements are properly defined

### Performance Optimization

- **Caching**: Implement Redis caching for frequently accessed content
- **Geospatial Indexing**: Use Firestore's geospatial capabilities for location queries
- **CDN**: Serve static assets (flags, images) via CDN for faster loading
- **Query Optimization**: Use composite indexes for complex queries

### Testing the Service

```bash
# Test with correct service secret
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "X-Service-Auth: your-service-secret" \
  https://your-service-url/health

# Test landmark search
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "X-Service-Auth: your-service-secret" \
  "https://your-service-url/landmarks?country=usa&limit=5"
```

## Service Integration

### With Core Service

The Content Service provides boundary enrichment for the Core Service's grid squares:

```go
// Core Service integration example
func enrichSquareWithContent(square *Square) {
    response := contentService.BatchLookupBoundaries([]Point{
        {Lat: square.CenterLat, Lon: square.CenterLon, SquareID: square.ID}
    })
    
    square.BoundaryTags = response.Results[0].BoundaryTags
    square.Resolution = response.Results[0].Resolution
}
```

### With Profile Service

Achievement definitions are sourced from the Content Service:

```go
// Profile Service integration example
func checkLandmarkAchievements(userID string, lat, lon float64) {
    landmarks := contentService.GetLandmarksNearby(lat, lon, 50)
    
    for _, landmark := range landmarks {
        if !userHasAchievement(userID, landmark.Achievement.ID) {
            unlockAchievement(userID, landmark.Achievement)
        }
    }
}
```

This service forms the content backbone of the Statlas platform, providing rich geographic and cultural context that enhances user exploration and achievement systems! 🌍
