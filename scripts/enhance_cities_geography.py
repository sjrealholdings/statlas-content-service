#!/usr/bin/env python3
"""
Script to enhance existing cities with geographic context
Adds coordinates and country/state information using reverse geocoding
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import logging
import time
import requests
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CityGeographyEnhancer:
    def __init__(self):
        """Initialize the city geography enhancer"""
        self.db = None
        self.app = None
        
    def connect_firestore(self) -> bool:
        """Establish Firestore connection"""
        try:
            # Initialize Firebase Admin SDK
            self.app = firebase_admin.initialize_app()
            
            # Get Firestore client for statlas-content database
            self.db = firestore.Client(database='statlas-content')
            
            logger.info("Firestore connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}")
            return False
    
    def disconnect_firestore(self):
        """Close Firestore connection"""
        if self.app:
            firebase_admin.delete_app(self.app)
            logger.info("Firestore connection closed")
    
    def get_geographic_context(self, lon: float, lat: float) -> Dict[str, Any]:
        """Get geographic context using reverse geocoding"""
        try:
            # Use Nominatim (OpenStreetMap) for reverse geocoding
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
            headers = {'User-Agent': 'StatlasCityImporter/1.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                return {
                    'country': address.get('country'),
                    'state': address.get('state') or address.get('province'),
                    'county': address.get('county'),
                    'city': address.get('city') or address.get('town'),
                    'postcode': address.get('postcode'),
                    'country_code': address.get('country_code', '').upper(),
                    'display_name': data.get('display_name', ''),
                    'osm_id': data.get('osm_id'),
                    'osm_type': data.get('osm_type')
                }
            else:
                logger.warning(f"Reverse geocoding failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in reverse geocoding: {e}")
            return {}
    
    def calculate_centroid(self, boundary_json: str) -> tuple:
        """Calculate centroid from GeoJSON boundary"""
        try:
            boundary_data = json.loads(boundary_json)
            if boundary_data.get('type') == 'Polygon' and boundary_data.get('coordinates'):
                # Calculate centroid from first ring
                coords = boundary_data['coordinates'][0]
                if len(coords) > 0:
                    # Simple centroid calculation
                    lons = [p[0] for p in coords]
                    lats = [p[1] for p in coords]
                    centroid_lon = sum(lons) / len(lons)
                    centroid_lat = sum(lats) / len(lats)
                    return centroid_lon, centroid_lat
        except Exception as e:
            logger.error(f"Error calculating centroid: {e}")
        
        return None, None
    
    def enhance_cities_with_geography(self, batch_size: int = 25) -> bool:
        """Enhance cities with geographic context"""
        try:
            collection_ref = self.db.collection('cities')
            
            # Get all cities that don't have geographic context yet
            cities_to_enhance = []
            for doc in collection_ref.stream():
                data = doc.to_dict()
                if not data.get('country') and data.get('boundary'):
                    cities_to_enhance.append((doc.id, data))
            
            logger.info(f"Found {len(cities_to_enhance)} cities to enhance")
            
            if not cities_to_enhance:
                logger.info("No cities need enhancement")
                return True
            
            # Process in batches
            total_enhanced = 0
            for i in range(0, len(cities_to_enhance), batch_size):
                batch = cities_to_enhance[i:i + batch_size]
                batch_ref = self.db.batch()
                
                for doc_id, city_data in batch:
                    try:
                        # Extract centroid from boundary
                        centroid_lon, centroid_lat = self.calculate_centroid(city_data['boundary'])
                        
                        if centroid_lon is not None and centroid_lat is not None:
                            # Get geographic context
                            geo_context = self.get_geographic_context(centroid_lon, centroid_lat)
                            
                            if geo_context:
                                # Update city document
                                doc_ref = collection_ref.document(doc_id)
                                updates = {
                                    'centroid_lon': centroid_lon,
                                    'centroid_lat': centroid_lat,
                                    'country': geo_context.get('country'),
                                    'state': geo_context.get('state'),
                                    'county': geo_context.get('county'),
                                    'country_code': geo_context.get('country_code'),
                                    'display_name': geo_context.get('display_name'),
                                    'enhanced_at': firestore.SERVER_TIMESTAMP
                                }
                                
                                batch_ref.update(doc_ref, updates)
                                total_enhanced += 1
                                
                                logger.info(f"Enhanced {city_data.get('name', 'Unknown')}: {geo_context.get('country', 'Unknown')}, {geo_context.get('state', 'Unknown')}")
                            
                            # Rate limiting for Nominatim (1 request per second)
                            time.sleep(1)
                        else:
                            logger.warning(f"Could not calculate centroid for {city_data.get('name', 'Unknown')}")
                            
                    except Exception as e:
                        logger.error(f"Error processing city {city_data.get('name', 'Unknown')}: {e}")
                        continue
                
                # Commit batch
                try:
                    batch_ref.commit(timeout=30)
                    logger.info(f"Enhanced batch: {total_enhanced} cities processed")
                except Exception as e:
                    logger.error(f"Failed to commit enhancement batch: {e}")
                    # Try individual updates
                    for doc_id, city_data in batch:
                        try:
                            doc_ref = collection_ref.document(doc_id)
                            centroid_lon, centroid_lat = self.calculate_centroid(city_data['boundary'])
                            
                            if centroid_lon is not None and centroid_lat is not None:
                                geo_context = self.get_geographic_context(centroid_lon, centroid_lat)
                                if geo_context:
                                    updates = {
                                        'centroid_lon': centroid_lon,
                                        'centroid_lat': centroid_lat,
                                        'country': geo_context.get('country'),
                                        'state': geo_context.get('state'),
                                        'county': geo_context.get('county'),
                                        'country_code': geo_context.get('country_code'),
                                        'display_name': geo_context.get('display_name'),
                                        'enhanced_at': firestore.SERVER_TIMESTAMP
                                    }
                                    doc_ref.update(updates)
                                    total_enhanced += 1
                                    logger.info(f"Individual update: {city_data.get('name', 'Unknown')}")
                                time.sleep(1)
                        except Exception as doc_error:
                            logger.error(f"Failed to enhance city {city_data.get('name', 'Unknown')}: {doc_error}")
                            continue
            
            logger.info(f"Successfully enhanced {total_enhanced} cities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enhance cities: {e}")
            return False
    
    def show_enhanced_albany_cities(self):
        """Show detailed information about enhanced Albany cities"""
        try:
            collection_ref = self.db.collection('cities')
            
            # Query for cities with Albany in the name
            albany_cities = []
            for doc in collection_ref.stream():
                data = doc.to_dict()
                if 'Albany' in data.get('name', ''):
                    albany_cities.append((doc.id, data))
            
            print(f"\nFound {len(albany_cities)} Albany cities:")
            print("=" * 80)
            
            for doc_id, data in albany_cities:
                print(f"\nCity: {data.get('name', 'N/A')}")
                print(f"ID: {data.get('id', 'N/A')}")
                print(f"Population: {data.get('population', 'N/A'):,}")
                print(f"Area: {data.get('sq_km', 'N/A')} km²")
                print(f"Country: {data.get('country', 'Unknown')}")
                print(f"State/Province: {data.get('state', 'Unknown')}")
                print(f"County: {data.get('county', 'Unknown')}")
                print(f"Coordinates: {data.get('centroid_lon', 'N/A')}, {data.get('centroid_lat', 'N/A')}")
                print(f"Display Name: {data.get('display_name', 'N/A')}")
                print("-" * 50)
            
        except Exception as e:
            logger.error(f"Error showing Albany cities: {e}")

def main():
    """Main function to enhance cities with geography"""
    
    enhancer = CityGeographyEnhancer()
    
    try:
        # Connect to Firestore
        if not enhancer.connect_firestore():
            print("Failed to connect to Firestore")
            return
        
        # Show current Albany cities
        enhancer.show_enhanced_albany_cities()
        
        # Ask user if they want to enhance
        response = input("\nDo you want to enhance cities with geographic context? (y/n): ")
        if response.lower() == 'y':
            print("Starting city enhancement...")
            if enhancer.enhance_cities_with_geography():
                print("City enhancement completed successfully!")
                print("\nEnhanced Albany cities:")
                enhancer.show_enhanced_albany_cities()
            else:
                print("City enhancement failed!")
        else:
            print("Skipping city enhancement")
        
    except KeyboardInterrupt:
        print("\nEnhancement interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        enhancer.disconnect_firestore()

if __name__ == "__main__":
    main()
