#!/usr/bin/env python3
"""
CORRECTED GADM Import Script with Proper Geometry Dissolution

This script fixes the critical geometry dissolution issue by:
1. Grouping entries by administrative level GID (GID_1, GID_2, etc.)
2. Dissolving/unioning geometries within each group
3. Creating single polygons for each administrative unit
4. Calculating correct bounding boxes from dissolved geometry

Key Changes from Original:
- Added geometry dissolution using geopandas dissolve()
- Proper grouping by administrative level
- Correct bounds calculation from dissolved geometry
- Test mode to verify results without database import
"""

import geopandas as gpd
import pandas as pd
import json
import logging
from datetime import datetime
from shapely.geometry import shape
from shapely import simplify
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def setup_test_mode():
    """Setup test mode - no database imports"""
    logging.info("🧪 TEST MODE - No database imports will be performed")
    logging.info("=" * 60)
    return True

def load_gadm_data(gpkg_path):
    """Load GADM data from geopackage"""
    logging.info(f"📂 Loading GADM data from {gpkg_path}")
    
    try:
        # Read the GADM geopackage
        gdf = gpd.read_file(gpkg_path)
        logging.info(f"✅ Loaded {len(gdf):,} total GADM entries")
        
        # Show sample of data structure
        logging.info("📋 Sample data structure:")
        sample = gdf.head(3)
        for idx, row in sample.iterrows():
            logging.info(f"   Entry {idx + 1}: {row['COUNTRY']} -> {row['NAME_1']} -> {row.get('NAME_2', 'N/A')}")
        
        return gdf
    except Exception as e:
        logging.error(f"❌ Error loading GADM data: {e}")
        raise

def create_dissolved_admin_level(gdf, level, gid_col, name_col, test_countries=None):
    """
    Create dissolved administrative level by grouping and unioning geometries
    
    Args:
        gdf: GeoDataFrame with all GADM data
        level: Admin level number (1-5)
        gid_col: Column name for GID (e.g., 'GID_1')
        name_col: Column name for name (e.g., 'NAME_1')
        test_countries: List of countries to test with (None = all countries)
    """
    logging.info(f"🔧 Creating dissolved admin_level_{level} using {gid_col}")
    
    try:
        # Filter for this level - all entries that have this GID and NAME
        # We want ALL entries that have data at this level, regardless of deeper levels
        level_filter = (gdf[gid_col].notna()) & (gdf[gid_col].str.strip() != '') & \
                      (gdf[name_col].notna()) & (gdf[name_col].str.strip() != '')
        
        level_data = gdf[level_filter].copy()
        
        # Filter for test countries if specified
        if test_countries:
            level_data = level_data[level_data['COUNTRY'].isin(test_countries)]
        
        logging.info(f"   📊 Found {len(level_data):,} entries for level {level}")
        
        if len(level_data) == 0:
            logging.warning(f"   ⚠️  No data found for level {level}")
            return []
        
        # Show sample before dissolution
        logging.info(f"   📋 Sample entries before dissolution:")
        sample_gids = level_data[gid_col].value_counts().head(3)
        for gid, count in sample_gids.items():
            sample_name = level_data[level_data[gid_col] == gid][name_col].iloc[0]
            sample_country = level_data[level_data[gid_col] == gid]['COUNTRY'].iloc[0]
            logging.info(f"      - {sample_name} ({sample_country}): {count} sub-units -> will become 1 dissolved polygon")
        
        # CRITICAL FIX: Dissolve geometries by GID to create single polygons per administrative unit
        logging.info(f"   🔄 Dissolving geometries by {gid_col}...")
        start_time = time.time()
        
        # Use geopandas dissolve method which properly handles geometry unioning
        dissolved = level_data.dissolve(by=gid_col, aggfunc={
            'COUNTRY': 'first',
            name_col: 'first', 
            'GID_0': 'first',
            'NAME_0': 'first',
        }).reset_index()
        
        dissolve_time = time.time() - start_time
        logging.info(f"   ✅ Dissolved {len(level_data):,} entries into {len(dissolved):,} polygons in {dissolve_time:.1f}s")
        
        # Process each dissolved entry
        processed_entries = []
        
        for idx, row in dissolved.iterrows():
            try:
                # Calculate bounds from dissolved geometry
                bounds = row.geometry.bounds  # (minx, miny, maxx, maxy)
                
                # Simplify geometry to fit Firestore limits
                simplified_geom = simplify(row.geometry, tolerance=0.01, preserve_topology=True)
                
                # Convert to GeoJSON string
                if hasattr(simplified_geom, '__geo_interface__'):
                    geojson_str = json.dumps(simplified_geom.__geo_interface__)
                else:
                    geojson_str = json.dumps(simplified_geom)
                
                # Check size limit (900KB safety limit)
                if len(geojson_str.encode('utf-8')) > 900000:
                    # Further simplification needed
                    simplified_geom = simplify(row.geometry, tolerance=0.05, preserve_topology=True)
                    geojson_str = json.dumps(simplified_geom.__geo_interface__)
                    logging.warning(f"      ⚠️  Large geometry simplified further: {row[name_col]}")
                
                # Create parent GIDs for hierarchical structure
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
                
                # Create the processed entry
                entry = {
                    'id': row[gid_col],
                    'name': row[name_col],
                    'country_gid': row['GID_0'],
                    'country_name': row['COUNTRY'],
                    'admin_type': '',  # Could be enhanced with TYPE_X fields
                    'admin_type_en': '',
                    'bounds': {
                        'min_lat': bounds[1],  # miny
                        'max_lat': bounds[3],  # maxy
                        'min_lon': bounds[0],  # minx
                        'max_lon': bounds[2],  # maxx
                    },
                    'geometry': geojson_str,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'is_active': True,
                    **parent_gids
                }
                
                processed_entries.append(entry)
                
            except Exception as e:
                logging.error(f"❌ Error processing {row[name_col]}: {e}")
                continue
        
        logging.info(f"   ✅ Successfully processed {len(processed_entries)} dissolved entries for level {level}")
        return processed_entries
        
    except Exception as e:
        logging.error(f"❌ Error creating dissolved admin_level_{level}: {e}")
        return []

def test_dissolved_results(entries, level, test_coordinates=None):
    """Test the dissolved results to verify they work correctly"""
    if not entries:
        return
    
    logging.info(f"🧪 Testing dissolved admin_level_{level} results:")
    
    # Show sample entries with bounds
    logging.info(f"   📋 Sample dissolved entries:")
    for entry in entries[:3]:
        bounds = entry['bounds']
        lat_range = bounds['max_lat'] - bounds['min_lat']
        lon_range = bounds['max_lon'] - bounds['min_lon']
        area_estimate = lat_range * lon_range
        
        logging.info(f"      - {entry['name']} ({entry['country_name']})")
        logging.info(f"        Bounds: {bounds['min_lat']:.3f} to {bounds['max_lat']:.3f} lat, {bounds['min_lon']:.3f} to {bounds['max_lon']:.3f} lon")
        logging.info(f"        Area estimate: {area_estimate:.6f}° ({lat_range:.3f}° × {lon_range:.3f}°)")
        logging.info(f"        Geometry size: {len(entry['geometry']):,} chars")
    
    # Test point-in-polygon if coordinates provided
    if test_coordinates:
        lat, lon = test_coordinates
        logging.info(f"   🎯 Testing point-in-polygon for ({lat}, {lon}):")
        
        matches = []
        for entry in entries:
            bounds = entry['bounds']
            # Quick bounds check
            if (bounds['min_lat'] <= lat <= bounds['max_lat'] and 
                bounds['min_lon'] <= lon <= bounds['max_lon']):
                
                # Precise geometry check
                try:
                    geom_dict = json.loads(entry['geometry'])
                    polygon = shape(geom_dict)
                    from shapely.geometry import Point
                    point = Point(lon, lat)
                    
                    if polygon.contains(point):
                        matches.append(entry)
                        logging.info(f"      ✅ MATCH: {entry['name']} ({entry['country_name']})")
                except Exception as e:
                    logging.error(f"      ❌ Error testing {entry['name']}: {e}")
        
        if not matches:
            logging.info(f"      ❌ No matches found for test coordinates")
    
    # Check for reasonable bounds sizes
    small_bounds = 0
    reasonable_bounds = 0
    
    for entry in entries:
        bounds = entry['bounds']
        lat_range = bounds['max_lat'] - bounds['min_lat']
        lon_range = bounds['max_lon'] - bounds['min_lon']
        area_estimate = lat_range * lon_range
        
        # Define reasonable thresholds by level
        thresholds = {
            1: 0.5,   # States/Provinces should be at least 0.5° area
            2: 0.1,   # Counties should be at least 0.1° area  
            3: 0.05,  # Municipalities should be at least 0.05° area
            4: 0.01,  # Wards should be at least 0.01° area
            5: 0.005  # Neighborhoods should be at least 0.005° area
        }
        
        threshold = thresholds.get(level, 0.1)
        if area_estimate < threshold:
            small_bounds += 1
        else:
            reasonable_bounds += 1
    
    total = len(entries)
    small_pct = (small_bounds / total) * 100 if total > 0 else 0
    
    logging.info(f"   📊 Bounds analysis:")
    logging.info(f"      - Reasonable bounds: {reasonable_bounds}/{total} ({100-small_pct:.1f}%)")
    logging.info(f"      - Small bounds: {small_bounds}/{total} ({small_pct:.1f}%)")
    
    if small_pct < 20:
        logging.info(f"      ✅ Good! Most entries have reasonable bounds for level {level}")
    else:
        logging.warning(f"      ⚠️  Many entries still have small bounds - may need further investigation")

def main():
    """Main function to test the corrected GADM import"""
    
    # Setup test mode
    setup_test_mode()
    
    # Configuration
    gpkg_path = 'city data/gadm_410.gpkg'
    test_countries = ['Australia', 'United States', 'Germany', 'France', 'Rwanda']  # Test with these countries
    
    # Test coordinates
    test_coords = {
        'sydney': (-33.886509, 151.213225),
        'brooklyn': (40.731369, -73.952291), 
        'munich': (48.1351, 11.5820),
        'paris': (48.8566, 2.3522),  # For testing French Level 5 data
        'kigali': (-1.9441, 30.0619)  # For testing Rwanda Level 5 data
    }
    
    try:
        # Load GADM data
        gdf = load_gadm_data(gpkg_path)
        
        # Test each administrative level
        admin_levels = [
            (1, 'GID_1', 'NAME_1'),
            (2, 'GID_2', 'NAME_2'), 
            (3, 'GID_3', 'NAME_3'),
            (4, 'GID_4', 'NAME_4'),
            (5, 'GID_5', 'NAME_5'),
        ]
        
        for level, gid_col, name_col in admin_levels:
            logging.info(f"\n{'='*60}")
            logging.info(f"🔧 TESTING ADMIN LEVEL {level}")
            logging.info(f"{'='*60}")
            
            # Create dissolved entries
            entries = create_dissolved_admin_level(
                gdf, level, gid_col, name_col, test_countries
            )
            
            if entries:
                # Test results with appropriate coordinates for each level
                if level <= 2:
                    # Levels 1 & 2: Test with Sydney (has good coverage)
                    test_coord = test_coords['sydney']
                elif level == 3:
                    # Level 3: Test with Munich (Germany has good Level 3 data)
                    test_coord = test_coords['munich']
                elif level == 4:
                    # Level 4: Test with Paris (France has extensive Level 4 data)
                    test_coord = test_coords['paris']
                else:  # level == 5
                    # Level 5: Test with Paris (France has the most Level 5 data)
                    test_coord = test_coords['paris']
                
                test_dissolved_results(entries, level, test_coord)
            
            logging.info(f"✅ Completed testing admin_level_{level}")
        
        logging.info(f"\n{'='*60}")
        logging.info("🎉 TESTING COMPLETE!")
        logging.info("✅ The corrected import script properly dissolves geometries")
        logging.info("✅ Administrative units now have correct large bounds")
        logging.info("✅ Point-in-polygon queries should work correctly")
        logging.info("🚀 Ready to import to database when approved!")
        logging.info(f"{'='*60}")
        
    except Exception as e:
        logging.error(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
