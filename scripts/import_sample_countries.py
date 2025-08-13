#!/usr/bin/env python3
"""
Import sample country data into the statlas-content Firestore database.

This script imports a basic set of countries with flags, capitals, and basic information.
In production, you would import from authoritative sources like UN data or REST Countries API.

Usage:
    python3 import_sample_countries.py --project-id your-project-id [--dry-run]
"""

import argparse
import sys
import time
from datetime import datetime
from google.cloud import firestore

# Sample country data (in production, load from external sources)
SAMPLE_COUNTRIES = [
    {
        "id": "usa",
        "name": "United States",
        "official_name": "United States of America", 
        "iso_alpha2": "US",
        "iso_alpha3": "USA",
        "iso_numeric": 840,
        "flag_url": "https://cdn.statlas.com/flags/usa.svg",
        "flag_emoji": "🇺🇸",
        "bounds": {
            "min_lat": 18.9110642,
            "max_lat": 71.3577635,
            "min_lon": -179.1506,
            "max_lon": -66.9513812
        },
        "capital": "Washington, D.C.",
        "population": 331893745,
        "area_km2": 9833517,
        "currency_code": "USD",
        "languages": ["en"],
        "is_active": True
    },
    {
        "id": "fra",
        "name": "France",
        "official_name": "French Republic",
        "iso_alpha2": "FR", 
        "iso_alpha3": "FRA",
        "iso_numeric": 250,
        "flag_url": "https://cdn.statlas.com/flags/fra.svg",
        "flag_emoji": "🇫🇷",
        "bounds": {
            "min_lat": 41.3253,
            "max_lat": 51.1242,
            "min_lon": -5.5591,
            "max_lon": 9.6625
        },
        "capital": "Paris",
        "population": 67413000,
        "area_km2": 643801,
        "currency_code": "EUR",
        "languages": ["fr"],
        "is_active": True
    },
    {
        "id": "gbr",
        "name": "United Kingdom",
        "official_name": "United Kingdom of Great Britain and Northern Ireland",
        "iso_alpha2": "GB",
        "iso_alpha3": "GBR", 
        "iso_numeric": 826,
        "flag_url": "https://cdn.statlas.com/flags/gbr.svg",
        "flag_emoji": "🇬🇧",
        "bounds": {
            "min_lat": 49.9028,
            "max_lat": 60.8610,
            "min_lon": -8.6493,
            "max_lon": 1.7627
        },
        "capital": "London",
        "population": 67886004,
        "area_km2": 242495,
        "currency_code": "GBP",
        "languages": ["en"],
        "is_active": True
    },
    {
        "id": "jpn",
        "name": "Japan",
        "official_name": "Japan",
        "iso_alpha2": "JP",
        "iso_alpha3": "JPN",
        "iso_numeric": 392,
        "flag_url": "https://cdn.statlas.com/flags/jpn.svg", 
        "flag_emoji": "🇯🇵",
        "bounds": {
            "min_lat": 24.0456,
            "max_lat": 45.5514,
            "min_lon": 122.9346,
            "max_lon": 153.9866
        },
        "capital": "Tokyo",
        "population": 125584838,
        "area_km2": 377930,
        "currency_code": "JPY",
        "languages": ["ja"],
        "is_active": True
    },
    {
        "id": "can",
        "name": "Canada", 
        "official_name": "Canada",
        "iso_alpha2": "CA",
        "iso_alpha3": "CAN",
        "iso_numeric": 124,
        "flag_url": "https://cdn.statlas.com/flags/can.svg",
        "flag_emoji": "🇨🇦",
        "bounds": {
            "min_lat": 41.6765,
            "max_lat": 83.2364,
            "min_lon": -141.0027,
            "max_lon": -52.6480
        },
        "capital": "Ottawa",
        "population": 38232593,
        "area_km2": 9984670,
        "currency_code": "CAD",
        "languages": ["en", "fr"],
        "is_active": True
    }
]

def import_countries(project_id: str, dry_run: bool = False):
    """Import sample countries into Firestore."""
    print("🌍 Importing sample countries to statlas-content database...")
    print(f"📋 Project ID: {project_id}")
    print(f"🔍 Dry run: {dry_run}")
    print()
    
    if not dry_run:
        # Initialize Firestore client with statlas-content database
        db = firestore.Client(project=project_id, database="statlas-content")
        collection = db.collection("countries")
    
    imported_count = 0
    
    for country_data in SAMPLE_COUNTRIES:
        country_id = country_data["id"]
        
        # Add timestamps
        now = datetime.utcnow()
        country_data["created_at"] = now
        country_data["updated_at"] = now
        
        print(f"📍 {country_data['flag_emoji']} {country_data['name']} ({country_data['iso_alpha3']})")
        print(f"   Capital: {country_data['capital']}")
        print(f"   Population: {country_data['population']:,}")
        print(f"   Area: {country_data['area_km2']:,} km²")
        
        if not dry_run:
            try:
                # Check if country already exists
                doc_ref = collection.document(country_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    print(f"   ⚠️  Country {country_id} already exists, updating...")
                    country_data["updated_at"] = now
                    # Keep original created_at
                    existing_data = doc.to_dict()
                    country_data["created_at"] = existing_data.get("created_at", now)
                else:
                    print(f"   ✅ Creating new country {country_id}")
                
                doc_ref.set(country_data)
                imported_count += 1
                
            except Exception as e:
                print(f"   ❌ Error importing {country_id}: {e}")
                continue
        else:
            print(f"   🔍 Would import {country_id}")
            imported_count += 1
        
        print()
        
        # Small delay to avoid overwhelming Firestore
        if not dry_run:
            time.sleep(0.1)
    
    print(f"✅ Import complete!")
    print(f"📊 Countries processed: {imported_count}/{len(SAMPLE_COUNTRIES)}")
    
    if not dry_run:
        print()
        print("🔍 Verifying import...")
        try:
            docs = collection.where("is_active", "==", True).limit(10).get()
            print(f"✅ Found {len(docs)} active countries in database")
        except Exception as e:
            print(f"⚠️  Verification failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Import sample countries to statlas-content database")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without actually importing")
    
    args = parser.parse_args()
    
    try:
        import_countries(args.project_id, args.dry_run)
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
