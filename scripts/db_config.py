# Firestore configuration for city import
# Update these values with your actual Firestore project details

import os

# Option 1: Service account key file
SERVICE_ACCOUNT_KEY_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'path/to/serviceAccountKey.json')

# Option 2: Project ID (for default credentials)
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'statlas-467715')

# Option 3: Use environment variable for service account JSON
SERVICE_ACCOUNT_JSON = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', None)

# Collection name for cities
CITIES_COLLECTION = 'cities'

# Database name (Firestore database)
DATABASE_NAME = 'statlas-content'

# Batch size for Firestore writes
BATCH_SIZE = 100  # Reduced from 500 to prevent hanging, Firestore allows up to 500 operations per batch

# ID generation strategy
# Options: 'name', 'uuid', 'name_population', 'custom'
ID_STRATEGY = 'name'

# Custom ID prefix (if using custom strategy)
CUSTOM_ID_PREFIX = 'city_'

# Import options
IMPORT_BOUNDARIES = True  # Set to False to skip boundary import if there are issues
SKIP_INVALID_BOUNDARIES = True  # Skip cities with invalid boundaries instead of failing

# Test mode - set to True to import only first 10 cities for testing
TEST_MODE = False
MAX_CITIES_TEST = 10
