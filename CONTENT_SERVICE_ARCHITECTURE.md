# Statlas Content Service Architecture

## 🌍 **Service Overview**

The Statlas Content Service manages all geographic reference data, landmarks, points of interest, and administrative boundaries for the Statlas platform. It provides structured content that enriches the core grid system with meaningful context and enables achievement unlocking.

```
┌─────────────────────────────────────────────────────────────┐
│                 Statlas Content Service                     │
├─────────────────────────────────────────────────────────────┤
│  Geographic Reference Data                                  │
│  ├── Countries with Flags & Boundaries                     │
│  ├── States/Provinces/Regions                              │
│  ├── Cities & Metropolitan Areas                           │
│  └── Administrative Districts/Boroughs                     │
├─────────────────────────────────────────────────────────────┤
│  Points of Interest                                         │
│  ├── Landmarks & Monuments                                 │
│  ├── Museums & Cultural Attractions                        │
│  ├── Restaurants (including Michelin)                      │
│  └── Historic & Religious Sites                            │
├─────────────────────────────────────────────────────────────┤
│  Special Areas                                              │
│  ├── National Parks & Protected Areas                      │
│  ├── City Parks & Recreation Areas                         │
│  ├── Business Districts & Special Zones                    │
│  └── UNESCO World Heritage Sites                           │
├─────────────────────────────────────────────────────────────┤
│  Content Management                                         │
│  ├── Multi-language Support                                │
│  ├── Image & Asset Management                              │
│  ├── Content Versioning & Updates                          │
│  └── Achievement Integration                               │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 **Service Responsibilities**

### **Core Functions**
- **Geographic Reference Data**: Countries, states, cities with official names, codes, and boundaries
- **Landmark Management**: Famous locations, monuments, attractions with precise coordinates
- **Boundary Definitions**: Polygon definitions for administrative and special areas
- **Point of Interest (POI) Data**: Restaurants, museums, cultural sites with detailed information
- **Content Localization**: Multi-language support for names, descriptions, and metadata
- **Asset Management**: Flags, images, icons, and media content with CDN optimization

### **Integration Points**
- **Core Service**: Provides boundary data for resolution determination and square tagging
- **Profile Service**: Supplies landmark data for achievement definitions and unlocking
- **Maps Service**: Enriches map displays with POI information and custom markers
- **Activities Service**: Links activities to landmarks and geographic features
- **Social Service**: Provides content for sharing achievements and location-based posts

## 🗄️ **Database Design: `statlas-content`**

### **Collection Structure**

```go
// Countries - Official country reference data
countries/ {
    country_id: "usa"                    // ISO 3166-1 alpha-3 code
    name: "United States"
    official_name: "United States of America"
    iso_alpha2: "US"                     // ISO 3166-1 alpha-2
    iso_alpha3: "USA"                    // ISO 3166-1 alpha-3
    iso_numeric: 840                     // ISO 3166-1 numeric
    flag_url: "https://cdn.statlas.com/flags/usa.svg"
    flag_emoji: "🇺🇸"
    bounds: {
        min_lat: 18.9110642, max_lat: 71.3577635,
        min_lon: -179.1506, max_lon: -66.9513812
    }
    capital: "Washington, D.C."
    capital_coordinates: {lat: 38.9072, lon: -77.0369}
    population: 331893745
    area_km2: 9833517
    currency_code: "USD"
    currency_name: "US Dollar"
    languages: ["en"]                    // ISO 639-1 codes
    timezone_info: {
        primary: "America/New_York",
        all_zones: ["America/New_York", "America/Chicago", ...]
    }
    calling_code: "+1"
    internet_tld: ".us"
    continent: "North America"
    region: "Northern America"           // UN M49 classification
    subregion: "Northern America"
    states_count: 50
    national_parks_count: 63
    landmarks_count: 1247
    unesco_sites_count: 24
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// States/Provinces/Regions - First-level administrative divisions
states/ {
    state_id: "ny_usa"                   // {state_code}_{country_id}
    country_id: "usa"
    name: "New York"
    official_name: "State of New York"
    abbreviation: "NY"
    iso_code: "US-NY"                    // ISO 3166-2 code
    type: "state"                        // "state", "province", "region", "territory"
    capital: "Albany"
    capital_coordinates: {lat: 42.6584, lon: -73.7810}
    largest_city: "New York City"
    largest_city_coordinates: {lat: 40.7128, lon: -74.0060}
    population: 19336776
    area_km2: 141297
    bounds: {
        min_lat: 40.4774, max_lat: 45.0153,
        min_lon: -79.7625, max_lon: -71.7517
    }
    timezone: "America/New_York"
    cities_count: 62
    landmarks_count: 342
    national_parks_count: 0
    state_parks_count: 180
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// Cities - Major urban areas and municipalities
cities/ {
    city_id: "nyc_ny_usa"               // {city}_{state}_{country}
    country_id: "usa"
    state_id: "ny_usa"
    name: "New York City"
    official_name: "City of New York"
    type: "city"                         // "city", "town", "municipality", "metro_area"
    coordinates: {lat: 40.7128, lon: -74.0060}
    population: 8336817
    metro_population: 20140470
    area_km2: 783.8
    bounds: {
        min_lat: 40.4774, max_lat: 40.9176,
        min_lon: -74.2591, max_lon: -73.7004
    }
    timezone: "America/New_York"
    boroughs: ["manhattan", "brooklyn", "queens", "bronx", "staten_island"]
    landmarks_count: 89
    museums_count: 34
    restaurants_count: 1247
    parks_count: 29
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// Landmarks - Points of interest and famous locations
landmarks/ {
    landmark_id: "statue_of_liberty"
    name: "Statue of Liberty"
    official_name: "Liberty Enlightening the World"
    type: "monument"                     // "monument", "building", "natural", "religious", etc.
    category: "historic_site"            // More specific categorization
    coordinates: {
        lat: 40.6892494, 
        lon: -74.0445004, 
        altitude: 93                     // meters above sea level
    }
    precision_radius_meters: 30          // Achievement trigger radius
    country_id: "usa"
    state_id: "ny_usa"
    city_id: "nyc_ny_usa"
    borough_id: "manhattan"              // Optional sub-city division
    
    description: "A colossal neoclassical sculpture on Liberty Island..."
    short_description: "Iconic symbol of freedom and democracy"
    
    images: [
        {
            url: "https://cdn.statlas.com/landmarks/statue_of_liberty_main.jpg",
            type: "primary",
            caption: "Statue of Liberty from the harbor",
            photographer: "John Doe",
            license: "CC BY-SA 4.0"
        }
    ]
    
    visiting_info: {
        hours: {
            monday: {open: "08:30", close: "18:00"},
            tuesday: {open: "08:30", close: "18:00"},
            // ... other days
            special_hours: [
                {date: "2024-07-04", hours: "closed", reason: "Independence Day"}
            ]
        },
        admission: {
            required: true,
            adult_price: {amount: 23.50, currency: "USD"},
            child_price: {amount: 18.00, currency: "USD"},
            booking_url: "https://www.nps.gov/stli/planyourvisit/fees.htm"
        },
        accessibility: {
            wheelchair_accessible: false,
            audio_tours: true,
            sign_language: true
        }
    }
    
    achievement: {
        achievement_id: "statue_of_liberty_visitor",
        title: "Lady Liberty",
        description: "Visit the iconic Statue of Liberty",
        points: 50,
        rarity: "uncommon"               // "common", "uncommon", "rare", "legendary"
        category: "landmarks"
        unlock_message: "You've visited one of America's most iconic symbols!"
    }
    
    external_links: {
        wikipedia_url: "https://en.wikipedia.org/wiki/Statue_of_Liberty",
        official_website: "https://www.nps.gov/stli/",
        tripadvisor_id: "104674",
        google_places_id: "ChIJPTacEpBQwokRKwIlDXelxkA"
    }
    
    facts: [
        "Gifted by France in 1886",
        "Height: 93 meters (305 feet) including pedestal",
        "Made of copper that has oxidized to green"
    ]
    
    tags: ["nyc", "monument", "historic", "unesco", "ferry_required", "crown_access"]
    unesco_world_heritage: false
    national_historic_landmark: true
    
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// Boundaries - Polygon definitions for geographic areas
boundaries/ {
    boundary_id: "manhattan_core"
    name: "Manhattan"
    type: "borough"                      // "country", "state", "city", "borough", "district"
    category: "administrative"           // "administrative" or "special_area"
    level: 3                            // 0=country, 1=state, 2=city, 3=borough/district
    
    country_id: "usa"
    state_id: "ny_usa"
    city_id: "nyc_ny_usa"
    parent_boundary_id: "nyc_ny_usa"
    
    // GeoJSON-style polygon definition
    geometry: {
        type: "Polygon",
        coordinates: [
            [
                [-74.0479, 40.6829],
                [-73.9067, 40.6829],
                [-73.9067, 40.8820],
                [-74.0479, 40.8820],
                [-74.0479, 40.6829]
            ]
        ]
    }
    
    // For boundaries with holes (like Vatican in Rome)
    holes: [
        {
            name: "Central Park",
            geometry: {
                type: "Polygon",
                coordinates: [[[...]]]
            }
        }
    ]
    
    properties: {
        population: 1630000,
        area_km2: 60.0,
        density_per_km2: 27167,
        established: "1624"
    }
    
    resolution_requirement: "100m"       // Grid resolution for this area
    overlays_ids: ["central_park", "times_square_district"]
    overlaid_by_ids: []                  // What overlaps this boundary
    
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// National Parks - Detailed park information
national_parks/ {
    park_id: "yellowstone"
    name: "Yellowstone National Park"
    official_name: "Yellowstone National Park"
    country_id: "usa"
    states: ["wy_usa", "mt_usa", "id_usa"]  // Parks can span multiple states
    
    coordinates: {lat: 44.4280, lon: -110.5885}  // Park center
    established: "1872-03-01"
    area_km2: 8991
    
    geometry: {
        type: "MultiPolygon",            // Complex park boundaries
        coordinates: [[[[...]]], [[[...]]]]
    }
    
    description: "The world's first national park, famous for geysers..."
    features: ["geysers", "hot_springs", "wildlife", "mountains", "lakes"]
    
    visitor_info: {
        annual_visitors: 4860242,
        peak_season: "June to September",
        entrance_fee: {
            vehicle_7_day: {amount: 35, currency: "USD"},
            annual_pass: {amount: 70, currency: "USD"}
        },
        visitor_centers: [
            {
                name: "Albright Visitor Center",
                coordinates: {lat: 44.9778, lon: -110.6968},
                hours: "seasonal"
            }
        ]
    }
    
    attractions: [
        {
            name: "Old Faithful",
            type: "geyser",
            coordinates: {lat: 44.4605, lon: -110.8281},
            achievement_id: "old_faithful_visitor"
        }
    ]
    
    wildlife: ["bison", "bears", "wolves", "elk", "eagles"]
    activities: ["hiking", "camping", "wildlife_watching", "photography"]
    
    unesco_world_heritage: true
    achievement: {
        achievement_id: "yellowstone_explorer",
        title: "Yellowstone Explorer",
        description: "Visit America's first national park",
        points: 100,
        rarity: "rare"
    }
    
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// Restaurants - Dining establishments with special focus on Michelin
restaurants/ {
    restaurant_id: "le_bernardin_nyc"
    name: "Le Bernardin"
    type: "restaurant"
    cuisine_type: "french_seafood"
    
    coordinates: {lat: 40.7614, lon: -73.9776}
    precision_radius_meters: 5           // Very precise for Michelin restaurants
    
    country_id: "usa"
    state_id: "ny_usa" 
    city_id: "nyc_ny_usa"
    address: "155 W 51st St, New York, NY 10019"
    
    michelin: {
        stars: 3,
        year_awarded: 2005,
        guide: "New York",
        description: "Exceptional cuisine that is worth a special journey"
    }
    
    achievement: {
        achievement_id: "le_bernardin_diner",
        title: "Three-Star Excellence",
        description: "Dine at Le Bernardin, a 3-Michelin-star restaurant",
        points: 200,
        rarity: "legendary"
    }
    
    details: {
        chef: "Eric Ripert",
        opened: 1986,
        price_range: "$$$$",
        reservations_required: true,
        dress_code: "business_casual"
    }
    
    external_links: {
        website: "https://www.le-bernardin.com/",
        reservation_url: "https://resy.com/cities/ny/le-bernardin",
        michelin_guide_url: "https://guide.michelin.com/us/en/new-york-state/new-york/restaurant/le-bernardin"
    }
    
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}

// Content Translations - Multi-language support
translations/ {
    translation_id: "statue_of_liberty_es"
    entity_type: "landmark"              // "country", "landmark", "restaurant", etc.
    entity_id: "statue_of_liberty"
    language_code: "es"                  // ISO 639-1
    
    translated_fields: {
        name: "Estatua de la Libertad",
        description: "Una escultura neoclásica colosal en Liberty Island...",
        short_description: "Símbolo icónico de libertad y democracia"
    }
    
    created_at: timestamp
    updated_at: timestamp
    is_active: true
}
```

## 🔌 **API Design**

### **Core Endpoints**

```go
// Geographic Reference Data
GET    /countries                       // List all countries
GET    /countries/{id}                  // Get country details
GET    /countries/{id}/states           // Get states in country
GET    /states/{id}                     // Get state details  
GET    /states/{id}/cities              // Get cities in state
GET    /cities/{id}                     // Get city details

// Landmarks & Points of Interest
GET    /landmarks                       // Search landmarks (with filters)
GET    /landmarks/{id}                  // Get landmark details
GET    /landmarks/nearby?lat={}&lon={}  // Find landmarks near coordinates
GET    /restaurants                     // Search restaurants
GET    /restaurants/michelin            // Get Michelin-starred restaurants

// Boundaries & Geographic Features
GET    /boundaries                      // List boundaries (with filters)
GET    /boundaries/{id}                 // Get boundary details
GET    /boundaries/containing?lat={}&lon={} // Find boundaries containing point
GET    /national-parks                  // List national parks
GET    /national-parks/{id}             // Get park details

// Bulk & Integration APIs
POST   /boundaries/batch-lookup         // Bulk boundary queries for Core Service
GET    /content/for-square/{square_id}  // Get all content for a grid square
GET    /achievements/definitions        // Get all achievement definitions

// Search & Discovery
GET    /search?q={query}&type={type}    // Universal content search
GET    /content/featured                // Featured content (daily highlights)
GET    /content/by-location?lat={}&lon={} // All content near coordinates

// Admin & Content Management
POST   /countries                       // Create country (admin)
PUT    /countries/{id}                  // Update country (admin)
POST   /landmarks                       // Create landmark (admin)
PUT    /landmarks/{id}                  // Update landmark (admin)
POST   /boundaries                      // Create boundary (admin)
POST   /translations                    // Add translation (admin)
```

### **Example API Responses**

```json
// GET /landmarks/statue_of_liberty
{
  "id": "statue_of_liberty",
  "name": "Statue of Liberty",
  "type": "monument",
  "coordinates": {
    "lat": 40.6892494,
    "lon": -74.0445004
  },
  "precision_radius_meters": 30,
  "location": {
    "country": "United States",
    "state": "New York", 
    "city": "New York City"
  },
  "description": "A colossal neoclassical sculpture...",
  "images": [
    {
      "url": "https://cdn.statlas.com/landmarks/statue_of_liberty_main.jpg",
      "type": "primary"
    }
  ],
  "achievement": {
    "id": "statue_of_liberty_visitor",
    "title": "Lady Liberty",
    "points": 50,
    "rarity": "uncommon"
  },
  "visiting_info": {
    "hours": {
      "monday": {"open": "08:30", "close": "18:00"}
    },
    "admission": {
      "adult_price": {"amount": 23.50, "currency": "USD"}
    }
  }
}

// GET /boundaries/containing?lat=40.7128&lon=-74.0060
{
  "boundaries": [
    {
      "id": "usa",
      "name": "United States",
      "type": "country",
      "level": 0,
      "resolution_requirement": "1km"
    },
    {
      "id": "ny_usa", 
      "name": "New York",
      "type": "state",
      "level": 1,
      "resolution_requirement": "100m"
    },
    {
      "id": "nyc_ny_usa",
      "name": "New York City", 
      "type": "city",
      "level": 2,
      "resolution_requirement": "100m"
    },
    {
      "id": "manhattan_core",
      "name": "Manhattan",
      "type": "borough",
      "level": 3, 
      "resolution_requirement": "100m"
    }
  ]
}

// POST /boundaries/batch-lookup (for Core Service integration)
{
  "points": [
    {"lat": 40.7128, "lon": -74.0060, "square_id": "sq_manhattan_123"},
    {"lat": 48.8566, "lon": 2.3522, "square_id": "sq_paris_456"}
  ]
}
// Response:
{
  "results": [
    {
      "square_id": "sq_manhattan_123",
      "boundary_tags": ["usa", "new_york", "nyc", "manhattan"],
      "resolution": "100m",
      "landmarks_nearby": ["statue_of_liberty", "empire_state_building"]
    },
    {
      "square_id": "sq_paris_456", 
      "boundary_tags": ["france", "ile_de_france", "paris"],
      "resolution": "100m",
      "landmarks_nearby": ["eiffel_tower", "louvre"]
    }
  ]
}
```

## 🔄 **Service Integration**

### **With Core Service**
```go
// Core Service calls Content Service to enrich squares
func enrichSquareWithBoundaries(square *Square) {
    response := contentService.BatchLookupBoundaries([]Point{
        {Lat: square.CenterLat, Lon: square.CenterLon, SquareID: square.ID}
    })
    
    square.BoundaryTags = response.Results[0].BoundaryTags
    square.Resolution = response.Results[0].Resolution
}
```

### **With Profile Service**
```go
// Profile Service gets achievement definitions from Content Service
func checkLandmarkAchievements(userID string, lat, lon float64) {
    landmarks := contentService.GetLandmarksNearby(lat, lon, 50) // 50m radius
    
    for _, landmark := range landmarks {
        if !userHasAchievement(userID, landmark.Achievement.ID) {
            unlockAchievement(userID, landmark.Achievement)
        }
    }
}
```

## 📊 **Performance Considerations**

### **Caching Strategy**
- **Country/State Data**: Cache for 24 hours (rarely changes)
- **Landmarks**: Cache for 6 hours (occasional updates)
- **Boundaries**: Cache for 12 hours (stable geographic data)
- **Restaurant Data**: Cache for 1 hour (prices, hours may change)

### **Query Optimization**
```go
// Use geospatial indexing for location-based queries
func (s *ContentService) GetLandmarksNearby(lat, lon, radiusMeters float64) []Landmark {
    // Create bounding box for efficient query
    bounds := calculateBoundingBox(lat, lon, radiusMeters)
    
    query := s.db.Collection("landmarks").
        Where("coordinates.lat", ">=", bounds.MinLat).
        Where("coordinates.lat", "<=", bounds.MaxLat).
        Where("coordinates.lon", ">=", bounds.MinLon).
        Where("coordinates.lon", "<=", bounds.MaxLon)
        
    // Further filter by precise distance calculation
    return filterByDistance(query.Documents(), lat, lon, radiusMeters)
}
```

## 🚀 **Implementation Roadmap**

### **Phase 1: Foundation (Weeks 1-2)**
- [x] Service structure setup (Go, Firestore, Cloud Run)
- [x] Basic CRUD operations for countries, states, cities
- [x] Health checks and monitoring
- [x] Service-to-service authentication

### **Phase 2: Core Data (Weeks 3-4)**
- [ ] Import world countries with flags and basic info
- [ ] Add major landmarks (top 1000 world attractions)
- [ ] Implement boundary polygon storage
- [ ] Basic search and lookup endpoints

### **Phase 3: Landmark System (Weeks 5-6)**
- [ ] Michelin restaurant database
- [ ] Achievement definitions and metadata
- [ ] Precise coordinate system with radius definitions
- [ ] Integration with Profile Service for achievements

### **Phase 4: Advanced Features (Weeks 7-8)**
- [ ] Multi-language support and translations
- [ ] Image and asset management with CDN
- [ ] Advanced search with filters and categories
- [ ] Bulk APIs for efficient service integration

This architecture provides a comprehensive content management system that enriches the Statlas platform with meaningful geographic and cultural context while maintaining high performance and scalability! 🌍
