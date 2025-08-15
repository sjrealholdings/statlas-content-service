#!/usr/bin/env python3
"""
Quick fidelity check - compare original vs stored geometries
"""

import json
import geopandas as gpd
from google.cloud import firestore
from shapely.geometry import shape

def main():
    # Initialize Firestore
    db = firestore.Client(database='statlas-content')
    
    print("🔍 QUICK GEOMETRY FIDELITY CHECK")
    print("=" * 50)
    
    # Load original GADM data
    try:
        print("📂 Loading original GADM data...")
        gdf = gpd.read_file("city data/gadm_410.gpkg", layer='gadm_410')
        print(f"   ✅ Loaded {len(gdf):,} original polygons")
        
        # Filter for Level 1 France data as example (has GID_1 but not GID_2)
        france_level1 = gdf[(gdf['COUNTRY'] == 'France') & 
                           (gdf['GID_1'].notna()) & 
                           (gdf['GID_2'].isna())]
        print(f"   🇫🇷 Found {len(france_level1)} French Level 1 areas")
        
        if len(france_level1) == 0:
            print("   ❌ No French Level 1 data found")
            return
            
        # Get one example - Île-de-France
        ile_de_france = france_level1[france_level1['NAME_1'] == 'Île-de-France']
        if len(ile_de_france) == 0:
            # Just take the first one
            ile_de_france = france_level1.iloc[0:1]
            region_name = ile_de_france.iloc[0]['NAME_1']
        else:
            region_name = 'Île-de-France'
            
        original_geom = ile_de_france.iloc[0].geometry
        
        # Calculate original stats
        original_json = json.dumps(original_geom.__geo_interface__)
        original_size = len(original_json.encode('utf-8'))
        original_vertices = count_vertices(original_geom.__geo_interface__)
        
        print(f"\n📍 ORIGINAL {region_name}:")
        print(f"   📏 Size: {original_size:,} bytes ({original_size/1024:.1f} KB)")
        print(f"   🔺 Vertices: {original_vertices:,}")
        
    except Exception as e:
        print(f"   ❌ Error loading original data: {e}")
        return
    
    # Get stored data
    try:
        print(f"\n🗃️  Loading stored data...")
        stored_docs = list(db.collection('admin_level_1')
                          .where('country_name', '==', 'France')
                          .where('name', '==', region_name)
                          .limit(1)
                          .stream())
        
        if not stored_docs:
            print(f"   ❌ No stored data found for {region_name}")
            return
            
        stored_data = stored_docs[0].to_dict()
        stored_geom_json = json.loads(stored_data['geometry'])
        stored_size = len(stored_data['geometry'].encode('utf-8'))
        stored_vertices = count_vertices(stored_geom_json)
        
        print(f"\n📍 STORED {region_name}:")
        print(f"   📏 Size: {stored_size:,} bytes ({stored_size/1024:.1f} KB)")
        print(f"   🔺 Vertices: {stored_vertices:,}")
        
        # Calculate reductions
        size_reduction = (original_size - stored_size) / original_size * 100
        vertex_reduction = (original_vertices - stored_vertices) / original_vertices * 100
        
        print(f"\n📊 FIDELITY LOSS:")
        print(f"   📏 Size reduction: {size_reduction:.1f}%")
        print(f"   🔺 Vertex reduction: {vertex_reduction:.1f}%")
        
        # Test different simplification tolerances on original
        print(f"\n🧪 SIMPLIFICATION TOLERANCE TEST:")
        print("   (What different tolerances would produce)")
        
        from shapely import simplify
        tolerances = [0.001, 0.01, 0.05, 0.1, 0.2, 0.5]
        
        for tolerance in tolerances:
            try:
                simplified = simplify(original_geom, tolerance=tolerance, preserve_topology=True)
                simplified_json = json.dumps(simplified.__geo_interface__)
                simplified_size = len(simplified_json.encode('utf-8'))
                simplified_vertices = count_vertices(simplified.__geo_interface__)
                
                size_red = (original_size - simplified_size) / original_size * 100
                vertex_red = (original_vertices - simplified_vertices) / original_vertices * 100
                
                marker = " ← ACTUAL" if abs(simplified_size - stored_size) < 1000 else ""
                print(f"   🔧 {tolerance:>5}: {simplified_size:>7,} bytes ({size_red:>5.1f}%), {simplified_vertices:>6,} vertices ({vertex_red:>5.1f}%){marker}")
                
            except Exception as e:
                print(f"   ⚠️  Tolerance {tolerance} failed: {e}")
        
    except Exception as e:
        print(f"   ❌ Error loading stored data: {e}")

def count_vertices(geometry_json):
    """Count vertices in a GeoJSON geometry"""
    if geometry_json['type'] == 'Polygon':
        return sum(len(ring) for ring in geometry_json['coordinates'])
    elif geometry_json['type'] == 'MultiPolygon':
        return sum(sum(len(ring) for ring in polygon) for polygon in geometry_json['coordinates'])
    else:
        return 0

if __name__ == "__main__":
    main()
