#!/usr/bin/env python3
"""
Quick script to update specific countries with continent data as requested.
"""

import logging
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_specific_continents(project_id: str, dry_run: bool = True):
    """Update specific countries with continent mappings."""
    
    # Initialize Firestore client with explicit database name
    db = firestore.Client(project=project_id, database='statlas-content')
    
    # Define the specific mappings
    mappings = {
        # Major countries/territories
        "united_states_of_america": "North America",
        "macao": "Asia", 
        "w_sahara": "Africa",
        
        # European territories
        "åland": "Europe",  # Will also rename to start with 'A'
        "faeroe_is": "Europe",
        "gibraltar": "Europe", 
        "guernsey": "Europe",
        "isle_of_man": "Europe",
        "jersey": "Europe",
        
        # Everything else gets 'Other' for now
        "fr_s_antarctic_lands": "Other",
        "heard_i_and_mcdonald_is": "Other",
        "s_geo_and_the_is": "Other",
        "ashmore_and_cartier_is": "Other",
        "coral_sea_is": "Other",
        "u_s_minor_outlying_is": "Other",
        "br_indian_ocean_ter": "Other",
        "indian_ocean_ter": "Other",
        "saint_helena": "Other",
        "brazilian_i": "Other",
        "clipperton_i": "Other",
        "n_cyprus": "Other",
        "cyprus_u_n_buffer_zone": "Other",
        "baikonur": "Other",
        "siachen_glacier": "Other",
        "usnb_guantanamo_bay": "Other",
        "bir_tawil": "Other",
        "southern_patagonian_ice_field": "Other",
        "scarborough_reef": "Other",
        "spratly_is": "Other",
        "bajo_nuevo_bank": "Other",
        "serranilla_bank": "Other",
    }
    
    collections = ["sovereign_states", "countries", "map_units"]
    total_updated = 0
    
    for collection_name in collections:
        logger.info(f"Processing {collection_name} collection...")
        collection_ref = db.collection(collection_name)
        
        # Get all active documents
        docs = collection_ref.where(filter=FieldFilter("is_active", "==", True)).get()
        updated_in_collection = 0
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_id = doc_data.get("id", doc.id)
            
            if doc_id in mappings:
                continent = mappings[doc_id]
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would update {collection_name}/{doc.id}: {doc_data.get('name')} -> continent: {continent}")
                    
                    # Special case for Åland rename
                    if doc_id == "åland":
                        logger.info(f"[DRY RUN] Would also rename 'Åland' to 'Aland' (starting with 'A')")
                else:
                    # Prepare update data
                    update_data = {"continent": continent}
                    
                    # Special case for Åland - change name to start with 'A'
                    if doc_id == "åland":
                        update_data["name"] = "Aland"
                        logger.info(f"Updating {collection_name}/{doc.id}: continent -> {continent}, name -> Aland")
                    else:
                        logger.info(f"Updating {collection_name}/{doc.id}: {doc_data.get('name')} -> continent: {continent}")
                    
                    # Update the document
                    doc.reference.update(update_data)
                
                updated_in_collection += 1
        
        logger.info(f"{'[DRY RUN] Would update' if dry_run else 'Updated'} {updated_in_collection} documents in {collection_name}")
        total_updated += updated_in_collection
    
    logger.info(f"{'[DRY RUN] Would update' if dry_run else 'Updated'} {total_updated} total documents")
    return total_updated

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Update specific countries with continent data')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    logger.info(f"Starting continent updates for project: {args.project_id}")
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    try:
        total_updated = update_specific_continents(args.project_id, args.dry_run)
        logger.info("Script completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during update: {e}")
        raise

if __name__ == "__main__":
    main()
