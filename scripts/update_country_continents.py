#!/usr/bin/env python3
"""
Update Continent Data for Countries

This script updates all countries in the Firestore database with their correct continent information.
It handles sovereign states, countries, and map units with comprehensive continent mapping.
"""

import argparse
import sys
from typing import Dict, Optional
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

class ContinentUpdater:
    """Updates continent information for countries in Firestore."""
    
    def __init__(self, project_id: str, database_id: str = "statlas-content"):
        """Initialize the continent updater.
        
        Args:
            project_id: Google Cloud project ID
            database_id: Firestore database ID
        """
        self.project_id = project_id
        self.database_id = database_id
        self.db = firestore.Client(project=project_id, database=database_id)
        
        # Comprehensive continent mapping based on ISO codes and country names
        self.continent_mapping = self._create_continent_mapping()
    
    def _create_continent_mapping(self) -> Dict[str, str]:
        """Create comprehensive continent mapping for countries."""
        return {
            # Africa
            "DZ": "Africa", "algeria": "Africa",
            "AO": "Africa", "angola": "Africa", 
            "BJ": "Africa", "benin": "Africa",
            "BW": "Africa", "botswana": "Africa",
            "BF": "Africa", "burkina_faso": "Africa",
            "BI": "Africa", "burundi": "Africa",
            "CM": "Africa", "cameroon": "Africa",
            "CV": "Africa", "cape_verde": "Africa",
            "CF": "Africa", "central_african_republic": "Africa",
            "TD": "Africa", "chad": "Africa",
            "KM": "Africa", "comoros": "Africa",
            "CG": "Africa", "congo": "Africa",
            "CD": "Africa", "democratic_republic_of_the_congo": "Africa",
            "DJ": "Africa", "djibouti": "Africa",
            "EG": "Africa", "egypt": "Africa",
            "GQ": "Africa", "equatorial_guinea": "Africa",
            "ER": "Africa", "eritrea": "Africa",
            "ET": "Africa", "ethiopia": "Africa",
            "GA": "Africa", "gabon": "Africa",
            "GM": "Africa", "gambia": "Africa",
            "GH": "Africa", "ghana": "Africa",
            "GN": "Africa", "guinea": "Africa",
            "GW": "Africa", "guinea_bissau": "Africa",
            "CI": "Africa", "ivory_coast": "Africa", "cote_d_ivoire": "Africa",
            "KE": "Africa", "kenya": "Africa",
            "LS": "Africa", "lesotho": "Africa",
            "LR": "Africa", "liberia": "Africa",
            "LY": "Africa", "libya": "Africa",
            "MG": "Africa", "madagascar": "Africa",
            "MW": "Africa", "malawi": "Africa",
            "ML": "Africa", "mali": "Africa",
            "MR": "Africa", "mauritania": "Africa",
            "MU": "Africa", "mauritius": "Africa",
            "MA": "Africa", "morocco": "Africa",
            "MZ": "Africa", "mozambique": "Africa",
            "NA": "Africa", "namibia": "Africa",
            "NE": "Africa", "niger": "Africa",
            "NG": "Africa", "nigeria": "Africa",
            "RW": "Africa", "rwanda": "Africa",
            "ST": "Africa", "sao_tome_and_principe": "Africa",
            "SN": "Africa", "senegal": "Africa",
            "SC": "Africa", "seychelles": "Africa",
            "SL": "Africa", "sierra_leone": "Africa",
            "SO": "Africa", "somalia": "Africa",
            "ZA": "Africa", "south_africa": "Africa",
            "SS": "Africa", "south_sudan": "Africa",
            "SD": "Africa", "sudan": "Africa",
            "SZ": "Africa", "swaziland": "Africa", "eswatini": "Africa",
            "TZ": "Africa", "tanzania": "Africa",
            "TG": "Africa", "togo": "Africa",
            "TN": "Africa", "tunisia": "Africa",
            "UG": "Africa", "uganda": "Africa",
            "ZM": "Africa", "zambia": "Africa",
            "ZW": "Africa", "zimbabwe": "Africa",
            
            # Asia
            "AF": "Asia", "afghanistan": "Asia",
            "AM": "Asia", "armenia": "Asia",
            "AZ": "Asia", "azerbaijan": "Asia",
            "BH": "Asia", "bahrain": "Asia",
            "BD": "Asia", "bangladesh": "Asia",
            "BT": "Asia", "bhutan": "Asia",
            "BN": "Asia", "brunei": "Asia",
            "KH": "Asia", "cambodia": "Asia",
            "CN": "Asia", "china": "Asia",
            "CY": "Asia", "cyprus": "Asia",  # Geographically in Asia
            "GE": "Asia", "georgia": "Asia",
            "IN": "Asia", "india": "Asia",
            "ID": "Asia", "indonesia": "Asia",
            "IR": "Asia", "iran": "Asia",
            "IQ": "Asia", "iraq": "Asia",
            "IL": "Asia", "israel": "Asia",
            "JP": "Asia", "japan": "Asia",
            "JO": "Asia", "jordan": "Asia",
            "KZ": "Asia", "kazakhstan": "Asia",
            "KW": "Asia", "kuwait": "Asia",
            "KG": "Asia", "kyrgyzstan": "Asia",
            "LA": "Asia", "laos": "Asia",
            "LB": "Asia", "lebanon": "Asia",
            "MY": "Asia", "malaysia": "Asia",
            "MV": "Asia", "maldives": "Asia",
            "MN": "Asia", "mongolia": "Asia",
            "MM": "Asia", "myanmar": "Asia", "burma": "Asia",
            "NP": "Asia", "nepal": "Asia",
            "KP": "Asia", "north_korea": "Asia",
            "OM": "Asia", "oman": "Asia",
            "PK": "Asia", "pakistan": "Asia",
            "PS": "Asia", "palestine": "Asia",
            "PH": "Asia", "philippines": "Asia",
            "QA": "Asia", "qatar": "Asia",
            "SA": "Asia", "saudi_arabia": "Asia",
            "SG": "Asia", "singapore": "Asia",
            "KR": "Asia", "south_korea": "Asia",
            "LK": "Asia", "sri_lanka": "Asia",
            "SY": "Asia", "syria": "Asia",
            "TW": "Asia", "taiwan": "Asia",
            "TJ": "Asia", "tajikistan": "Asia",
            "TH": "Asia", "thailand": "Asia",
            "TL": "Asia", "east_timor": "Asia", "timor_leste": "Asia",
            "TR": "Asia", "turkey": "Asia",  # Mostly in Asia
            "TM": "Asia", "turkmenistan": "Asia",
            "AE": "Asia", "united_arab_emirates": "Asia",
            "UZ": "Asia", "uzbekistan": "Asia",
            "VN": "Asia", "vietnam": "Asia",
            "YE": "Asia", "yemen": "Asia",
            
            # Europe
            "AL": "Europe", "albania": "Europe",
            "AD": "Europe", "andorra": "Europe",
            "AT": "Europe", "austria": "Europe",
            "BY": "Europe", "belarus": "Europe",
            "BE": "Europe", "belgium": "Europe",
            "BA": "Europe", "bosnia_and_herzegovina": "Europe",
            "BG": "Europe", "bulgaria": "Europe",
            "HR": "Europe", "croatia": "Europe",
            "CZ": "Europe", "czech_republic": "Europe", "czechia": "Europe",
            "DK": "Europe", "denmark": "Europe",
            "EE": "Europe", "estonia": "Europe",
            "FI": "Europe", "finland": "Europe",
            "FR": "Europe", "france": "Europe",
            "DE": "Europe", "germany": "Europe",
            "GR": "Europe", "greece": "Europe",
            "HU": "Europe", "hungary": "Europe",
            "IS": "Europe", "iceland": "Europe",
            "IE": "Europe", "ireland": "Europe",
            "IT": "Europe", "italy": "Europe",
            "XK": "Europe", "kosovo": "Europe",
            "LV": "Europe", "latvia": "Europe",
            "LI": "Europe", "liechtenstein": "Europe",
            "LT": "Europe", "lithuania": "Europe",
            "LU": "Europe", "luxembourg": "Europe",
            "MT": "Europe", "malta": "Europe",
            "MD": "Europe", "moldova": "Europe",
            "MC": "Europe", "monaco": "Europe",
            "ME": "Europe", "montenegro": "Europe",
            "NL": "Europe", "netherlands": "Europe",
            "MK": "Europe", "north_macedonia": "Europe", "macedonia": "Europe",
            "NO": "Europe", "norway": "Europe",
            "PL": "Europe", "poland": "Europe",
            "PT": "Europe", "portugal": "Europe",
            "RO": "Europe", "romania": "Europe",
            "RU": "Europe", "russia": "Europe",  # Mostly in Asia, but politically/culturally European
            "SM": "Europe", "san_marino": "Europe",
            "RS": "Europe", "serbia": "Europe",
            "SK": "Europe", "slovakia": "Europe",
            "SI": "Europe", "slovenia": "Europe",
            "ES": "Europe", "spain": "Europe",
            "SE": "Europe", "sweden": "Europe",
            "CH": "Europe", "switzerland": "Europe",
            "UA": "Europe", "ukraine": "Europe",
            "GB": "Europe", "united_kingdom": "Europe",
            "VA": "Europe", "vatican": "Europe", "vatican_city": "Europe",
            
            # North America
            "AG": "North America", "antigua_and_barbuda": "North America",
            "BS": "North America", "bahamas": "North America",
            "BB": "North America", "barbados": "North America",
            "BZ": "North America", "belize": "North America",
            "CA": "North America", "canada": "North America",
            "CR": "North America", "costa_rica": "North America",
            "CU": "North America", "cuba": "North America",
            "DM": "North America", "dominica": "North America",
            "DO": "North America", "dominican_republic": "North America",
            "SV": "North America", "el_salvador": "North America",
            "GD": "North America", "grenada": "North America",
            "GT": "North America", "guatemala": "North America",
            "HT": "North America", "haiti": "North America",
            "HN": "North America", "honduras": "North America",
            "JM": "North America", "jamaica": "North America",
            "MX": "North America", "mexico": "North America",
            "NI": "North America", "nicaragua": "North America",
            "PA": "North America", "panama": "North America",
            "KN": "North America", "saint_kitts_and_nevis": "North America",
            "LC": "North America", "saint_lucia": "North America",
            "VC": "North America", "saint_vincent_and_the_grenadines": "North America",
            "TT": "North America", "trinidad_and_tobago": "North America",
            "US": "North America", "united_states": "North America",
            
            # North American Territories
            "AI": "North America", "anguilla": "North America",
            "AW": "North America", "aruba": "North America",
            "BM": "North America", "bermuda": "North America",
            "VG": "North America", "british_virgin_islands": "North America",
            "KY": "North America", "cayman_islands": "North America",
            "CW": "North America", "curacao": "North America",
            "GL": "North America", "greenland": "North America",
            "GP": "North America", "guadeloupe": "North America",
            "MQ": "North America", "martinique": "North America",
            "MS": "North America", "montserrat": "North America",
            "PR": "North America", "puerto_rico": "North America",
            "BL": "North America", "saint_barthelemy": "North America",
            "MF": "North America", "saint_martin": "North America",
            "PM": "North America", "saint_pierre_and_miquelon": "North America",
            "SX": "North America", "sint_maarten": "North America",
            "TC": "North America", "turks_and_caicos_islands": "North America",
            "VI": "North America", "us_virgin_islands": "North America",
            
            # South America
            "AR": "South America", "argentina": "South America",
            "BO": "South America", "bolivia": "South America",
            "BR": "South America", "brazil": "South America",
            "CL": "South America", "chile": "South America",
            "CO": "South America", "colombia": "South America",
            "EC": "South America", "ecuador": "South America",
            "FK": "South America", "falkland_islands": "South America",
            "GF": "South America", "french_guiana": "South America",
            "GY": "South America", "guyana": "South America",
            "PY": "South America", "paraguay": "South America",
            "PE": "South America", "peru": "South America",
            "SR": "South America", "suriname": "South America",
            "UY": "South America", "uruguay": "South America",
            "VE": "South America", "venezuela": "South America",
            
            # Oceania
            "AU": "Oceania", "australia": "Oceania",
            "FJ": "Oceania", "fiji": "Oceania",
            "KI": "Oceania", "kiribati": "Oceania",
            "MH": "Oceania", "marshall_islands": "Oceania",
            "FM": "Oceania", "micronesia": "Oceania",
            "NR": "Oceania", "nauru": "Oceania",
            "NZ": "Oceania", "new_zealand": "Oceania",
            "PW": "Oceania", "palau": "Oceania",
            "PG": "Oceania", "papua_new_guinea": "Oceania",
            "WS": "Oceania", "samoa": "Oceania",
            "SB": "Oceania", "solomon_islands": "Oceania",
            "TO": "Oceania", "tonga": "Oceania",
            "TV": "Oceania", "tuvalu": "Oceania",
            "VU": "Oceania", "vanuatu": "Oceania",
            
            # Oceania Territories
            "AS": "Oceania", "american_samoa": "Oceania",
            "CK": "Oceania", "cook_islands": "Oceania",
            "PF": "Oceania", "french_polynesia": "Oceania",
            "GU": "Oceania", "guam": "Oceania",
            "NC": "Oceania", "new_caledonia": "Oceania",
            "NU": "Oceania", "niue": "Oceania",
            "NF": "Oceania", "norfolk_island": "Oceania",
            "MP": "Oceania", "northern_mariana_islands": "Oceania",
            "PN": "Oceania", "pitcairn": "Oceania",
            "TK": "Oceania", "tokelau": "Oceania",
            "WF": "Oceania", "wallis_and_futuna": "Oceania",
            
            # Antarctica
            "AQ": "Antarctica", "antarctica": "Antarctica",
            
            # Special cases and territories
            "akrotiri": "Asia",  # British base in Cyprus
            "dhekelia": "Asia",  # British base in Cyprus
            "hong_kong": "Asia",
            "macau": "Asia",
            "western_sahara": "Africa",
            "somaliland": "Africa",
        }
    
    def get_continent_for_country(self, country_data: dict) -> Optional[str]:
        """Determine the continent for a country based on various identifiers.
        
        Args:
            country_data: Country document data
            
        Returns:
            Continent name or None if not found
        """
        # Try ISO alpha-2 code first
        if country_data.get("iso_alpha2") and country_data["iso_alpha2"] != "-99":
            continent = self.continent_mapping.get(country_data["iso_alpha2"])
            if continent:
                return continent
        
        # Try ISO alpha-3 code
        if country_data.get("iso_alpha3") and country_data["iso_alpha3"] != "-99":
            continent = self.continent_mapping.get(country_data["iso_alpha3"])
            if continent:
                return continent
        
        # Try country ID (normalized name)
        if country_data.get("id"):
            continent = self.continent_mapping.get(country_data["id"])
            if continent:
                return continent
        
        # Try normalized name
        if country_data.get("name"):
            normalized_name = country_data["name"].lower().replace(" ", "_").replace("-", "_")
            continent = self.continent_mapping.get(normalized_name)
            if continent:
                return continent
        
        return None
    
    def update_collection_continents(self, collection_name: str, dry_run: bool = False) -> tuple[int, int]:
        """Update continent information for a collection.
        
        Args:
            collection_name: Name of the Firestore collection
            dry_run: If True, only show what would be updated
            
        Returns:
            Tuple of (updated_count, total_count)
        """
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Processing {collection_name} collection...")
        
        collection_ref = self.db.collection(collection_name)
        docs = collection_ref.where(filter=FieldFilter("is_active", "==", True)).get()
        
        updated_count = 0
        total_count = 0
        
        for doc in docs:
            total_count += 1
            data = doc.to_dict()
            
            # Skip if continent is already set
            if data.get("continent"):
                continue
            
            continent = self.get_continent_for_country(data)
            
            if continent:
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Updating {data.get('name', doc.id)} -> {continent}")
                
                if not dry_run:
                    doc.reference.update({"continent": continent})
                
                updated_count += 1
            else:
                logger.warning(f"Could not determine continent for: {data.get('name', doc.id)} (ID: {doc.id}, ISO2: {data.get('iso_alpha2')}, ISO3: {data.get('iso_alpha3')})")
        
        return updated_count, total_count
    
    def update_all_continents(self, dry_run: bool = False) -> None:
        """Update continent information for all geographic collections.
        
        Args:
            dry_run: If True, only show what would be updated
        """
        collections = ["sovereign_states", "countries", "map_units"]
        total_updated = 0
        total_processed = 0
        
        for collection_name in collections:
            try:
                updated, total = self.update_collection_continents(collection_name, dry_run)
                total_updated += updated
                total_processed += total
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}{collection_name}: {updated}/{total} records {'would be ' if dry_run else ''}updated")
            except Exception as e:
                logger.error(f"Error processing {collection_name}: {e}")
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Summary: {total_updated}/{total_processed} total records {'would be ' if dry_run else ''}updated")


def main():
    """Main function to run the continent updater."""
    parser = argparse.ArgumentParser(description="Update continent information for countries in Firestore")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID")
    parser.add_argument("--database-id", default="statlas-content", help="Firestore database ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--collection", choices=["sovereign_states", "countries", "map_units"], 
                       help="Update only a specific collection (default: all)")
    
    args = parser.parse_args()
    
    try:
        updater = ContinentUpdater(args.project_id, args.database_id)
        
        if args.collection:
            updated, total = updater.update_collection_continents(args.collection, args.dry_run)
            logger.info(f"{'[DRY RUN] ' if args.dry_run else ''}{args.collection}: {updated}/{total} records {'would be ' if args.dry_run else ''}updated")
        else:
            updater.update_all_continents(args.dry_run)
        
        logger.info("Continent update completed successfully!")
        
    except Exception as e:
        logger.error(f"Error updating continents: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
