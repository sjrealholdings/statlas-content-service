# GADM Scripts Archive

This directory contains archived scripts related to GADM (Global Administrative Areas) data import and processing.

## Archived Date
August 14, 2025

## Reason for Archival
GADM administrative boundary data was removed from the Statlas Content Service due to technical complexity around Firestore's 1MB document size limits and geometry handling challenges. See `docs/GADM_DATA_REMOVAL.md` for full details.

## Archived Files
- `import_gadm_batched.py.backup` - Backup of the batched GADM import script

## Original Functionality
These scripts were designed to import 5 levels of administrative boundaries:
- Level 1: States, Provinces, Regions
- Level 2: Counties, Districts  
- Level 3: Municipalities, Cities
- Level 4: Wards, Villages
- Level 5: Neighborhoods

## Future Use
These scripts may be useful if GADM functionality is re-implemented in the future using:
- Geometry chunking strategies
- External geocoding services
- Cloud Storage + caching approaches

## Related Documentation
- `docs/GADM_DATA_REMOVAL.md` - Full removal documentation
- `docs/HIGH_FIDELITY_STRATEGY_ANALYSIS.md` - Analysis of chunking strategies
- `docs/EXCLUDED_COUNTRIES_GADM.md` - Countries that were excluded from import
