# Coastline Detection System for Grid Generation

## Overview

This system provides coastline detection and land-ocean classification for the Core Service's hierarchical grid generation system. The grid uses different resolutions based on location:

- **Ocean**: 100x100km or 10x10km squares (based on distance from coast)
- **Land**: 1x1km or 100x100m squares (based on urban density)

## Data Sources

Using [Natural Earth Vector](https://github.com/nvkelso/natural-earth-vector) 10m physical data:

### Primary Option: Coastlines
- **File**: `ne_10m_coastline.shp`
- **Purpose**: Direct coastline geometry for distance calculations
- **Advantages**: Most precise for distance-from-coast calculations

### Fallback Option: Land/Ocean Split
- **Files**: 
  - `ne_10m_land.shp` (land polygons)
  - `ne_10m_ocean.shp` (ocean polygons)
- **Purpose**: Point-in-polygon classification
- **Advantages**: Direct land/ocean classification

## Implementation Strategy

### Phase 1: Data Import and Storage
1. Download Natural Earth 10m coastline and land/ocean shapefiles
2. Import into Firestore with spatial indexing
3. Store as GeoJSON for efficient querying

### Phase 2: Coastline Detection API
1. **Distance-based classification** (primary method)
2. Distance-to-coastline calculations using 4,133 coastline segments
3. Batch processing for grid generation

**Note**: Natural Earth land polygons are global-scale MultiPolygons designed for map rendering, not suitable for point-in-polygon classification.

### Phase 3: Grid Resolution Logic
```
For each point (lat, lon):
  if is_ocean(point):
    distance = distance_to_coast(point)
    if distance > 1000km:
      return "100x100km"
    else:
      return "10x10km"
  else:  # on land
    urban_density = get_urban_density(point)  # Future implementation
    if urban_density > threshold:
      return "100x100m"
    else:
      return "1x1km"
```

## API Endpoints

### `/coastline/classify`
**Purpose**: Classify a point as land or ocean
```json
{
  "lat": 40.7128,
  "lon": -74.0060,
  "result": {
    "type": "land",
    "distance_to_coast_km": 0.5,
    "grid_resolution": "1x1km"  // Will be "100x100m" with urban density
  }
}
```

### `/coastline/distance`
**Purpose**: Calculate distance to nearest coastline
```json
{
  "lat": 40.0,
  "lon": -50.0,
  "result": {
    "distance_to_coast_km": 1247.3,
    "nearest_coast_point": {
      "lat": 41.2,
      "lon": -45.1
    }
  }
}
```

### `/coastline/batch-classify`
**Purpose**: Batch processing for grid generation
```json
{
  "points": [
    {"lat": 40.7128, "lon": -74.0060},
    {"lat": 35.0, "lon": -40.0}
  ],
  "results": [
    {"type": "land", "distance_to_coast_km": 0.5},
    {"type": "ocean", "distance_to_coast_km": 856.2}
  ]
}
```

## Data Processing Requirements

### Coordinate System
- **Input**: WGS84 (EPSG:4326) lat/lon
- **Processing**: May need projection for accurate distance calculations
- **Output**: Distances in kilometers

### Performance Considerations
- **Spatial Indexing**: Use Firestore's geohash indexing
- **Caching**: Cache common coastline queries
- **Batch Processing**: Optimize for grid generation workloads

## Natural Earth Data Specifications

### 10m Physical Coastlines
- **Resolution**: 1:10,000,000 scale
- **Accuracy**: ~1km accuracy at equator
- **Coverage**: Global coastlines including islands
- **Format**: Shapefile with LineString geometries

### 10m Land/Ocean
- **Resolution**: 1:10,000,000 scale  
- **Coverage**: Complete global land/ocean split
- **Format**: Shapefile with Polygon geometries
- **Advantages**: No gaps or overlaps

## Implementation Plan

### Immediate Tasks
1. Download Natural Earth 10m coastline data
2. Create import script for shapefile to Firestore
3. Implement basic land/ocean classification endpoint
4. Add distance-to-coastline calculations

### Future Enhancements
1. Urban density integration (separate data source)
2. Performance optimization with spatial indexing
3. Caching layer for common queries
4. Integration with Core Service grid generation
