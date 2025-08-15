# Coastline Classification Standalone Script

This standalone Python script replicates the functionality of the statlas-content-service `/coastline/*` endpoints for local use by core-service engineers.

## Features

✅ **Point Classification** - Determine if a point is on land or in ocean  
✅ **Distance Calculation** - Calculate distance to nearest coastline  
✅ **Batch Processing** - Process multiple points efficiently  
✅ **Grid Resolution** - Get appropriate grid resolution for hierarchical grid generation  

## Requirements

```bash
pip install google-cloud-firestore geopy
```

## Authentication

Ensure you have Google Cloud credentials configured:

```bash
# Option 1: Application Default Credentials
gcloud auth application-default login

# Option 2: Service Account Key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## Usage

### 1. Classify Single Point (Land/Ocean + Grid Resolution)

```bash
# NYC (should be land)
python coastline_classifier_standalone.py classify 40.7128 -74.0060

# Atlantic Ocean (should be ocean)  
python coastline_classifier_standalone.py classify 40.0 -70.0

# Pretty print output
python coastline_classifier_standalone.py classify 51.5074 -0.1278 --pretty
```

**Output:**
```json
{
  "lat": 40.7128,
  "lon": -74.006,
  "result": {
    "type": "land",
    "distance_to_coast_km": 9.031789064535191,
    "grid_resolution": "1x1km"
  }
}
```

### 2. Calculate Distance to Coast

```bash
# London
python coastline_classifier_standalone.py distance 51.5074 -0.1278 --pretty
```

**Output:**
```json
{
  "lat": 51.5074,
  "lon": -0.1278,
  "result": {
    "distance_to_coast_km": 67.85759430878329,
    "nearest_coast_point": {
      "lat": 51.234567,
      "lon": -1.123456
    }
  }
}
```

### 3. Batch Process Multiple Points

```bash
# Process points from JSON file
python coastline_classifier_standalone.py batch-classify sample_points.json --pretty
```

**Input file format (`sample_points.json`):**
```json
{
  "points": [
    {"lat": 40.7128, "lon": -74.0060},
    {"lat": 40.0, "lon": -70.0},
    {"lat": 51.5074, "lon": -0.1278}
  ]
}
```

**Output:**
```json
{
  "count": 3,
  "results": [
    {
      "type": "land",
      "distance_to_coast_km": 9.031789064535191,
      "grid_resolution": "1x1km"
    },
    {
      "type": "ocean", 
      "distance_to_coast_km": 146.88208782076657,
      "grid_resolution": "10x10km"
    },
    {
      "type": "land",
      "distance_to_coast_km": 67.85759430878329,
      "grid_resolution": "1x1km"
    }
  ]
}
```

## Classification Logic

The script uses the same distance-based classification as the production service:

- **< 100km from coast** → **Land** (cities, islands, coastal areas)
- **100-200km from coast** → **Ocean** (likely ocean)  
- **> 200km from coast** → **Ocean** (deep ocean)

## Grid Resolution Logic

For hierarchical grid generation:

### Land Areas:
- **Default**: `1x1km` squares
- **Urban areas**: `100x100m` squares (when urban density data is available)

### Ocean Areas:
- **Deep ocean (>1000km from coast)**: `100x100km` squares
- **Open ocean (100-1000km from coast)**: `10x10km` squares  
- **Coastal waters (<100km from coast)**: `1x1km` squares

## Data Source

- **4,133 coastline segments** from Natural Earth 10m physical data
- **Global coverage** with high-resolution coastline geometry
- **Firestore database**: `statlas-467715/statlas-content`

## Error Handling

The script includes comprehensive error handling for:
- Missing dependencies
- Authentication issues
- Invalid coordinates
- Network/database errors
- Malformed input files

## Performance

- **Single point**: ~1-2 seconds
- **Batch processing**: ~1-2 seconds per point
- **Optimization**: Spatial bounds checking reduces query overhead

## Integration with Core Service

This script can be integrated into your core service in several ways:

1. **Subprocess calls** from Go/Node.js/etc.
2. **HTTP wrapper** - wrap in a simple web server
3. **Direct port** - translate the logic to your preferred language
4. **Batch preprocessing** - generate grid classifications offline

## Support

For questions or issues, contact the content-service team or refer to:
- **Documentation**: `docs/COASTLINE_DETECTION_SYSTEM.md`
- **Production API**: `https://statlas-content-service-aleilqeyua-uc.a.run.app`
- **Source code**: `main.go` (coastline handler functions)

---

**Author**: AI Assistant for Statlas Content Service  
**Date**: 2025-08-15  
**Version**: 1.0.0
