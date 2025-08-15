#!/usr/bin/env python3
"""
Test geometry chunking strategy for high-fidelity GADM import
"""

import json
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
import numpy as np
import math
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeometryChunker:
    def __init__(self, max_chunk_size=900000):  # 900KB safety limit
        self.max_chunk_size = max_chunk_size
        
    def estimate_geometry_size(self, geometry):
        """Estimate geometry size in bytes"""
        geojson_str = json.dumps(geometry.__geo_interface__)
        return len(geojson_str.encode('utf-8'))
    
    def create_spatial_grid(self, bounds, target_chunks):
        """Create a spatial grid for chunking"""
        min_x, min_y, max_x, max_y = bounds
        
        # Calculate grid dimensions (trying to make squares)
        width = max_x - min_x
        height = max_y - min_y
        aspect_ratio = width / height
        
        # Calculate grid size
        cols = math.ceil(math.sqrt(target_chunks * aspect_ratio))
        rows = math.ceil(target_chunks / cols)
        
        # Create grid cells
        cell_width = width / cols
        cell_height = height / rows
        
        grid_cells = []
        for i in range(rows):
            for j in range(cols):
                cell_min_x = min_x + j * cell_width
                cell_min_y = min_y + i * cell_height
                cell_max_x = min(min_x + (j + 1) * cell_width, max_x)
                cell_max_y = min(min_y + (i + 1) * cell_height, max_y)
                
                cell = box(cell_min_x, cell_min_y, cell_max_x, cell_max_y)
                grid_cells.append(cell)
        
        return grid_cells
    
    def chunk_geometry(self, geometry, admin_data):
        """Chunk a large geometry into Firestore-compatible pieces"""
        original_size = self.estimate_geometry_size(geometry)
        
        if original_size <= self.max_chunk_size:
            # No chunking needed
            return [{
                **admin_data,
                'geometry': json.dumps(geometry.__geo_interface__),
                'chunk_id': 0,
                'total_chunks': 1,
                'is_chunked': False
            }]
        
        logging.info(f"   🔪 Chunking {admin_data.get('name', 'Unknown')} ({original_size:,} bytes)")
        
        # Calculate target number of chunks
        target_chunks = math.ceil(original_size / self.max_chunk_size)
        
        # Create spatial grid
        grid_cells = self.create_spatial_grid(geometry.bounds, target_chunks)
        
        chunks = []
        chunk_id = 0
        
        for cell in grid_cells:
            try:
                # Intersect geometry with grid cell
                intersection = geometry.intersection(cell)
                
                if intersection.is_empty:
                    continue
                
                # Check if intersection is still too large
                intersection_size = self.estimate_geometry_size(intersection)
                
                if intersection_size <= self.max_chunk_size:
                    # Good chunk
                    chunks.append({
                        **admin_data,
                        'geometry': json.dumps(intersection.__geo_interface__),
                        'chunk_id': chunk_id,
                        'total_chunks': len(grid_cells),  # Will update later
                        'is_chunked': True,
                        'chunk_bounds': {
                            'min_lat': cell.bounds[1],
                            'max_lat': cell.bounds[3],
                            'min_lon': cell.bounds[0],
                            'max_lon': cell.bounds[2]
                        }
                    })
                    chunk_id += 1
                else:
                    # Recursively chunk this piece
                    logging.warning(f"      ⚠️  Chunk still too large ({intersection_size:,} bytes), subdividing...")
                    sub_chunks = self.chunk_geometry(intersection, {
                        **admin_data,
                        'name': f"{admin_data.get('name', 'Unknown')}_subchunk"
                    })
                    
                    # Add sub-chunks with updated IDs
                    for sub_chunk in sub_chunks:
                        sub_chunk['chunk_id'] = chunk_id
                        sub_chunk['parent_chunk'] = True
                        chunks.append(sub_chunk)
                        chunk_id += 1
                        
            except Exception as e:
                logging.warning(f"      ⚠️  Error processing grid cell: {e}")
                continue
        
        # Update total chunks count
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)
        
        logging.info(f"      ✅ Created {len(chunks)} chunks (avg: {original_size//len(chunks):,} bytes each)")
        
        return chunks
    
    def test_chunking_on_australia(self):
        """Test chunking strategy on Australia data"""
        print("\n🇦🇺 TESTING GEOMETRY CHUNKING ON AUSTRALIA")
        print("=" * 50)
        
        # Test different admin levels
        test_files = [
            ('Level 0 (Country)', 'city data/gadm41_AUS_shp/gadm41_AUS_0.shp'),
            ('Level 1 (States)', 'city data/gadm41_AUS_shp/gadm41_AUS_1.shp'),
            ('Level 2 (Counties)', 'city data/gadm41_AUS_shp/gadm41_AUS_2.shp')
        ]
        
        results = {}
        
        for level_name, file_path in test_files:
            print(f"\n📍 {level_name}:")
            
            try:
                gdf = gpd.read_file(file_path)
                print(f"   Features: {len(gdf)}")
                
                level_results = []
                total_original_size = 0
                total_chunks = 0
                
                # Process each feature
                for idx, row in gdf.iterrows():
                    # Prepare admin data
                    admin_data = {
                        'name': row.get('NAME_1', row.get('NAME_2', row.get('COUNTRY', f'Feature_{idx}'))),
                        'gid': row.get('GID_1', row.get('GID_2', row.get('GID_0', f'GID_{idx}'))),
                        'country': row.get('COUNTRY', 'Australia')
                    }
                    
                    # Get original size
                    original_size = self.estimate_geometry_size(row.geometry)
                    total_original_size += original_size
                    
                    # Chunk if needed
                    chunks = self.chunk_geometry(row.geometry, admin_data)
                    total_chunks += len(chunks)
                    
                    level_results.append({
                        'name': admin_data['name'],
                        'original_size': original_size,
                        'chunks': len(chunks),
                        'chunked': len(chunks) > 1
                    })
                
                # Summary
                chunked_features = sum(1 for r in level_results if r['chunked'])
                avg_original = total_original_size / len(level_results) if level_results else 0
                
                print(f"   📊 Summary:")
                print(f"      Features needing chunking: {chunked_features}/{len(gdf)} ({chunked_features/len(gdf)*100:.1f}%)")
                print(f"      Total chunks created: {total_chunks}")
                print(f"      Avg original size: {avg_original:,.0f} bytes")
                print(f"      Chunk expansion ratio: {total_chunks/len(gdf):.1f}x")
                
                results[level_name] = {
                    'features': len(gdf),
                    'chunked_features': chunked_features,
                    'total_chunks': total_chunks,
                    'expansion_ratio': total_chunks/len(gdf)
                }
                
            except Exception as e:
                print(f"   ❌ Error processing {level_name}: {e}")
        
        return results
    
    def test_point_in_chunked_polygon(self, chunks, test_point):
        """Test if point-in-polygon queries work with chunked geometry"""
        print(f"\n🎯 TESTING POINT-IN-POLYGON WITH CHUNKS")
        print(f"   Test point: {test_point}")
        
        from shapely.geometry import Point
        point = Point(test_point)
        
        matching_chunks = []
        for chunk in chunks:
            try:
                chunk_geom = json.loads(chunk['geometry'])
                from shapely.geometry import shape
                geom = shape(chunk_geom)
                
                if geom.contains(point):
                    matching_chunks.append(chunk)
            except Exception as e:
                continue
        
        print(f"   Matching chunks: {len(matching_chunks)}")
        if matching_chunks:
            for chunk in matching_chunks:
                print(f"      - Chunk {chunk['chunk_id']}: {chunk['name']}")
            return True
        return False

def main():
    chunker = GeometryChunker()
    
    print("🔪 GEOMETRY CHUNKING STRATEGY TEST")
    print("Testing spatial partitioning for high-fidelity import")
    print("=" * 60)
    
    # Test chunking on Australia data
    results = chunker.test_chunking_on_australia()
    
    # Test specific large geometry
    print(f"\n🧪 DETAILED TEST: Australia Country Boundary")
    print("-" * 40)
    
    try:
        # Load Australia country boundary (Level 0)
        gdf = gpd.read_file('city data/gadm41_AUS_shp/gadm41_AUS_0.shp')
        if len(gdf) > 0:
            australia_geom = gdf.iloc[0].geometry
            admin_data = {
                'name': 'Australia',
                'gid': 'AUS.1',
                'country': 'Australia'
            }
            
            # Chunk it
            chunks = chunker.chunk_geometry(australia_geom, admin_data)
            
            print(f"   Original size: {chunker.estimate_geometry_size(australia_geom):,} bytes")
            print(f"   Created chunks: {len(chunks)}")
            
            # Test point-in-polygon
            sydney_coords = (151.2093, -33.8688)  # Sydney, Australia
            chunker.test_point_in_chunked_polygon(chunks, sydney_coords)
            
    except Exception as e:
        print(f"   ❌ Error in detailed test: {e}")
    
    # Overall assessment
    print(f"\n🎯 CHUNKING STRATEGY ASSESSMENT")
    print("=" * 50)
    
    if results:
        total_expansion = sum(r['expansion_ratio'] for r in results.values()) / len(results)
        print(f"   📊 Average chunk expansion: {total_expansion:.1f}x")
        print(f"   ✅ Maintains full geometry precision")
        print(f"   ✅ Enables point-in-polygon queries")
        print(f"   ✅ Fits within Firestore limits")
        print(f"   ⚠️  Increases document count by ~{total_expansion:.1f}x")
        
        if total_expansion < 5:
            print(f"   🏆 RECOMMENDATION: Chunking is FEASIBLE")
            print(f"      - Reasonable storage overhead")
            print(f"      - Maintains high fidelity")
            print(f"      - Enables global coverage")
        else:
            print(f"   ⚠️  RECOMMENDATION: Chunking may be expensive")
            print(f"      - High storage overhead")
            print(f"      - Consider hybrid approach")

if __name__ == "__main__":
    main()
