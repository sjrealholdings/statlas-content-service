#!/usr/bin/env python3
"""
Analyze geometry fidelity loss from GADM import simplification
"""

import logging
import time
from google.cloud import firestore
import geopandas as gpd
from shapely.geometry import mapping
from shapely import simplify
import json
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeometryFidelityAnalyzer:
    def __init__(self):
        self.db = firestore.Client(database='statlas-content')
        self.gadm_collections = ['admin_level_1', 'admin_level_2', 'admin_level_3', 'admin_level_4', 'admin_level_5']
        
    def analyze_collection_fidelity(self, collection_name, sample_size=50):
        """Analyze geometry fidelity for a specific collection"""
        logging.info(f"\n📊 ANALYZING {collection_name.upper()}")
        logging.info("=" * 50)
        
        # Get sample documents
        docs = list(self.db.collection(collection_name).limit(sample_size).stream())
        if not docs:
            logging.warning(f"   ⚠️  No documents found in {collection_name}")
            return None
            
        logging.info(f"   📋 Analyzing {len(docs)} sample documents")
        
        size_stats = []
        complexity_stats = []
        
        for doc in docs:
            data = doc.to_dict()
            if 'geometry' not in data:
                continue
                
            try:
                # Parse the stored geometry
                geometry_json = json.loads(data['geometry'])
                size = len(data['geometry'].encode('utf-8'))
                
                # Count vertices (complexity measure)
                vertices = self._count_vertices(geometry_json)
                
                size_stats.append(size)
                complexity_stats.append(vertices)
                
            except Exception as e:
                logging.warning(f"   ⚠️  Error processing document {doc.id}: {e}")
                continue
        
        if not size_stats:
            logging.warning(f"   ⚠️  No valid geometries found in {collection_name}")
            return None
            
        # Calculate statistics
        stats = {
            'collection': collection_name,
            'sample_size': len(size_stats),
            'size_bytes': {
                'min': min(size_stats),
                'max': max(size_stats),
                'mean': statistics.mean(size_stats),
                'median': statistics.median(size_stats)
            },
            'vertices': {
                'min': min(complexity_stats),
                'max': max(complexity_stats),
                'mean': statistics.mean(complexity_stats),
                'median': statistics.median(complexity_stats)
            }
        }
        
        # Log results
        logging.info(f"   📏 Size: {stats['size_bytes']['min']:,} - {stats['size_bytes']['max']:,} bytes (avg: {stats['size_bytes']['mean']:,.0f})")
        logging.info(f"   🔺 Vertices: {stats['vertices']['min']:,} - {stats['vertices']['max']:,} (avg: {stats['vertices']['mean']:,.0f})")
        
        # Check for potential over-simplification
        large_geometries = sum(1 for s in size_stats if s > 500000)  # > 500KB
        small_geometries = sum(1 for s in size_stats if s < 10000)   # < 10KB
        
        logging.info(f"   📊 Large (>500KB): {large_geometries}/{len(size_stats)} ({large_geometries/len(size_stats)*100:.1f}%)")
        logging.info(f"   📊 Small (<10KB): {small_geometries}/{len(size_stats)} ({small_geometries/len(size_stats)*100:.1f}%)")
        
        return stats
    
    def _count_vertices(self, geometry_json):
        """Count vertices in a GeoJSON geometry"""
        if geometry_json['type'] == 'Polygon':
            return sum(len(ring) for ring in geometry_json['coordinates'])
        elif geometry_json['type'] == 'MultiPolygon':
            return sum(sum(len(ring) for ring in polygon) for polygon in geometry_json['coordinates'])
        else:
            return 0
    
    def compare_with_original(self, gpkg_path="city data/gadm_410.gpkg", sample_countries=['France', 'Germany', 'Rwanda']):
        """Compare stored geometries with original GADM data"""
        logging.info(f"\n🔍 COMPARING WITH ORIGINAL GADM DATA")
        logging.info("=" * 50)
        
        try:
            # Load original data for comparison
            gdf = gpd.read_file(gpkg_path, layer='gadm_410')  # GADM layer
            gdf = gdf[gdf['LEVEL'] == 1]  # Filter for Level 1
            gdf = gdf[gdf['COUNTRY'].isin(sample_countries)]
            
            logging.info(f"   📂 Loaded {len(gdf)} original Level 1 areas from {sample_countries}")
            
            # Get corresponding stored data
            stored_docs = list(self.db.collection('admin_level_1')
                             .where('country_name', 'in', sample_countries)
                             .stream())
            
            logging.info(f"   🗃️  Found {len(stored_docs)} stored Level 1 areas")
            
            # Compare a few examples
            comparisons = []
            for doc in stored_docs[:5]:  # Compare first 5
                data = doc.to_dict()
                name = data.get('name', 'Unknown')
                
                try:
                    # Find matching original
                    original = gdf[gdf['NAME_1'] == name]
                    if len(original) == 0:
                        continue
                    
                    original_geom = original.iloc[0].geometry
                    stored_geom_json = json.loads(data['geometry'])
                    
                    # Calculate sizes
                    original_size = len(json.dumps(original_geom.__geo_interface__).encode('utf-8'))
                    stored_size = len(data['geometry'].encode('utf-8'))
                    
                    # Calculate vertex counts
                    original_vertices = self._count_vertices(original_geom.__geo_interface__)
                    stored_vertices = self._count_vertices(stored_geom_json)
                    
                    comparison = {
                        'name': name,
                        'original_size': original_size,
                        'stored_size': stored_size,
                        'size_reduction': (original_size - stored_size) / original_size * 100,
                        'original_vertices': original_vertices,
                        'stored_vertices': stored_vertices,
                        'vertex_reduction': (original_vertices - stored_vertices) / original_vertices * 100 if original_vertices > 0 else 0
                    }
                    
                    comparisons.append(comparison)
                    
                    logging.info(f"   📍 {name}:")
                    logging.info(f"      Size: {original_size:,} → {stored_size:,} bytes ({comparison['size_reduction']:.1f}% reduction)")
                    logging.info(f"      Vertices: {original_vertices:,} → {stored_vertices:,} ({comparison['vertex_reduction']:.1f}% reduction)")
                    
                except Exception as e:
                    logging.warning(f"   ⚠️  Error comparing {name}: {e}")
                    continue
            
            if comparisons:
                avg_size_reduction = statistics.mean([c['size_reduction'] for c in comparisons])
                avg_vertex_reduction = statistics.mean([c['vertex_reduction'] for c in comparisons])
                
                logging.info(f"\n   📊 AVERAGE REDUCTIONS:")
                logging.info(f"      Size: {avg_size_reduction:.1f}%")
                logging.info(f"      Vertices: {avg_vertex_reduction:.1f}%")
                
                return {
                    'comparisons': comparisons,
                    'avg_size_reduction': avg_size_reduction,
                    'avg_vertex_reduction': avg_vertex_reduction
                }
            
        except Exception as e:
            logging.error(f"   ❌ Error comparing with original: {e}")
            return None
    
    def test_simplification_tolerances(self, sample_geometry_size='medium'):
        """Test different simplification tolerances on sample geometry"""
        logging.info(f"\n🧪 TESTING SIMPLIFICATION TOLERANCES")
        logging.info("=" * 50)
        
        # Get a sample geometry from the database
        docs = list(self.db.collection('admin_level_2').limit(10).stream())
        if not docs:
            logging.warning("   ⚠️  No sample geometries found")
            return
        
        sample_doc = None
        for doc in docs:
            data = doc.to_dict()
            if 'geometry' in data:
                size = len(data['geometry'].encode('utf-8'))
                if ((sample_geometry_size == 'small' and size < 50000) or
                    (sample_geometry_size == 'medium' and 50000 <= size <= 200000) or
                    (sample_geometry_size == 'large' and size > 200000)):
                    sample_doc = data
                    break
        
        if not sample_doc:
            logging.warning(f"   ⚠️  No {sample_geometry_size} geometry found")
            return
        
        try:
            from shapely.geometry import shape
            original_geom = shape(json.loads(sample_doc['geometry']))
            original_size = len(sample_doc['geometry'].encode('utf-8'))
            original_vertices = self._count_vertices(json.loads(sample_doc['geometry']))
            
            logging.info(f"   📍 Testing with {sample_doc.get('name', 'Unknown')} ({original_size:,} bytes, {original_vertices:,} vertices)")
            
            tolerances = [0.001, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
            
            for tolerance in tolerances:
                try:
                    simplified = simplify(original_geom, tolerance=tolerance, preserve_topology=True)
                    simplified_json = json.dumps(simplified.__geo_interface__)
                    simplified_size = len(simplified_json.encode('utf-8'))
                    simplified_vertices = self._count_vertices(simplified.__geo_interface__)
                    
                    size_reduction = (original_size - simplified_size) / original_size * 100
                    vertex_reduction = (original_vertices - simplified_vertices) / original_vertices * 100 if original_vertices > 0 else 0
                    
                    logging.info(f"   🔧 Tolerance {tolerance:>5}: {simplified_size:>7,} bytes ({size_reduction:>5.1f}%), {simplified_vertices:>6,} vertices ({vertex_reduction:>5.1f}%)")
                    
                except Exception as e:
                    logging.warning(f"   ⚠️  Tolerance {tolerance} failed: {e}")
                    
        except Exception as e:
            logging.error(f"   ❌ Error testing tolerances: {e}")

def main():
    analyzer = GeometryFidelityAnalyzer()
    
    # Analyze each collection
    all_stats = []
    for collection in analyzer.gadm_collections:
        stats = analyzer.analyze_collection_fidelity(collection)
        if stats:
            all_stats.append(stats)
    
    # Overall summary
    if all_stats:
        logging.info(f"\n📋 OVERALL SUMMARY")
        logging.info("=" * 50)
        
        total_samples = sum(s['sample_size'] for s in all_stats)
        avg_size = statistics.mean([s['size_bytes']['mean'] for s in all_stats])
        avg_vertices = statistics.mean([s['vertices']['mean'] for s in all_stats])
        
        logging.info(f"   📊 Total samples analyzed: {total_samples}")
        logging.info(f"   📏 Average geometry size: {avg_size:,.0f} bytes")
        logging.info(f"   🔺 Average vertex count: {avg_vertices:,.0f}")
        
        # Check for Firestore limit compliance
        max_sizes = [s['size_bytes']['max'] for s in all_stats]
        largest_geometry = max(max_sizes)
        logging.info(f"   📐 Largest geometry: {largest_geometry:,} bytes ({largest_geometry/1048576:.2f} MB)")
        
        if largest_geometry > 900000:
            logging.warning(f"   ⚠️  Some geometries exceed 900KB safety limit!")
        else:
            logging.info(f"   ✅ All geometries within Firestore limits")
    
    # Compare with original data if available
    analyzer.compare_with_original()
    
    # Test different simplification levels
    analyzer.test_simplification_tolerances('medium')

if __name__ == "__main__":
    main()
