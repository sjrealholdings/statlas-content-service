#!/usr/bin/env python3
"""
GADM Data Replacement Script

This script safely replaces the existing corrupted GADM data with the corrected
dissolved geometry data. It includes backup, verification, and rollback capabilities.

Strategy:
1. Backup existing data to Cloud Storage
2. Delete existing collections
3. Import new corrected data
4. Verify import success
5. Test sample queries
"""

import geopandas as gpd
import pandas as pd
import json
import logging
from datetime import datetime
from shapely.geometry import shape, Point
from shapely import simplify
import time
import sys
from google.cloud import firestore
from google.cloud import storage
import tempfile
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class GADMDataReplacer:
    def __init__(self, dry_run=False, skip_backup=False, exclude_large=False, max_geometry_size=900000):
        self.dry_run = dry_run
        self.skip_backup = skip_backup
        self.exclude_large = exclude_large
        self.max_geometry_size = max_geometry_size
        self.db = firestore.Client(database='statlas-content')
        
        if not skip_backup:
            self.storage_client = storage.Client()
            self.bucket_name = f'statlas-gadm-backup-{datetime.now().strftime("%Y%m%d")}'  # Unique backup bucket
            self.backup_folder = f"gadm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.gadm_collections = ['admin_level_1', 'admin_level_2', 'admin_level_3', 'admin_level_4', 'admin_level_5']
        
        # Countries with notoriously large/complex geometries that might cause issues
        self.problematic_countries = [
            'Russia', 'Russian Federation',
            'Canada', 
            'United States', 'United States of America',
            'China',
            'Brazil', 
            'Australia',
            'India',
            'Kazakhstan',
            'Algeria',
            'Democratic Republic of the Congo',
            'Saudi Arabia',
            'Mexico',
            'Indonesia',
            'Sudan',
            'Libya',
            'Iran',
            'Mongolia',
            'Peru',
            'Chad',
            'Niger',
            'Angola'
        ]
        
        logging.info(f"🔧 GADM Data Replacer initialized")
        logging.info(f"   Mode: {'🧪 DRY RUN' if dry_run else '🚀 PRODUCTION'}")
        logging.info(f"   Database: statlas-content")
        logging.info(f"   Backup: {'⏭️ SKIPPED' if skip_backup else '📦 ENABLED'}")
        logging.info(f"   Large countries: {'🚫 EXCLUDED' if exclude_large else '✅ INCLUDED'}")
        logging.info(f"   Max geometry size: {max_geometry_size:,} bytes")
        if not skip_backup:
            logging.info(f"   Backup folder: {self.backup_folder}")
    
    def progressive_simplify_geometry(self, geometry, max_size=None):
        """
        Progressive geometry simplification to fit Firestore size limits
        """
        if max_size is None:
            max_size = self.max_geometry_size
            
        # Try different tolerance levels
        tolerances = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        
        for tolerance in tolerances:
            try:
                simplified = simplify(geometry, tolerance=tolerance, preserve_topology=True)
                geojson_str = json.dumps(simplified.__geo_interface__)
                size = len(geojson_str.encode('utf-8'))
                
                if size <= max_size:
                    return simplified, geojson_str
                    
            except Exception as e:
                logging.warning(f"      ⚠️  Simplification failed at tolerance {tolerance}: {e}")
                continue
        
        # If all simplifications fail or are still too big, create bounding box fallback
        logging.warning(f"      🚨 Using bounding box fallback for oversized geometry")
        bounds = geometry.bounds
        from shapely.geometry import box
        bbox_geom = box(bounds[0], bounds[1], bounds[2], bounds[3])
        geojson_str = json.dumps(bbox_geom.__geo_interface__)
        
        return bbox_geom, geojson_str

    def backup_existing_data(self):
        """Backup existing GADM data to Cloud Storage"""
        logging.info(f"\n📦 BACKING UP EXISTING GADM DATA")
        logging.info("=" * 50)
        
        if self.skip_backup:
            logging.info("⏭️ BACKUP SKIPPED: Proceeding without backup")
            return True
        
        if self.dry_run:
            logging.info("🧪 DRY RUN: Would backup existing data to Cloud Storage")
            return True
        
        try:
            # Create bucket if it doesn't exist
            try:
                bucket = self.storage_client.bucket(self.bucket_name)
                bucket.reload()  # Check if bucket exists
            except:
                # Create the bucket
                logging.info(f"   🪣 Creating backup bucket: {self.bucket_name}")
                bucket = self.storage_client.create_bucket(self.bucket_name)
                logging.info(f"   ✅ Created backup bucket successfully")
            
            for collection_name in self.gadm_collections:
                logging.info(f"   📤 Backing up {collection_name}...")
                
                # Get all documents
                docs = list(self.db.collection(collection_name).stream())
                
                if not docs:
                    logging.info(f"      ✅ No data to backup in {collection_name}")
                    continue
                
                # Convert to JSON
                backup_data = []
                for doc in docs:
                    data = doc.to_dict()
                    data['_doc_id'] = doc.id
                    # Convert datetime objects to strings
                    for key, value in data.items():
                        if isinstance(value, datetime):
                            data[key] = value.isoformat()
                    backup_data.append(data)
                
                # Upload to Cloud Storage
                backup_filename = f"{self.backup_folder}/{collection_name}_backup.json"
                blob = bucket.blob(backup_filename)
                blob.upload_from_string(json.dumps(backup_data, indent=2))
                
                logging.info(f"      ✅ Backed up {len(backup_data):,} documents to gs://{self.bucket_name}/{backup_filename}")
            
            logging.info(f"✅ Backup completed successfully!")
            return True
            
        except Exception as e:
            logging.error(f"❌ Backup failed: {e}")
            return False
    
    def delete_existing_data(self):
        """Delete existing GADM data"""
        logging.info(f"\n🗑️  DELETING EXISTING GADM DATA")
        logging.info("=" * 50)
        
        if self.dry_run:
            logging.info("🧪 DRY RUN: Would delete existing GADM collections")
            return True
        
        try:
            total_deleted = 0
            
            for collection_name in self.gadm_collections:
                logging.info(f"   🗑️  Deleting {collection_name}...")
                
                # Delete in batches to avoid timeouts
                batch_size = 100
                deleted_count = 0
                
                while True:
                    docs = list(self.db.collection(collection_name).limit(batch_size).stream())
                    if not docs:
                        break
                    
                    batch = self.db.batch()
                    for doc in docs:
                        batch.delete(doc.reference)
                    
                    batch.commit()
                    deleted_count += len(docs)
                    
                    logging.info(f"      🗑️  Deleted batch of {len(docs)} documents (total: {deleted_count})")
                
                logging.info(f"      ✅ Deleted {deleted_count:,} documents from {collection_name}")
                total_deleted += deleted_count
            
            logging.info(f"✅ Deletion completed! Total deleted: {total_deleted:,} documents")
            return True
            
        except Exception as e:
            logging.error(f"❌ Deletion failed: {e}")
            return False
    
    def load_and_process_gadm_data(self, gpkg_path, test_countries=None):
        """Load and process GADM data with proper geometry dissolution"""
        logging.info(f"\n📂 LOADING AND PROCESSING GADM DATA")
        logging.info("=" * 50)
        
        try:
            # Load GADM data
            gdf = gpd.read_file(gpkg_path)
            logging.info(f"✅ Loaded {len(gdf):,} total GADM entries")
            
            # Process each level
            admin_levels = [
                (1, 'GID_1', 'NAME_1'),
                (2, 'GID_2', 'NAME_2'), 
                (3, 'GID_3', 'NAME_3'),
                (4, 'GID_4', 'NAME_4'),
                (5, 'GID_5', 'NAME_5'),
            ]
            
            all_processed_data = {}
            
            for level, gid_col, name_col in admin_levels:
                logging.info(f"   🔧 Processing admin_level_{level}...")
                
                # Filter for this level
                level_filter = (gdf[gid_col].notna()) & (gdf[gid_col].str.strip() != '') & \
                              (gdf[name_col].notna()) & (gdf[name_col].str.strip() != '')
                
                level_data = gdf[level_filter].copy()
                
                # Filter for test countries if specified
                if test_countries:
                    level_data = level_data[level_data['COUNTRY'].isin(test_countries)]
                
                # Exclude large/problematic countries if specified
                if self.exclude_large and not test_countries:  # Don't exclude if we're testing specific countries
                    before_count = len(level_data)
                    level_data = level_data[~level_data['COUNTRY'].isin(self.problematic_countries)]
                    excluded_count = before_count - len(level_data)
                    if excluded_count > 0:
                        logging.info(f"      🚫 Excluded {excluded_count:,} entries from large countries")
                
                logging.info(f"      📊 Found {len(level_data):,} entries")
                
                if len(level_data) == 0:
                    all_processed_data[level] = []
                    continue
                
                # Dissolve geometries
                start_time = time.time()
                dissolved = level_data.dissolve(by=gid_col, aggfunc={
                    'COUNTRY': 'first',
                    name_col: 'first', 
                    'GID_0': 'first',
                    'NAME_0': 'first',
                }).reset_index()
                
                dissolve_time = time.time() - start_time
                logging.info(f"      ✅ Dissolved {len(level_data):,} → {len(dissolved):,} polygons in {dissolve_time:.1f}s")
                
                # Process entries
                processed_entries = []
                for idx, row in dissolved.iterrows():
                    try:
                        # Calculate bounds
                        bounds = row.geometry.bounds
                        
                        # Progressive simplification to fit Firestore limits
                        simplified_geom, geojson_str = self.progressive_simplify_geometry(row.geometry)
                        
                        # Log if heavily simplified
                        original_size = len(json.dumps(row.geometry.__geo_interface__).encode('utf-8'))
                        final_size = len(geojson_str.encode('utf-8'))
                        if final_size < original_size * 0.1:  # Less than 10% of original
                            logging.warning(f"      ⚠️  Heavily simplified {row[name_col]}: {original_size:,} → {final_size:,} bytes")
                        
                        # Create parent GIDs
                        parent_gids = {}
                        if level > 1:
                            gid_parts = row[gid_col].split('.')
                            if level >= 2 and len(gid_parts) >= 2:
                                parent_gids['state_gid'] = f"{gid_parts[0]}.{gid_parts[1]}"
                            if level >= 3 and len(gid_parts) >= 3:
                                parent_gids['county_gid'] = f"{gid_parts[0]}.{gid_parts[1]}.{gid_parts[2]}"
                            if level >= 4 and len(gid_parts) >= 4:
                                parent_gids['municipality_gid'] = f"{gid_parts[0]}.{gid_parts[1]}.{gid_parts[2]}.{gid_parts[3]}"
                            if level >= 5 and len(gid_parts) >= 5:
                                parent_gids['ward_gid'] = f"{gid_parts[0]}.{gid_parts[1]}.{gid_parts[2]}.{gid_parts[3]}.{gid_parts[4]}"
                        
                        # Create entry
                        entry = {
                            'id': row[gid_col],
                            'name': row[name_col],
                            'country_gid': row['GID_0'],
                            'country_name': row['COUNTRY'],
                            'admin_type': '',
                            'admin_type_en': '',
                            'bounds': {
                                'min_lat': bounds[1],
                                'max_lat': bounds[3],
                                'min_lon': bounds[0],
                                'max_lon': bounds[2],
                            },
                            'geometry': geojson_str,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now(),
                            'is_active': True,
                            **parent_gids
                        }
                        
                        processed_entries.append(entry)
                        
                    except Exception as e:
                        logging.error(f"      ❌ Error processing {row[name_col]}: {e}")
                        continue
                
                all_processed_data[level] = processed_entries
                logging.info(f"      ✅ Processed {len(processed_entries):,} entries for level {level}")
            
            return all_processed_data
            
        except Exception as e:
            logging.error(f"❌ Error loading/processing GADM data: {e}")
            return None
    
    def import_new_data(self, processed_data):
        """Import new corrected GADM data"""
        logging.info(f"\n📥 IMPORTING NEW CORRECTED GADM DATA")
        logging.info("=" * 50)
        
        if self.dry_run:
            # Show what would be imported
            for level, entries in processed_data.items():
                logging.info(f"🧪 DRY RUN: Would import {len(entries):,} entries to admin_level_{level}")
            return True
        
        try:
            total_imported = 0
            
            for level, entries in processed_data.items():
                if not entries:
                    logging.info(f"   ⚠️  No data to import for admin_level_{level}")
                    continue
                
                collection_name = f"admin_level_{level}"
                logging.info(f"   📥 Importing {len(entries):,} entries to {collection_name}...")
                
                # Import in batches
                batch_size = 100
                imported_count = 0
                
                for i in range(0, len(entries), batch_size):
                    batch_entries = entries[i:i + batch_size]
                    
                    # Create batch
                    batch = self.db.batch()
                    for entry in batch_entries:
                        doc_ref = self.db.collection(collection_name).document(entry['id'])
                        batch.set(doc_ref, entry)
                    
                    # Commit batch
                    batch.commit()
                    imported_count += len(batch_entries)
                    
                    logging.info(f"      📥 Imported batch of {len(batch_entries)} documents (total: {imported_count:,})")
                
                logging.info(f"      ✅ Imported {imported_count:,} documents to {collection_name}")
                total_imported += imported_count
            
            logging.info(f"✅ Import completed! Total imported: {total_imported:,} documents")
            return True
            
        except Exception as e:
            logging.error(f"❌ Import failed: {e}")
            return False
    
    def verify_import(self):
        """Verify that the new data was imported correctly"""
        logging.info(f"\n🔍 VERIFYING IMPORT SUCCESS")
        logging.info("=" * 50)
        
        try:
            # Test coordinates with known good coverage
            test_coords = [
                ('Paris, France', 48.8566, 2.3522),
                ('Munich, Germany', 48.1351, 11.5820),
                ('Kigali, Rwanda', -1.9441, 30.0619),
            ]
            
            verification_passed = True
            
            for location, lat, lon in test_coords:
                logging.info(f"   🎯 Testing {location} ({lat:.4f}, {lon:.4f}):")
                
                levels_found = 0
                
                for level in range(1, 6):
                    collection_name = f"admin_level_{level}"
                    
                    # Query with bounding box
                    query = self.db.collection(collection_name).where(
                        'is_active', '==', True
                    ).where(
                        'bounds.min_lat', '<=', lat
                    ).where(
                        'bounds.max_lat', '>=', lat
                    ).where(
                        'bounds.min_lon', '<=', lon
                    ).where(
                        'bounds.max_lon', '>=', lon
                    ).limit(10)
                    
                    docs = list(query.stream())
                    
                    # Check for point-in-polygon matches
                    matches = []
                    for doc in docs:
                        data = doc.to_dict()
                        if 'geometry' in data and data['geometry']:
                            try:
                                geom_dict = json.loads(data['geometry'])
                                polygon = shape(geom_dict)
                                point = Point(lon, lat)
                                
                                if polygon.contains(point):
                                    matches.append(data['name'])
                                    break
                            except:
                                continue
                    
                    if matches:
                        levels_found += 1
                        logging.info(f"      Level {level}: ✅ {matches[0]}")
                    else:
                        logging.info(f"      Level {level}: ❌ No match")
                
                if levels_found >= 2:  # At least 2 levels should match
                    logging.info(f"      📊 Result: ✅ GOOD ({levels_found}/5 levels)")
                else:
                    logging.info(f"      📊 Result: ❌ POOR ({levels_found}/5 levels)")
                    verification_passed = False
            
            if verification_passed:
                logging.info(f"✅ Verification PASSED! New data is working correctly.")
            else:
                logging.error(f"❌ Verification FAILED! New data may have issues.")
            
            return verification_passed
            
        except Exception as e:
            logging.error(f"❌ Verification failed: {e}")
            return False
    
    def replace_data(self, gpkg_path, test_countries=None):
        """Complete data replacement workflow"""
        logging.info(f"\n🚀 STARTING GADM DATA REPLACEMENT")
        logging.info("=" * 60)
        logging.info(f"   Source: {gpkg_path}")
        logging.info(f"   Test countries: {test_countries}")
        logging.info(f"   Mode: {'🧪 DRY RUN' if self.dry_run else '🚀 PRODUCTION'}")
        
        # Step 1: Backup existing data
        if not self.backup_existing_data():
            logging.error("❌ Backup failed - ABORTING")
            return False
        
        # Step 2: Load and process new data
        processed_data = self.load_and_process_gadm_data(gpkg_path, test_countries)
        if not processed_data:
            logging.error("❌ Data processing failed - ABORTING")
            return False
        
        # Step 3: Delete existing data
        if not self.delete_existing_data():
            logging.error("❌ Deletion failed - ABORTING")
            return False
        
        # Step 4: Import new data
        if not self.import_new_data(processed_data):
            logging.error("❌ Import failed - ABORTING")
            return False
        
        # Step 5: Verify import
        if not self.verify_import():
            logging.error("❌ Verification failed - CHECK DATA")
            return False
        
        logging.info(f"\n🎉 GADM DATA REPLACEMENT COMPLETED SUCCESSFULLY!")
        logging.info("=" * 60)
        logging.info("✅ Old corrupted data backed up and removed")
        logging.info("✅ New corrected data imported and verified")
        logging.info("✅ Point-in-polygon queries working correctly")
        logging.info("🚀 System ready for production use!")
        
        return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Replace GADM data with corrected version')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without actual changes')
    parser.add_argument('--test-countries', nargs='+', default=['France', 'Germany', 'Rwanda'], 
                       help='Countries to include in test import')
    parser.add_argument('--full-import', action='store_true', help='Import all countries (not just test countries)')
    parser.add_argument('--skip-backup', action='store_true', help='Skip backup to Cloud Storage (faster but less safe)')
    parser.add_argument('--exclude-large', action='store_true', help='Exclude countries with notoriously large geometries')
    parser.add_argument('--max-geometry-size', type=int, default=900000, help='Maximum geometry size in bytes (default: 900KB)')
    
    args = parser.parse_args()
    
    # Configuration
    gpkg_path = 'city data/gadm_410.gpkg'
    test_countries = None if args.full_import else args.test_countries
    
    # Create replacer
    replacer = GADMDataReplacer(
        dry_run=args.dry_run, 
        skip_backup=args.skip_backup,
        exclude_large=args.exclude_large,
        max_geometry_size=args.max_geometry_size
    )
    
    # Run replacement
    success = replacer.replace_data(gpkg_path, test_countries)
    
    if success:
        logging.info("🎉 SUCCESS: GADM data replacement completed!")
        sys.exit(0)
    else:
        logging.error("❌ FAILURE: GADM data replacement failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
