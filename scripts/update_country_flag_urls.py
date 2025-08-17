#!/usr/bin/env python3
"""
Update country flag URLs to use Cloudflare CDN.

This script updates all country documents in Firestore to use the new
cdn.statlas.app URLs instead of the placeholder URLs.

Usage:
    python update_country_flag_urls.py --project-id statlas-467715 [--dry-run]
"""

import argparse
import logging
import sys
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from google.cloud import firestore
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    logger.error("Install with: pip install google-cloud-firestore")
    DEPENDENCIES_AVAILABLE = False


class CountryFlagURLUpdater:
    """Updates country flag URLs to use Cloudflare CDN."""
    
    def __init__(self, project_id: str):
        """Initialize the updater."""
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Required dependencies not available")
            
        self.project_id = project_id
        self.firestore_client = firestore.Client(project=project_id, database="statlas-content")
        self.cdn_base_url = "https://cdn.statlas.app/flags"
        
        logger.info(f"Initialized CountryFlagURLUpdater for project: {project_id}")
    
    def get_country_iso_mappings(self) -> Dict[str, str]:
        """Get mapping of country IDs to ISO codes from Firestore."""
        logger.info("Fetching country ISO code mappings from Firestore")
        
        countries = {}
        docs = self.firestore_client.collection("countries").stream()
        
        for doc in docs:
            data = doc.to_dict()
            country_id = doc.id
            iso_alpha2 = data.get("iso_alpha2", "").upper()
            current_flag_url = data.get("flag_url", "")
            
            if iso_alpha2:
                countries[country_id] = {
                    "iso_alpha2": iso_alpha2,
                    "current_flag_url": current_flag_url
                }
        
        logger.info(f"Found {len(countries)} countries with ISO codes")
        return countries
    
    def update_flag_urls(self, dry_run: bool = False) -> int:
        """Update country documents with Cloudflare CDN flag URLs."""
        logger.info("Updating country flag URLs to use Cloudflare CDN")
        
        country_mappings = self.get_country_iso_mappings()
        updated_count = 0
        
        for country_id, country_data in country_mappings.items():
            iso_code = country_data["iso_alpha2"]
            current_url = country_data["current_flag_url"]
            new_flag_url = f"{self.cdn_base_url}/{iso_code.lower()}.svg"
            
            # Skip if already using CDN URL
            if current_url == new_flag_url:
                logger.debug(f"Skipping {country_id} - already using CDN URL")
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] Would update {country_id} ({iso_code})")
                logger.info(f"  FROM: {current_url}")
                logger.info(f"  TO:   {new_flag_url}")
                updated_count += 1
                continue
            
            try:
                # Update country document
                doc_ref = self.firestore_client.collection("countries").document(country_id)
                doc_ref.update({
                    "flag_url": new_flag_url,
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                
                logger.info(f"Updated {country_id} ({iso_code}) -> {new_flag_url}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update {country_id}: {e}")
        
        logger.info(f"Updated {updated_count} country flag URLs")
        return updated_count
    
    def verify_cdn_availability(self) -> bool:
        """Verify that the CDN is responding correctly."""
        import requests
        
        test_url = f"{self.cdn_base_url}/us.svg"
        logger.info(f"Testing CDN availability: {test_url}")
        
        try:
            response = requests.head(test_url, timeout=10)
            if response.status_code == 200:
                logger.info("✅ CDN is responding correctly")
                return True
            else:
                logger.warning(f"⚠️ CDN returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ CDN test failed: {e}")
            return False


def main():
    """Main CLI interface."""
    if not DEPENDENCIES_AVAILABLE:
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Update country flag URLs to use Cloudflare CDN",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--project-id", default="statlas-467715",
                       help="Google Cloud project ID")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--skip-verification", action="store_true",
                       help="Skip CDN availability verification")
    
    args = parser.parse_args()
    
    try:
        updater = CountryFlagURLUpdater(args.project_id)
        
        # Step 1: Verify CDN is working (unless skipped)
        if not args.skip_verification:
            logger.info("Step 1: Verifying CDN availability...")
            if not updater.verify_cdn_availability():
                logger.error("CDN verification failed. Please check your Cloudflare setup.")
                logger.info("You can skip this check with --skip-verification")
                sys.exit(1)
        else:
            logger.info("Step 1: Skipped CDN verification")
        
        # Step 2: Update flag URLs
        logger.info("Step 2: Updating country flag URLs...")
        updated_count = updater.update_flag_urls(dry_run=args.dry_run)
        
        if args.dry_run:
            logger.info(f"Dry run complete: {updated_count} countries would be updated")
        else:
            logger.info(f"Update complete: {updated_count} countries updated")
        
    except Exception as e:
        logger.error(f"Update failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

