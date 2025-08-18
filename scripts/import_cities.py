#!/usr/bin/env python3
"""
Script to import city objects from stanford shapefile into Firestore database
Extracts: name, population, sq_km, and boundary polygon
"""

import shapefile
import json
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
import sys
import logging
from typing import Dict, List, Any, Optional
import uuid
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FirestoreCityImporter:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Firestore city importer"""
        self.config = config
        self.db = None
        self.app = None
        self.id_strategy = config.get('id_strategy', 'name')
        self.custom_prefix = config.get('custom_prefix', 'city_')
        
    def connect_firestore(self) -> bool:
        """Establish Firestore connection"""
        try:
            # Initialize Firebase Admin SDK
            if self.config.get('service_account_json'):
                # Use service account JSON from environment variable
                cred = credentials.Certificate(json.loads(self.config['service_account_json']))
                self.app = firebase_admin.initialize_app(cred)
            elif self.config.get('service_account_key_path'):
                # Use service account key file
                cred = credentials.Certificate(self.config['service_account_key_path'])
                self.app = firebase_admin.initialize_app(cred)
            else:
                # Use default credentials (requires gcloud auth)
                self.app = firebase_admin.initialize_app()
            
            # Get Firestore client with timeout settings
            if self.config.get('database_name'):
                # Use specific database
                self.db = firestore.Client(database=self.config['database_name'])
            else:
                # Use default database
                self.db = firestore.client()
            
            # Test the connection with a simple operation
            test_collection = self.db.collection('_test_connection')
            test_doc = test_collection.document('test')
            test_doc.get(timeout=10)  # 10 second timeout
            
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
    
    def extract_city_data(self, shapefile_path: Path) -> List[Dict[str, Any]]:
        """Extract city data from shapefile"""
        cities = []
        
        try:
            # Read the shapefile with encoding handling
            try:
                sf = shapefile.Reader(shapefile_path, encoding='latin-1')
            except:
                sf = shapefile.Reader(shapefile_path)
            logger.info(f"Reading shapefile: {len(sf.shapes())} shapes found")
            
            # Get field indices
            fields = [field[0] for field in sf.fields[1:]]  # Skip deletion flag
            name_idx = fields.index('name_conve')
            pop_idx = fields.index('max_pop_al')
            area_km_idx = fields.index('min_areakm')
            
            # Process each record
            for i, (shape, record) in enumerate(zip(sf.shapes(), sf.records())):
                try:
                    # Extract basic data
                    name = record[name_idx]
                    population = record[pop_idx]
                    sq_km = record[area_km_idx]
                    
                    # Skip records with missing essential data
                    if not name or population is None or sq_km is None:
                        logger.warning(f"Skipping record {i}: missing essential data")
                        continue
                    
                    # Handle encoding issues
                    if isinstance(name, bytes):
                        try:
                            name = name.decode('latin-1')
                        except:
                            name = str(name)
                    
                    # Convert population to integer if it's a float
                    if isinstance(population, float):
                        population = int(population) if population > 0 else None
                    
                    # Convert area to float
                    if isinstance(sq_km, (int, float)):
                        sq_km = float(sq_km)
                    else:
                        sq_km = None
                    
                    # Extract boundary polygon (optional)
                    boundary = None
                    if self.config.get('import_boundaries', True):
                        boundary = self.extract_boundary_polygon(shape)
                        if not boundary and self.config.get('skip_invalid_boundaries', True):
                            logger.warning(f"Skipping city '{name}' due to invalid boundary")
                            continue
                    
                    # Create city data
                    city_data = {
                        'name': str(name),
                        'population': population,
                        'sq_km': sq_km,
                        'imported_at': firestore.SERVER_TIMESTAMP
                    }
                    
                    # Add boundary if available
                    if boundary:
                        city_data['boundary'] = boundary
                    
                    cities.append(city_data)
                    
                    if (i + 1) % 1000 == 0:
                        logger.info(f"Processed {i + 1} cities...")
                    
                except Exception as e:
                    logger.error(f"Error processing record {i}: {e}")
                    continue
            
            logger.info(f"Successfully extracted data for {len(cities)} cities")
            return cities
            
        except Exception as e:
            logger.error(f"Failed to read shapefile: {e}")
            return []
    
    def generate_city_id(self, city_data: Dict[str, Any]) -> str:
        """Generate a unique ID for a city based on the configured strategy"""
        try:
            if self.id_strategy == 'name':
                # Use sanitized city name as ID
                city_name = city_data['name']
                sanitized = city_name.replace(' ', '_').replace('-', '_').replace(',', '').replace('.', '').replace("'", '').replace('"', '').replace('(', '').replace(')', '').replace('&', 'and')
                return sanitized[:50]  # Limit length for Firestore
                
            elif self.id_strategy == 'uuid':
                # Use UUID for random IDs
                return str(uuid.uuid4())
                
            elif self.id_strategy == 'name_population':
                # Use combination of name and population
                city_name = city_data['name'].replace(' ', '_').replace('-', '_').replace(',', '').replace('.', '').replace("'", '').replace('"', '').replace('(', '').replace(')', '')
                population = city_data.get('population', 'unknown')
                return f"{city_name}_{population}"[:50]
                
            elif self.id_strategy == 'custom':
                # Use custom prefix with incremental number
                city_name = city_data['name'].replace(' ', '_').replace('-', '_').replace(',', '').replace('.', '').replace("'", '').replace('"', '').replace('(', '').replace(')', '')
                return f"{self.custom_prefix}{city_name}"[:50]
                
            else:
                # Default to name strategy
                city_name = city_data['name']
                sanitized = city_name.replace(' ', '_').replace('-', '_').replace(',', '').replace('.', '').replace("'", '').replace('"', '').replace('(', '').replace(')', '')
                return sanitized[:50]
                
        except Exception as e:
            logger.error(f"Error generating city ID: {e}")
            # Fallback to UUID
            return str(uuid.uuid4())
    
    def extract_boundary_polygon(self, shape) -> Optional[Dict[str, Any]]:
        """Extract boundary polygon as GeoJSON-compatible format for Firestore"""
        try:
            if shape.shapeType == shapefile.POLYGON:
                # Convert to GeoJSON format
                parts = shape.parts
                points = shape.points
                
                if not parts or not points:
                    return None
                
                # Build GeoJSON polygon with coordinate validation
                coordinates = []
                for i, part_start in enumerate(parts):
                    part_end = parts[i + 1] if i + 1 < len(parts) else len(points)
                    part_points = points[part_start:part_end]
                    
                    # Clean and validate coordinates
                    ring = []
                    for p in part_points:
                        lon, lat = p[0], p[1]
                        
                        # Validate coordinate ranges
                        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                            logger.warning(f"Invalid coordinates: lon={lon}, lat={lat}")
                            continue
                        
                        # Round coordinates to reasonable precision (6 decimal places = ~1 meter)
                        clean_lon = round(float(lon), 6)
                        clean_lat = round(float(lat), 6)
                        
                        # Ensure coordinates are finite numbers
                        if not (isinstance(clean_lon, (int, float)) and isinstance(clean_lat, (int, float))):
                            continue
                        if not (math.isfinite(clean_lon) and math.isfinite(clean_lat)):
                            continue
                        
                        ring.append([clean_lon, clean_lat])
                    
                    # Skip empty rings
                    if len(ring) < 3:
                        logger.warning(f"Ring {i} has insufficient points: {len(ring)}")
                        continue
                    
                    coordinates.append(ring)
                
                # Validate final polygon
                if not coordinates or len(coordinates) == 0:
                    logger.warning("No valid coordinate rings found")
                    return None
                
                # Create GeoJSON polygon as string (Firestore compatible)
                geojson = {
                    'type': 'Polygon',
                    'coordinates': coordinates
                }
                
                # Convert to string for Firestore compatibility
                try:
                    geojson_string = json.dumps(geojson)
                    return geojson_string
                except Exception as e:
                    logger.error(f"Error converting GeoJSON to string: {e}")
                    return None
            else:
                logger.warning(f"Unsupported shape type: {shape.shapeType}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting boundary: {e}")
            return None
    
    def import_cities(self, cities: List[Dict[str, Any]], batch_size: int = 500) -> bool:
        """Import cities into Firestore in batches"""
        if not cities:
            logger.warning("No cities to import")
            return False
        
        try:
            collection_ref = self.db.collection(self.config['cities_collection'])
            total_imported = 0
            
            for i in range(0, len(cities), batch_size):
                batch = cities[i:i + batch_size]
                batch_ref = self.db.batch()
                
                for city in batch:
                    # Generate a unique ID for the city
                    city_id = self.generate_city_id(city)
                    
                    # Check if ID already exists (optional - for name-based IDs)
                    if self.id_strategy == 'name':
                        try:
                            existing_doc = collection_ref.document(city_id).get(timeout=5)
                            if existing_doc.exists:
                                # Add population to make ID unique
                                city_id = f"{city_id}_{city.get('population', 'unknown')}"[:50]
                        except Exception as e:
                            logger.warning(f"Timeout checking existing ID {city_id}: {e}")
                            # Continue with current ID
                    
                    doc_ref = collection_ref.document(city_id)
                    
                    # Add city data to batch with the ID included in the document
                    city_data_with_id = {**city, 'id': city_id}
                    batch_ref.set(doc_ref, city_data_with_id)
                
                # Commit batch with timeout
                try:
                    batch_ref.commit(timeout=30)  # 30 second timeout per batch
                    total_imported += len(batch)
                    logger.info(f"Imported batch: {total_imported}/{len(cities)} cities")
                except Exception as e:
                    logger.error(f"Failed to commit batch {i//batch_size + 1}: {e}")
                    # Try to commit individual documents
                    logger.info("Attempting individual document commits...")
                    for city in batch:
                        try:
                            city_id = self.generate_city_id(city)
                            doc_ref = collection_ref.document(city_id)
                            city_data_with_id = {**city, 'id': city_id}
                            doc_ref.set(city_data_with_id, timeout=10)
                            total_imported += 1
                        except Exception as doc_error:
                            logger.error(f"Failed to import city {city.get('name', 'unknown')}: {doc_error}")
                            continue
            
            logger.info(f"Successfully imported {total_imported} cities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import cities: {e}")
            return False
    
    def validate_import(self) -> Dict[str, Any]:
        """Validate the imported data"""
        try:
            collection_ref = self.db.collection(self.config['cities_collection'])
            
            # Get total count
            total_count = len(list(collection_ref.stream()))
            
            # Get population statistics
            cities_with_pop = []
            cities_with_area = []
            cities_with_boundary = []
            
            for doc in collection_ref.stream():
                data = doc.to_dict()
                
                if data.get('population'):
                    cities_with_pop.append(data['population'])
                
                if data.get('sq_km'):
                    cities_with_area.append(data['sq_km'])
                
                if data.get('boundary'):
                    cities_with_boundary.append(True)
            
            validation = {
                'total_cities': total_count,
                'with_population': len(cities_with_pop),
                'with_area': len(cities_with_area),
                'with_boundary': len(cities_with_boundary),
                'population_stats': {
                    'min': min(cities_with_pop) if cities_with_pop else None,
                    'max': max(cities_with_pop) if cities_with_pop else None,
                    'average': round(sum(cities_with_pop) / len(cities_with_pop), 2) if cities_with_pop else None
                },
                'area_stats': {
                    'min': min(cities_with_area) if cities_with_area else None,
                    'max': max(cities_with_area) if cities_with_area else None,
                    'average': round(sum(cities_with_area) / len(cities_with_area), 2) if cities_with_area else None
                }
            }
            
            return validation
            
        except Exception as e:
            logger.error(f"Failed to validate import: {e}")
            return {}

def main():
    """Main function to run the city import"""
    
    # Import configuration
    try:
                from db_config import (
            SERVICE_ACCOUNT_KEY_PATH, 
            PROJECT_ID, 
            SERVICE_ACCOUNT_JSON,
            CITIES_COLLECTION,
            DATABASE_NAME,
            BATCH_SIZE,
            ID_STRATEGY,
            CUSTOM_ID_PREFIX,
            IMPORT_BOUNDARIES,
            SKIP_INVALID_BOUNDARIES,
            TEST_MODE,
            MAX_CITIES_TEST
        )
        
        # Build config
        config = {
            'cities_collection': CITIES_COLLECTION,
            'database_name': DATABASE_NAME,
            'batch_size': BATCH_SIZE,
            'id_strategy': ID_STRATEGY,
            'custom_prefix': CUSTOM_ID_PREFIX,
            'import_boundaries': IMPORT_BOUNDARIES,
            'skip_invalid_boundaries': SKIP_INVALID_BOUNDARIES,
            'test_mode': TEST_MODE,
            'max_cities_test': MAX_CITIES_TEST
        }
        
        # Set authentication method
        if SERVICE_ACCOUNT_JSON:
            config['service_account_json'] = SERVICE_ACCOUNT_JSON
            logger.info("Using service account JSON from environment")
        elif SERVICE_ACCOUNT_KEY_PATH != 'path/to/serviceAccountKey.json':
            config['service_account_key_path'] = SERVICE_ACCOUNT_KEY_PATH
            logger.info("Using service account key file")
        elif PROJECT_ID != 'your-project-id':
            config['project_id'] = PROJECT_ID
            logger.info("Using project ID with default credentials")
        else:
            logger.error("No valid Firestore configuration found!")
            logger.error("Please update db_config.py or set environment variables")
            sys.exit(1)
            
    except ImportError as e:
        logger.error(f"Failed to import configuration: {e}")
        sys.exit(1)
    
    # Shapefile path
    shapefile_path = Path("../city data/stanford-yk247bg4748-shapefile/yk247bg4748.shp")
    
    if not shapefile_path.exists():
        logger.error(f"Shapefile not found at: {shapefile_path}")
        sys.exit(1)
    
    # Initialize importer
    importer = FirestoreCityImporter(config)
    
    try:
        # Connect to Firestore
        if not importer.connect_firestore():
            sys.exit(1)
        
        # Extract city data
        logger.info("Extracting city data from shapefile...")
        cities = importer.extract_city_data(shapefile_path)
        
        if not cities:
            logger.error("No cities extracted from shapefile")
            sys.exit(1)
        
        # Apply test mode if enabled
        if config.get('test_mode', False):
            max_cities = config.get('max_cities_test', 10)
            cities = cities[:max_cities]
            logger.info(f"TEST MODE: Importing only first {len(cities)} cities")
        
        # Import cities
        logger.info(f"Importing {len(cities)} cities into Firestore...")
        logger.info(f"Using batch size: {config['batch_size']} cities per batch")
        logger.info("Starting import (this may take several minutes)...")
        
        if not importer.import_cities(cities, config['batch_size']):
            logger.error("Import failed! Check the logs above for details.")
            sys.exit(1)
        
        # Validate import
        logger.info("Validating import...")
        validation = importer.validate_import()
        
        if validation:
            logger.info("Import validation results:")
            logger.info(f"  Total cities: {validation['total_cities']}")
            logger.info(f"  With population: {validation['with_population']}")
            logger.info(f"  With area: {validation['with_area']}")
            logger.info(f"  With boundary: {validation['with_boundary']}")
            logger.info(f"  Population range: {validation['population_stats']['min']} - {validation['population_stats']['max']}")
            logger.info(f"  Area range: {validation['area_stats']['min']} - {validation['area_stats']['max']} km²")
        
        logger.info("City import completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Import interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        importer.disconnect_firestore()

if __name__ == "__main__":
    main()
