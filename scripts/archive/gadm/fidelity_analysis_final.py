#!/usr/bin/env python3
"""
Final geometry fidelity analysis - compare dissolved vs original GADM data
"""

import json
import geopandas as gpd
from google.cloud import firestore
from shapely.geometry import shape
from shapely import simplify
import statistics

def count_vertices(geometry_json):
    """Count vertices in a GeoJSON geometry"""
    if geometry_json['type'] == 'Polygon':
        return sum(len(ring) for ring in geometry_json['coordinates'])
    elif geometry_json['type'] == 'MultiPolygon':
        return sum(sum(len(ring) for ring in polygon) for polygon in geometry_json['coordinates'])
    else:
        return 0

def analyze_level_fidelity(level=1, sample_regions=['Île-de-France', 'Bayern', 'Provence-Alpes-Côte d\'Azur']):
    """Analyze fidelity for a specific administrative level"""
    print(f"\n🔍 LEVEL {level} FIDELITY ANALYSIS")
    print("=" * 50)
    
    # Initialize Firestore
    db = firestore.Client(database='statlas-content')
    
    try:
        # Load original GADM data
        print("📂 Loading original GADM data...")
        gdf = gpd.read_file("city data/gadm_410.gpkg", layer='gadm_410')
        
        # Filter for specific level by checking which GID columns are populated
        level_col = f'GID_{level}'
        name_col = f'NAME_{level}'
        
        # Get all data for this level
        level_data = gdf[gdf[level_col].notna() & gdf[name_col].notna()].copy()
        print(f"   ✅ Found {len(level_data):,} original polygons at Level {level}")
        
        # Dissolve by GID to match what our import script does
        print("   🔄 Dissolving geometries by GID...")
        dissolved = level_data.dissolve(by=level_col, aggfunc={
            'COUNTRY': 'first',
            name_col: 'first'
        }).reset_index()
        
        print(f"   ✅ Dissolved to {len(dissolved):,} unique administrative areas")
        
        # Analyze a few sample regions
        results = []
        for region_name in sample_regions:
            region_data = dissolved[dissolved[name_col] == region_name]
            if len(region_data) == 0:
                print(f"   ⚠️  Region '{region_name}' not found at Level {level}")
                continue
                
            original_geom = region_data.iloc[0].geometry
            country = region_data.iloc[0]['COUNTRY']
            
            # Calculate original (dissolved) stats
            original_json = json.dumps(original_geom.__geo_interface__)
            original_size = len(original_json.encode('utf-8'))
            original_vertices = count_vertices(original_geom.__geo_interface__)
            
            print(f"\n   📍 {region_name} ({country}):")
            print(f"      🔸 Original dissolved: {original_size:,} bytes, {original_vertices:,} vertices")
            
            # Get stored data from Firestore
            try:
                stored_docs = list(db.collection(f'admin_level_{level}')
                                  .where('name', '==', region_name)
                                  .limit(1)
                                  .stream())
                
                if stored_docs:
                    stored_data = stored_docs[0].to_dict()
                    stored_size = len(stored_data['geometry'].encode('utf-8'))
                    stored_vertices = count_vertices(json.loads(stored_data['geometry']))
                    
                    size_reduction = (original_size - stored_size) / original_size * 100
                    vertex_reduction = (original_vertices - stored_vertices) / original_vertices * 100
                    
                    print(f"      🔹 Stored simplified: {stored_size:,} bytes, {stored_vertices:,} vertices")
                    print(f"      📊 Reduction: {size_reduction:.1f}% size, {vertex_reduction:.1f}% vertices")
                    
                    # Test what tolerance would achieve this
                    tolerances = [0.001, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
                    closest_tolerance = None
                    closest_diff = float('inf')
                    
                    for tolerance in tolerances:
                        try:
                            simplified = simplify(original_geom, tolerance=tolerance, preserve_topology=True)
                            simplified_size = len(json.dumps(simplified.__geo_interface__).encode('utf-8'))
                            diff = abs(simplified_size - stored_size)
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_tolerance = tolerance
                        except:
                            continue
                    
                    if closest_tolerance:
                        print(f"      🎯 Estimated tolerance used: ~{closest_tolerance}")
                    
                    results.append({
                        'region': region_name,
                        'country': country,
                        'original_size': original_size,
                        'stored_size': stored_size,
                        'size_reduction': size_reduction,
                        'vertex_reduction': vertex_reduction,
                        'tolerance': closest_tolerance
                    })
                    
                else:
                    print(f"      ❌ No stored data found")
                    
            except Exception as e:
                print(f"      ❌ Error getting stored data: {e}")
        
        if results:
            print(f"\n   📊 LEVEL {level} SUMMARY:")
            avg_size_reduction = statistics.mean([r['size_reduction'] for r in results])
            avg_vertex_reduction = statistics.mean([r['vertex_reduction'] for r in results])
            common_tolerance = statistics.mode([r['tolerance'] for r in results if r['tolerance']])
            
            print(f"      Average size reduction: {avg_size_reduction:.1f}%")
            print(f"      Average vertex reduction: {avg_vertex_reduction:.1f}%")
            print(f"      Most common tolerance: {common_tolerance}")
            
            return {
                'level': level,
                'avg_size_reduction': avg_size_reduction,
                'avg_vertex_reduction': avg_vertex_reduction,
                'common_tolerance': common_tolerance,
                'results': results
            }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    print("🎯 GADM GEOMETRY FIDELITY ANALYSIS")
    print("=" * 50)
    
    # Analyze different levels
    level_analyses = []
    
    # Level 1 - States/Provinces
    result1 = analyze_level_fidelity(1, ['Île-de-France', 'Bayern', 'Provence-Alpes-Côte d\'Azur'])
    if result1:
        level_analyses.append(result1)
    
    # Level 2 - Counties/Departments  
    result2 = analyze_level_fidelity(2, ['Paris', 'München (Kreisfreie Stadt)', 'Bouches-du-Rhône'])
    if result2:
        level_analyses.append(result2)
        
    # Overall summary
    if level_analyses:
        print(f"\n🎯 OVERALL FIDELITY SUMMARY")
        print("=" * 50)
        
        for analysis in level_analyses:
            print(f"   Level {analysis['level']}: {analysis['avg_size_reduction']:.1f}% size reduction, {analysis['avg_vertex_reduction']:.1f}% vertex reduction")
        
        overall_size_reduction = statistics.mean([a['avg_size_reduction'] for a in level_analyses])
        overall_vertex_reduction = statistics.mean([a['avg_vertex_reduction'] for a in level_analyses])
        
        print(f"\n   🎯 Overall Average:")
        print(f"      Size reduction: {overall_size_reduction:.1f}%")
        print(f"      Vertex reduction: {overall_vertex_reduction:.1f}%")
        
        # Interpret results
        if overall_size_reduction < 50:
            print(f"      ✅ Low fidelity loss - geometries retain most detail")
        elif overall_size_reduction < 80:
            print(f"      ⚠️  Moderate fidelity loss - noticeable simplification")
        else:
            print(f"      🚨 High fidelity loss - significant simplification")

if __name__ == "__main__":
    main()
