#!/usr/bin/env python3
"""
GADM Administrative Boundaries Import Script for Statlas Content Service

This script imports GADM 4.1.0 administrative boundary data into Firestore
to enable comprehensive location detection at all administrative levels:
- Level 0: Countries (already handled by Natural Earth)
- Level 1: States/Provinces/Regions  
- Level 2: Counties/Districts
- Level 3: Municipalities/Cities
- Level 4: Wards/Villages
- Level 5: Neighborhoods/Sub-villages

Usage:
    python scripts/import_gadm_data.py [--dry-run]
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional

import geopandas as gpd
import pandas as pd
from google.cloud import firestore
from google.cloud import storage
from shapely.geometry import shape
from shapely import simplify
import geojson

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GADMImporter:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.db = None if dry_run else firestore.Client()
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
        # Administrative level configurations
        self.admin_levels = {
            1: {
                'collection': 'admin_level_1',  # States/Provinces
                'description': 'States, Provinces, Regions',
                'name_col': 'NAME_1',
                'gid_col': 'GID_1',
                'type_col': 'ENGTYPE_1',
                'parent_gid_col': 'GID_0'
            },
            2: {
                'collection': 'admin_level_2',  # Counties/Districts
                'description': 'Counties, Districts, Departments',
                'name_col': 'NAME_2', 
                'gid_col': 'GID_2',
                'type_col': 'ENGTYPE_2',
                'parent_gid_col': 'GID_1'
            },
            3: {
                'collection': 'admin_level_3',  # Municipalities/Cities
                'description': 'Municipalities, Cities, Sub-districts',
                'name_col': 'NAME_3',
                'gid_col': 'GID_3', 
                'type_col': 'ENGTYPE_3',
                'parent_gid_col': 'GID_2'
            },
            4: {
                'collection': 'admin_level_4',  # Wards/Villages
                'description': 'Wards, Villages, Localities',
                'name_col': 'NAME_4',
                'gid_col': 'GID_4',
                'type_col': 'ENGTYPE_4', 
                'parent_gid_col': 'GID_3'
            },
            5: {
                'collection': 'admin_level_5',  # Neighborhoods
                'description': 'Neighborhoods, Sub-villages',
                'name_col': 'NAME_5',
                'gid_col': 'GID_5',
                'type_col': 'ENGTYPE_5',
                'parent_gid_col': 'GID_4'
            }
        }

    def simplify_geometry(self, geometry, tolerance: float = 0.001) -> Optional[str]:
        """Simplify geometry and convert to GeoJSON string for Firestore storage."""
        try:
            if geometry is None or geometry.is_empty:
                return None
                
            # Simplify the geometry to reduce size
            simplified = simplify(geometry, tolerance=tolerance)
            
            # Convert to GeoJSON
            geojson_geom = geojson.Feature(geometry=simplified)['geometry']
            geojson_str = json.dumps(geojson_geom)
            
            # Check size limit (Firestore has 1MB limit, use 900KB safety margin)
            if len(geojson_str.encode('utf-8')) > 900000:
                # Try with higher tolerance
                simplified = simplify(geometry, tolerance=tolerance * 10)
                geojson_geom = geojson.Feature(geometry=simplified)['geometry']
                geojson_str = json.dumps(geojson_geom)
                
                if len(geojson_str.encode('utf-8')) > 900000:
                    logger.warning(f"Geometry still too large after simplification, skipping")
                    return None
            
            return geojson_str
            
        except Exception as e:
            logger.error(f"Error simplifying geometry: {e}")
            return None

    def calculate_bounds(self, geometry) -> Dict[str, float]:
        """Calculate bounding box for geometry."""
        try:
            bounds = geometry.bounds
            return {
                'min_lat': bounds[1],
                'max_lat': bounds[3], 
                'min_lon': bounds[0],
                'max_lon': bounds[2]
            }
        except Exception as e:
            logger.error(f"Error calculating bounds: {e}")
            return {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0}

    def process_administrative_level(self, df: gpd.GeoDataFrame, level: int) -> int:
        """Process and import data for a specific administrative level."""
        config = self.admin_levels[level]
        collection_name = config['collection']
        
        logger.info(f"Processing {config['description']} (Level {level})...")
        
        # Filter to records that have data for this level
        level_data = df[df[config['name_col']].notna()].copy()
        
        if len(level_data) == 0:
            logger.info(f"No data found for Level {level}")
            return 0
            
        # Group by GID to get unique administrative units
        unique_units = level_data.groupby(config['gid_col']).first().reset_index()
        logger.info(f"Found {len(unique_units):,} unique {config['description']}")
        
        imported_count = 0
        
        for idx, row in unique_units.iterrows():
            try:
                # Create administrative unit document with hierarchical structure
                admin_unit = {
                    'id': row[config['gid_col']],
                    'name': row[config['name_col']],
                    'country_gid': row['GID_0'],
                    'country_name': row['NAME_0'],
                    'admin_level': level,
                    'admin_type': row.get(f'TYPE_{level}', ''),
                    'admin_type_en': row.get(config['type_col'], ''),
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'is_active': True
                }
                
                # Add hierarchical parent information
                if level >= 1:
                    admin_unit['state_gid'] = row.get('GID_1', '') if level > 1 else row[config['gid_col']]
                    admin_unit['state_name'] = row.get('NAME_1', '') if level > 1 else row[config['name_col']]
                if level >= 2:
                    admin_unit['county_gid'] = row.get('GID_2', '') if level > 2 else row[config['gid_col']]
                    admin_unit['county_name'] = row.get('NAME_2', '') if level > 2 else row[config['name_col']]
                if level >= 3:
                    admin_unit['municipality_gid'] = row.get('GID_3', '') if level > 3 else row[config['gid_col']]
                    admin_unit['municipality_name'] = row.get('NAME_3', '') if level > 3 else row[config['name_col']]
                if level >= 4:
                    admin_unit['ward_gid'] = row.get('GID_4', '') if level > 4 else row[config['gid_col']]
                    admin_unit['ward_name'] = row.get('NAME_4', '') if level > 4 else row[config['name_col']]
                
                # Add geometry and bounds
                if hasattr(row, 'geometry') and row.geometry is not None:
                    geometry_json = self.simplify_geometry(row.geometry)
                    if geometry_json:
                        admin_unit['geometry'] = geometry_json
                        admin_unit['bounds'] = self.calculate_bounds(row.geometry)
                    else:
                        admin_unit['geometry'] = ''
                        admin_unit['bounds'] = {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0}
                else:
                    admin_unit['geometry'] = ''
                    admin_unit['bounds'] = {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0}
                
                if not self.dry_run:
                    # Import to Firestore
                    doc_ref = self.db.collection(collection_name).document(admin_unit['id'])
                    doc_ref.set(admin_unit)
                
                imported_count += 1
                self.processed_count += 1
                
                if imported_count % 1000 == 0:
                    logger.info(f"Imported {imported_count:,} {config['description']}...")
                    
            except Exception as e:
                logger.error(f"Error processing {config['description']} {row.get(config['gid_col'], 'unknown')}: {e}")
                self.error_count += 1
                continue
        
        logger.info(f"✅ Completed Level {level}: {imported_count:,} {config['description']} imported")
        return imported_count

    def import_gadm_data(self, gpkg_path: str):
        """Main import function."""
        logger.info("🌍 Starting GADM Administrative Boundaries Import")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE IMPORT'}")
        
        try:
            # Load the full GADM dataset
            logger.info("📊 Loading GADM dataset...")
            df = gpd.read_file(gpkg_path)
            logger.info(f"Loaded {len(df):,} administrative boundary features")
            
            # Import each administrative level
            total_imported = 0
            for level in range(1, 6):  # Levels 1-5 (Level 0 is countries, handled by Natural Earth)
                if level in self.admin_levels:
                    count = self.process_administrative_level(df, level)
                    total_imported += count
            
            logger.info(f"\\n🎉 Import Summary:")
            logger.info(f"   Total processed: {self.processed_count:,}")
            logger.info(f"   Total imported: {total_imported:,}")
            logger.info(f"   Errors: {self.error_count:,}")
            logger.info(f"   Mode: {'DRY RUN - No data saved' if self.dry_run else 'LIVE IMPORT - Data saved to Firestore'}")
            
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Import GADM administrative boundaries to Firestore')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run without actually importing data (for testing)')
    
    args = parser.parse_args()
    
    # Path to GADM geopackage
    gpkg_path = 'city data/gadm_410.gpkg'
    
    # Create importer and run
    importer = GADMImporter(dry_run=args.dry_run)
    importer.import_gadm_data(gpkg_path)

if __name__ == '__main__':
    main()
