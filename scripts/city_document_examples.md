# City Document Examples in Firestore

This document shows examples of how city data will be stored in your Firestore database.

## Document Structure

Each city will be stored as a document in the `cities` collection with the following structure:

### Example 1: Aalborg, Denmark
```json
{
  "id": "Aalborg",
  "name": "Aalborg",
  "population": 101616,
  "sq_km": 76.0,
  "boundary": {
    "type": "Polygon",
    "coordinates": [
      [
        [9.85, 56.98333333],
        [10.03333333, 56.98333333],
        [10.03333333, 57.1],
        [9.85, 57.1],
        [9.85, 56.98333333]
      ]
    ]
  },
  "imported_at": "2024-01-01T00:00:00Z"
}
```

### Example 2: New York, USA
```json
{
  "id": "New_York",
  "name": "New York",
  "population": 8336817,
  "sq_km": 778.2,
  "boundary": {
    "type": "Polygon",
    "coordinates": [
      [
        [-74.25909, 40.477399],
        [-73.700181, 40.477399],
        [-73.700181, 40.916178],
        [-74.25909, 40.916178],
        [-74.25909, 40.477399]
      ]
    ]
  },
  "imported_at": "2024-01-01T00:00:00Z"
}
```

### Example 3: Tokyo, Japan
```json
{
  "id": "Tokyo",
  "name": "Tokyo",
  "population": 13929286,
  "sq_km": 2194.0,
  "boundary": {
    "type": "Polygon",
    "coordinates": [
      [
        [139.6917, 35.6895],
        [139.7673, 35.6895],
        [139.7673, 35.7317],
        [139.6917, 35.7317],
        [139.6917, 35.6895]
      ]
    ]
  },
  "imported_at": "2024-01-01T00:00:00Z"
}
```

## ID Generation Examples

### Name-based IDs (default)
- `Aalborg` → `Aalborg`
- `New York` → `New_York`
- `São Paulo` → `São_Paulo`
- `Los Angeles` → `Los_Angeles`

### Name + Population IDs
- `Aalborg` → `Aalborg_101616`
- `New York` → `New_York_8336817`
- `Tokyo` → `Tokyo_13929286`

### Custom Prefix IDs
- `Aalborg` → `city_Aalborg`
- `New York` → `city_New_York`
- `Tokyo` → `city_Tokyo`

## Querying Examples

### Get city by name
```javascript
// Firestore query
const cityRef = db.collection('cities').where('name', '==', 'Aalborg');
```

### Get cities by population range
```javascript
// Cities with population > 1 million
const largeCities = db.collection('cities')
  .where('population', '>', 1000000)
  .orderBy('population', 'desc');
```

### Get cities by area
```javascript
// Cities larger than 1000 km²
const largeAreaCities = db.collection('cities')
  .where('sq_km', '>', 1000)
  .orderBy('sq_km', 'desc');
```

### Get city by ID
```javascript
// Direct document access
const cityDoc = db.collection('cities').doc('Aalborg');
```

## Benefits of This Structure

1. **Unique IDs**: Each city has a guaranteed unique identifier
2. **Searchable**: Can query by name, population, or area
3. **Geospatial**: Boundary data stored in GeoJSON format
4. **Scalable**: Firestore handles large datasets efficiently
5. **Flexible**: Easy to add additional fields later
6. **Indexable**: Can create composite indexes for complex queries
