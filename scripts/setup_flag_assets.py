#!/usr/bin/env python3
"""
Setup Flag Assets for Statlas

This script:
1. Sets up Google Cloud Storage bucket for flag assets
2. Configures Cloud CDN for fast global delivery
3. Uploads FlagKit SVG assets to the bucket
4. Updates country data with correct flag URLs
5. Configures the new statlas.app domain

Requirements:
- google-cloud-storage
- google-cloud-firestore
- gcloud CLI configured with appropriate permissions

Usage:
    python setup_flag_assets.py --project-id statlas-467715 [--dry-run]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from google.cloud import storage
    from google.cloud import firestore
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    logger.error("Install with: pip install google-cloud-storage google-cloud-firestore")
    DEPENDENCIES_AVAILABLE = False


class FlagAssetManager:
    """Manages flag assets for Statlas platform."""
    
    def __init__(self, project_id: str, bucket_name: str = "statlas-flag-assets"):
        """Initialize the flag asset manager."""
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Required dependencies not available")
            
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.storage_client = storage.Client(project=project_id)
        self.firestore_client = firestore.Client(project=project_id, database="statlas-content")
        
        # Flag asset paths
        self.flagkit_svg_path = Path("../flagkit-assets/Assets/SVG")
        self.flagkit_png_path = Path("../flagkit-assets/Assets/PNG")
        self.cdn_base_url = "https://cdn.statlas.app/flags"
        
        logger.info(f"Initialized FlagAssetManager for project: {project_id}")
    
    def create_storage_bucket(self, location: str = "US", dry_run: bool = False) -> bool:
        """Create Google Cloud Storage bucket for flag assets."""
        logger.info(f"Creating storage bucket: {self.bucket_name}")
        
        if dry_run:
            logger.info("[DRY RUN] Would create bucket")
            return True
        
        try:
            # Check if bucket already exists
            bucket = self.storage_client.bucket(self.bucket_name)
            if bucket.exists():
                logger.info(f"Bucket {self.bucket_name} already exists")
                return True
            
            # Create bucket
            bucket = self.storage_client.create_bucket(self.bucket_name, location=location)
            logger.info(f"Created bucket: {bucket.name}")
            
            # Configure bucket for public read access
            policy = bucket.get_iam_policy(requested_policy_version=3)
            policy.bindings.append({
                "role": "roles/storage.objectViewer",
                "members": {"allUsers"}
            })
            bucket.set_iam_policy(policy)
            
            # Set CORS policy for web access
            bucket.cors = [{
                'origin': ['*'],
                'method': ['GET'],
                'responseHeader': ['Content-Type'],
                'maxAgeSeconds': 3600
            }]
            bucket.patch()
            
            logger.info("Configured bucket for public access and CORS")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create bucket: {e}")
            return False
    
    def get_available_flags(self) -> Dict[str, Dict[str, Path]]:
        """Get list of available flag files from FlagKit (SVG and PNG)."""
        if not self.flagkit_svg_path.exists():
            raise FileNotFoundError(f"FlagKit SVG path not found: {self.flagkit_svg_path}")
        if not self.flagkit_png_path.exists():
            raise FileNotFoundError(f"FlagKit PNG path not found: {self.flagkit_png_path}")
        
        flags = {}
        
        # Get SVG files
        for svg_file in self.flagkit_svg_path.glob("*.svg"):
            iso_code = svg_file.stem.upper()
            if iso_code not in flags:
                flags[iso_code] = {}
            flags[iso_code]['svg'] = svg_file
        
        # Get PNG files (all resolutions)
        for png_file in self.flagkit_png_path.glob("*.png"):
            filename = png_file.stem
            if '@' in filename:
                # Handle @2x, @3x resolutions
                iso_code, resolution = filename.split('@', 1)
                iso_code = iso_code.upper()
                resolution_key = f"png_{resolution}"
            else:
                # Handle 1x resolution
                iso_code = filename.upper()
                resolution_key = "png"
            
            if iso_code not in flags:
                flags[iso_code] = {}
            flags[iso_code][resolution_key] = png_file
        
        logger.info(f"Found {len(flags)} countries with flag assets")
        return flags
    
    def upload_flag_assets(self, dry_run: bool = False) -> Dict[str, str]:
        """Upload flag assets (SVG and PNG) to Cloud Storage."""
        logger.info("Uploading flag assets to Cloud Storage")
        
        available_flags = self.get_available_flags()
        bucket = self.storage_client.bucket(self.bucket_name)
        uploaded_urls = {}
        total_uploads = 0
        
        for iso_code, flag_formats in available_flags.items():
            for format_key, flag_path in flag_formats.items():
                # Determine file extension and content type
                if format_key == 'svg':
                    extension = 'svg'
                    content_type = 'image/svg+xml'
                    blob_name = f"flags/{iso_code.lower()}.svg"
                elif format_key.startswith('png'):
                    extension = 'png'
                    content_type = 'image/png'
                    if format_key == 'png':
                        blob_name = f"flags/{iso_code.lower()}.png"
                    else:
                        # png_2x, png_3x
                        resolution = format_key.replace('png_', '@')
                        blob_name = f"flags/{iso_code.lower()}{resolution}.png"
                else:
                    continue  # Skip unknown formats
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would upload {flag_path.name} -> {blob_name}")
                    total_uploads += 1
                    continue
                
                try:
                    # Upload file
                    blob = bucket.blob(blob_name)
                    blob.upload_from_filename(str(flag_path))
                    
                    # Set content type and cache control
                    blob.content_type = content_type
                    blob.cache_control = "public, max-age=86400"  # 24 hours
                    blob.patch()
                    
                    # Generate public URL (only track SVG URLs for country updates)
                    public_url = f"{self.cdn_base_url}/{blob_name.replace('flags/', '')}"
                    if format_key == 'svg':
                        uploaded_urls[iso_code] = public_url
                    
                    logger.info(f"Uploaded: {iso_code} {format_key} -> {public_url}")
                    total_uploads += 1
                    
                except Exception as e:
                    logger.error(f"Failed to upload {iso_code} {format_key}: {e}")
        
        logger.info(f"Upload complete: {total_uploads} files uploaded ({len(uploaded_urls)} SVG flags for country updates)")
        return uploaded_urls
    
    def get_country_iso_mappings(self) -> Dict[str, str]:
        """Get mapping of country IDs to ISO codes from Firestore."""
        logger.info("Fetching country ISO code mappings from Firestore")
        
        countries = {}
        docs = self.firestore_client.collection("countries").stream()
        
        for doc in docs:
            data = doc.to_dict()
            country_id = doc.id
            iso_alpha2 = data.get("iso_alpha2", "").upper()
            
            if iso_alpha2:
                countries[country_id] = iso_alpha2
        
        logger.info(f"Found {len(countries)} countries with ISO codes")
        return countries
    
    def update_country_flag_urls(self, uploaded_flags: Dict[str, str], dry_run: bool = False) -> int:
        """Update country documents with correct flag URLs."""
        logger.info("Updating country flag URLs in Firestore")
        
        country_mappings = self.get_country_iso_mappings()
        updated_count = 0
        
        for country_id, iso_code in country_mappings.items():
            if iso_code in uploaded_flags:
                flag_url = uploaded_flags[iso_code]
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would update {country_id} -> {flag_url}")
                    updated_count += 1
                    continue
                
                try:
                    # Update country document
                    doc_ref = self.firestore_client.collection("countries").document(country_id)
                    doc_ref.update({
                        "flag_url": flag_url,
                        "updated_at": firestore.SERVER_TIMESTAMP
                    })
                    
                    logger.info(f"Updated {country_id} ({iso_code}) -> {flag_url}")
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to update {country_id}: {e}")
            else:
                logger.warning(f"No flag found for {country_id} ({iso_code})")
        
        logger.info(f"Updated {updated_count} country flag URLs")
        return updated_count
    
    def generate_cloud_cdn_config(self) -> Dict:
        """Generate Cloud CDN configuration for the flag assets."""
        return {
            "name": "statlas-flag-assets-cdn",
            "description": "CDN for Statlas flag assets",
            "urlMap": {
                "defaultService": f"projects/{self.project_id}/global/backendBuckets/statlas-flag-assets-backend"
            },
            "hostRules": [{
                "hosts": ["cdn.statlas.app"],
                "pathMatcher": "flag-assets"
            }],
            "pathMatchers": [{
                "name": "flag-assets",
                "defaultService": f"projects/{self.project_id}/global/backendBuckets/statlas-flag-assets-backend",
                "pathRules": [{
                    "paths": ["/flags/*"],
                    "service": f"projects/{self.project_id}/global/backendBuckets/statlas-flag-assets-backend"
                }]
            }]
        }
    
    def print_setup_instructions(self):
        """Print manual setup instructions for Cloud CDN and domain configuration."""
        logger.info("\n" + "="*80)
        logger.info("MANUAL SETUP INSTRUCTIONS")
        logger.info("="*80)
        
        print(f"""
🔧 GOOGLE CLOUD CDN SETUP:

1. Create Backend Bucket:
   gcloud compute backend-buckets create statlas-flag-assets-backend \\
     --gcs-bucket-name={self.bucket_name} \\
     --project={self.project_id}

2. Create URL Map:
   gcloud compute url-maps create statlas-flag-assets-urlmap \\
     --default-backend-bucket=statlas-flag-assets-backend \\
     --project={self.project_id}

3. Create SSL Certificate:
   gcloud compute ssl-certificates create statlas-app-ssl-cert \\
     --domains=cdn.statlas.app \\
     --global \\
     --project={self.project_id}

4. Create HTTPS Load Balancer:
   gcloud compute target-https-proxies create statlas-flag-assets-proxy \\
     --url-map=statlas-flag-assets-urlmap \\
     --ssl-certificates=statlas-app-ssl-cert \\
     --project={self.project_id}

5. Create Global Forwarding Rule:
   gcloud compute forwarding-rules create statlas-flag-assets-forwarding-rule \\
     --global \\
     --target-https-proxy=statlas-flag-assets-proxy \\
     --ports=443 \\
     --project={self.project_id}

🌐 DOMAIN CONFIGURATION (statlas.app):

1. Get Load Balancer IP:
   gcloud compute forwarding-rules describe statlas-flag-assets-forwarding-rule \\
     --global --project={self.project_id} --format="value(IPAddress)"

2. Configure DNS Records:
   - A Record: cdn.statlas.app -> [LOAD_BALANCER_IP]
   - CNAME Record: www.statlas.app -> statlas.app
   - A Record: statlas.app -> [YOUR_WEB_APP_IP]

3. Verify SSL Certificate:
   gcloud compute ssl-certificates describe statlas-app-ssl-cert \\
     --global --project={self.project_id}

📋 VERIFICATION:

1. Test flag URL: https://cdn.statlas.app/flags/us.svg
2. Check CDN headers: curl -I https://cdn.statlas.app/flags/us.svg
3. Verify country flag URLs in Firestore

🚀 DEPLOYMENT COMPLETE!
        """)


def main():
    """Main CLI interface."""
    if not DEPENDENCIES_AVAILABLE:
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Setup flag assets for Statlas platform",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--project-id", default="statlas-467715",
                       help="Google Cloud project ID")
    parser.add_argument("--bucket-name", default="statlas-flag-assets",
                       help="Cloud Storage bucket name")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--skip-upload", action="store_true",
                       help="Skip file upload (useful for testing)")
    parser.add_argument("--skip-firestore", action="store_true",
                       help="Skip Firestore updates")
    
    args = parser.parse_args()
    
    try:
        manager = FlagAssetManager(args.project_id, args.bucket_name)
        
        # Step 1: Create storage bucket
        logger.info("Step 1: Creating storage bucket...")
        if not manager.create_storage_bucket(dry_run=args.dry_run):
            logger.error("Failed to create storage bucket")
            sys.exit(1)
        
        # Step 2: Upload flag assets
        uploaded_flags = {}
        if not args.skip_upload:
            logger.info("Step 2: Uploading flag assets...")
            uploaded_flags = manager.upload_flag_assets(dry_run=args.dry_run)
        else:
            logger.info("Step 2: Skipped (--skip-upload)")
        
        # Step 3: Update country flag URLs
        if not args.skip_firestore and uploaded_flags:
            logger.info("Step 3: Updating country flag URLs...")
            updated_count = manager.update_country_flag_urls(uploaded_flags, dry_run=args.dry_run)
            logger.info(f"Updated {updated_count} countries")
        else:
            logger.info("Step 3: Skipped (--skip-firestore or no uploads)")
        
        # Step 4: Print manual setup instructions
        logger.info("Step 4: Generating setup instructions...")
        manager.print_setup_instructions()
        
        logger.info("Flag asset setup complete!")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
