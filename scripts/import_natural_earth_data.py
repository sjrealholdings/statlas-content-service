#!/usr/bin/env python3
"""
Import Natural Earth 10m Cultural data into the statlas-content Firestore database.

This script downloads and processes Natural Earth's 10m cultural vector data to create
the 4-tier hierarchical country system:
1. Sovereign States (209 total) - Passport-issuing entities
2. Countries (258 total) - Distinct countries 
3. Map Units (298 total) - Dependencies and territories
4. Map Subunits (360 total) - Non-contiguous regions

Data source: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-details/
GitHub: https://github.com/nvkelso/natural-earth-vector/blob/master/10m_cultural

Usage:
    python3 import_natural_earth_data.py --project-id your-project-id [--dry-run]
"""

import argparse
import sys
import os
import time
import zipfile
import tempfile
import shutil
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import requests
import pandas as pd
import geopandas as gpd
from google.cloud import firestore
from google.cloud import storage
from tqdm import tqdm

# Natural Earth 10m Cultural data URLs - Correct download links
NATURAL_EARTH_FILES = {
    "admin_0_countries": {
        "url": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip",
        "description": "Admin-0 Countries (258 countries)"
    },
    "admin_0_map_units": {
        "url": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_map_units.zip", 
        "description": "Admin-0 Map Units (298 map units)"
    },
    "admin_0_map_subunits": {
        "url": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_map_subunits.zip",
        "description": "Admin-0 Map Subunits (360 map subunits)"
    },
    "admin_0_sovereignty": {
        "url": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_sovereignty.zip",
        "description": "Admin-0 Sovereignty (209 sovereign states)"
    }
}

class NaturalEarthImporter:
    def __init__(self, project_id: str, dry_run: bool = False):
        self.project_id = project_id
        self.dry_run = dry_run
        self.temp_dir = None
        
        if not dry_run:
            # Initialize Firestore client with statlas-content database
            self.db = firestore.Client(project=project_id, database="statlas-content")
        
        print(f"🌍 Natural Earth Data Importer")
        print(f"📋 Project ID: {project_id}")
        print(f"🔍 Dry run: {dry_run}")
        print(f"📊 Data source: Natural Earth 10m Cultural Vectors")
        print()

    def download_and_extract_data(self) -> Dict[str, str]:
        """Download and extract all Natural Earth data files."""
        print("📥 Downloading Natural Earth 10m Cultural data...")
        
        self.temp_dir = tempfile.mkdtemp(prefix="natural_earth_")
        extracted_paths = {}
        
        for file_key, file_info in NATURAL_EARTH_FILES.items():
            print(f"   Downloading {file_info['description']}...")
            
            # Download the zip file
            response = requests.get(file_info["url"], stream=True)
            response.raise_for_status()
            
            zip_path = os.path.join(self.temp_dir, f"{file_key}.zip")
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract the zip file
            extract_dir = os.path.join(self.temp_dir, file_key)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the shapefile
            shp_file = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.shp'):
                        shp_file = os.path.join(root, file)
                        break
                if shp_file:
                    break
            
            if not shp_file:
                raise FileNotFoundError(f"No shapefile found in {file_key}")
            
            extracted_paths[file_key] = shp_file
            print(f"   ✅ Extracted: {os.path.basename(shp_file)}")
        
        print(f"📁 Data extracted to: {self.temp_dir}")
        print()
        return extracted_paths

    def process_sovereignty_data(self, shapefile_path: str) -> List[Dict[str, Any]]:
        """
        Process sovereignty data (209 sovereign states).
        Filter: Remove level=2,3,4 units AND remove type=Dependency, type=Lease, type=Country
        """
        print("🏛️ Processing Sovereign States data...")
        
        gdf = gpd.read_file(shapefile_path)
        print(f"   Total features loaded: {len(gdf)}")
        
        # Apply Natural Earth filtering rules for sovereignty
        # Remove level=2, level=3, level=4 units
        if 'LEVEL' in gdf.columns:
            gdf = gdf[~gdf['LEVEL'].isin([2, 3, 4])]
            print(f"   After level filtering: {len(gdf)}")
        
        # Remove type=Dependency, type=Lease, type=Country
        if 'TYPE' in gdf.columns:
            gdf = gdf[~gdf['TYPE'].isin(['Dependency', 'Lease', 'Country'])]
            print(f"   After type filtering: {len(gdf)}")
        
        sovereign_states = []
        
        for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Processing sovereign states"):
            # Create sovereign state ID from name
            state_id = self._create_id(row.get('NAME', ''))
            if not state_id:
                continue
            
            # Use simplified geometry for Firestore (enables point-in-polygon queries)
            geometry = None
            if row.geometry is not None:
                # Simplify geometry to reduce size (tolerance ~1km)
                simplified_geom = row.geometry.simplify(tolerance=0.01)
                geojson_str = gpd.GeoSeries([simplified_geom]).to_json()
                geometry_obj = eval(geojson_str)['features'][0]['geometry']
                
                # Check if simplified geometry fits in Firestore
                geometry_json = json.dumps(geometry_obj)
                if len(geometry_json.encode('utf-8')) < 900000:  # 900KB safety limit
                    geometry = geometry_json
            
            # Calculate bounds
            bounds = self._calculate_bounds(row.geometry)
            
            sovereign_state = {
                "id": state_id,
                "name": row.get('NAME', ''),
                "official_name": row.get('NAME_LONG', row.get('NAME', '')),
                "iso_alpha2": row.get('ISO_A2', ''),
                "iso_alpha3": row.get('ISO_A3', ''),
                "iso_numeric": self._safe_int(row.get('ISO_N3', 0)),
                "flag_url": f"https://cdn.statlas.com/flags/{state_id}.svg",
                "flag_emoji": self._get_flag_emoji(row.get('ISO_A2', '')),
                "bounds": bounds,
                "capital": row.get('ADMIN', ''),
                "population": self._safe_int(row.get('POP_EST', 0)),
                "area_km2": self._safe_float(row.get('POP_EST', 0)),  # Use area calculation if available
                "currency_code": "",  # Not available in base data
                "languages": [],  # Not available in base data
                "geometry": geometry,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
            
            sovereign_states.append(sovereign_state)
        
        print(f"   ✅ Processed {len(sovereign_states)} sovereign states")
        return sovereign_states

    def process_countries_data(self, shapefile_path: str) -> List[Dict[str, Any]]:
        """
        Process countries data (258 countries).
        Filter: Remove level=3 and level=4 rows
        """
        print("🌍 Processing Countries data...")
        
        gdf = gpd.read_file(shapefile_path)
        print(f"   Total features loaded: {len(gdf)}")
        
        # Apply Natural Earth filtering rules for countries
        # Remove level=3 and level=4 rows
        if 'LEVEL' in gdf.columns:
            gdf = gdf[~gdf['LEVEL'].isin([3, 4])]
            print(f"   After level filtering: {len(gdf)}")
        
        countries = []
        
        for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Processing countries"):
            # Create country ID from name
            country_id = self._create_id(row.get('NAME', ''))
            if not country_id:
                continue
            
            # Find parent sovereign state
            sovereign_state_id = self._create_id(row.get('SOVEREIGNT', ''))
            
            # Use simplified geometry for Firestore (enables point-in-polygon queries)
            geometry = None
            if row.geometry is not None:
                # Simplify geometry to reduce size (tolerance ~1km)
                simplified_geom = row.geometry.simplify(tolerance=0.01)
                geojson_str = gpd.GeoSeries([simplified_geom]).to_json()
                geometry_obj = eval(geojson_str)['features'][0]['geometry']
                
                # Check if simplified geometry fits in Firestore
                geometry_json = json.dumps(geometry_obj)
                if len(geometry_json.encode('utf-8')) < 900000:  # 900KB safety limit
                    geometry = geometry_json
            
            # Calculate bounds
            bounds = self._calculate_bounds(row.geometry)
            
            country = {
                "id": country_id,
                "sovereign_state_id": sovereign_state_id,
                "name": row.get('NAME', ''),
                "official_name": row.get('NAME_LONG', row.get('NAME', '')),
                "type": row.get('TYPE', 'Country'),
                "level": self._safe_int(row.get('LEVEL', 1)),
                "iso_alpha2": row.get('ISO_A2', ''),
                "iso_alpha3": row.get('ISO_A3', ''),
                "bounds": bounds,
                "capital": row.get('ADMIN', ''),
                "population": self._safe_int(row.get('POP_EST', 0)),
                "area_km2": self._safe_float(row.get('POP_EST', 0)),
                "geometry": geometry,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
            
            countries.append(country)
        
        print(f"   ✅ Processed {len(countries)} countries")
        return countries

    def process_map_units_data(self, shapefile_path: str) -> List[Dict[str, Any]]:
        """
        Process map units data (298 map units).
        Filter: Remove level=4 rows
        """
        print("🗺️ Processing Map Units data...")
        
        gdf = gpd.read_file(shapefile_path)
        print(f"   Total features loaded: {len(gdf)}")
        
        # Apply Natural Earth filtering rules for map units
        # Remove level=4 rows
        if 'LEVEL' in gdf.columns:
            gdf = gdf[gdf['LEVEL'] != 4]
            print(f"   After level filtering: {len(gdf)}")
        
        map_units = []
        
        for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Processing map units"):
            # Create map unit ID from name
            unit_id = self._create_id(row.get('NAME', ''))
            if not unit_id:
                continue
            
            # Find parent IDs
            sovereign_state_id = self._create_id(row.get('SOVEREIGNT', ''))
            country_id = self._create_id(row.get('NAME', ''))  # May be same as unit_id
            
            # Use simplified geometry for Firestore (enables point-in-polygon queries)
            geometry = None
            if row.geometry is not None:
                # Simplify geometry to reduce size (tolerance ~1km)
                simplified_geom = row.geometry.simplify(tolerance=0.01)
                geojson_str = gpd.GeoSeries([simplified_geom]).to_json()
                geometry_obj = eval(geojson_str)['features'][0]['geometry']
                
                # Check if simplified geometry fits in Firestore
                geometry_json = json.dumps(geometry_obj)
                if len(geometry_json.encode('utf-8')) < 900000:  # 900KB safety limit
                    geometry = geometry_json
            
            # Calculate bounds
            bounds = self._calculate_bounds(row.geometry)
            
            map_unit = {
                "id": unit_id,
                "sovereign_state_id": sovereign_state_id,
                "country_id": country_id,
                "name": row.get('NAME', ''),
                "official_name": row.get('NAME_LONG', row.get('NAME', '')),
                "type": row.get('TYPE', 'Country'),
                "level": self._safe_int(row.get('LEVEL', 1)),
                "admin_level": row.get('ADM0_A3', ''),
                "iso_alpha2": row.get('ISO_A2', ''),
                "iso_alpha3": row.get('ISO_A3', ''),
                "bounds": bounds,
                "population": self._safe_int(row.get('POP_EST', 0)),
                "area_km2": self._safe_float(row.get('POP_EST', 0)),
                "geometry": geometry,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
            
            map_units.append(map_unit)
        
        print(f"   ✅ Processed {len(map_units)} map units")
        return map_units

    def process_map_subunits_data(self, shapefile_path: str) -> List[Dict[str, Any]]:
        """
        Process map subunits data (360 map subunits).
        Filter: Export all rows (no filtering)
        """
        print("🏝️ Processing Map Subunits data...")
        
        gdf = gpd.read_file(shapefile_path)
        print(f"   Total features loaded: {len(gdf)}")
        
        map_subunits = []
        
        for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Processing map subunits"):
            # Create subunit ID from name
            subunit_id = self._create_id(row.get('NAME', ''))
            if not subunit_id:
                continue
            
            # Find parent IDs
            sovereign_state_id = self._create_id(row.get('SOVEREIGNT', ''))
            country_id = self._create_id(row.get('ADMIN', ''))
            map_unit_id = self._create_id(row.get('NAME', ''))  # May be same as subunit_id
            
            # Use simplified geometry for Firestore (enables point-in-polygon queries)
            geometry = None
            if row.geometry is not None:
                # Simplify geometry to reduce size (tolerance ~1km)
                simplified_geom = row.geometry.simplify(tolerance=0.01)
                geojson_str = gpd.GeoSeries([simplified_geom]).to_json()
                geometry_obj = eval(geojson_str)['features'][0]['geometry']
                
                # Check if simplified geometry fits in Firestore
                geometry_json = json.dumps(geometry_obj)
                if len(geometry_json.encode('utf-8')) < 900000:  # 900KB safety limit
                    geometry = geometry_json
            
            # Calculate bounds
            bounds = self._calculate_bounds(row.geometry)
            
            # Determine if this is mainland or island
            is_mainland = not any(keyword in row.get('NAME', '').lower() 
                                for keyword in ['island', 'islands', 'isle', 'atoll', 'archipelago'])
            
            map_subunit = {
                "id": subunit_id,
                "sovereign_state_id": sovereign_state_id,
                "country_id": country_id,
                "map_unit_id": map_unit_id,
                "name": row.get('NAME', ''),
                "official_name": row.get('NAME_LONG', row.get('NAME', '')),
                "type": row.get('TYPE', 'Country'),
                "level": self._safe_int(row.get('LEVEL', 1)),
                "admin_level": row.get('ADM0_A3', ''),
                "is_mainland": is_mainland,
                "bounds": bounds,
                "population": self._safe_int(row.get('POP_EST', 0)),
                "area_km2": self._safe_float(row.get('POP_EST', 0)),
                "geometry": geometry,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
            
            map_subunits.append(map_subunit)
        
        print(f"   ✅ Processed {len(map_subunits)} map subunits")
        return map_subunits

    def import_to_firestore(self, collection_name: str, data: List[Dict[str, Any]]):
        """Import data to Firestore collection."""
        if self.dry_run:
            print(f"   🔍 Would import {len(data)} items to {collection_name}")
            return
        
        print(f"   📤 Importing {len(data)} items to {collection_name}...")
        
        collection = self.db.collection(collection_name)
        batch = self.db.batch()
        batch_count = 0
        
        for item in tqdm(data, desc=f"Importing {collection_name}"):
            doc_ref = collection.document(item['id'])
            batch.set(doc_ref, item)
            batch_count += 1
            
            # Commit batch every 500 items (Firestore limit)
            if batch_count >= 500:
                batch.commit()
                batch = self.db.batch()
                batch_count = 0
                time.sleep(0.1)  # Small delay to avoid rate limits
        
        # Commit remaining items
        if batch_count > 0:
            batch.commit()
        
        print(f"   ✅ Imported {len(data)} items to {collection_name}")

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up temporary files")

    # Helper methods
    def _create_id(self, name: str) -> str:
        """Create a safe ID from a name."""
        if not name:
            return ""
        
        # Convert to lowercase and replace spaces/special chars with underscores
        safe_id = name.lower().strip()
        safe_id = ''.join(c if c.isalnum() else '_' for c in safe_id)
        safe_id = '_'.join(filter(None, safe_id.split('_')))  # Remove empty parts
        
        return safe_id[:50]  # Limit length

    def _calculate_bounds(self, geometry) -> Dict[str, float]:
        """Calculate bounding box from geometry."""
        if geometry is None or geometry.is_empty:
            return {"min_lat": 0, "max_lat": 0, "min_lon": 0, "max_lon": 0}
        
        bounds = geometry.bounds
        return {
            "min_lat": float(bounds[1]),
            "max_lat": float(bounds[3]),
            "min_lon": float(bounds[0]),
            "max_lon": float(bounds[2])
        }

    def _safe_int(self, value) -> int:
        """Safely convert value to int."""
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0

    def _safe_float(self, value) -> float:
        """Safely convert value to float."""
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0.0

    def _get_flag_emoji(self, iso_a2: str) -> str:
        """Convert ISO A2 code to flag emoji."""
        if not iso_a2 or len(iso_a2) != 2:
            return ""
        
        # Convert to regional indicator symbols
        return ''.join(chr(ord(c) - ord('A') + 0x1F1E6) for c in iso_a2.upper())

    def run_import(self):
        """Run the complete import process."""
        try:
            # Download and extract data
            extracted_paths = self.download_and_extract_data()
            
            print("🔄 Processing Natural Earth data...")
            print()
            
            # Process each data type according to Natural Earth filtering rules
            sovereign_states = self.process_sovereignty_data(extracted_paths['admin_0_sovereignty'])
            countries = self.process_countries_data(extracted_paths['admin_0_countries'])
            map_units = self.process_map_units_data(extracted_paths['admin_0_map_units'])
            map_subunits = self.process_map_subunits_data(extracted_paths['admin_0_map_subunits'])
            
            print()
            print("📊 Import Summary:")
            print(f"   • Sovereign States: {len(sovereign_states)}")
            print(f"   • Countries: {len(countries)}")
            print(f"   • Map Units: {len(map_units)}")
            print(f"   • Map Subunits: {len(map_subunits)}")
            print()
            
            # Import to Firestore
            if not self.dry_run:
                print("📤 Importing to Firestore...")
                self.import_to_firestore("sovereign_states", sovereign_states)
                self.import_to_firestore("countries", countries)
                self.import_to_firestore("map_units", map_units)
                self.import_to_firestore("map_subunits", map_subunits)
                
                print()
                print("🔍 Verifying import...")
                self._verify_import()
            
            print()
            print("✅ Natural Earth import complete!")
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            raise
        finally:
            self.cleanup()

    def _verify_import(self):
        """Verify the import was successful."""
        collections = ["sovereign_states", "countries", "map_units", "map_subunits"]
        
        for collection_name in collections:
            try:
                docs = list(self.db.collection(collection_name).where("is_active", "==", True).limit(5).stream())
                print(f"   ✅ {collection_name}: {len(docs)} sample records found")
            except Exception as e:
                print(f"   ⚠️  {collection_name}: Verification failed - {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Import Natural Earth 10m Cultural data to statlas-content database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Import all Natural Earth data
    python3 import_natural_earth_data.py --project-id statlas-467715
    
    # Dry run to see what would be imported
    python3 import_natural_earth_data.py --project-id statlas-467715 --dry-run
        """
    )
    
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be imported without actually importing")
    
    args = parser.parse_args()
    
    try:
        importer = NaturalEarthImporter(args.project_id, args.dry_run)
        importer.run_import()
    except KeyboardInterrupt:
        print("\n⚠️  Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
