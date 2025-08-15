#!/usr/bin/env python3
"""
Standalone Coastline Classification Script

This script replicates the functionality of the statlas-content-service 
/coastline/* endpoints for local use by core-service engineers.

Endpoints replicated:
- /coastline/classify - Point classification + distance + grid resolution
- /coastline/distance - Distance to nearest coastline + coordinates  
- /coastline/batch-classify - Batch processing of multiple points

Requirements:
- Python 3.7+
- google-cloud-firestore
- geopy (for distance calculations)

Usage:
    python coastline_classifier_standalone.py classify 40.7128 -74.0060
    python coastline_classifier_standalone.py distance 40.7128 -74.0060  
    python coastline_classifier_standalone.py batch-classify points.json

Author: AI Assistant for Statlas Content Service
Date: 2025-08-15
"""

import argparse
import json
import math
import sys
from typing import Dict, List, Tuple, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from google.cloud import firestore
    from geopy.distance import geodesic
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    logger.error("Install with: pip install google-cloud-firestore geopy")
    DEPENDENCIES_AVAILABLE = False


class CoastlineClassifier:
    """Standalone coastline classification system."""
    
    def __init__(self, project_id: str = "statlas-467715", database: str = "statlas-content"):
        """Initialize the classifier with Firestore connection."""
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Required dependencies not available")
            
        self.project_id = project_id
        self.database = database
        self.db = firestore.Client(project=project_id, database=database)
        logger.info(f"Connected to Firestore: {project_id}/{database}")
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        Returns distance in kilometers.
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
    
    def calculate_distance_to_coast(self, lat: float, lon: float) -> Tuple[float, Dict[str, float]]:
        """
        Calculate distance to nearest coastline.
        Returns (distance_km, nearest_point_coords).
        """
        logger.info(f"Calculating distance to coast for ({lat}, {lon})")
        
        # Query coastlines collection
        coastlines = self.db.collection("coastlines").where("is_active", "==", True).stream()
        
        min_distance = float('inf')
        closest_point = {"lat": 0.0, "lon": 0.0}
        
        coastline_count = 0
        for doc in coastlines:
            coastline_count += 1
            data = doc.to_dict()
            
            # Check if point is within reasonable bounds of this coastline
            bounds = data.get("bounds", {})
            if bounds:
                min_lat = bounds.get("min_lat", -90)
                max_lat = bounds.get("max_lat", 90)
                min_lon = bounds.get("min_lon", -180)
                max_lon = bounds.get("max_lon", 180)
                
                # Expand bounds by ~2 degrees for distance calculations
                if lat < min_lat - 2 or lat > max_lat + 2 or lon < min_lon - 2 or lon > max_lon + 2:
                    continue
            
            # Calculate distance to center of coastline bounds (simplified approach)
            if bounds:
                center_lat = (min_lat + max_lat) / 2
                center_lon = (min_lon + max_lon) / 2
                
                distance = self.haversine_distance(lat, lon, center_lat, center_lon)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_point = {"lat": center_lat, "lon": center_lon}
        
        logger.info(f"Checked {coastline_count} coastline segments")
        
        if min_distance == float('inf'):
            raise ValueError("No coastline data found")
            
        return min_distance, closest_point
    
    def classify_point(self, lat: float, lon: float) -> Tuple[bool, float]:
        """
        Classify a point as land or ocean based on distance to coastline.
        Returns (is_land, distance_to_coast_km).
        """
        distance_to_coast, _ = self.calculate_distance_to_coast(lat, lon)
        
        # Distance-based classification logic (matches production)
        if distance_to_coast > 200.0:
            # Points very far from any coastline (>200km) are definitely deep ocean
            is_land = False
        elif distance_to_coast > 100.0:
            # Points 100-200km from coast are likely ocean, but could be large landmasses
            is_land = False
        else:
            # Points within 100km of coastline are likely land or coastal waters
            # This includes major cities, islands, and coastal areas
            is_land = True
        
        return is_land, distance_to_coast
    
    def determine_grid_resolution(self, is_land: bool, distance_to_coast: float) -> str:
        """
        Determine appropriate grid resolution based on location.
        Matches the production logic.
        """
        if is_land:
            # On land: use urban density when available, default to 1x1km
            # TODO: Integrate with urban density data
            return "1x1km"  # Will be "100x100m" in urban areas
        else:
            # In ocean: use distance from coast
            if distance_to_coast > 1000:
                return "100x100km"
            elif distance_to_coast > 100:
                return "10x10km"
            else:
                return "1x1km"  # Coastal waters
    
    def classify_endpoint(self, lat: float, lon: float) -> Dict[str, Any]:
        """Replicate /coastline/classify endpoint."""
        is_land, distance_to_coast = self.classify_point(lat, lon)
        grid_resolution = self.determine_grid_resolution(is_land, distance_to_coast)
        
        return {
            "lat": lat,
            "lon": lon,
            "result": {
                "type": "land" if is_land else "ocean",
                "distance_to_coast_km": distance_to_coast,
                "grid_resolution": grid_resolution
            }
        }
    
    def distance_endpoint(self, lat: float, lon: float) -> Dict[str, Any]:
        """Replicate /coastline/distance endpoint."""
        distance_to_coast, nearest_point = self.calculate_distance_to_coast(lat, lon)
        
        return {
            "lat": lat,
            "lon": lon,
            "result": {
                "distance_to_coast_km": distance_to_coast,
                "nearest_coast_point": nearest_point
            }
        }
    
    def batch_classify_endpoint(self, points: List[Dict[str, float]]) -> Dict[str, Any]:
        """Replicate /coastline/batch-classify endpoint."""
        results = []
        
        for point in points:
            lat = point["lat"]
            lon = point["lon"]
            
            is_land, distance_to_coast = self.classify_point(lat, lon)
            grid_resolution = self.determine_grid_resolution(is_land, distance_to_coast)
            
            results.append({
                "type": "land" if is_land else "ocean",
                "distance_to_coast_km": distance_to_coast,
                "grid_resolution": grid_resolution
            })
        
        return {
            "count": len(results),
            "results": results
        }


def main():
    """Main CLI interface."""
    if not DEPENDENCIES_AVAILABLE:
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Standalone coastline classification for core-service engineers",
        epilog="""
Examples:
  %(prog)s classify 40.7128 -74.0060                    # Classify NYC
  %(prog)s distance 51.5074 -0.1278                     # Distance to coast for London
  %(prog)s batch-classify points.json                   # Process multiple points
  
  points.json format:
  {
    "points": [
      {"lat": 40.7128, "lon": -74.0060},
      {"lat": 40.0, "lon": -70.0}
    ]
  }
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("command", choices=["classify", "distance", "batch-classify"],
                       help="Command to execute")
    parser.add_argument("lat_or_file", type=str,
                       help="Latitude (for classify/distance) or JSON file path (for batch-classify)")
    parser.add_argument("lon", type=float, nargs="?",
                       help="Longitude (required for classify/distance)")
    parser.add_argument("--project", default="statlas-467715",
                       help="Google Cloud project ID (default: statlas-467715)")
    parser.add_argument("--database", default="statlas-content",
                       help="Firestore database name (default: statlas-content)")
    parser.add_argument("--pretty", action="store_true",
                       help="Pretty-print JSON output")
    
    args = parser.parse_args()
    
    try:
        classifier = CoastlineClassifier(args.project, args.database)
        
        if args.command in ["classify", "distance"]:
            if args.lon is None:
                parser.error(f"{args.command} command requires both latitude and longitude")
            
            lat = float(args.lat_or_file)
            lon = args.lon
            
            if args.command == "classify":
                result = classifier.classify_endpoint(lat, lon)
            else:  # distance
                result = classifier.distance_endpoint(lat, lon)
        
        elif args.command == "batch-classify":
            file_path = args.lat_or_file
            
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                points = data.get("points", [])
                
                if not points:
                    raise ValueError("No points found in JSON file")
                
                result = classifier.batch_classify_endpoint(points)
                
            except FileNotFoundError:
                logger.error(f"File not found: {file_path}")
                sys.exit(1)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in file: {file_path}")
                sys.exit(1)
        
        # Output result
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
