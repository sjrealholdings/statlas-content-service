#!/usr/bin/env python3
"""
Import Natural Earth coastline data for land-ocean classification and distance calculations.

This script downloads and imports Natural Earth 10m physical coastline data
to support the Core Service's hierarchical grid generation system.
"""

import argparse
import json
import logging
import os
import sys
import time
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
import fiona
import shapely.geometry
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NaturalEarthCoastlineImporter:
    """Import Natural Earth coastline data into Firestore."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.db = firestore.Client(project=project_id, database='statlas-content')
        
        # Natural Earth data URLs (GitHub raw files)
        self.base_url = 'https://github.com/nvkelso/natural-earth-vector/raw/master/10m_physical'
        self.shapefile_components = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
        
        self.data_dir = 'natural_earth_data'
        
    def download_data(self, data_type: str = 'coastlines') -> str:
        """Download Natural Earth shapefile components."""
        # Map data types to filenames
        filename_map = {
            'coastlines': 'ne_10m_coastline',
            'land': 'ne_10m_land', 
            'ocean': 'ne_10m_ocean'
        }
        
        if data_type not in filename_map:
            raise ValueError(f"Unknown data type: {data_type}")
            
        base_filename = filename_map[data_type]
        data_subdir = os.path.join(self.data_dir, data_type)
        
        # Create data directory
        os.makedirs(data_subdir, exist_ok=True)
        
        # Download all shapefile components
        logger.info(f"Downloading {data_type} data from Natural Earth GitHub...")
        
        for ext in self.shapefile_components:
            filename = f"{base_filename}{ext}"
            filepath = os.path.join(data_subdir, filename)
            
            if os.path.exists(filepath):
                logger.info(f"File {filename} already exists, skipping download")
                continue
                
            url = f"{self.base_url}/{filename}"
            logger.info(f"Downloading {filename}...")
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        # Return path to the .shp file
        shp_path = os.path.join(data_subdir, f"{base_filename}.shp")
        logger.info(f"Downloaded {data_type} shapefile successfully")
        return shp_path
        

        
    def geometry_to_geojson(self, geometry) -> Dict:
        """Convert Shapely geometry to GeoJSON."""
        if hasattr(geometry, '__geo_interface__'):
            return geometry.__geo_interface__
        else:
            return shapely.geometry.mapping(geometry)
            
    def calculate_bounds(self, geometry) -> Dict[str, float]:
        """Calculate bounding box for geometry."""
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        return {
            'min_lon': bounds[0],
            'min_lat': bounds[1], 
            'max_lon': bounds[2],
            'max_lat': bounds[3]
        }
        
    def import_coastlines(self, shapefile_path: str, dry_run: bool = False) -> int:
        """Import coastline data from shapefile."""
        logger.info(f"Importing coastlines from {shapefile_path}")
        
        collection_ref = self.db.collection('coastlines')
        imported_count = 0
        
        # Clear existing coastline data if not dry run
        if not dry_run:
            logger.info("Clearing existing coastline data...")
            docs = collection_ref.get()
            for doc in docs:
                doc.reference.delete()
                
        with fiona.open(shapefile_path) as shapefile:
            logger.info(f"Found {len(shapefile)} coastline features")
            
            for idx, feature in enumerate(shapefile):
                try:
                    # Extract geometry and properties
                    geometry = shapely.geometry.shape(feature['geometry'])
                    properties = dict(feature['properties']) if feature['properties'] else {}
                    
                    # Create document data
                    doc_data = {
                        'id': f"coastline_{idx}",
                        'type': 'coastline',
                        'geometry': json.dumps(self.geometry_to_geojson(geometry)),
                        'bounds': self.calculate_bounds(geometry),
                        'properties': properties,
                        'length_km': geometry.length * 111.32,  # Rough conversion to km
                        'is_active': True,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'source': 'natural_earth_10m',
                        'version': '5.1.1'
                    }
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would import coastline {idx}: {properties}")
                    else:
                        # Import to Firestore
                        doc_ref = collection_ref.document(f"coastline_{idx}")
                        doc_ref.set(doc_data)
                        
                    imported_count += 1
                    
                    if imported_count % 100 == 0:
                        logger.info(f"Processed {imported_count} coastline features...")
                        
                except Exception as e:
                    logger.error(f"Error processing coastline feature {idx}: {e}")
                    continue
                    
        logger.info(f"{'[DRY RUN] Would import' if dry_run else 'Imported'} {imported_count} coastline features")
        return imported_count
        
    def import_land_ocean(self, land_shapefile: str, ocean_shapefile: str, dry_run: bool = False) -> Tuple[int, int]:
        """Import land and ocean polygon data."""
        land_count = self.import_polygons(land_shapefile, 'land_polygons', 'land', dry_run)
        ocean_count = self.import_polygons(ocean_shapefile, 'ocean_polygons', 'ocean', dry_run)
        return land_count, ocean_count
        
    def import_polygons(self, shapefile_path: str, collection_name: str, polygon_type: str, dry_run: bool = False) -> int:
        """Import polygon data (land or ocean) from shapefile."""
        logger.info(f"Importing {polygon_type} polygons from {shapefile_path}")
        
        collection_ref = self.db.collection(collection_name)
        imported_count = 0
        
        # Clear existing data if not dry run
        if not dry_run:
            logger.info(f"Clearing existing {polygon_type} data...")
            docs = collection_ref.get()
            for doc in docs:
                doc.reference.delete()
                
        with fiona.open(shapefile_path) as shapefile:
            logger.info(f"Found {len(shapefile)} {polygon_type} features")
            
            for idx, feature in enumerate(shapefile):
                try:
                    # Extract geometry and properties
                    geometry = shapely.geometry.shape(feature['geometry'])
                    properties = dict(feature['properties']) if feature['properties'] else {}
                    
                    # Create document data
                    doc_data = {
                        'id': f"{polygon_type}_{idx}",
                        'type': polygon_type,
                        'geometry': json.dumps(self.geometry_to_geojson(geometry)),
                        'bounds': self.calculate_bounds(geometry),
                        'properties': properties,
                        'area_km2': geometry.area * (111.32 ** 2),  # Rough conversion to km²
                        'is_active': True,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'source': 'natural_earth_10m',
                        'version': '5.1.1'
                    }
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would import {polygon_type} {idx}: {properties}")
                    else:
                        # Import to Firestore
                        doc_ref = collection_ref.document(f"{polygon_type}_{idx}")
                        doc_ref.set(doc_data)
                        
                    imported_count += 1
                    
                    if imported_count % 50 == 0:
                        logger.info(f"Processed {imported_count} {polygon_type} features...")
                        
                except Exception as e:
                    logger.error(f"Error processing {polygon_type} feature {idx}: {e}")
                    continue
                    
        logger.info(f"{'[DRY RUN] Would import' if dry_run else 'Imported'} {imported_count} {polygon_type} features")
        return imported_count

def main():
    parser = argparse.ArgumentParser(description='Import Natural Earth coastline data')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--data-type', choices=['coastlines', 'land-ocean', 'all'], 
                       default='coastlines', help='Type of data to import')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without making changes')
    
    args = parser.parse_args()
    
    logger.info(f"Starting Natural Earth import for project: {args.project_id}")
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        
    try:
        importer = NaturalEarthCoastlineImporter(args.project_id)
        
        if args.data_type in ['coastlines', 'all']:
            # Download and import coastlines
            shapefile_path = importer.download_data('coastlines')
            
            coastline_count = importer.import_coastlines(shapefile_path, args.dry_run)
            logger.info(f"Coastline import complete: {coastline_count} features")
            
        if args.data_type in ['land-ocean', 'all']:
            # Download and import land polygons
            land_shapefile = importer.download_data('land')
            
            # Download and import ocean polygons  
            ocean_shapefile = importer.download_data('ocean')
            
            land_count, ocean_count = importer.import_land_ocean(land_shapefile, ocean_shapefile, args.dry_run)
            logger.info(f"Land-Ocean import complete: {land_count} land, {ocean_count} ocean features")
            
        logger.info("Natural Earth import completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during import: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
