#!/usr/bin/env python3
"""
Check existing countries in Firestore database.

This script lists all countries currently in the database to understand the existing structure.
"""

import argparse
import sys
from google.cloud import firestore

def check_existing_countries(project_id: str, database_id: str = "statlas-content"):
    """Check what countries exist in the database."""
    print(f"🔍 Checking countries in {database_id} database...")
    print(f"📋 Project ID: {project_id}")
    print()
    
    try:
        # Initialize Firestore client
        db = firestore.Client(project=project_id, database=database_id)
        collection = db.collection("countries")
        
        # Get all documents
        docs = collection.limit(1000).get()
        
        if not docs:
            print("❌ No countries found in database")
            return
        
        print(f"✅ Found {len(docs)} countries in database:")
        print("=" * 50)
        
        for i, doc in enumerate(docs, 1):
            data = doc.to_dict()
            doc_id = doc.id
            
            # Display key information
            name = data.get('name', 'Unknown')
            country_code = data.get('country_code', 'N/A')
            iso_alpha2 = data.get('iso_alpha2', 'N/A')
            iso_alpha3 = data.get('iso_alpha3', 'N/A')
            
            print(f"{i:3d}. {name}")
            print(f"     ID: {doc_id}")
            print(f"     Country Code: {country_code}")
            print(f"     ISO Alpha2: {iso_alpha2}")
            print(f"     ISO Alpha3: {iso_alpha3}")
            
            # Show all available fields
            fields = list(data.keys())
            if fields:
                print(f"     Fields: {', '.join(fields)}")
            print()
        
        print("=" * 50)
        print(f"Total countries: {len(docs)}")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Check existing countries in Firestore database")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--database-id", default="statlas-content", help="Firestore database ID")
    
    args = parser.parse_args()
    
    try:
        check_existing_countries(args.project_id, args.database_id)
    except Exception as e:
        print(f"❌ Check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
