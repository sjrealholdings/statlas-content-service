# City Import Script

This script imports city objects from the Stanford shapefile into your content-service database with the following fields:
- **name**: City name
- **population**: Population data
- **sq_km**: Area in square kilometers
- **boundary**: Geographic boundary polygon

## Prerequisites

1. **PostgreSQL Database** with PostGIS extension enabled
2. **Python 3.7+** with pip
3. **Stanford Shapefile** located at `../city data/stanford-yk247bg4748-shapefile/`

## Installation

1. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements_cities.txt
   ```

2. **Verify PostGIS extension:**
   ```sql
   -- Connect to your database and run:
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```

## Configuration

1. **Update Firestore credentials** in `db_config.py`:
   ```python
   # Option 1: Service account key file
   SERVICE_ACCOUNT_KEY_PATH = 'path/to/serviceAccountKey.json'
   
   # Option 2: Project ID (for default credentials)
   PROJECT_ID = 'your-project-id'
   
   # Option 3: Use environment variables
   export FIREBASE_SERVICE_ACCOUNT_KEY='path/to/key.json'
   export FIREBASE_PROJECT_ID='your-project-id'
   export FIREBASE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
   ```

2. **Configure ID generation strategy:**
   ```python
   # Options: 'name', 'uuid', 'name_population', 'custom'
   ID_STRATEGY = 'name'  # Uses sanitized city name as ID
   ```

## Usage

### Basic Import
```bash
python3 import_cities.py
```

### Import with Environment Variables
```bash
python3 import_cities.py
# (Make sure environment variables are set)
```

## What the Script Does

1. **Connects** to your PostgreSQL database
2. **Creates** a `cities` table with proper indexes:
   - Spatial index on boundary (GIST)
   - Index on name for text searches
   - Index on population for sorting/filtering
3. **Reads** the Stanford shapefile (6,018 cities)
4. **Extracts** name, population, area, and boundary data
5. **Imports** cities in batches of 100 for performance
6. **Validates** the import and provides statistics

## Firestore Document Structure

Each city document will have this structure:

```json
{
  "id": "Aalborg",
  "name": "Aalborg",
  "population": 101616,
  "sq_km": 76.0,
  "boundary": {
    "type": "Polygon",
    "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
  },
  "imported_at": "2024-01-01T00:00:00Z"
}
```

### ID Generation Options

The script supports multiple ID generation strategies:

1. **`name`** (default): Uses sanitized city name (e.g., "Aalborg", "New_York")
2. **`uuid`**: Generates random UUIDs for each city
3. **`name_population`**: Combines name and population (e.g., "Aalborg_101616")
4. **`custom`**: Uses custom prefix with city name (e.g., "city_Aalborg")

## Expected Results

- **~6,000 cities** imported worldwide
- **Population data** for most cities
- **Area measurements** in square kilometers
- **Boundary polygons** in WGS 84 coordinates (EPSG:4326)
- **Spatial indexes** for efficient geographic queries

## Performance Features

- **Batch processing** (100 cities per batch)
- **Spatial indexing** for boundary queries
- **Upsert logic** (update existing cities by name)
- **Progress logging** every 1,000 cities
- **Error handling** with detailed logging

## Troubleshooting

### Common Issues

1. **PostGIS not installed:**
   ```sql
   CREATE EXTENSION postgis;
   ```

2. **Permission denied:**
   - Check database user permissions
   - Verify table creation rights

3. **Shapefile not found:**
   - Verify path: `../city data/stanford-yk247bg4748-shapefile/`
   - Check file permissions

4. **Memory issues:**
   - Reduce batch size in the script
   - Process in smaller chunks

### Logs

The script provides detailed logging:
- Database connection status
- Shapefile processing progress
- Import batch progress
- Validation results
- Error details

## Post-Import Queries

### Basic Queries
```sql
-- Count total cities
SELECT COUNT(*) FROM cities;

-- Cities with population > 1M
SELECT name, population, sq_km 
FROM cities 
WHERE population > 1000000 
ORDER BY population DESC;

-- Cities by area
SELECT name, sq_km 
FROM cities 
WHERE sq_km IS NOT NULL 
ORDER BY sq_km DESC;
```

### Spatial Queries
```sql
-- Cities within 100km of a point
SELECT name, population 
FROM cities 
WHERE ST_DWithin(
    boundary::geography, 
    ST_Point(-74.006, 40.7128)::geography, 
    100000
);

-- Cities intersecting a region
SELECT name, population 
FROM cities 
WHERE ST_Intersects(
    boundary, 
    ST_GeomFromText('POLYGON((...))', 4326)
);
```

## Data Quality Notes

- **Population**: Uses `max_pop_al` (maximum across all time periods)
- **Area**: Uses `min_areakm` (minimum area in square kilometers)
- **Boundaries**: Complex polygons with potential holes/exclusions
- **Coordinates**: WGS 84 (EPSG:4326) - standard for web mapping

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Verify database connectivity and permissions
3. Ensure PostGIS extension is enabled
4. Check shapefile path and permissions
