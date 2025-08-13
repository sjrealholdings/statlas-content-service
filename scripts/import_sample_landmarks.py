#!/usr/bin/env python3
"""
Import sample landmark data into the statlas-content Firestore database.

This script imports a basic set of world-famous landmarks with achievement integration.
In production, you would import from sources like TripAdvisor, Wikipedia, or UNESCO.

Usage:
    python3 import_sample_landmarks.py --project-id your-project-id [--dry-run]
"""

import argparse
import sys
import time
from datetime import datetime
from google.cloud import firestore

# Sample landmark data (in production, load from external sources)
SAMPLE_LANDMARKS = [
    {
        "id": "statue_of_liberty",
        "name": "Statue of Liberty",
        "official_name": "Liberty Enlightening the World",
        "type": "monument",
        "category": "historic_site",
        "coordinates": {
            "lat": 40.6892494,
            "lon": -74.0445004,
            "altitude": 93
        },
        "precision_radius_meters": 30,
        "country_id": "usa",
        "state_id": "ny_usa",
        "city_id": "nyc_ny_usa",
        "description": "A colossal neoclassical sculpture on Liberty Island in New York Harbor, a symbol of freedom and democracy.",
        "short_description": "Iconic symbol of freedom and democracy",
        "images": [
            {
                "url": "https://cdn.statlas.com/landmarks/statue_of_liberty_main.jpg",
                "type": "primary",
                "caption": "Statue of Liberty from the harbor"
            }
        ],
        "visiting_info": {
            "hours": {
                "monday": {"open": "08:30", "close": "18:00"},
                "tuesday": {"open": "08:30", "close": "18:00"},
                "wednesday": {"open": "08:30", "close": "18:00"},
                "thursday": {"open": "08:30", "close": "18:00"},
                "friday": {"open": "08:30", "close": "18:00"},
                "saturday": {"open": "08:30", "close": "18:00"},
                "sunday": {"open": "08:30", "close": "18:00"}
            },
            "admission": {
                "required": True,
                "adult_price": {"amount": 23.50, "currency": "USD"},
                "child_price": {"amount": 18.00, "currency": "USD"}
            }
        },
        "achievement": {
            "id": "statue_of_liberty_visitor",
            "title": "Lady Liberty",
            "description": "Visit the iconic Statue of Liberty",
            "points": 50,
            "rarity": "uncommon",
            "category": "landmarks",
            "unlock_message": "You've visited one of America's most iconic symbols!"
        },
        "external_links": {
            "wikipedia_url": "https://en.wikipedia.org/wiki/Statue_of_Liberty",
            "official_website": "https://www.nps.gov/stli/"
        },
        "tags": ["nyc", "monument", "historic", "ferry_required"],
        "unesco_world_heritage": False,
        "national_historic_landmark": True,
        "is_active": True
    },
    {
        "id": "eiffel_tower",
        "name": "Eiffel Tower",
        "official_name": "Tour Eiffel",
        "type": "monument",
        "category": "architectural",
        "coordinates": {
            "lat": 48.8583,
            "lon": 2.2944,
            "altitude": 330
        },
        "precision_radius_meters": 25,
        "country_id": "fra",
        "state_id": "ile_de_france",
        "city_id": "paris",
        "description": "A wrought-iron lattice tower on the Champ de Mars in Paris, named after engineer Gustave Eiffel.",
        "short_description": "Iconic iron tower and symbol of Paris",
        "images": [
            {
                "url": "https://cdn.statlas.com/landmarks/eiffel_tower_main.jpg",
                "type": "primary",
                "caption": "Eiffel Tower at sunset"
            }
        ],
        "visiting_info": {
            "hours": {
                "monday": {"open": "09:30", "close": "23:45"},
                "tuesday": {"open": "09:30", "close": "23:45"},
                "wednesday": {"open": "09:30", "close": "23:45"},
                "thursday": {"open": "09:30", "close": "23:45"},
                "friday": {"open": "09:30", "close": "23:45"},
                "saturday": {"open": "09:30", "close": "23:45"},
                "sunday": {"open": "09:30", "close": "23:45"}
            },
            "admission": {
                "required": True,
                "adult_price": {"amount": 29.40, "currency": "EUR"},
                "child_price": {"amount": 14.70, "currency": "EUR"}
            }
        },
        "achievement": {
            "id": "eiffel_tower_visitor",
            "title": "Iron Lady",
            "description": "Visit the iconic Eiffel Tower in Paris",
            "points": 60,
            "rarity": "uncommon",
            "category": "landmarks",
            "unlock_message": "Bonjour! You've visited the symbol of Paris!"
        },
        "external_links": {
            "wikipedia_url": "https://en.wikipedia.org/wiki/Eiffel_Tower",
            "official_website": "https://www.toureiffel.paris/"
        },
        "tags": ["paris", "monument", "tower", "viewpoint"],
        "unesco_world_heritage": True,
        "national_historic_landmark": False,
        "is_active": True
    },
    {
        "id": "big_ben",
        "name": "Big Ben",
        "official_name": "Elizabeth Tower",
        "type": "building",
        "category": "architectural",
        "coordinates": {
            "lat": 51.5007,
            "lon": -0.1246,
            "altitude": 96
        },
        "precision_radius_meters": 20,
        "country_id": "gbr",
        "state_id": "england",
        "city_id": "london",
        "description": "The nickname for the Great Bell of the striking clock at the north end of the Palace of Westminster in London.",
        "short_description": "Iconic clock tower and symbol of London",
        "images": [
            {
                "url": "https://cdn.statlas.com/landmarks/big_ben_main.jpg",
                "type": "primary",
                "caption": "Big Ben clock tower"
            }
        ],
        "visiting_info": {
            "hours": {
                "note": "External viewing only - tours suspended for renovation"
            },
            "admission": {
                "required": False
            }
        },
        "achievement": {
            "id": "big_ben_visitor",
            "title": "Timekeeping",
            "description": "Visit Big Ben, London's famous clock tower",
            "points": 45,
            "rarity": "uncommon",
            "category": "landmarks",
            "unlock_message": "Right on time! You've seen London's most famous timepiece!"
        },
        "external_links": {
            "wikipedia_url": "https://en.wikipedia.org/wiki/Big_Ben",
            "official_website": "https://www.parliament.uk/bigben"
        },
        "tags": ["london", "clock", "tower", "parliament"],
        "unesco_world_heritage": True,
        "national_historic_landmark": False,
        "is_active": True
    },
    {
        "id": "tokyo_tower",
        "name": "Tokyo Tower",
        "official_name": "Tokyo Tower",
        "type": "building",
        "category": "architectural",
        "coordinates": {
            "lat": 35.6586,
            "lon": 139.7454,
            "altitude": 333
        },
        "precision_radius_meters": 30,
        "country_id": "jpn",
        "state_id": "tokyo",
        "city_id": "tokyo",
        "description": "A communications and observation tower in Tokyo, inspired by the Eiffel Tower.",
        "short_description": "Tokyo's iconic red and white communications tower",
        "images": [
            {
                "url": "https://cdn.statlas.com/landmarks/tokyo_tower_main.jpg",
                "type": "primary",
                "caption": "Tokyo Tower illuminated at night"
            }
        ],
        "visiting_info": {
            "hours": {
                "monday": {"open": "09:00", "close": "23:00"},
                "tuesday": {"open": "09:00", "close": "23:00"},
                "wednesday": {"open": "09:00", "close": "23:00"},
                "thursday": {"open": "09:00", "close": "23:00"},
                "friday": {"open": "09:00", "close": "23:00"},
                "saturday": {"open": "09:00", "close": "23:00"},
                "sunday": {"open": "09:00", "close": "23:00"}
            },
            "admission": {
                "required": True,
                "adult_price": {"amount": 1200, "currency": "JPY"},
                "child_price": {"amount": 700, "currency": "JPY"}
            }
        },
        "achievement": {
            "id": "tokyo_tower_visitor",
            "title": "Tokyo Skyline",
            "description": "Visit Tokyo Tower, the symbol of modern Japan",
            "points": 40,
            "rarity": "common",
            "category": "landmarks",
            "unlock_message": "Konnichiwa! You've reached new heights in Tokyo!"
        },
        "external_links": {
            "wikipedia_url": "https://en.wikipedia.org/wiki/Tokyo_Tower",
            "official_website": "https://www.tokyotower.co.jp/"
        },
        "tags": ["tokyo", "tower", "viewpoint", "modern"],
        "unesco_world_heritage": False,
        "national_historic_landmark": False,
        "is_active": True
    },
    {
        "id": "cn_tower",
        "name": "CN Tower",
        "official_name": "Canadian National Tower",
        "type": "building",
        "category": "architectural",
        "coordinates": {
            "lat": 43.6426,
            "lon": -79.3871,
            "altitude": 553
        },
        "precision_radius_meters": 25,
        "country_id": "can",
        "state_id": "ontario",
        "city_id": "toronto",
        "description": "A communications and observation tower in Toronto, once the world's tallest free-standing structure.",
        "short_description": "Toronto's iconic concrete communications tower",
        "images": [
            {
                "url": "https://cdn.statlas.com/landmarks/cn_tower_main.jpg",
                "type": "primary",
                "caption": "CN Tower dominating Toronto's skyline"
            }
        ],
        "visiting_info": {
            "hours": {
                "monday": {"open": "09:00", "close": "22:30"},
                "tuesday": {"open": "09:00", "close": "22:30"},
                "wednesday": {"open": "09:00", "close": "22:30"},
                "thursday": {"open": "09:00", "close": "22:30"},
                "friday": {"open": "09:00", "close": "22:30"},
                "saturday": {"open": "08:30", "close": "23:00"},
                "sunday": {"open": "08:30", "close": "22:30"}
            },
            "admission": {
                "required": True,
                "adult_price": {"amount": 38.00, "currency": "CAD"},
                "child_price": {"amount": 28.00, "currency": "CAD"}
            }
        },
        "achievement": {
            "id": "cn_tower_visitor",
            "title": "Sky High",
            "description": "Visit the CN Tower in Toronto",
            "points": 35,
            "rarity": "common",
            "category": "landmarks",
            "unlock_message": "Eh! You've reached the top of Toronto!"
        },
        "external_links": {
            "wikipedia_url": "https://en.wikipedia.org/wiki/CN_Tower",
            "official_website": "https://www.cntower.ca/"
        },
        "tags": ["toronto", "tower", "viewpoint", "edgewalk"],
        "unesco_world_heritage": False,
        "national_historic_landmark": False,
        "is_active": True
    }
]

def import_landmarks(project_id: str, dry_run: bool = False):
    """Import sample landmarks into Firestore."""
    print("🏛️ Importing sample landmarks to statlas-content database...")
    print(f"📋 Project ID: {project_id}")
    print(f"🔍 Dry run: {dry_run}")
    print()
    
    if not dry_run:
        # Initialize Firestore client with statlas-content database
        db = firestore.Client(project=project_id, database="statlas-content")
        collection = db.collection("landmarks")
    
    imported_count = 0
    
    for landmark_data in SAMPLE_LANDMARKS:
        landmark_id = landmark_data["id"]
        
        # Add timestamps
        now = datetime.utcnow()
        landmark_data["created_at"] = now
        landmark_data["updated_at"] = now
        
        print(f"🏛️ {landmark_data['name']} ({landmark_data['country_id'].upper()})")
        print(f"   Type: {landmark_data['type']} - {landmark_data['category']}")
        print(f"   Location: {landmark_data['coordinates']['lat']:.4f}, {landmark_data['coordinates']['lon']:.4f}")
        print(f"   Achievement: {landmark_data['achievement']['title']} ({landmark_data['achievement']['points']} pts)")
        
        if not dry_run:
            try:
                # Check if landmark already exists
                doc_ref = collection.document(landmark_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    print(f"   ⚠️  Landmark {landmark_id} already exists, updating...")
                    landmark_data["updated_at"] = now
                    # Keep original created_at
                    existing_data = doc.to_dict()
                    landmark_data["created_at"] = existing_data.get("created_at", now)
                else:
                    print(f"   ✅ Creating new landmark {landmark_id}")
                
                doc_ref.set(landmark_data)
                imported_count += 1
                
            except Exception as e:
                print(f"   ❌ Error importing {landmark_id}: {e}")
                continue
        else:
            print(f"   🔍 Would import {landmark_id}")
            imported_count += 1
        
        print()
        
        # Small delay to avoid overwhelming Firestore
        if not dry_run:
            time.sleep(0.1)
    
    print(f"✅ Import complete!")
    print(f"📊 Landmarks processed: {imported_count}/{len(SAMPLE_LANDMARKS)}")
    
    if not dry_run:
        print()
        print("🔍 Verifying import...")
        try:
            docs = collection.where("is_active", "==", True).limit(10).get()
            print(f"✅ Found {len(docs)} active landmarks in database")
            
            # Show achievement summary
            achievement_points = sum(landmark["achievement"]["points"] for landmark in SAMPLE_LANDMARKS)
            print(f"🏆 Total achievement points available: {achievement_points}")
            
        except Exception as e:
            print(f"⚠️  Verification failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Import sample landmarks to statlas-content database")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without actually importing")
    
    args = parser.parse_args()
    
    try:
        import_landmarks(args.project_id, args.dry_run)
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
