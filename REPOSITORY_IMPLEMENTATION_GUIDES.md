# Repository Implementation Guides

## 🎯 **Per-Repository Implementation Plans**

This document provides specific implementation guidance for each Statlas service repository, designed to be used by engineers (human or AI) working on individual services.

---

## 📍 **statlas-core-service (CURRENT REPOSITORY)**

### **Repository Status**: ✅ Active Development
### **Database**: `statlas-core` (default)
### **Timeline**: 4 weeks (Phase 1)

### **Current State**
- ✅ Basic 1km grid system with UUID support
- ✅ Single resolution location tracking
- ✅ Python grid generation tools
- ❌ Multi-resolution support (1km/100m/10m)
- ❌ Boundary tagging system
- ❌ Collection partitioning

### **Phase 1 Implementation Tasks**

#### **Week 1: Multi-Resolution Data Structures**
```go
// TODO: Update main.go Square struct
type Square struct {
    ID                  string    `firestore:"id" json:"id"`
    Resolution          string    `firestore:"resolution" json:"resolution"` // "1km", "100m", "10m"
    MinLatitude         float64   `firestore:"min_latitude" json:"min_latitude"`
    MaxLatitude         float64   `firestore:"max_latitude" json:"max_latitude"`
    MinLongitude        float64   `firestore:"min_longitude" json:"min_longitude"`
    MaxLongitude        float64   `firestore:"max_longitude" json:"max_longitude"`
    Geohash             string    `firestore:"geohash" json:"geohash"`
    
    // NEW FIELDS
    BoundaryTags        []string  `firestore:"boundary_tags" json:"boundary_tags"`
    ParentSquareID      *string   `firestore:"parent_square_id,omitempty" json:"parent_square_id,omitempty"`
    ChildSquareIDs      []string  `firestore:"child_square_ids,omitempty" json:"child_square_ids,omitempty"`
    UrbanClassification string    `firestore:"urban_classification" json:"urban_classification"`
    
    CreatedAt           time.Time `firestore:"created_at" json:"created_at"`
}

// TODO: Add resolution-based collection routing
func getSquareCollection(resolution string) string {
    switch resolution {
    case "1km":
        return "squares_1km"
    case "100m":
        // Partition by geohash prefix for performance
        return fmt.Sprintf("squares_100m_%s", geohashPrefix)
    case "10m":
        return "squares_10m_landmarks"
    default:
        return "squares_1km"
    }
}
```

**Deliverables:**
- [ ] Update Square struct in main.go
- [ ] Create collection partitioning logic
- [ ] Update all handlers to support resolution field
- [ ] Create database migration script for existing data

#### **Week 2: Enhanced Grid Generation**
```python
# TODO: Update generate_test_grid.py
class MultiResolutionGridGenerator:
    def __init__(self, target_size_meters: int = 1000, geohash_precision: int = 8):
        self.target_size = target_size_meters
        self.geohash_precision = self._get_optimal_precision()
    
    def _get_optimal_precision(self):
        if self.target_size <= 100:
            return 10  # ~19m x 38m
        elif self.target_size <= 500:
            return 9   # ~76m x 153m  
        else:
            return 8   # ~610m x 1220m

    def generate_multi_resolution_grid(self, output_filename: str, 
                                     resolution: str = "1km",
                                     urban_areas: List[Dict] = None):
        # Implementation for generating different resolution grids
        pass

# TODO: Create urban area definitions
URBAN_AREAS = [
    {
        "name": "Manhattan",
        "bounds": {"min_lat": 40.7000, "max_lat": 40.8800, 
                  "min_lon": -74.0200, "max_lon": -73.9100},
        "resolution": "100m",
        "tags": ["usa", "new_york", "manhattan"]
    },
    {
        "name": "Central Paris", 
        "bounds": {"min_lat": 48.8155, "max_lat": 48.9021,
                  "min_lon": 2.2241, "max_lon": 2.4697},
        "resolution": "100m",
        "tags": ["france", "paris", "city_center"]
    }
]
```

**Deliverables:**
- [ ] Enhance generate_test_grid.py for 100m resolution
- [ ] Generate 100m test grids for NYC, Paris, London
- [ ] Create urban area configuration system
- [ ] Update import_test_grid.py for partitioned collections

#### **Week 3: Resolution-Based Routing**
```go
// TODO: Implement resolution determination
func determineResolution(lat, lon float64) string {
    // Hardcoded rules for Phase 1
    // Phase 2 will use boundary system
    
    urbanAreas := []UrbanArea{
        {
            Name: "Manhattan",
            Bounds: Bounds{MinLat: 40.7000, MaxLat: 40.8800, MinLon: -74.0200, MaxLon: -73.9100},
            Resolution: "100m",
            Tags: []string{"usa", "new_york", "manhattan"},
        },
        {
            Name: "Central Paris",
            Bounds: Bounds{MinLat: 48.8155, MaxLat: 48.9021, MinLon: 2.2241, MaxLon: 2.4697},
            Resolution: "100m", 
            Tags: []string{"france", "paris", "city_center"},
        },
    }
    
    for _, area := range urbanAreas {
        if pointInBounds(lat, lon, area.Bounds) {
            return area.Resolution
        }
    }
    
    return "1km" // Default rural resolution
}

// TODO: Implement resolution-specific square lookup
func findSquareByResolution(ctx context.Context, lat, lon float64, resolution string) (*Square, error) {
    switch resolution {
    case "100m":
        return findSquare100m(ctx, lat, lon)
    case "1km":
        return findSquare1km(ctx, lat, lon)
    default:
        return findSquare1km(ctx, lat, lon)
    }
}

// TODO: Update location handler
func updateLocationHandler(w http.ResponseWriter, r *http.Request) {
    var req LocationRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    
    ctx := context.Background()
    
    // NEW: Determine resolution based on location
    resolution := determineResolution(req.Latitude, req.Longitude)
    
    // NEW: Find square using appropriate resolution
    square, err := findSquareByResolution(ctx, req.Latitude, req.Longitude, resolution)
    if err != nil {
        http.Error(w, fmt.Sprintf("Failed to find square: %v", err), http.StatusInternalServerError)
        return
    }
    
    // Record visit with resolution info
    visit := UserSquareVisit{
        ID:         fmt.Sprintf("%s_%s_%d", req.UserID, square.ID, time.Now().Unix()),
        UserID:     req.UserID,
        SquareID:   square.ID,
        Resolution: square.Resolution, // NEW FIELD
        Latitude:   req.Latitude,
        Longitude:  req.Longitude,
        Timestamp:  time.Now(),
    }
    
    // Store visit
    _, err = firestoreClient.Collection("user_square_visits").Doc(visit.ID).Set(ctx, visit)
    if err != nil {
        http.Error(w, fmt.Sprintf("Failed to store visit: %v", err), http.StatusInternalServerError)
        return
    }
    
    // NEW: Enhanced response with resolution info
    response := LocationUpdateResponse{
        SquareID:     square.ID,
        Resolution:   square.Resolution,
        BoundaryTags: square.BoundaryTags,
        IsNewVisit:   true, // TODO: Implement proper new visit detection
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}
```

**Deliverables:**
- [ ] Implement hardcoded resolution determination
- [ ] Create findSquare1km() and findSquare100m() functions
- [ ] Update location handler for multi-resolution
- [ ] Add resolution info to all API responses

#### **Week 4: Integration & Testing**
```go
// TODO: Add basic boundary tagging
func generateBoundaryTags(lat, lon float64) []string {
    tags := []string{}
    
    // Basic country detection (hardcoded for Phase 1)
    if lat >= 25.0 && lat <= 49.0 && lon >= -125.0 && lon <= -66.0 {
        tags = append(tags, "usa")
        
        // Basic state detection for major states
        if lat >= 40.5 && lat <= 45.0 && lon >= -79.8 && lon <= -71.8 {
            tags = append(tags, "new_york")
            
            // Basic city detection
            if lat >= 40.4774 && lat <= 40.9176 && lon >= -74.2591 && lon <= -73.7004 {
                tags = append(tags, "new_york_city")
                
                // Basic borough detection
                if lat >= 40.7000 && lat <= 40.8800 && lon >= -74.0200 && lon <= -73.9100 {
                    tags = append(tags, "manhattan")
                }
            }
        }
    } else if lat >= 41.0 && lat <= 51.0 && lon >= -5.0 && lon <= 10.0 {
        tags = append(tags, "france")
        
        if lat >= 48.8155 && lat <= 48.9021 && lon >= 2.2241 && lon <= 2.4697 {
            tags = append(tags, "paris")
        }
    }
    
    return tags
}

// TODO: Update user statistics for multi-resolution
func getUserStatsHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    userID := vars["user_id"]
    
    ctx := context.Background()
    
    // Query visits across all collections
    var totalVisits int
    var resolutionBreakdown map[string]int = make(map[string]int)
    
    // Count 1km visits
    iter1km := firestoreClient.Collection("user_square_visits").
        Where("user_id", "==", userID).
        Where("resolution", "==", "1km").Documents(ctx)
    count1km := countDocuments(iter1km)
    resolutionBreakdown["1km"] = count1km
    totalVisits += count1km
    
    // Count 100m visits  
    iter100m := firestoreClient.Collection("user_square_visits").
        Where("user_id", "==", userID).
        Where("resolution", "==", "100m").Documents(ctx)
    count100m := countDocuments(iter100m)
    resolutionBreakdown["100m"] = count100m
    totalVisits += count100m
    
    // Calculate coverage percentage (approximate)
    coveragePercentage := float64(totalVisits) / float64(EARTH_SQUARES_APPROX) * 100
    
    response := UserStatsResponse{
        UserID:              userID,
        TotalVisitedSquares: totalVisits,
        ResolutionBreakdown: resolutionBreakdown, // NEW FIELD
        CoveragePercentage:  coveragePercentage,
        // TODO: Add boundary-based statistics in Phase 2
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}
```

**Deliverables:**
- [ ] Add basic boundary tagging (hardcoded geographic regions)
- [ ] Update user statistics for multi-resolution tracking
- [ ] Performance testing with partitioned collections
- [ ] Update API documentation and README

### **Success Criteria for Phase 1**
- [ ] Location updates return resolution info ("1km" or "100m")
- [ ] NYC coordinates return 100m squares, rural coordinates return 1km
- [ ] Collections properly partitioned (squares_1km/, squares_100m_XX/)
- [ ] All existing functionality preserved during migration
- [ ] Performance: <200ms for location updates

---

## 🗺️ **statlas-maps-service (NEW REPOSITORY)**

### **Repository Status**: 📋 To Be Created
### **Database**: `statlas-maps`
### **Timeline**: 3 weeks (Phase 2 - High Priority)

### **Repository Creation**
```bash
# Create new repository
git clone --template statlas-core-service statlas-maps-service
cd statlas-maps-service

# Update service configuration
sed -i 's/statlas-core-service/statlas-maps-service/g' Dockerfile
sed -i 's/8082/8084/g' main.go  # Different port
sed -i 's/statlas-core/statlas-maps/g' main.go  # Different database
```

### **Service Structure**
```
statlas-maps-service/
├── cmd/
│   └── server/
│       └── main.go              # Main server entry point
├── internal/
│   ├── models/                  # Data models (MapConfig, CachedPlace, etc.)
│   │   ├── map_config.go
│   │   ├── geocoding.go
│   │   ├── places.go
│   │   └── routing.go
│   ├── handlers/                # HTTP handlers
│   │   ├── geocoding.go         # Geocoding endpoints
│   │   ├── places.go            # Places API endpoints
│   │   ├── routing.go           # Directions endpoints
│   │   ├── config.go            # Platform configuration
│   │   └── preferences.go       # User preferences
│   ├── services/                # Business logic
│   │   ├── google_maps.go       # Google Maps Platform client
│   │   ├── caching.go           # Caching strategies
│   │   ├── cost_optimizer.go    # Cost optimization
│   │   └── usage_tracker.go     # API usage monitoring
│   └── middleware/              # HTTP middleware
│       ├── auth.go              # Service authentication
│       ├── rate_limit.go        # Rate limiting
│       └── monitoring.go        # Request monitoring
├── pkg/
│   └── gmaps/                   # Google Maps Platform SDK wrapper
│       ├── client.go
│       ├── geocoding.go
│       ├── places.go
│       └── directions.go
├── configs/
│   ├── map_styles/              # Custom map styling configs
│   └── platform_configs/        # Platform-specific settings
├── Dockerfile
├── Makefile
├── go.mod
├── go.sum
└── README.md
```

### **Week 1: Google Maps Platform Integration**

#### **Core Models**
```go
// TODO: Create internal/models/map_config.go
type MapConfiguration struct {
    ConfigID            string            `firestore:"config_id" json:"config_id"`
    Platform            string            `firestore:"platform" json:"platform"` // "web", "ios", "android"
    MapStyle            string            `firestore:"map_style" json:"map_style"`
    DefaultZoom         int               `firestore:"default_zoom" json:"default_zoom"`
    CenterCoordinates   Coordinates       `firestore:"center_coordinates" json:"center_coordinates"`
    UIControls          map[string]bool   `firestore:"ui_controls" json:"ui_controls"`
    StylingOptions      map[string]interface{} `firestore:"styling_options" json:"styling_options"`
    IsActive            bool              `firestore:"is_active" json:"is_active"`
    UpdatedAt           time.Time         `firestore:"updated_at" json:"updated_at"`
}

// TODO: Create internal/models/geocoding.go
type CachedGeocoding struct {
    CacheID       string            `firestore:"cache_id" json:"cache_id"`
    InputQuery    string            `firestore:"input_query" json:"input_query"`
    Result        GeocodingResult   `firestore:"result" json:"result"`
    CachedAt      time.Time         `firestore:"cached_at" json:"cached_at"`
    ExpiresAt     time.Time         `firestore:"expires_at" json:"expires_at"`
    HitCount      int               `firestore:"hit_count" json:"hit_count"`
    LastAccessed  time.Time         `firestore:"last_accessed" json:"last_accessed"`
}
```

#### **Google Maps Client**
```go
// TODO: Create pkg/gmaps/client.go
type GoogleMapsClient struct {
    webAPIKey     string
    iosAPIKey     string
    androidAPIKey string
    httpClient    *http.Client
    rateLimiter   *rate.Limiter
}

func NewGoogleMapsClient(webKey, iosKey, androidKey string) *GoogleMapsClient {
    return &GoogleMapsClient{
        webAPIKey:     webKey,
        iosAPIKey:     iosKey,
        androidAPIKey: androidKey,
        httpClient:    &http.Client{Timeout: 10 * time.Second},
        rateLimiter:   rate.NewLimiter(rate.Limit(100), 10), // 100 requests/second
    }
}
```

#### **Caching Service**
```go
// TODO: Create internal/services/caching.go
type CachingService struct {
    firestoreClient *firestore.Client
    memoryCache     *sync.Map // In-memory cache
}

func (c *CachingService) GetGeocoding(query string) (*GeocodingResult, error) {
    // Check memory cache first
    if cached, exists := c.memoryCache.Load(query); exists {
        return cached.(*GeocodingResult), nil
    }
    
    // Check database cache
    result, err := c.getGeocodingFromDB(query)
    if err == nil {
        c.memoryCache.Store(query, result)
        return result, nil
    }
    
    // Cache miss - will need to call Google Maps API
    return nil, errors.New("cache miss")
}
```

**Week 1 Deliverables:**
- [ ] Create statlas-maps-service repository
- [ ] Set up Go service structure with Google Maps Platform integration
- [ ] Implement basic geocoding with caching
- [ ] Deploy to Cloud Run with API key management
- [ ] Create statlas-maps Firestore database

### **Week 2: Cost Optimization & Advanced Features**

#### **Places API Integration**
```go
// TODO: Create internal/handlers/places.go
func (h *PlacesHandler) GetPlaceDetails(w http.ResponseWriter, r *http.Request) {
    placeID := mux.Vars(r)["place_id"]
    
    // Check cache first
    cached, err := h.cachingService.GetPlace(placeID)
    if err == nil {
        w.Header().Set("X-Cache", "HIT")
        json.NewEncoder(w).Encode(cached)
        return
    }
    
    // Call Google Places API
    details, err := h.googleMapsClient.GetPlaceDetails(placeID)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    // Cache the result
    h.cachingService.SetPlace(placeID, details, 7*24*time.Hour) // 7 days
    
    w.Header().Set("X-Cache", "MISS")
    json.NewEncoder(w).Encode(details)
}
```

#### **Cost Optimization**
```go
// TODO: Create internal/services/cost_optimizer.go
type CostOptimizer struct {
    usageTracker *UsageTracker
    cacheService *CachingService
}

func (c *CostOptimizer) OptimizeRequest(requestType string, params map[string]interface{}) (*OptimizationResult, error) {
    // Check if we can batch this request
    if c.canBatch(requestType) {
        return c.suggestBatching(requestType, params)
    }
    
    // Check cache hit probability
    cacheHitProb := c.calculateCacheHitProbability(requestType, params)
    if cacheHitProb > 0.8 {
        return &OptimizationResult{
            Recommendation: "use_cache",
            EstimatedCost:  0.0,
        }, nil
    }
    
    return c.calculateDirectAPICall(requestType, params)
}
```

**Week 2 Deliverables:**
- [ ] Implement Places API with intelligent caching
- [ ] Add routing/directions API with cache expiry
- [ ] Implement cost optimization algorithms
- [ ] Add API usage monitoring and alerting
- [ ] Create request batching system

### **Week 3: Platform Integration & Frontend APIs**

#### **Platform Configuration**
```go
// TODO: Create internal/handlers/config.go
func (h *ConfigHandler) GetPlatformConfig(w http.ResponseWriter, r *http.Request) {
    platform := r.URL.Query().Get("platform")
    userID := r.Header.Get("X-User-ID")
    
    config, err := h.configService.GetConfigForPlatform(platform, userID)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    // Add user preferences
    preferences, _ := h.preferencesService.GetUserPreferences(userID)
    if preferences != nil {
        config.ApplyUserPreferences(preferences)
    }
    
    json.NewEncoder(w).Encode(config)
}
```

#### **Core Service Integration**
```go
// TODO: Create integration endpoint for Core service
func (h *IntegrationHandler) EnrichLocation(w http.ResponseWriter, r *http.Request) {
    var req LocationEnrichmentRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request", http.StatusBadRequest)
        return
    }
    
    // Parallel enrichment calls
    var wg sync.WaitGroup
    var address string
    var places []Place
    var routing *RoutingInfo
    
    wg.Add(3)
    
    // Reverse geocode
    go func() {
        defer wg.Done()
        address, _ = h.geocodingService.ReverseGeocode(req.Latitude, req.Longitude)
    }()
    
    // Find nearby places
    go func() {
        defer wg.Done()
        places, _ = h.placesService.FindNearby(req.Latitude, req.Longitude, 500)
    }()
    
    // Get routing context
    go func() {
        defer wg.Done()
        routing, _ = h.routingService.GetRoutingContext(req.Latitude, req.Longitude)
    }()
    
    wg.Wait()
    
    response := LocationEnrichmentResponse{
        Address:     address,
        NearbyPOIs:  places,
        RoutingInfo: routing,
    }
    
    json.NewEncoder(w).Encode(response)
}
```

**Week 3 Deliverables:**
- [ ] Implement platform-specific configuration endpoints
- [ ] Add user map preferences and customization
- [ ] Create Core service integration endpoints
- [ ] Add map styling and theming configuration
- [ ] Performance monitoring and optimization

### **Success Criteria**
✅ **Performance**: 80%+ cache hit rate for geocoding requests  
✅ **Speed**: <100ms average response time for cached requests  
✅ **Cost**: <$0.15/user/month for Maps API usage  
✅ **Integration**: Seamless Core service location enrichment  
✅ **Platform Support**: Web, iOS, Android configuration APIs  
✅ **Monitoring**: Complete API usage tracking and cost optimization

---

## 📚 **statlas-content-service (NEW REPOSITORY)**

### **Repository Status**: 📋 To Be Created
### **Database**: `statlas-content`
### **Timeline**: 6 weeks (Phase 2)

### **Repository Setup**
```bash
# Create new repository
git clone --template statlas-core-service statlas-content-service
cd statlas-content-service

# Update service configuration
sed -i 's/statlas-core-service/statlas-content-service/g' Dockerfile
sed -i 's/8082/8083/g' main.go  # Different port
sed -i 's/statlas-core/statlas-content/g' main.go  # Different database
```

### **Service Structure**
```
statlas-content-service/
├── cmd/
│   └── server/
│       └── main.go              # Main server entry point
├── internal/
│   ├── models/                  # Data models (Country, Landmark, Boundary)
│   ├── handlers/                # HTTP handlers
│   ├── services/                # Business logic
│   ├── repository/              # Firestore operations
│   └── utils/                   # Utility functions
├── data/                        # Reference data files
│   ├── countries.json           # Country data with flags
│   ├── landmarks.json           # Major landmarks
│   └── boundaries.json          # Boundary polygons
├── scripts/                     # Data import scripts
│   ├── import_countries.py      # Import country data
│   ├── import_landmarks.py      # Import landmarks
│   └── import_boundaries.py     # Import boundary polygons
├── Dockerfile                   # Container configuration
├── Makefile                     # Development tasks
└── README.md                    # Service documentation
```

### **Phase 2 Implementation Tasks**

#### **Week 1-2: Service Foundation**
```go
// TODO: Create main.go for content service
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    
    "cloud.google.com/go/firestore"
    "github.com/gorilla/mux"
)

// TODO: Define core data models
type Country struct {
    ID          string  `firestore:"id" json:"id"`
    Name        string  `firestore:"name" json:"name"`
    ISOCode     string  `firestore:"iso_code" json:"iso_code"`
    FlagURL     string  `firestore:"flag_url" json:"flag_url"`
    Bounds      Bounds  `firestore:"bounds" json:"bounds"`
    Capital     string  `firestore:"capital" json:"capital"`
    Population  int64   `firestore:"population" json:"population"`
    AreaKm2     float64 `firestore:"area_km2" json:"area_km2"`
    Currency    string  `firestore:"currency" json:"currency"`
    Languages   []string `firestore:"languages" json:"languages"`
}

type Landmark struct {
    ID                    string     `firestore:"id" json:"id"`
    Name                  string     `firestore:"name" json:"name"`
    Type                  string     `firestore:"type" json:"type"`
    Coordinates           LatLng     `firestore:"coordinates" json:"coordinates"`
    CountryID             string     `firestore:"country_id" json:"country_id"`
    StateID               string     `firestore:"state_id,omitempty" json:"state_id,omitempty"`
    CityID                string     `firestore:"city_id,omitempty" json:"city_id,omitempty"`
    Description           string     `firestore:"description" json:"description"`
    Images                []string   `firestore:"images" json:"images"`
    AchievementID         string     `firestore:"achievement_id,omitempty" json:"achievement_id,omitempty"`
    PrecisionRadiusMeters float64    `firestore:"precision_radius_meters" json:"precision_radius_meters"`
    WikipediaURL          string     `firestore:"wikipedia_url,omitempty" json:"wikipedia_url,omitempty"`
    OfficialWebsite       string     `firestore:"official_website,omitempty" json:"official_website,omitempty"`
}

// TODO: Implement basic CRUD handlers
func getCountriesHandler(w http.ResponseWriter, r *http.Request) {
    ctx := context.Background()
    
    iter := firestoreClient.Collection("countries").Documents(ctx)
    var countries []Country
    
    for {
        doc, err := iter.Next()
        if err != nil {
            break
        }
        
        var country Country
        if err := doc.DataTo(&country); err != nil {
            continue
        }
        countries = append(countries, country)
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(countries)
}

func main() {
    ctx := context.Background()
    
    // Initialize Firestore with content database
    projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
    var err error
    firestoreClient, err = firestore.NewClient(ctx, projectID, 
        option.WithDatabase("statlas-content"))
    if err != nil {
        log.Fatalf("Failed to create Firestore client: %v", err)
    }
    defer firestoreClient.Close()
    
    // Create router
    router := mux.NewRouter()
    
    // Health check
    router.HandleFunc("/health", healthHandler).Methods("GET")
    
    // Core endpoints
    router.HandleFunc("/countries", getCountriesHandler).Methods("GET")
    router.HandleFunc("/countries/{id}", getCountryHandler).Methods("GET")
    router.HandleFunc("/landmarks", getLandmarksHandler).Methods("GET")
    router.HandleFunc("/landmarks/{id}", getLandmarkHandler).Methods("GET")
    router.HandleFunc("/boundaries/bulk", getBoundariesBulkHandler).Methods("GET")
    
    // Start server
    port := os.Getenv("PORT")
    if port == "" {
        port = "8083"
    }
    
    log.Printf("Content service starting on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, router))
}
```

**Deliverables:**
- [ ] Create statlas-content-service repository
- [ ] Set up Go service structure with Firestore integration
- [ ] Implement basic CRUD endpoints for countries/landmarks
- [ ] Deploy to Cloud Run with health checks
- [ ] Create statlas-content Firestore database

#### **Week 3-4: Reference Data Population**
```python
# TODO: Create data import scripts
# scripts/import_countries.py
import json
import requests
from google.cloud import firestore

def import_countries():
    db = firestore.Client(database='statlas-content')
    
    # Country data with flags from reliable source
    countries_data = [
        {
            "id": "usa",
            "name": "United States",
            "iso_code": "US", 
            "flag_url": "https://cdn.statlas.com/flags/usa.svg",
            "bounds": {
                "min_lat": 25.0, "max_lat": 49.0,
                "min_lon": -125.0, "max_lon": -66.0
            },
            "capital": "Washington, D.C.",
            "population": 331000000,
            "area_km2": 9833517,
            "currency": "USD",
            "languages": ["en"]
        },
        # Add more countries...
    ]
    
    batch = db.batch()
    for country in countries_data:
        doc_ref = db.collection('countries').document(country['id'])
        batch.set(doc_ref, country)
    
    batch.commit()
    print(f"Imported {len(countries_data)} countries")

# scripts/import_landmarks.py
def import_landmarks():
    db = firestore.Client(database='statlas-content')
    
    landmarks_data = [
        {
            "id": "statue_of_liberty",
            "name": "Statue of Liberty",
            "type": "monument",
            "coordinates": {"lat": 40.6892, "lon": -74.0445},
            "country_id": "usa",
            "state_id": "new_york",
            "city_id": "new_york_city",
            "description": "A symbol of freedom and democracy...",
            "images": [
                "https://cdn.statlas.com/landmarks/statue_of_liberty_1.jpg",
                "https://cdn.statlas.com/landmarks/statue_of_liberty_2.jpg"
            ],
            "achievement_id": "statue_of_liberty_visitor",
            "precision_radius_meters": 30,
            "wikipedia_url": "https://en.wikipedia.org/wiki/Statue_of_Liberty",
            "official_website": "https://www.nps.gov/stli/"
        },
        # Add more landmarks...
    ]
    
    batch = db.batch()
    for landmark in landmarks_data:
        doc_ref = db.collection('landmarks').document(landmark['id'])
        batch.set(doc_ref, landmark)
    
    batch.commit()
    print(f"Imported {len(landmarks_data)} landmarks")
```

**Deliverables:**
- [ ] Import comprehensive country data with flags and boundaries
- [ ] Add major world landmarks and points of interest
- [ ] Create boundary polygon definitions for major regions
- [ ] Set up CDN for images and static assets (Cloud Storage + CDN)

#### **Week 5-6: API Development & Integration**
```go
// TODO: Implement advanced search and filtering
func searchLandmarksHandler(w http.ResponseWriter, r *http.Request) {
    ctx := context.Background()
    
    // Parse query parameters
    query := r.URL.Query().Get("q")
    country := r.URL.Query().Get("country")
    landmarkType := r.URL.Query().Get("type")
    
    // Build Firestore query
    collection := firestoreClient.Collection("landmarks")
    
    if country != "" {
        collection = collection.Where("country_id", "==", country)
    }
    if landmarkType != "" {
        collection = collection.Where("type", "==", landmarkType)
    }
    
    iter := collection.Documents(ctx)
    var landmarks []Landmark
    
    for {
        doc, err := iter.Next()
        if err != nil {
            break
        }
        
        var landmark Landmark
        if err := doc.DataTo(&landmark); err != nil {
            continue
        }
        
        // Text search filtering (simple implementation)
        if query != "" && !strings.Contains(strings.ToLower(landmark.Name), strings.ToLower(query)) {
            continue
        }
        
        landmarks = append(landmarks, landmark)
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(landmarks)
}

// TODO: Implement bulk boundary lookup for core service integration
func getBoundariesBulkHandler(w http.ResponseWriter, r *http.Request) {
    ctx := context.Background()
    
    // Parse boundary IDs from query parameter
    idsParam := r.URL.Query().Get("ids")
    if idsParam == "" {
        http.Error(w, "Missing ids parameter", http.StatusBadRequest)
        return
    }
    
    ids := strings.Split(idsParam, ",")
    var boundaries []BoundaryInfo
    
    for _, id := range ids {
        doc, err := firestoreClient.Collection("boundaries").Doc(id).Get(ctx)
        if err != nil {
            continue
        }
        
        var boundary BoundaryInfo
        if err := doc.DataTo(&boundary); err != nil {
            continue
        }
        
        boundaries = append(boundaries, boundary)
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(boundaries)
}
```

**Deliverables:**
- [ ] Implement search and filtering endpoints
- [ ] Add bulk lookup APIs for boundary enrichment
- [ ] Create admin endpoints for content management
- [ ] Integration testing with core service for boundary resolution

### **Success Criteria for Phase 2**
- [ ] Content service deployed and accessible
- [ ] Comprehensive country and landmark data available
- [ ] Core service can enrich responses with boundary information
- [ ] Search and filtering work correctly
- [ ] Performance: <100ms for reference data lookups

---

## 👥 **statlas-social-service (NEW REPOSITORY)**

### **Repository Status**: 📋 To Be Created  
### **Database**: `statlas-social`
### **Timeline**: 8 weeks (Phase 3)

### **Phase 3 Implementation Tasks**

#### **Week 1-2: Service Foundation & Social Connections**
```go
// TODO: Create social service structure
package main

type SocialConnection struct {
    ConnectionID     string    `firestore:"connection_id" json:"connection_id"`
    UserID          string    `firestore:"user_id" json:"user_id"`
    FriendID        string    `firestore:"friend_id" json:"friend_id"`
    Status          string    `firestore:"status" json:"status"` // "pending", "accepted", "blocked"
    InitiatedBy     string    `firestore:"initiated_by" json:"initiated_by"`
    ConnectedAt     time.Time `firestore:"connected_at" json:"connected_at"`
    ConnectionType  string    `firestore:"connection_type" json:"connection_type"` // "friend", "follower"
}

// TODO: Implement friend request system
func sendFriendRequestHandler(w http.ResponseWriter, r *http.Request) {
    // Implementation for sending friend requests
}

func acceptFriendRequestHandler(w http.ResponseWriter, r *http.Request) {
    // Implementation for accepting friend requests
}

func getFriendsHandler(w http.ResponseWriter, r *http.Request) {
    // Implementation for getting user's friends list
}
```

#### **Week 3-4: Activity Feed System**
```go
// TODO: Implement activity feed generation
type ActivityFeedItem struct {
    ActivityID   string                 `firestore:"activity_id" json:"activity_id"`
    UserID       string                 `firestore:"user_id" json:"user_id"`
    ActivityType string                 `firestore:"activity_type" json:"activity_type"`
    Data         map[string]interface{} `firestore:"data" json:"data"`
    Timestamp    time.Time              `firestore:"timestamp" json:"timestamp"`
    Visibility   string                 `firestore:"visibility" json:"visibility"`
    Reactions    []Reaction             `firestore:"reactions" json:"reactions"`
    Comments     []Comment              `firestore:"comments" json:"comments"`
}

// TODO: Create activity feed from external events
func createActivityFeedItem(userID, activityType string, data map[string]interface{}) error {
    // Implementation for creating activity feed items
}
```

#### **Week 5-6: Leaderboards & Rankings**
```go
// TODO: Implement leaderboard system
type Leaderboard struct {
    LeaderboardID      string      `firestore:"leaderboard_id" json:"leaderboard_id"`
    Type              string      `firestore:"type" json:"type"`
    Period            string      `firestore:"period" json:"period"`
    Category          string      `firestore:"category" json:"category"`
    Rankings          []Ranking   `firestore:"rankings" json:"rankings"`
    TotalParticipants int         `firestore:"total_participants" json:"total_participants"`
    LastUpdated       time.Time   `firestore:"last_updated" json:"last_updated"`
}

func updateLeaderboards(userID string, newScore int, category string) error {
    // Implementation for updating leaderboards
}
```

#### **Week 7-8: Challenges & Gamification**
```go
// TODO: Implement community challenges
type Challenge struct {
    ChallengeID       string                 `firestore:"challenge_id" json:"challenge_id"`
    Title            string                 `firestore:"title" json:"title"`
    Description      string                 `firestore:"description" json:"description"`
    ChallengeType    string                 `firestore:"challenge_type" json:"challenge_type"`
    Requirements     map[string]interface{} `firestore:"requirements" json:"requirements"`
    StartDate        time.Time              `firestore:"start_date" json:"start_date"`
    EndDate          time.Time              `firestore:"end_date" json:"end_date"`
    Participants     []ChallengeParticipant `firestore:"participants" json:"participants"`
    Rewards          ChallengeRewards       `firestore:"rewards" json:"rewards"`
}
```

**Success Criteria for Phase 3:**
- [ ] Friend connection system working
- [ ] Activity feeds generated from core/profile events
- [ ] Leaderboards update automatically
- [ ] Community challenges functional
- [ ] Social interactions (likes, comments) working

---

## 👤 **statlas-profile-service (ENHANCEMENT)**

### **Repository Status**: ✅ Existing - Needs Enhancement
### **Database**: `statlas-profiles`
### **Timeline**: 4 weeks (Phase 4)

### **Current Enhancement Tasks**

#### **Week 1-2: Achievement System Migration**
```go
// TODO: Migrate achievements to statlas-profiles database
// Ensure achievements are moved from any existing location to profiles database

// TODO: Enhance achievement evaluation engine
func checkAchievementsForVisit(userID string, visit SquareVisit) []Achievement {
    // Implementation for checking if visit triggers achievements
    // This will be called by core service after location updates
}

// TODO: Add achievement categories and rarity
type Achievement struct {
    AchievementID   string    `firestore:"achievement_id" json:"achievement_id"`
    Title          string    `firestore:"title" json:"title"`
    Description    string    `firestore:"description" json:"description"`
    Category       string    `firestore:"category" json:"category"` // "dining", "travel", "exploration"
    Rarity         string    `firestore:"rarity" json:"rarity"`     // "common", "rare", "legendary"
    Points         int       `firestore:"points" json:"points"`
    Requirements   Requirements `firestore:"requirements" json:"requirements"`
}
```

#### **Week 3-4: Social Integration**
```go
// TODO: Add social profile features
type UserProfile struct {
    UserID              string    `firestore:"user_id" json:"user_id"`
    DisplayName         string    `firestore:"display_name" json:"display_name"`
    Bio                 string    `firestore:"bio" json:"bio"`
    AvatarURL           string    `firestore:"avatar_url" json:"avatar_url"`
    Location            string    `firestore:"location" json:"location"`
    PrivacyLevel        string    `firestore:"privacy_level" json:"privacy_level"`
    TotalAchievements   int       `firestore:"total_achievements" json:"total_achievements"`
    AchievementPoints   int       `firestore:"achievement_points" json:"achievement_points"`
    ProfileCompletion   int       `firestore:"profile_completion" json:"profile_completion"`
}

// TODO: Implement cross-service achievement triggers
func handleLocationVisit(userID string, visitData SquareVisit) {
    // Check for achievements and notify social service
}
```

---

## 🎯 **statlas-activities-service (ENHANCEMENT)**

### **Repository Status**: ✅ Existing - Needs Grid Integration
### **Database**: `statlas-activities`  
### **Timeline**: 2 weeks (Phase 5)

### **Enhancement Tasks**

#### **Week 1: Grid Integration**
```go
// TODO: Implement activity-to-grid mapping
type ActivityGridMapping struct {
    MappingID      string  `firestore:"mapping_id" json:"mapping_id"`
    ActivityID     string  `firestore:"activity_id" json:"activity_id"`
    SquareID       string  `firestore:"square_id" json:"square_id"`
    GridResolution string  `firestore:"grid_resolution" json:"grid_resolution"`
    DistanceMeters float64 `firestore:"distance_meters" json:"distance_meters"`
    RelevanceScore float64 `firestore:"relevance_score" json:"relevance_score"`
}

// TODO: Add grid-based activity search
func getActivitiesForSquare(squareID string) ([]Activity, error) {
    // Implementation for finding activities in a specific grid square
}

// TODO: Update sync process to include grid mapping
func mapActivityToGrid(activity Activity) error {
    // Call core service to find appropriate grid squares for activity location
    // Store mapping in activity_grid_mapping collection
}
```

#### **Week 2: Personalization & Social Integration**
```go
// TODO: Add user preference-based filtering
func getPersonalizedActivities(userID string, location LatLng, radius float64) ([]Activity, error) {
    // Get user preferences from profile service
    // Filter activities based on preferences
    // Add social context from social service
}

// TODO: Implement social context
func addSocialContext(activities []Activity, userID string) []ActivityWithSocialContext {
    // Call social service to get friends who have done these activities
    // Add social proof to activity recommendations
}
```

This comprehensive implementation guide provides clear, actionable tasks for each repository, designed to be used by engineers (human or AI) working on individual services! 🚀
