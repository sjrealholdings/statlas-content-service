#!/usr/bin/env python3
"""
Purge GADM Administrative Level Data from Firestore

This script removes all documents from admin_level_1 through admin_level_5 collections
in the statlas-content Firestore database.

Usage:
    python3 scripts/purge_gadm_data.py [--dry-run] [--backup]
    
Options:
    --dry-run    Show what would be deleted without actually deleting
    --backup     Backup data to Cloud Storage before deletion
"""

import argparse
import logging
from google.cloud import firestore
from google.cloud import storage
import json
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GADMDataPurger:
    def __init__(self, dry_run=False, backup=False):
        self.dry_run = dry_run
        self.backup = backup
        self.db = firestore.Client(database='statlas-content')
        if backup:
            self.storage_client = storage.Client()
            self.bucket_name = 'statlas-content-backups'
        
        # GADM collections to purge
        self.gadm_collections = [
            'admin_level_1',
            'admin_level_2', 
            'admin_level_3',
            'admin_level_4',
            'admin_level_5'
        ]
    
    def count_documents_in_collection(self, collection_name):
        """Count total documents in a collection"""
        try:
            docs = list(self.db.collection(collection_name).stream())
            return len(docs)
        except Exception as e:
            logging.warning(f"Could not count documents in {collection_name}: {e}")
            return 0
    
    def backup_collection(self, collection_name):
        """Backup collection to Cloud Storage"""
        if not self.backup:
            return
            
        logging.info(f"📦 Backing up {collection_name} to Cloud Storage...")
        
        try:
            # Get bucket
            bucket = self.storage_client.bucket(self.bucket_name)
            
            # Create backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"gadm_purge_backup/{collection_name}_{timestamp}.json"
            
            # Collect all documents
            docs = []
            for doc in self.db.collection(collection_name).stream():
                doc_data = doc.to_dict()
                doc_data['_firestore_id'] = doc.id
                docs.append(doc_data)
            
            if docs:
                # Upload to Cloud Storage
                blob = bucket.blob(backup_filename)
                blob.upload_from_string(json.dumps(docs, indent=2))
                logging.info(f"   ✅ Backed up {len(docs)} documents to gs://{self.bucket_name}/{backup_filename}")
            else:
                logging.info(f"   ⚠️  No documents to backup in {collection_name}")
                
        except Exception as e:
            logging.error(f"   ❌ Backup failed for {collection_name}: {e}")
            raise
    
    def delete_collection_documents(self, collection_name):
        """Delete all documents in a collection"""
        logging.info(f"🗑️  {'[DRY RUN] ' if self.dry_run else ''}Deleting documents from {collection_name}...")
        
        try:
            collection_ref = self.db.collection(collection_name)
            docs = list(collection_ref.stream())
            
            if not docs:
                logging.info(f"   ✅ Collection {collection_name} is already empty")
                return 0
            
            deleted_count = 0
            batch_size = 500  # Firestore batch limit
            
            # Process in batches
            for i in range(0, len(docs), batch_size):
                batch = self.db.batch()
                batch_docs = docs[i:i + batch_size]
                
                for doc in batch_docs:
                    if not self.dry_run:
                        batch.delete(doc.reference)
                    deleted_count += 1
                
                if not self.dry_run:
                    batch.commit()
                    
                logging.info(f"   📊 {'Would delete' if self.dry_run else 'Deleted'} batch {i//batch_size + 1}: {len(batch_docs)} documents")
                
                # Small delay between batches
                if not self.dry_run:
                    time.sleep(0.1)
            
            logging.info(f"   ✅ {'Would delete' if self.dry_run else 'Deleted'} {deleted_count} documents from {collection_name}")
            return deleted_count
            
        except Exception as e:
            logging.error(f"   ❌ Failed to delete from {collection_name}: {e}")
            raise
    
    def get_purge_summary(self):
        """Get summary of what will be purged"""
        logging.info("📊 GADM DATA PURGE SUMMARY")
        logging.info("=" * 50)
        
        total_docs = 0
        collection_stats = {}
        
        for collection in self.gadm_collections:
            count = self.count_documents_in_collection(collection)
            collection_stats[collection] = count
            total_docs += count
            logging.info(f"   {collection}: {count:,} documents")
        
        logging.info("-" * 50)
        logging.info(f"   TOTAL: {total_docs:,} documents across {len(self.gadm_collections)} collections")
        
        if self.dry_run:
            logging.info("   🔍 DRY RUN MODE: No data will be deleted")
        if self.backup:
            logging.info("   📦 BACKUP MODE: Data will be backed up to Cloud Storage")
        
        return total_docs, collection_stats
    
    def purge_gadm_data(self):
        """Main purge operation"""
        logging.info("🧹 GADM DATA PURGE OPERATION")
        logging.info("=" * 60)
        
        # Get summary
        total_docs, collection_stats = self.get_purge_summary()
        
        if total_docs == 0:
            logging.info("✅ No GADM data found to purge. Database is already clean.")
            return
        
        # Confirm operation
        if not self.dry_run:
            logging.warning("⚠️  THIS WILL PERMANENTLY DELETE ALL GADM ADMINISTRATIVE DATA")
            logging.warning("⚠️  This action cannot be undone unless you have backups")
            
        logging.info("\n🚀 Starting purge operation...")
        start_time = time.time()
        
        total_deleted = 0
        
        for collection in self.gadm_collections:
            if collection_stats[collection] > 0:
                try:
                    # Backup first if requested
                    if self.backup:
                        self.backup_collection(collection)
                    
                    # Delete documents
                    deleted = self.delete_collection_documents(collection)
                    total_deleted += deleted
                    
                except Exception as e:
                    logging.error(f"❌ Failed to process {collection}: {e}")
                    raise
        
        # Summary
        duration = time.time() - start_time
        logging.info("\n🎯 PURGE OPERATION COMPLETE")
        logging.info("=" * 50)
        logging.info(f"   {'Would delete' if self.dry_run else 'Deleted'}: {total_deleted:,} documents")
        logging.info(f"   Collections processed: {len([c for c in self.gadm_collections if collection_stats[c] > 0])}")
        logging.info(f"   Duration: {duration:.1f} seconds")
        
        if self.backup and not self.dry_run:
            logging.info(f"   📦 Backups stored in: gs://{self.bucket_name}/gadm_purge_backup/")
        
        logging.info("✅ GADM administrative level data has been purged from Firestore")

def main():
    parser = argparse.ArgumentParser(description='Purge GADM administrative level data from Firestore')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--backup', action='store_true',
                       help='Backup data to Cloud Storage before deletion')
    
    args = parser.parse_args()
    
    try:
        purger = GADMDataPurger(dry_run=args.dry_run, backup=args.backup)
        purger.purge_gadm_data()
        
    except Exception as e:
        logging.error(f"❌ Purge operation failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
