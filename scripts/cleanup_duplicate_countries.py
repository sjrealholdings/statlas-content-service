#!/usr/bin/env python3
"""
Cleanup Duplicate Countries

This script removes the duplicate two-character ID country documents that were
accidentally created during the update process.
"""

import argparse
import sys
from google.cloud import firestore
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_duplicate_countries(project_id: str, database_id: str = "statlas-content", dry_run: bool = True):
    """Remove duplicate two-character ID country documents."""
    print(f"🧹 Cleaning up duplicate countries in {database_id} database...")
    print(f"📋 Project ID: {project_id}")
    print(f"🔍 Dry run: {dry_run}")
    print()
    
    try:
        # Initialize Firestore client
        db = firestore.Client(project=project_id, database=database_id)
        collection = db.collection("countries")
        
        # Find all documents with two-character IDs
        docs = collection.limit(1000).get()
        
        two_char_docs = []
        for doc in docs:
            doc_id = doc.id
            if len(doc_id) == 2 and doc_id.isalpha():
                two_char_docs.append(doc)
        
        print(f"Found {len(two_char_docs)} documents with two-character IDs")
        print()
        
        if not two_char_docs:
            print("✅ No duplicate documents found to clean up")
            return
        
        # Show what would be deleted
        print("📋 Documents that would be deleted:")
        for doc in two_char_docs[:10]:  # Show first 10
            doc_data = doc.to_dict()
            print(f"   {doc.id} - {doc_data.get('name', 'Unknown')}")
        if len(two_char_docs) > 10:
            print(f"   ... and {len(two_char_docs) - 10} more")
        print()
        
        if dry_run:
            print("🔍 This was a dry run. No documents were deleted.")
            print("Run without --dry-run to actually delete the duplicates.")
            return
        
        # Confirm deletion
        response = input(f"⚠️  Are you sure you want to delete {len(two_char_docs)} duplicate documents? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Deletion cancelled")
            return
        
        # Delete the documents
        deleted_count = 0
        for doc in two_char_docs:
            try:
                doc.reference.delete()
                deleted_count += 1
                print(f"   ✅ Deleted {doc.id}")
            except Exception as e:
                print(f"   ❌ Error deleting {doc.id}: {e}")
        
        print()
        print(f"🎉 Successfully deleted {deleted_count} duplicate documents")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Clean up duplicate country documents")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--database-id", default="statlas-content", help="Firestore database ID")
    parser.add_argument("--no-dry-run", action="store_true", 
                       help="Actually delete the documents (default is dry-run)")
    
    args = parser.parse_args()
    
    # Default to dry-run unless --no-dry-run is specified
    dry_run = not args.no_dry_run
    
    cleanup_duplicate_countries(args.project_id, args.database_id, dry_run)

if __name__ == "__main__":
    main()
