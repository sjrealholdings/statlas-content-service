# Polygon/Geometry API Endpoints

## Overview

The Content Service provides three polygon/geometry endpoints specifically designed for frontend mapping and visualization. These endpoints return GeoJSON polygon data that the Core Service frontend can use to draw country outlines, continent maps, and world maps.

## Endpoints

### 1. Country Polygon Endpoint

```
GET /polygons/country/{id}
```

**Purpose**: Fetch polygon geometry for a specific country or territory

**Parameters**:
- `id` (path): Country ID (e.g., "australia", "france", "usa")

**Response Format**:
```json
{
  "id": "australia",
  "name": "Australia",
  "type": "country",
  "geometry": "{\"type\": \"Polygon\", \"coordinates\": [...]}",
  "bounds": {
    "min_lat": -54.75,
    "max_lat": -9.24,
    "min_lon": 112.92,
    "max_lon": 159.11
  }
}
```

**Error Responses**:
- `404 Not Found`: Country not found
- `404 Not Found`: Country not active  
- `404 Not Found`: Country geometry not available

### 2. Continent Polygon Endpoint

```
GET /polygons/continent/{continent}
```

**Purpose**: Fetch all country polygons for a specific continent

**Parameters**:
- `continent` (path): Continent name (e.g., "Europe", "Asia", "North America")

**Response Format**:
```json
{
  "continent": "Europe",
  "count": 51,
  "polygons": [
    {
      "id": "albania",
      "name": "Albania", 
      "type": "country",
      "geometry": "{\"type\": \"Polygon\", \"coordinates\": [...]}",
      "bounds": {...}
    },
    // ... more countries
  ]
}
```

### 3. World Polygon Endpoint

```
GET /polygons/world
```

**Purpose**: Fetch all country polygons in the world

**Response Format**:
```json
{
  "world": true,
  "count": 257,
  "polygons": [
    {
      "id": "afghanistan",
      "name": "Afghanistan",
      "type": "country", 
      "continent": "Asia",
      "geometry": "{\"type\": \"Polygon\", \"coordinates\": [...]}",
      "bounds": {...}
    },
    // ... all countries
  ]
}
```

## Data Source

- **Collection**: Only queries the `countries` collection in Firestore
- **Database**: `statlas-content` 
- **Geometry Format**: GeoJSON strings stored in the `geometry` field
- **Filtering**: Only returns active countries (`is_active: true`)

## Authentication

All endpoints require service authentication using the same mechanism as other Content Service endpoints.

## Usage Examples

### Frontend Integration

```javascript
// Get country outline for map
const countryResponse = await fetch('/polygons/country/france');
const countryData = await countryResponse.json();
const geoJSON = JSON.parse(countryData.geometry);

// Draw on map using Leaflet/Mapbox
L.geoJSON(geoJSON).addTo(map);

// Get all countries in a continent
const continentResponse = await fetch('/polygons/continent/Europe');
const continentData = await continentResponse.json();

continentData.polygons.forEach(country => {
  const geoJSON = JSON.parse(country.geometry);
  L.geoJSON(geoJSON).addTo(map);
});
```

### Bounds Usage

The `bounds` object provides the bounding box for efficient map viewport fitting:

```javascript
const bounds = L.latLngBounds([
  [country.bounds.min_lat, country.bounds.min_lon],
  [country.bounds.max_lat, country.bounds.max_lon]
]);
map.fitBounds(bounds);
```

## Performance Considerations

- **Geometry Size**: Country polygons can be large (50KB-200KB each)
- **Caching**: Consider caching responses on the frontend
- **Selective Loading**: Load only needed countries/continents when possible
- **Compression**: Responses are gzipped by Cloud Run

## Data Coverage

Current world coverage (as of latest update):

| Continent | Countries |
|-----------|-----------|
| Africa | 56 |
| Asia | 53 |
| Europe | 51 |
| North America | 37 |
| Oceania | 24 |
| South America | 13 |
| Other | 22 |
| Antarctica | 1 |
| **Total** | **257** |

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful response with polygon data
- `404 Not Found`: Country/data not found
- `500 Internal Server Error`: Database or processing error

## Implementation Notes

### No Double-Counting

These endpoints were specifically designed to avoid double-counting by only querying the `countries` collection, unlike earlier implementations that queried multiple collections (`countries`, `sovereign_states`, `map_units`).

### Consistent Data Model

All responses use a consistent structure with:
- `id`: Internal country identifier
- `name`: Display name
- `type`: Always "country" for these endpoints
- `geometry`: GeoJSON string
- `bounds`: Bounding box coordinates
- `continent`: Continent classification (world endpoint only)

### GeoJSON Format

The geometry field contains a JSON string with standard GeoJSON format:

```json
{
  "type": "Polygon",
  "coordinates": [
    [
      [longitude, latitude],
      [longitude, latitude],
      // ... more coordinate pairs
    ]
  ]
}
```

For complex countries with multiple polygons (islands, etc.), the format may be `MultiPolygon`.
