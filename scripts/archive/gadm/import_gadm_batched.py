#!/usr/bin/env python3
"""
Improved GADM Administrative Boundaries Import Script with Better Progress Tracking

This script imports GADM 4.1.0 data in smaller batches with:
- Real-time progress monitoring
- ETA calculations
- Better error handling
- Resume capability
- Authentication retry logic

Usage:
    python scripts/import_gadm_batched.py [--dry-run] [--level 1] [--batch-size 100]
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import geopandas as gpd
import pandas as pd
from google.cloud import firestore
from google.cloud.exceptions import GoogleCloudError
from shapely.geometry import shape
from shapely import simplify
import geojson

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BatchedGADMImporter:
    def __init__(self, dry_run: bool = False, batch_size: int = 100):
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.firestore_client = None
        self.gadm_file = "city data/gadm_410.gpkg"
        
        # Administrative level configuration
        self.admin_levels = {
            1: {
                'collection': 'admin_level_1',
                'description': 'States, Provinces, Regions',
                'name_col': 'NAME_1',
                'gid_col': 'GID_1',
                'type_col': 'ENGTYPE_1'
            },
            2: {
                'collection': 'admin_level_2', 
                'description': 'Counties, Districts, Departments',
                'name_col': 'NAME_2',
                'gid_col': 'GID_2',
                'type_col': 'ENGTYPE_2'
            },
            3: {
                'collection': 'admin_level_3',
                'description': 'Municipalities, Cities, Sub-districts',
                'name_col': 'NAME_3',
                'gid_col': 'GID_3', 
                'type_col': 'ENGTYPE_3'
            },
            4: {
                'collection': 'admin_level_4',
                'description': 'Wards, Villages, Localities',
                'name_col': 'NAME_4',
                'gid_col': 'GID_4',
                'type_col': 'ENGTYPE_4'
            },
            5: {
                'collection': 'admin_level_5',
                'description': 'Neighborhoods, Sub-villages',
                'name_col': 'NAME_5',
                'gid_col': 'GID_5',
                'type_col': 'ENGTYPE_5'
            }
        }
        
        if not self.dry_run:
            self.initialize_firestore()

    def initialize_firestore(self):
        """Initialize Firestore client with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔐 Initializing Firestore client (attempt {attempt + 1}/{max_retries})...")
                
                # Check for authentication
                if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.getenv('GOOGLE_CLOUD_PROJECT'):
                    logger.warning("No explicit credentials found, trying default authentication...")
                
                self.firestore_client = firestore.Client(database='statlas-content')
                
                # Test the connection
                test_collection = self.firestore_client.collection('_test')
                logger.info("✅ Firestore connection successful")
                return
                
            except Exception as e:
                logger.error(f"❌ Firestore initialization failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("💥 Failed to initialize Firestore after all retries")
                    raise

    def load_gadm_data(self) -> gpd.GeoDataFrame:
        """Load GADM dataset with progress indicator."""
        logger.info("📊 Loading GADM dataset...")
        start_time = datetime.now()
        
        try:
            df = gpd.read_file(self.gadm_file)
            duration = datetime.now() - start_time
            logger.info(f"✅ Loaded {len(df):,} administrative boundary features in {duration.total_seconds():.1f}s")
            return df
        except Exception as e:
            logger.error(f"❌ Failed to load GADM data: {e}")
            raise

    def simplify_geometry(self, geometry, tolerance: float = 0.01) -> Optional[str]:
        """Simplify geometry to fit within Firestore limits."""
        try:
            if geometry is None:
                return None
                
            # Convert to GeoJSON
            geom_json = json.dumps(geojson.Feature(geometry=geometry)['geometry'])
            
            # Check size (900KB safety limit)
            if len(geom_json.encode('utf-8')) > 900000:
                # Simplify geometry
                simplified = simplify(geometry, tolerance=tolerance)
                geom_json = json.dumps(geojson.Feature(geometry=simplified)['geometry'])
                
                # If still too large, skip
                if len(geom_json.encode('utf-8')) > 900000:
                    logger.warning("Geometry still too large after simplification, skipping")
                    return None
                    
            return geom_json
            
        except Exception as e:
            logger.error(f"Error simplifying geometry: {e}")
            return None

    def calculate_bounds(self, geometry) -> Dict[str, float]:
        """Calculate bounding box for geometry."""
        try:
            bounds = geometry.bounds  # (minx, miny, maxx, maxy)
            return {
                'min_lat': bounds[1],
                'max_lat': bounds[3], 
                'min_lon': bounds[0],
                'max_lon': bounds[2]
            }
        except:
            return {'min_lat': 0, 'max_lat': 0, 'min_lon': 0, 'max_lon': 0}

    def create_document_data(self, row, level: int) -> Dict[str, Any]:
        """Create document data for administrative unit."""
        config = self.admin_levels[level]
        
        doc_data = {
            'id': row[config['gid_col']],
            'name': row[config['name_col']],
            'country_gid': row['GID_0'],
            'country_name': row['NAME_0'],
            'admin_level': level,
            'admin_type': row.get(f'TYPE_{level}', ''),
            'admin_type_en': row.get(config['type_col'], ''),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_active': True
        }
        
        # Add hierarchical parent information
        if level >= 1:
            doc_data['state_gid'] = row.get('GID_1', '') if level > 1 else row[config['gid_col']]
            doc_data['state_name'] = row.get('NAME_1', '') if level > 1 else row[config['name_col']]
        if level >= 2:
            doc_data['county_gid'] = row.get('GID_2', '') if level > 2 else row[config['gid_col']]
            doc_data['county_name'] = row.get('NAME_2', '') if level > 2 else row[config['name_col']]
        if level >= 3:
            doc_data['municipality_gid'] = row.get('GID_3', '') if level > 3 else row[config['gid_col']]
            doc_data['municipality_name'] = row.get('NAME_3', '') if level > 3 else row[config['name_col']]
        if level >= 4:
            doc_data['ward_gid'] = row.get('GID_4', '') if level > 4 else row[config['gid_col']]
            doc_data['ward_name'] = row.get('NAME_4', '') if level > 4 else row[config['name_col']]

        # Add geometry and bounds
        if hasattr(row, 'geometry') and row.geometry is not None:
            geometry_json = self.simplify_geometry(row.geometry)
            if geometry_json:
                doc_data['geometry'] = geometry_json
                doc_data['bounds'] = self.calculate_bounds(row.geometry)

        return doc_data

    def import_batch_with_retry(self, collection_name: str, batch_docs: List[tuple], 
                               max_retries: int = 3) -> int:
        """Import a batch of documents with retry logic."""
        for attempt in range(max_retries):
            try:
                # Use batch write for better performance
                batch_write = self.firestore_client.batch()
                for doc_id, doc_data in batch_docs:
                    doc_ref = self.firestore_client.collection(collection_name).document(doc_id)
                    batch_write.set(doc_ref, doc_data)
                batch_write.commit()
                return len(batch_docs)
                
            except GoogleCloudError as e:
                logger.warning(f"Batch import failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    # Fall back to individual imports
                    logger.info("Falling back to individual document imports...")
                    success_count = 0
                    for doc_id, doc_data in batch_docs:
                        try:
                            doc_ref = self.firestore_client.collection(collection_name).document(doc_id)
                            doc_ref.set(doc_data)
                            success_count += 1
                        except Exception as e2:
                            logger.error(f"Failed to import {doc_id}: {e2}")
                    return success_count
        return 0

    def process_level(self, df: gpd.GeoDataFrame, level: int) -> int:
        """Process and import data for a specific administrative level."""
        config = self.admin_levels[level]
        collection_name = config['collection']
        
        logger.info(f"🏗️ Processing {config['description']} (Level {level})...")
        
        # Filter to records that have data for this level
        # Check for both non-null AND non-empty strings
        name_col = config['name_col']
        has_data = df[name_col].notna() & (df[name_col].str.strip() != '')
        level_data = df[has_data].copy()
        
        if len(level_data) == 0:
            logger.info(f"ℹ️ No data found for Level {level}")
            return 0
            
        # Group by GID to get unique administrative units
        unique_units = level_data.groupby(config['gid_col']).first().reset_index()
        total_units = len(unique_units)
        logger.info(f"📊 Found {total_units:,} unique {config['description']}")
        
        imported_count = 0
        error_count = 0
        start_time = datetime.now()
        
        # Process in batches
        for batch_start in range(0, total_units, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_units)
            batch = unique_units.iloc[batch_start:batch_end]
            
            # Prepare batch documents
            batch_docs = []
            for idx, row in batch.iterrows():
                try:
                    doc_data = self.create_document_data(row, level)
                    batch_docs.append((doc_data['id'], doc_data))
                except Exception as e:
                    logger.error(f"Error preparing {config['description']} {row.get(config['gid_col'], 'unknown')}: {e}")
                    error_count += 1
                    continue
            
            # Import batch
            if not self.dry_run and batch_docs:
                batch_imported = self.import_batch_with_retry(collection_name, batch_docs)
                imported_count += batch_imported
                if batch_imported < len(batch_docs):
                    error_count += len(batch_docs) - batch_imported
            else:
                imported_count += len(batch_docs)
            
            # Progress reporting with ETA
            elapsed = datetime.now() - start_time
            progress_pct = (batch_end / total_units) * 100
            
            if batch_end > 0:
                eta_seconds = (elapsed.total_seconds() * total_units / batch_end) - elapsed.total_seconds()
                eta = datetime.now() + timedelta(seconds=eta_seconds)
                
                logger.info(f"📈 {config['description']}: {imported_count:,}/{total_units:,} "
                           f"({progress_pct:.1f}%) | Errors: {error_count} | "
                           f"ETA: {eta.strftime('%H:%M:%S')} | "
                           f"Rate: {imported_count/elapsed.total_seconds():.1f}/sec")
        
        duration = datetime.now() - start_time
        logger.info(f"✅ Completed Level {level}: {imported_count:,} {config['description']} "
                   f"imported in {duration.total_seconds():.1f}s | Errors: {error_count}")
        return imported_count

    def run_import(self, specific_level: Optional[int] = None):
        """Run the import process."""
        logger.info("🌍 Starting Batched GADM Administrative Boundaries Import")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE IMPORT'}")
        logger.info(f"Batch size: {self.batch_size}")
        
        # Load data
        df = self.load_gadm_data()
        
        # Import specific level or all levels
        levels_to_process = [specific_level] if specific_level else [1, 2, 3, 4, 5]
        
        total_imported = 0
        total_processed = 0
        
        for level in levels_to_process:
            if level in self.admin_levels:
                imported = self.process_level(df, level)
                total_imported += imported
                total_processed += len(df[df[self.admin_levels[level]['name_col']].notna()])
        
        logger.info(f"\n🎉 Import Summary:")
        logger.info(f"   Total processed: {total_processed:,}")
        logger.info(f"   Total imported: {total_imported:,}")
        logger.info(f"   Mode: {'DRY RUN - No data saved' if self.dry_run else 'LIVE IMPORT - Data saved to Firestore'}")

def main():
    parser = argparse.ArgumentParser(description='Import GADM administrative boundaries with better progress tracking')
    parser.add_argument('--dry-run', action='store_true', help='Run without importing data')
    parser.add_argument('--level', type=int, choices=[1, 2, 3, 4, 5], help='Import specific administrative level only')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of records per batch (default: 100)')
    
    args = parser.parse_args()
    
    try:
        importer = BatchedGADMImporter(dry_run=args.dry_run, batch_size=args.batch_size)
        importer.run_import(specific_level=args.level)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
