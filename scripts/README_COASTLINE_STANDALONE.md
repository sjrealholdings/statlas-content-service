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

## Git Workflow: Clean, Merge, and Push

When working with this script and making changes to the repository, follow this Git workflow:

### Recent Updates (2025-08-17)

**Countries Database Update:**
- Successfully updated 245 countries in Firestore with comprehensive data from `countries_info.json`
- Data includes: population, area, capital, government form, currency, dialing prefix, birth/death rates, coastline info
- Countries found in both `countries` and `map_units` collections
- 5 French territories not found (as expected): French Guiana, Guadeloupe, Martinique, Mayotte, Reunion
- Cleaned up duplicate documents that were accidentally created during the process
- Final result: 263 countries with comprehensive data, no duplicates

**Scripts Created:**
- `update_countries_from_json.py` - Updates existing countries with JSON data
- `check_existing_countries.py` - Lists all countries in the database
- `check_map_units.py` - Searches map_units collection for specific countries
- `cleanup_duplicate_countries.py` - Removes duplicate country documents

### 1. Clean Working Directory

Before merging or pushing changes, ensure your working directory is clean:

```bash
# Check current status
git status

# Add all changes to staging
git add .

# Or add specific files
git add scripts/coastline_classifier_standalone.py
git add scripts/README_COASTLINE_STANDALONE.md

# Commit your changes
git commit -m "feat: update coastline classifier with new functionality"
```

### 2. Merge Latest Changes

Before pushing, merge the latest changes from the main branch:

```bash
# Fetch latest changes from remote
git fetch origin

# Switch to main branch
git checkout main

# Pull latest changes
git pull origin main

# Switch back to your feature branch (if applicable)
git checkout your-feature-branch

# Merge main into your branch
git merge main
```

**Alternative: Rebase workflow**
```bash
# Rebase your changes on top of main (cleaner history)
git rebase main
```

### 3. Push Changes

After cleaning and merging, push your changes:

```bash
# Push to remote repository
git push origin main

# Or push your feature branch
git push origin your-feature-branch

# Force push after rebase (use with caution)
git push --force-with-lease origin your-feature-branch
```

### 4. Handle Merge Conflicts

If conflicts arise during merge:

```bash
# View conflicted files
git status

# Edit files to resolve conflicts
# Look for conflict markers: <<<<<<<, =======, >>>>>>>

# After resolving conflicts, add the files
git add resolved-file.py

# Continue the merge
git merge --continue

# Or continue the rebase
git rebase --continue
```

### 5. Pre-Push Checklist

Before pushing changes, ensure:

- ✅ All tests pass: `python -m pytest tests/` (if tests exist)
- ✅ Script runs without errors: `python coastline_classifier_standalone.py classify 40.7128 -74.0060`
- ✅ Documentation is updated
- ✅ No sensitive data in commits
- ✅ Commit messages follow conventional format

### 6. Branch Protection Best Practices

For production repositories:

```bash
# Create feature branch for changes
git checkout -b feature/coastline-improvements

# Make your changes and commits
git add .
git commit -m "feat: improve coastline classification accuracy"

# Push feature branch
git push origin feature/coastline-improvements

# Create pull request via GitHub/GitLab UI
# After review and approval, merge via UI
```

## Support

For questions or issues, contact the content-service team or refer to:
- **Documentation**: `docs/COASTLINE_DETECTION_SYSTEM.md`
- **Production API**: `https://statlas-content-service-aleilqeyua-uc.a.run.app`
- **Source code**: `main.go` (coastline handler functions)

---

**Author**: AI Assistant for Statlas Content Service  
**Date**: 2025-08-15  
**Version**: 1.0.0
