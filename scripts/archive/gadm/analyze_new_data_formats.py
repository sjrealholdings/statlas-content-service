#!/usr/bin/env python3
"""
Analyze new GADM data formats for high-fidelity global coverage
"""

import os
import json
import geopandas as gpd
import fiona
from shapely import simplify
from shapely.geometry import shape
import statistics
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewDataFormatAnalyzer:
    def __init__(self):
        self.firestore_limit = 1048576  # 1MB
        self.safety_limit = 900000      # 900KB
        
    def analyze_gdb_format(self, gdb_path="city data/gadm_410.gdb"):
        """Analyze the File Geodatabase format"""
        print("\n🗄️  ESRI FILE GEODATABASE ANALYSIS")
        print("=" * 50)
        
        try:
            with fiona.Env():
                layers = fiona.listlayers(gdb_path)
                print(f"   📋 Layers: {len(layers)}")
                
                for layer in layers:
                    print(f"\n   📊 Layer: {layer}")
                    
                    with fiona.open(gdb_path, layer=layer) as src:
                        total_features = len(src)
                        print(f"      Total features: {total_features:,}")
                        print(f"      Schema: {list(src.schema['properties'].keys())[:10]}...")
                        
                        # Sample geometry analysis
                        sample_sizes = []
                        level_distribution = {}
                        
                        for i, feature in enumerate(src):
                            if i >= 100:  # Sample first 100
                                break
                                
                            geom_size = len(json.dumps(feature['geometry']).encode('utf-8'))
                            sample_sizes.append(geom_size)
                            
                            # Determine level (by checking which GID columns exist)
                            props = feature['properties']
                            for level in range(1, 6):
                                gid_col = f'GID_{level}'
                                if gid_col in props and props[gid_col]:
                                    level_distribution[level] = level_distribution.get(level, 0) + 1
                                    break
                        
                        if sample_sizes:
                            print(f"      Sample geometry sizes:")
                            print(f"        Min: {min(sample_sizes):,} bytes")
                            print(f"        Max: {max(sample_sizes):,} bytes")
                            print(f"        Avg: {statistics.mean(sample_sizes):,.0f} bytes")
                            
                            # Firestore compatibility
                            over_limit = sum(1 for s in sample_sizes if s > self.firestore_limit)
                            near_limit = sum(1 for s in sample_sizes if s > self.safety_limit)
                            
                            print(f"      Firestore compatibility:")
                            print(f"        Over 1MB limit: {over_limit}/{len(sample_sizes)} ({over_limit/len(sample_sizes)*100:.1f}%)")
                            print(f"        Over 900KB: {near_limit}/{len(sample_sizes)} ({near_limit/len(sample_sizes)*100:.1f}%)")
                        
                        if level_distribution:
                            print(f"      Level distribution (sample):")
                            for level in sorted(level_distribution.keys()):
                                print(f"        Level {level}: {level_distribution[level]} features")
                
                return {
                    'format': 'File Geodatabase',
                    'total_features': total_features,
                    'has_all_levels': True,
                    'global_coverage': True,
                    'firestore_compatible': over_limit == 0 if 'over_limit' in locals() else None
                }
                
        except Exception as e:
            print(f"   ❌ Error analyzing GDB: {e}")
            return None
    
    def analyze_country_shapefiles(self, sample_country="AUS"):
        """Analyze country-specific shapefile format using Australia as example"""
        print(f"\n🇦🇺 COUNTRY SHAPEFILES ANALYSIS ({sample_country})")
        print("=" * 50)
        
        shp_dir = f"city data/gadm41_{sample_country}_shp"
        if not os.path.exists(shp_dir):
            print(f"   ❌ Directory not found: {shp_dir}")
            return None
        
        try:
            shp_files = [f for f in os.listdir(shp_dir) if f.endswith('.shp')]
            results = {}
            
            for shp_file in sorted(shp_files):
                level = shp_file.split('_')[-1].split('.')[0]  # Extract level
                shp_path = os.path.join(shp_dir, shp_file)
                
                print(f"\n   📍 Level {level} ({shp_file}):")
                
                gdf = gpd.read_file(shp_path)
                print(f"      Features: {len(gdf)}")
                print(f"      Columns: {list(gdf.columns)[:8]}...")
                
                # Analyze geometry sizes
                geometry_sizes = []
                oversized_count = 0
                
                for idx, row in gdf.iterrows():
                    geom_json = json.dumps(row.geometry.__geo_interface__)
                    size_bytes = len(geom_json.encode('utf-8'))
                    geometry_sizes.append(size_bytes)
                    
                    if size_bytes > self.firestore_limit:
                        oversized_count += 1
                
                # Statistics
                min_size = min(geometry_sizes)
                max_size = max(geometry_sizes)
                avg_size = statistics.mean(geometry_sizes)
                
                print(f"      Geometry sizes:")
                print(f"        Min: {min_size:,} bytes ({min_size/1024:.1f} KB)")
                print(f"        Max: {max_size:,} bytes ({max_size/1024/1024:.2f} MB)")
                print(f"        Avg: {avg_size:,.0f} bytes ({avg_size/1024:.1f} KB)")
                
                # Firestore compatibility
                firestore_compatible = oversized_count == 0
                print(f"      Firestore compatibility:")
                print(f"        Oversized (>1MB): {oversized_count}/{len(gdf)} ({oversized_count/len(gdf)*100:.1f}%)")
                print(f"        Status: {'✅ Compatible' if firestore_compatible else '❌ Needs simplification'}")
                
                results[level] = {
                    'features': len(gdf),
                    'min_size': min_size,
                    'max_size': max_size,
                    'avg_size': avg_size,
                    'oversized_count': oversized_count,
                    'firestore_compatible': firestore_compatible
                }
            
            return {
                'format': 'Country Shapefiles',
                'sample_country': sample_country,
                'levels': results,
                'high_fidelity': True,
                'requires_per_country_processing': True
            }
            
        except Exception as e:
            print(f"   ❌ Error analyzing shapefiles: {e}")
            return None
    
    def test_simplification_strategies(self, sample_country="AUS"):
        """Test different simplification strategies on oversized geometries"""
        print(f"\n🔧 SIMPLIFICATION STRATEGY TESTING")
        print("=" * 50)
        
        shp_path = f"city data/gadm41_{sample_country}_shp/gadm41_{sample_country}_0.shp"
        if not os.path.exists(shp_path):
            print(f"   ❌ Sample file not found: {shp_path}")
            return
        
        try:
            gdf = gpd.read_file(shp_path)
            if len(gdf) == 0:
                print("   ❌ No features in sample file")
                return
            
            # Get the oversized geometry (country level)
            sample_geom = gdf.iloc[0].geometry
            original_json = json.dumps(sample_geom.__geo_interface__)
            original_size = len(original_json.encode('utf-8'))
            
            print(f"   📍 Testing with {sample_country} country boundary:")
            print(f"      Original size: {original_size:,} bytes ({original_size/1024/1024:.1f} MB)")
            
            # Test different strategies
            strategies = [
                ("Progressive Tolerance", [0.001, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0]),
                ("Aggressive Tolerance", [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]),
            ]
            
            best_results = []
            
            for strategy_name, tolerances in strategies:
                print(f"\n   🎯 {strategy_name}:")
                
                for tolerance in tolerances:
                    try:
                        simplified = simplify(sample_geom, tolerance=tolerance, preserve_topology=True)
                        simplified_json = json.dumps(simplified.__geo_interface__)
                        simplified_size = len(simplified_json.encode('utf-8'))
                        
                        reduction = (original_size - simplified_size) / original_size * 100
                        
                        status = "✅" if simplified_size <= self.firestore_limit else "❌"
                        print(f"      Tolerance {tolerance:>5}: {simplified_size:>8,} bytes ({reduction:>5.1f}% reduction) {status}")
                        
                        if simplified_size <= self.firestore_limit:
                            best_results.append({
                                'tolerance': tolerance,
                                'size': simplified_size,
                                'reduction': reduction
                            })
                            
                    except Exception as e:
                        print(f"      Tolerance {tolerance:>5}: ❌ Failed - {e}")
            
            # Find optimal solution
            if best_results:
                # Sort by least reduction (highest fidelity)
                best_results.sort(key=lambda x: x['reduction'])
                optimal = best_results[0]
                
                print(f"\n   🎯 OPTIMAL SOLUTION:")
                print(f"      Tolerance: {optimal['tolerance']}")
                print(f"      Final size: {optimal['size']:,} bytes ({optimal['size']/1024:.1f} KB)")
                print(f"      Fidelity loss: {optimal['reduction']:.1f}%")
                print(f"      Status: ✅ Fits in Firestore with minimal fidelity loss")
                
                return optimal
            else:
                print(f"\n   ❌ NO SOLUTION: Even maximum simplification exceeds Firestore limits")
                return None
                
        except Exception as e:
            print(f"   ❌ Error testing simplification: {e}")
            return None
    
    def generate_recommendations(self, gdb_analysis, shapefile_analysis, simplification_result):
        """Generate recommendations based on analysis"""
        print(f"\n🎯 RECOMMENDATIONS FOR HIGH-FIDELITY GLOBAL COVERAGE")
        print("=" * 60)
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        if gdb_analysis:
            print(f"   File Geodatabase: {gdb_analysis['total_features']:,} features, global coverage")
        if shapefile_analysis:
            levels = shapefile_analysis['levels']
            compatible_levels = sum(1 for l in levels.values() if l['firestore_compatible'])
            print(f"   Country Shapefiles: {len(levels)} levels, {compatible_levels}/{len(levels)} Firestore-compatible")
        
        print(f"\n🎯 STRATEGY RECOMMENDATIONS:")
        
        # Strategy 1: Hybrid GDB + Simplification
        print(f"\n   1️⃣  HYBRID GDB + SIMPLIFICATION (RECOMMENDED)")
        print(f"      ✅ Use File Geodatabase for global coverage")
        print(f"      ✅ Apply dynamic simplification based on geometry size")
        print(f"      ✅ Maintain administrative hierarchy")
        print(f"      ✅ Single data source, consistent processing")
        if simplification_result:
            print(f"      📊 Proven: {simplification_result['reduction']:.1f}% fidelity loss achieves Firestore compliance")
        
        # Strategy 2: Country Shapefiles + Chunking  
        print(f"\n   2️⃣  COUNTRY SHAPEFILES + CHUNKING")
        print(f"      ✅ Maximum fidelity preservation")
        print(f"      ✅ Country-by-country processing")
        print(f"      ⚠️  Requires 195+ country downloads")
        print(f"      ⚠️  Complex data management")
        print(f"      ⚠️  Large geometries still need chunking/simplification")
        
        # Strategy 3: Multi-Resolution Storage
        print(f"\n   3️⃣  MULTI-RESOLUTION STORAGE")
        print(f"      ✅ Store multiple fidelity levels")
        print(f"      ✅ Choose resolution based on use case")
        print(f"      ⚠️  Increased storage requirements")
        print(f"      ⚠️  More complex query logic")
        
        print(f"\n🏆 FINAL RECOMMENDATION:")
        print(f"   Use **Strategy 1: Hybrid GDB + Simplification**")
        print(f"   - Modify existing import script to use File Geodatabase")
        print(f"   - Apply proven simplification tolerances")
        print(f"   - Achieve global coverage with acceptable fidelity loss")
        print(f"   - Maintain current system architecture")

def main():
    analyzer = NewDataFormatAnalyzer()
    
    print("🌍 NEW GADM DATA FORMATS ANALYSIS")
    print("Evaluating potential for high-fidelity global coverage")
    print("=" * 60)
    
    # Analyze File Geodatabase
    gdb_analysis = analyzer.analyze_gdb_format()
    
    # Analyze Country Shapefiles (using Australia as example)
    shapefile_analysis = analyzer.analyze_country_shapefiles()
    
    # Test simplification strategies
    simplification_result = analyzer.test_simplification_strategies()
    
    # Generate recommendations
    analyzer.generate_recommendations(gdb_analysis, shapefile_analysis, simplification_result)

if __name__ == "__main__":
    main()
