#!/usr/bin/env python3
"""
Update Countries from JSON Data

This script updates all countries in the Firestore database with comprehensive data
from the countries_info.json file. It can update existing documents or create new ones.

Usage:
    python3 update_countries_from_json.py --project-id your-project-id [--dry-run] [--create-missing]
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from google.cloud import firestore
    from google.cloud.firestore_v1 import FieldFilter
except ImportError:
    print("Error: google-cloud-firestore is required. Install with: pip install google-cloud-firestore")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CountriesUpdater:
    """Updates countries in Firestore with comprehensive data from JSON."""
    
    def __init__(self, project_id: str, database_id: str = "statlas-content"):
        """Initialize the countries updater.
        
        Args:
            project_id: Google Cloud project ID
            database_id: Firestore database ID
        """
        self.project_id = project_id
        self.database_id = database_id
        self.db = firestore.Client(project=project_id, database=database_id)
        self.collection = self.db.collection("countries")
        
    def load_countries_data(self, json_file_path: str) -> List[Dict]:
        """Load countries data from JSON file."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                countries_data = json.load(f)
            
            logger.info(f"Loaded {len(countries_data)} countries from {json_file_path}")
            return countries_data
        except Exception as e:
            logger.error(f"Failed to load countries data: {e}")
            raise
    
    def transform_country_data(self, country_data: Dict) -> Dict:
        """Transform country data to match Firestore schema."""
        # Create a standardized country document structure
        transformed = {
            "name": country_data["country"],
            "local_name": country_data.get("local_name", ""),
            "country_code": country_data["country_code"],
            "continent": country_data["continent"],
            "capital": country_data.get("capital", ""),
            "population": country_data.get("population", 0),
            "area_sq_km": country_data.get("area_sq_km", 0),
            "area_sq_mi": country_data.get("area_sq_mi", 0),
            "coastline_km": country_data.get("coastline_km", 0),
            "coastline_mi": country_data.get("coastline_mi", 0),
            "government_form": country_data.get("government_form", ""),
            "currency": country_data.get("currency", ""),
            "currency_code": country_data.get("currency_code", ""),
            "dialing_prefix": country_data.get("dialing_prefix", ""),
            "birthrate": country_data.get("birthrate", 0),
            "deathrate": country_data.get("deathrate", 0),
            "url": country_data.get("url", ""),
            "is_active": True,
            "updated_at": datetime.utcnow()
        }
        
        # Generate a consistent ID from country code
        country_id = country_data["country_code"].lower()
        transformed["id"] = country_id
        
        return transformed
    
    def get_existing_country(self, country_code: str) -> Optional[Dict]:
        """Get existing country document by ISO alpha2 code from both countries and map_units collections."""
        try:
            # First check the countries collection
            docs = self.collection.where("iso_alpha2", "==", country_code).limit(1).get()
            if docs:
                return docs[0].to_dict()
            
            # If not found, check the map_units collection
            map_units_collection = self.db.collection("map_units")
            docs = map_units_collection.where("iso_alpha2", "==", country_code).limit(1).get()
            if docs:
                logger.info(f"   📍 Found in map_units collection: {country_code}")
                return docs[0].to_dict()
            
            return None
        except Exception as e:
            logger.warning(f"Error querying for country {country_code}: {e}")
            return None
    
    def update_country(self, country_data: Dict, dry_run: bool = False) -> tuple[bool, bool]:
        """Update existing country document. Returns (success, was_found)."""
        country_id = country_data["id"]
        country_code = country_data["country_code"]
        
        try:
            # Check if country already exists
            existing_doc = self.get_existing_country(country_code)
            
            if existing_doc:
                logger.info(f"📍 Updating existing country: {country_data['name']} ({country_code})")
                
                # Get the actual document ID from the existing document
                # We need to get the document reference to update it properly
                existing_doc_id = None
                
                # First check the countries collection
                docs = self.collection.where("iso_alpha2", "==", country_code).limit(1).get()
                if docs:
                    existing_doc_id = docs[0].id
                    collection_to_update = self.collection
                else:
                    # Check map_units collection
                    map_units_collection = self.db.collection("map_units")
                    docs = map_units_collection.where("iso_alpha2", "==", country_code).limit(1).get()
                    if docs:
                        existing_doc_id = docs[0].id
                        collection_to_update = map_units_collection
                
                if existing_doc_id:
                    # Preserve existing fields that might not be in our JSON data
                    for key in ["created_at", "flag_url", "flag_emoji", "bounds", "iso_alpha3", "iso_numeric", "languages"]:
                        if key in existing_doc:
                            country_data[key] = existing_doc[key]
                    
                    # Set created_at if not present
                    if "created_at" not in country_data:
                        country_data["created_at"] = existing_doc.get("created_at", datetime.utcnow())
                    
                    if not dry_run:
                        # Update the existing document using its actual ID
                        doc_ref = collection_to_update.document(existing_doc_id)
                        doc_ref.set(country_data, merge=True)
                        logger.info(f"   ✅ Successfully updated {existing_doc_id}")
                    else:
                        logger.info(f"   🔍 Would update {existing_doc_id}")
                    
                    return True, True  # Success, was found
                else:
                    logger.error(f"   ❌ Could not determine document ID for {country_code}")
                    return False, False
            else:
                logger.warning(f"⚠️  Country not found in database: {country_data['name']} ({country_code})")
                return False, False  # Not successful, was not found
            
        except Exception as e:
            logger.error(f"   ❌ Error processing {country_id}: {e}")
            return False, False  # Not successful, was not found
    
    def update_all_countries(self, countries_data: List[Dict], dry_run: bool = False) -> Dict:
        """Update all countries in the database."""
        logger.info("🌍 Starting countries update process...")
        logger.info(f"📋 Project ID: {self.project_id}")
        logger.info(f"🔍 Dry run: {dry_run}")
        logger.info("")
        
        success_count = 0
        error_count = 0
        not_found_count = 0
        not_found_countries = []
        
        for i, country_data in enumerate(countries_data, 1):
            logger.info(f"Processing {i}/{len(countries_data)}: {country_data['country']}")
            
            try:
                transformed_data = self.transform_country_data(country_data)
                success, was_found = self.update_country(transformed_data, dry_run)
                
                if success and was_found:
                    success_count += 1
                elif not was_found:
                    not_found_count += 1
                    not_found_countries.append({
                        "name": country_data["country"],
                        "code": country_data["country_code"]
                    })
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Failed to process {country_data.get('country', 'Unknown')}: {e}")
                error_count += 1
                continue
            
            # Small delay to avoid overwhelming Firestore
            if not dry_run:
                time.sleep(0.1)
        
        return {
            "total": len(countries_data),
            "success": success_count,
            "errors": error_count,
            "not_found": not_found_count,
            "not_found_countries": not_found_countries
        }
    
    def verify_update(self) -> int:
        """Verify the update by counting active countries."""
        try:
            docs = self.collection.where("is_active", "==", True).limit(1000).get()
            count = len(docs)
            logger.info(f"✅ Found {count} active countries in database")
            return count
        except Exception as e:
            logger.warning(f"⚠️  Verification failed: {e}")
            return 0

def main():
    parser = argparse.ArgumentParser(description="Update countries in Firestore from JSON data")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--json-file", default="city data/countries_info.json", 
                       help="Path to countries_info.json file")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be updated without actually updating")
    parser.add_argument("--database-id", default="statlas-content", 
                       help="Firestore database ID")
    
    args = parser.parse_args()
    
    try:
        updater = CountriesUpdater(args.project_id, args.database_id)
        
        # Load countries data
        countries_data = updater.load_countries_data(args.json_file)
        
        # Update all countries
        results = updater.update_all_countries(countries_data, args.dry_run)
        
        # Print summary
        logger.info("=" * 50)
        logger.info("📊 UPDATE SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total countries processed: {results['total']}")
        logger.info(f"Successful updates: {results['success']}")
        logger.info(f"Errors: {results['errors']}")
        logger.info(f"Countries not found: {results['not_found']}")
        
        if results['not_found'] > 0:
            logger.info("")
            logger.info("⚠️  COUNTRIES NOT FOUND IN DATABASE:")
            logger.info("=" * 30)
            for country in results['not_found_countries']:
                logger.info(f"   {country['name']} ({country['code']})")
        
        if not args.dry_run:
            logger.info()
            logger.info("🔍 Verifying update...")
            active_count = updater.verify_update()
            logger.info(f"Active countries in database: {active_count}")
        
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
