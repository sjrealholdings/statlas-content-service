#!/usr/bin/env python3
"""
Check map_units collection in Firestore database.

This script searches for specific countries in the map_units collection
to see if they're stored there instead of the countries collection.
"""

import argparse
import sys
from google.cloud import firestore

def check_map_units_for_countries(project_id: str, database_id: str = "statlas-content"):
    """Check map_units collection for specific countries."""
    print(f"🔍 Checking map_units collection in {database_id} database...")
    print(f"📋 Project ID: {project_id}")
    print()
    
    # Countries that were not found in the countries collection
    missing_countries = [
        "BV", "GF", "GP", "BQ", "CC", "XK", "MQ", "YT", "NO", "RE", "SJ", "TW", "TK", "CX"
    ]
    
    try:
        # Initialize Firestore client
        db = firestore.Client(project=project_id, database=database_id)
        map_units_collection = db.collection("map_units")
        
        print("Searching for missing countries in map_units collection...")
        print("=" * 60)
        
        found_countries = []
        not_found_countries = []
        
        for country_code in missing_countries:
            # Search by iso_alpha2 field
            docs = map_units_collection.where("iso_alpha2", "==", country_code).limit(1).get()
            
            if docs:
                doc = docs[0]
                data = doc.to_dict()
                doc_id = doc.id
                name = data.get('name', 'Unknown')
                
                print(f"✅ Found: {name} ({country_code})")
                print(f"     ID: {doc_id}")
                print(f"     Type: {data.get('type', 'N/A')}")
                print(f"     Level: {data.get('level', 'N/A')}")
                
                # Show all available fields
                fields = list(data.keys())
                if fields:
                    print(f"     Fields: {', '.join(fields)}")
                print()
                
                found_countries.append({
                    "code": country_code,
                    "name": name,
                    "id": doc_id,
                    "type": data.get('type', 'N/A')
                })
            else:
                print(f"❌ Not found: {country_code}")
                not_found_countries.append(country_code)
        
        print("=" * 60)
        print(f"Found in map_units: {len(found_countries)}")
        print(f"Still not found: {len(not_found_countries)}")
        
        if found_countries:
            print("\n📋 COUNTRIES FOUND IN MAP_UNITS:")
            for country in found_countries:
                print(f"   {country['name']} ({country['code']}) - {country['type']}")
        
        if not_found_countries:
            print(f"\n❌ STILL NOT FOUND: {', '.join(not_found_countries)}")
        
    except Exception as e:
        print(f"❌ Error checking map_units collection: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Check map_units collection for missing countries")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--database-id", default="statlas-content", help="Firestore database ID")
    
    args = parser.parse_args()
    
    try:
        check_map_units_for_countries(args.project_id, args.database_id)
    except Exception as e:
        print(f"❌ Check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
