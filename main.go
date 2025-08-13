package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"cloud.google.com/go/firestore"
	"github.com/gorilla/mux"
	"github.com/paulmach/orb"
	"github.com/paulmach/orb/geojson"
	"github.com/paulmach/orb/planar"
)

// SovereignState represents a passport-issuing sovereign entity (209 total)
type SovereignState struct {
	ID           string    `firestore:"id" json:"id"`                       // e.g. "united_kingdom"
	Name         string    `firestore:"name" json:"name"`                   // e.g. "United Kingdom"
	OfficialName string    `firestore:"official_name" json:"official_name"` // e.g. "United Kingdom of Great Britain and Northern Ireland"
	ISOAlpha2    string    `firestore:"iso_alpha2" json:"iso_alpha2"`       // ISO 3166-1 alpha-2
	ISOAlpha3    string    `firestore:"iso_alpha3" json:"iso_alpha3"`       // ISO 3166-1 alpha-3
	ISONumerical int       `firestore:"iso_numeric" json:"iso_numeric"`     // ISO 3166-1 numeric
	FlagURL      string    `firestore:"flag_url" json:"flag_url"`
	FlagEmoji    string    `firestore:"flag_emoji" json:"flag_emoji"`
	Bounds       Bounds    `firestore:"bounds" json:"bounds"`
	Capital      string    `firestore:"capital" json:"capital"`
	Population   int64     `firestore:"population" json:"population"`
	AreaKM2      float64   `firestore:"area_km2" json:"area_km2"`
	CurrencyCode string    `firestore:"currency_code" json:"currency_code"`
	Languages    []string  `firestore:"languages" json:"languages"`
	Geometry     string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt    time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt    time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive     bool      `firestore:"is_active" json:"is_active"`
}

// Country represents a distinct country entity (258 total)
type Country struct {
	ID               string    `firestore:"id" json:"id"`                                 // e.g. "scotland"
	SovereignStateID string    `firestore:"sovereign_state_id" json:"sovereign_state_id"` // e.g. "united_kingdom"
	Name             string    `firestore:"name" json:"name"`                             // e.g. "Scotland"
	OfficialName     string    `firestore:"official_name" json:"official_name"`
	Type             string    `firestore:"type" json:"type"`             // "Country", "Territory", "Dependency"
	Level            int       `firestore:"level" json:"level"`           // Natural Earth level (1-2)
	ISOAlpha2        string    `firestore:"iso_alpha2" json:"iso_alpha2"` // May be empty for sub-countries
	ISOAlpha3        string    `firestore:"iso_alpha3" json:"iso_alpha3"` // May be empty for sub-countries
	Bounds           Bounds    `firestore:"bounds" json:"bounds"`
	Capital          string    `firestore:"capital" json:"capital"`
	Population       int64     `firestore:"population" json:"population"`
	AreaKM2          float64   `firestore:"area_km2" json:"area_km2"`
	Geometry         string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt        time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt        time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive         bool      `firestore:"is_active" json:"is_active"`
}

// MapUnit represents dependencies and territories (298 total)
type MapUnit struct {
	ID               string    `firestore:"id" json:"id"`                                 // e.g. "american_samoa"
	SovereignStateID string    `firestore:"sovereign_state_id" json:"sovereign_state_id"` // e.g. "united_states"
	CountryID        string    `firestore:"country_id" json:"country_id"`                 // Parent country if applicable
	Name             string    `firestore:"name" json:"name"`                             // e.g. "American Samoa"
	OfficialName     string    `firestore:"official_name" json:"official_name"`
	Type             string    `firestore:"type" json:"type"`               // "Dependency", "Territory", "Sovereign country"
	Level            int       `firestore:"level" json:"level"`             // Natural Earth level (1-3)
	AdminLevel       string    `firestore:"admin_level" json:"admin_level"` // Natural Earth admin level
	ISOAlpha2        string    `firestore:"iso_alpha2" json:"iso_alpha2"`
	ISOAlpha3        string    `firestore:"iso_alpha3" json:"iso_alpha3"`
	Bounds           Bounds    `firestore:"bounds" json:"bounds"`
	Population       int64     `firestore:"population" json:"population"`
	AreaKM2          float64   `firestore:"area_km2" json:"area_km2"`
	Geometry         string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt        time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt        time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive         bool      `firestore:"is_active" json:"is_active"`
}

// MapSubunit represents non-contiguous geographic regions (360 total)
type MapSubunit struct {
	ID               string    `firestore:"id" json:"id"`                                 // e.g. "alaska"
	SovereignStateID string    `firestore:"sovereign_state_id" json:"sovereign_state_id"` // e.g. "united_states"
	CountryID        string    `firestore:"country_id" json:"country_id"`                 // e.g. "united_states"
	MapUnitID        string    `firestore:"map_unit_id" json:"map_unit_id"`               // e.g. "united_states"
	Name             string    `firestore:"name" json:"name"`                             // e.g. "Alaska"
	OfficialName     string    `firestore:"official_name" json:"official_name"`
	Type             string    `firestore:"type" json:"type"`               // "Country", "Dependency", etc.
	Level            int       `firestore:"level" json:"level"`             // Natural Earth level (1-4)
	AdminLevel       string    `firestore:"admin_level" json:"admin_level"` // Natural Earth admin level
	IsMainland       bool      `firestore:"is_mainland" json:"is_mainland"` // True for mainland, false for islands/territories
	Bounds           Bounds    `firestore:"bounds" json:"bounds"`
	Population       int64     `firestore:"population" json:"population"`
	AreaKM2          float64   `firestore:"area_km2" json:"area_km2"`
	Geometry         string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt        time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt        time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive         bool      `firestore:"is_active" json:"is_active"`
}

// State represents a state/province/region
type State struct {
	ID           string      `firestore:"id" json:"id"`
	CountryID    string      `firestore:"country_id" json:"country_id"`
	Name         string      `firestore:"name" json:"name"`
	OfficialName string      `firestore:"official_name" json:"official_name"`
	Abbreviation string      `firestore:"abbreviation" json:"abbreviation"`
	ISOCode      string      `firestore:"iso_code" json:"iso_code"`
	Type         string      `firestore:"type" json:"type"` // "state", "province", "region"
	Capital      string      `firestore:"capital" json:"capital"`
	LargestCity  string      `firestore:"largest_city" json:"largest_city"`
	Population   int64       `firestore:"population" json:"population"`
	AreaKM2      float64     `firestore:"area_km2" json:"area_km2"`
	Bounds       Bounds      `firestore:"bounds" json:"bounds"`
	Coordinates  Coordinates `firestore:"coordinates" json:"coordinates"`
	CreatedAt    time.Time   `firestore:"created_at" json:"created_at"`
	UpdatedAt    time.Time   `firestore:"updated_at" json:"updated_at"`
	IsActive     bool        `firestore:"is_active" json:"is_active"`
}

// City represents a city or urban area
type City struct {
	ID              string      `firestore:"id" json:"id"`
	CountryID       string      `firestore:"country_id" json:"country_id"`
	StateID         string      `firestore:"state_id" json:"state_id"`
	Name            string      `firestore:"name" json:"name"`
	OfficialName    string      `firestore:"official_name" json:"official_name"`
	Type            string      `firestore:"type" json:"type"` // "city", "town", "municipality"
	Population      int64       `firestore:"population" json:"population"`
	MetroPopulation int64       `firestore:"metro_population" json:"metro_population"`
	AreaKM2         float64     `firestore:"area_km2" json:"area_km2"`
	Bounds          Bounds      `firestore:"bounds" json:"bounds"`
	Coordinates     Coordinates `firestore:"coordinates" json:"coordinates"`
	CreatedAt       time.Time   `firestore:"created_at" json:"created_at"`
	UpdatedAt       time.Time   `firestore:"updated_at" json:"updated_at"`
	IsActive        bool        `firestore:"is_active" json:"is_active"`
}

// Landmark represents a point of interest
type Landmark struct {
	ID                       string        `firestore:"id" json:"id"`
	Name                     string        `firestore:"name" json:"name"`
	OfficialName             string        `firestore:"official_name" json:"official_name"`
	Type                     string        `firestore:"type" json:"type"` // "monument", "building", "natural"
	Category                 string        `firestore:"category" json:"category"`
	Coordinates              Coordinates   `firestore:"coordinates" json:"coordinates"`
	PrecisionRadiusMeters    int           `firestore:"precision_radius_meters" json:"precision_radius_meters"`
	CountryID                string        `firestore:"country_id" json:"country_id"`
	StateID                  string        `firestore:"state_id" json:"state_id"`
	CityID                   string        `firestore:"city_id" json:"city_id"`
	Description              string        `firestore:"description" json:"description"`
	ShortDescription         string        `firestore:"short_description" json:"short_description"`
	Images                   []Image       `firestore:"images" json:"images"`
	VisitingInfo             VisitingInfo  `firestore:"visiting_info" json:"visiting_info"`
	Achievement              Achievement   `firestore:"achievement" json:"achievement"`
	ExternalLinks            ExternalLinks `firestore:"external_links" json:"external_links"`
	Tags                     []string      `firestore:"tags" json:"tags"`
	UNESCOWorldHeritage      bool          `firestore:"unesco_world_heritage" json:"unesco_world_heritage"`
	NationalHistoricLandmark bool          `firestore:"national_historic_landmark" json:"national_historic_landmark"`
	CreatedAt                time.Time     `firestore:"created_at" json:"created_at"`
	UpdatedAt                time.Time     `firestore:"updated_at" json:"updated_at"`
	IsActive                 bool          `firestore:"is_active" json:"is_active"`
}

// Boundary represents a geographic boundary polygon
type Boundary struct {
	ID                    string                 `firestore:"id" json:"id"`
	Name                  string                 `firestore:"name" json:"name"`
	Type                  string                 `firestore:"type" json:"type"`         // "country", "state", "city", "borough"
	Category              string                 `firestore:"category" json:"category"` // "administrative", "special_area"
	Level                 int                    `firestore:"level" json:"level"`       // 0=country, 1=state, 2=city, 3=borough
	CountryID             string                 `firestore:"country_id" json:"country_id"`
	StateID               string                 `firestore:"state_id" json:"state_id"`
	CityID                string                 `firestore:"city_id" json:"city_id"`
	ParentBoundaryID      string                 `firestore:"parent_boundary_id" json:"parent_boundary_id"`
	Geometry              string                 `firestore:"geometry" json:"geometry"` // GeoJSON as string
	Properties            map[string]interface{} `firestore:"properties" json:"properties"`
	ResolutionRequirement string                 `firestore:"resolution_requirement" json:"resolution_requirement"`
	OverlaysIDs           []string               `firestore:"overlays_ids" json:"overlays_ids"`
	OverlaidByIDs         []string               `firestore:"overlaid_by_ids" json:"overlaid_by_ids"`
	CreatedAt             time.Time              `firestore:"created_at" json:"created_at"`
	UpdatedAt             time.Time              `firestore:"updated_at" json:"updated_at"`
	IsActive              bool                   `firestore:"is_active" json:"is_active"`
}

// Restaurant represents a dining establishment
type Restaurant struct {
	ID                    string            `firestore:"id" json:"id"`
	Name                  string            `firestore:"name" json:"name"`
	Type                  string            `firestore:"type" json:"type"`
	CuisineType           string            `firestore:"cuisine_type" json:"cuisine_type"`
	Coordinates           Coordinates       `firestore:"coordinates" json:"coordinates"`
	PrecisionRadiusMeters int               `firestore:"precision_radius_meters" json:"precision_radius_meters"`
	CountryID             string            `firestore:"country_id" json:"country_id"`
	StateID               string            `firestore:"state_id" json:"state_id"`
	CityID                string            `firestore:"city_id" json:"city_id"`
	Address               string            `firestore:"address" json:"address"`
	Michelin              *Michelin         `firestore:"michelin,omitempty" json:"michelin,omitempty"`
	Achievement           Achievement       `firestore:"achievement" json:"achievement"`
	Details               RestaurantDetails `firestore:"details" json:"details"`
	ExternalLinks         ExternalLinks     `firestore:"external_links" json:"external_links"`
	CreatedAt             time.Time         `firestore:"created_at" json:"created_at"`
	UpdatedAt             time.Time         `firestore:"updated_at" json:"updated_at"`
	IsActive              bool              `firestore:"is_active" json:"is_active"`
}

// Supporting types
type Coordinates struct {
	Lat      float64  `firestore:"lat" json:"lat"`
	Lon      float64  `firestore:"lon" json:"lon"`
	Altitude *float64 `firestore:"altitude,omitempty" json:"altitude,omitempty"`
}

type Bounds struct {
	MinLat float64 `firestore:"min_lat" json:"min_lat"`
	MaxLat float64 `firestore:"max_lat" json:"max_lat"`
	MinLon float64 `firestore:"min_lon" json:"min_lon"`
	MaxLon float64 `firestore:"max_lon" json:"max_lon"`
}

type Image struct {
	URL          string `firestore:"url" json:"url"`
	Type         string `firestore:"type" json:"type"` // "primary", "secondary"
	Caption      string `firestore:"caption" json:"caption"`
	Photographer string `firestore:"photographer" json:"photographer"`
	License      string `firestore:"license" json:"license"`
}

type VisitingInfo struct {
	Hours         map[string]interface{} `firestore:"hours" json:"hours"`
	Admission     map[string]interface{} `firestore:"admission" json:"admission"`
	Accessibility map[string]interface{} `firestore:"accessibility" json:"accessibility"`
}

type Achievement struct {
	ID            string `firestore:"id" json:"id"`
	Title         string `firestore:"title" json:"title"`
	Description   string `firestore:"description" json:"description"`
	Points        int    `firestore:"points" json:"points"`
	Rarity        string `firestore:"rarity" json:"rarity"` // "common", "uncommon", "rare", "legendary"
	Category      string `firestore:"category" json:"category"`
	UnlockMessage string `firestore:"unlock_message" json:"unlock_message"`
}

type ExternalLinks struct {
	WikipediaURL    string `firestore:"wikipedia_url" json:"wikipedia_url"`
	OfficialWebsite string `firestore:"official_website" json:"official_website"`
	TripAdvisorID   string `firestore:"tripadvisor_id" json:"tripadvisor_id"`
	GooglePlacesID  string `firestore:"google_places_id" json:"google_places_id"`
}

type Michelin struct {
	Stars       int    `firestore:"stars" json:"stars"`
	YearAwarded int    `firestore:"year_awarded" json:"year_awarded"`
	Guide       string `firestore:"guide" json:"guide"`
	Description string `firestore:"description" json:"description"`
}

type RestaurantDetails struct {
	Chef                 string `firestore:"chef" json:"chef"`
	Opened               int    `firestore:"opened" json:"opened"`
	PriceRange           string `firestore:"price_range" json:"price_range"`
	ReservationsRequired bool   `firestore:"reservations_required" json:"reservations_required"`
	DressCode            string `firestore:"dress_code" json:"dress_code"`
}

// Request/Response types
type BatchLookupRequest struct {
	Points []PointLookup `json:"points"`
}

type PointLookup struct {
	Lat      float64 `json:"lat"`
	Lon      float64 `json:"lon"`
	SquareID string  `json:"square_id"`
}

type BatchLookupResponse struct {
	Results []SquareEnrichment `json:"results"`
}

type SquareEnrichment struct {
	SquareID        string   `json:"square_id"`
	BoundaryTags    []string `json:"boundary_tags"`
	Resolution      string   `json:"resolution"`
	LandmarksNearby []string `json:"landmarks_nearby"`
}

type NearbyLandmarksRequest struct {
	Lat          float64 `json:"lat"`
	Lon          float64 `json:"lon"`
	RadiusMeters float64 `json:"radius_meters"`
}

// Global variables
var (
	firestoreClient *firestore.Client
	serviceSecret   string
	cdnBaseURL      string
	startTime       time.Time
)

const (
	PORT = "8083" // Different port from core service (8082)
)

// Helper function to check if a point is inside a geometry
func isPointInGeometry(lat, lon float64, geometryJSON string) bool {
	if geometryJSON == "" {
		return false
	}
	
	// Convert to orb geometry directly from JSON bytes
	geom, err := geojson.UnmarshalGeometry([]byte(geometryJSON))
	if err != nil {
		log.Printf("Error converting to orb geometry: %v", err)
		return false
	}
	
	// Create point
	point := orb.Point{lon, lat}
	
	// Check if point is inside geometry
	switch g := geom.Geometry().(type) {
	case orb.Polygon:
		return planar.PolygonContains(g, point)
	case orb.MultiPolygon:
		for _, poly := range g {
			if planar.PolygonContains(poly, point) {
				return true
			}
		}
		return false
	default:
		log.Printf("Unsupported geometry type: %T", g)
		return false
	}
}

// Helper function to find entities containing a point
func findContainingEntities(ctx context.Context, collection string, lat, lon float64) []map[string]interface{} {
	var results []map[string]interface{}
	
	// Query all entities in the collection
	iter := firestoreClient.Collection(collection).Documents(ctx)
	defer iter.Stop()
	
	for {
		doc, err := iter.Next()
		if err != nil {
			break
		}
		
		var entity map[string]interface{}
		if err := doc.DataTo(&entity); err != nil {
			continue
		}
		
		// Check if geometry exists and point is inside
		if geometryJSON, ok := entity["geometry"].(string); ok && geometryJSON != "" {
			if isPointInGeometry(lat, lon, geometryJSON) {
				results = append(results, entity)
			}
		}
	}
	
	return results
}

func main() {
	ctx := context.Background()
	startTime = time.Now()

	// Get environment variables
	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
	serviceSecret = os.Getenv("SERVICE_SECRET")
	cdnBaseURL = os.Getenv("CDN_BASE_URL")
	if cdnBaseURL == "" {
		cdnBaseURL = "https://cdn.statlas.com" // Default CDN URL
	}

	if projectID == "" {
		log.Fatal("GOOGLE_CLOUD_PROJECT environment variable is required")
	}

	// Initialize Firestore client with statlas-content database
	var err error
	firestoreClient, err = firestore.NewClientWithDatabase(ctx, projectID, "statlas-content")
	if err != nil {
		log.Fatalf("Failed to create Firestore client: %v", err)
	}
	defer firestoreClient.Close()

	// Create router
	router := mux.NewRouter()

	// Add CORS middleware
	router.Use(corsMiddleware)

	// Add monitoring middleware
	router.Use(monitoringMiddleware)

	// Health check endpoint (no auth required)
	router.HandleFunc("/health", healthHandler).Methods("GET")

	// Metrics endpoint (no auth required for monitoring systems)
	router.HandleFunc("/metrics", metricsHandler).Methods("GET")

	// Geographic Reference Data endpoints - New Hierarchical Structure
	router.HandleFunc("/sovereign-states", requireServiceAuth(getSovereignStatesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/sovereign-states/{id}", requireServiceAuth(getSovereignStateHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/countries", requireServiceAuth(getCountriesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/countries/{id}", requireServiceAuth(getCountryHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/map-units", requireServiceAuth(getMapUnitsHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/map-units/{id}", requireServiceAuth(getMapUnitHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/map-subunits", requireServiceAuth(getMapSubunitsHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/map-subunits/{id}", requireServiceAuth(getMapSubunitHandler)).Methods("GET", "OPTIONS")

	// Hierarchical queries
	router.HandleFunc("/sovereign-states/{id}/countries", requireServiceAuth(getSovereignStateCountriesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/countries/{id}/map-units", requireServiceAuth(getCountryMapUnitsHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/map-units/{id}/subunits", requireServiceAuth(getMapUnitSubunitsHandler)).Methods("GET", "OPTIONS")

	// Legacy endpoint (kept for backward compatibility)
	router.HandleFunc("/countries/{id}/states", requireServiceAuth(getCountryStatesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/states/{id}", requireServiceAuth(getStateHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/states/{id}/cities", requireServiceAuth(getStateCitiesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/cities/{id}", requireServiceAuth(getCityHandler)).Methods("GET", "OPTIONS")

	// Landmarks & Points of Interest endpoints
	router.HandleFunc("/landmarks", requireServiceAuth(getLandmarksHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/landmarks/{id}", requireServiceAuth(getLandmarkHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/landmarks/nearby", requireServiceAuth(getLandmarksNearbyHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/restaurants", requireServiceAuth(getRestaurantsHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/restaurants/michelin", requireServiceAuth(getMichelinRestaurantsHandler)).Methods("GET", "OPTIONS")

	// Boundaries & Geographic Features endpoints
	router.HandleFunc("/boundaries", requireServiceAuth(getBoundariesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/boundaries/containing", requireServiceAuth(getBoundariesContainingHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/boundaries/{id}", requireServiceAuth(getBoundaryHandler)).Methods("GET", "OPTIONS")

	// Bulk & Integration APIs
	router.HandleFunc("/boundaries/batch-lookup", requireServiceAuth(batchLookupBoundariesHandler)).Methods("POST", "OPTIONS")
	router.HandleFunc("/achievements/definitions", requireServiceAuth(getAchievementDefinitionsHandler)).Methods("GET", "OPTIONS")

	// Search & Discovery endpoints
	router.HandleFunc("/search", requireServiceAuth(searchContentHandler)).Methods("GET", "OPTIONS")

	// Admin endpoints (require service auth)
	router.HandleFunc("/countries", requireServiceAuth(createCountryHandler)).Methods("POST", "OPTIONS")
	router.HandleFunc("/landmarks", requireServiceAuth(createLandmarkHandler)).Methods("POST", "OPTIONS")
	router.HandleFunc("/boundaries", requireServiceAuth(createBoundaryHandler)).Methods("POST", "OPTIONS")

	log.Printf("Starting statlas-content-service on port %s", PORT)
	log.Printf("Service started at %s", startTime.Format(time.RFC3339))
	log.Fatal(http.ListenAndServe(":"+PORT, router))
}

// CORS middleware to handle cross-origin requests from web app
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// CRITICAL: Set CORS headers FIRST, before any other checks
		allowedOrigin := os.Getenv("CORS_ALLOWED_ORIGIN")
		if allowedOrigin == "" {
			allowedOrigin = "https://statlas-web-app-aleilqeyua-uc.a.run.app"
		}

		w.Header().Set("Access-Control-Allow-Origin", allowedOrigin)
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Service-Auth")
		w.Header().Set("Access-Control-Max-Age", "3600")

		// Handle preflight OPTIONS request WITHOUT any authentication checks
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// Monitoring middleware for request tracking
func monitoringMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Log request
		log.Printf("Request: %s %s from %s", r.Method, r.URL.Path, r.RemoteAddr)

		// Call next handler
		next.ServeHTTP(w, r)

		// Log response time
		duration := time.Since(start)
		log.Printf("Response: %s for %s %s in %v", "200", r.Method, r.URL.Path, duration)
	})
}

// Middleware for service-to-service authentication
func requireServiceAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// CRITICAL: Skip authentication for OPTIONS requests (CORS preflight)
		// CORS headers are already set by corsMiddleware
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		if serviceSecret == "" {
			// If no service secret is configured, skip auth (for local development)
			next(w, r)
			return
		}

		authHeader := r.Header.Get("X-Service-Auth")
		if authHeader == "" {
			http.Error(w, "Missing X-Service-Auth header", http.StatusUnauthorized)
			return
		}

		// Use constant-time comparison to prevent timing attacks
		if subtle.ConstantTimeCompare([]byte(authHeader), []byte(serviceSecret)) != 1 {
			http.Error(w, "Invalid service authentication", http.StatusUnauthorized)
			return
		}

		next(w, r)
	}
}

// Health check handler
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

// Metrics handler for monitoring
func metricsHandler(w http.ResponseWriter, r *http.Request) {
	uptime := time.Since(startTime)

	metrics := fmt.Sprintf(`# HELP statlas_content_uptime_seconds Total uptime in seconds
# TYPE statlas_content_uptime_seconds counter
statlas_content_uptime_seconds %f

# HELP statlas_content_info Service information
# TYPE statlas_content_info gauge
statlas_content_info{version="1.0.0",service="statlas-content-service"} 1
`, uptime.Seconds())

	w.Header().Set("Content-Type", "text/plain")
	w.Write([]byte(metrics))
}

// Geographic Reference Data handlers - New Hierarchical Structure

// Sovereign States handlers (209 total)
func getSovereignStatesHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	limit := getIntQueryParam(r, "limit", 50)

	query := firestoreClient.Collection("sovereign_states").
		Where("is_active", "==", true).
		Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting sovereign states: %v", err)
		http.Error(w, "Failed to get sovereign states", http.StatusInternalServerError)
		return
	}

	var sovereignStates []SovereignState
	for _, doc := range docs {
		var state SovereignState
		if err := doc.DataTo(&state); err != nil {
			log.Printf("Error parsing sovereign state data: %v", err)
			continue
		}
		sovereignStates = append(sovereignStates, state)
	}

	response := map[string]interface{}{
		"sovereign_states": sovereignStates,
		"count":            len(sovereignStates),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getSovereignStateHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	stateID := vars["id"]

	doc, err := firestoreClient.Collection("sovereign_states").Doc(stateID).Get(ctx)
	if err != nil {
		http.Error(w, "Sovereign state not found", http.StatusNotFound)
		return
	}

	var state SovereignState
	if err := doc.DataTo(&state); err != nil {
		http.Error(w, "Failed to parse sovereign state data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(state)
}

// Countries handlers (258 total)
func getCountriesHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	limit := getIntQueryParam(r, "limit", 50)
	sovereignStateID := r.URL.Query().Get("sovereign_state")

	query := firestoreClient.Collection("countries").Where("is_active", "==", true)

	if sovereignStateID != "" {
		query = query.Where("sovereign_state_id", "==", sovereignStateID)
	}

	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting countries: %v", err)
		http.Error(w, "Failed to get countries", http.StatusInternalServerError)
		return
	}

	var countries []Country
	for _, doc := range docs {
		var country Country
		if err := doc.DataTo(&country); err != nil {
			log.Printf("Error parsing country data: %v", err)
			continue
		}
		countries = append(countries, country)
	}

	response := map[string]interface{}{
		"countries": countries,
		"count":     len(countries),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getCountryHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	countryID := vars["id"]

	doc, err := firestoreClient.Collection("countries").Doc(countryID).Get(ctx)
	if err != nil {
		http.Error(w, "Country not found", http.StatusNotFound)
		return
	}

	var country Country
	if err := doc.DataTo(&country); err != nil {
		http.Error(w, "Failed to parse country data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(country)
}

// Map Units handlers (298 total)
func getMapUnitsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	limit := getIntQueryParam(r, "limit", 50)
	sovereignStateID := r.URL.Query().Get("sovereign_state")
	countryID := r.URL.Query().Get("country")

	query := firestoreClient.Collection("map_units").Where("is_active", "==", true)

	if sovereignStateID != "" {
		query = query.Where("sovereign_state_id", "==", sovereignStateID)
	}
	if countryID != "" {
		query = query.Where("country_id", "==", countryID)
	}

	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting map units: %v", err)
		http.Error(w, "Failed to get map units", http.StatusInternalServerError)
		return
	}

	var mapUnits []MapUnit
	for _, doc := range docs {
		var unit MapUnit
		if err := doc.DataTo(&unit); err != nil {
			log.Printf("Error parsing map unit data: %v", err)
			continue
		}
		mapUnits = append(mapUnits, unit)
	}

	response := map[string]interface{}{
		"map_units": mapUnits,
		"count":     len(mapUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getMapUnitHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	unitID := vars["id"]

	doc, err := firestoreClient.Collection("map_units").Doc(unitID).Get(ctx)
	if err != nil {
		http.Error(w, "Map unit not found", http.StatusNotFound)
		return
	}

	var unit MapUnit
	if err := doc.DataTo(&unit); err != nil {
		http.Error(w, "Failed to parse map unit data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(unit)
}

// Map Subunits handlers (360 total)
func getMapSubunitsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	limit := getIntQueryParam(r, "limit", 50)
	sovereignStateID := r.URL.Query().Get("sovereign_state")
	countryID := r.URL.Query().Get("country")
	mapUnitID := r.URL.Query().Get("map_unit")

	query := firestoreClient.Collection("map_subunits").Where("is_active", "==", true)

	if sovereignStateID != "" {
		query = query.Where("sovereign_state_id", "==", sovereignStateID)
	}
	if countryID != "" {
		query = query.Where("country_id", "==", countryID)
	}
	if mapUnitID != "" {
		query = query.Where("map_unit_id", "==", mapUnitID)
	}

	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting map subunits: %v", err)
		http.Error(w, "Failed to get map subunits", http.StatusInternalServerError)
		return
	}

	var mapSubunits []MapSubunit
	for _, doc := range docs {
		var subunit MapSubunit
		if err := doc.DataTo(&subunit); err != nil {
			log.Printf("Error parsing map subunit data: %v", err)
			continue
		}
		mapSubunits = append(mapSubunits, subunit)
	}

	response := map[string]interface{}{
		"map_subunits": mapSubunits,
		"count":        len(mapSubunits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getMapSubunitHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	subunitID := vars["id"]

	doc, err := firestoreClient.Collection("map_subunits").Doc(subunitID).Get(ctx)
	if err != nil {
		http.Error(w, "Map subunit not found", http.StatusNotFound)
		return
	}

	var subunit MapSubunit
	if err := doc.DataTo(&subunit); err != nil {
		http.Error(w, "Failed to parse map subunit data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(subunit)
}

// Hierarchical relationship handlers
func getSovereignStateCountriesHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	stateID := vars["id"]
	limit := getIntQueryParam(r, "limit", 50)

	query := firestoreClient.Collection("countries").
		Where("sovereign_state_id", "==", stateID).
		Where("is_active", "==", true).
		Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting countries for sovereign state: %v", err)
		http.Error(w, "Failed to get countries", http.StatusInternalServerError)
		return
	}

	var countries []Country
	for _, doc := range docs {
		var country Country
		if err := doc.DataTo(&country); err != nil {
			continue
		}
		countries = append(countries, country)
	}

	response := map[string]interface{}{
		"countries": countries,
		"count":     len(countries),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getCountryMapUnitsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	countryID := vars["id"]
	limit := getIntQueryParam(r, "limit", 50)

	query := firestoreClient.Collection("map_units").
		Where("country_id", "==", countryID).
		Where("is_active", "==", true).
		Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting map units for country: %v", err)
		http.Error(w, "Failed to get map units", http.StatusInternalServerError)
		return
	}

	var mapUnits []MapUnit
	for _, doc := range docs {
		var unit MapUnit
		if err := doc.DataTo(&unit); err != nil {
			continue
		}
		mapUnits = append(mapUnits, unit)
	}

	response := map[string]interface{}{
		"map_units": mapUnits,
		"count":     len(mapUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getMapUnitSubunitsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	unitID := vars["id"]
	limit := getIntQueryParam(r, "limit", 50)

	query := firestoreClient.Collection("map_subunits").
		Where("map_unit_id", "==", unitID).
		Where("is_active", "==", true).
		Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting subunits for map unit: %v", err)
		http.Error(w, "Failed to get map subunits", http.StatusInternalServerError)
		return
	}

	var mapSubunits []MapSubunit
	for _, doc := range docs {
		var subunit MapSubunit
		if err := doc.DataTo(&subunit); err != nil {
			continue
		}
		mapSubunits = append(mapSubunits, subunit)
	}

	response := map[string]interface{}{
		"map_subunits": mapSubunits,
		"count":        len(mapSubunits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Landmarks handlers
func getLandmarksHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Get query parameters for filtering
	countryID := r.URL.Query().Get("country")
	landmarkType := r.URL.Query().Get("type")
	category := r.URL.Query().Get("category")
	limit := getIntQueryParam(r, "limit", 50)

	query := firestoreClient.Collection("landmarks").Where("is_active", "==", true)

	if countryID != "" {
		query = query.Where("country_id", "==", countryID)
	}
	if landmarkType != "" {
		query = query.Where("type", "==", landmarkType)
	}
	if category != "" {
		query = query.Where("category", "==", category)
	}

	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting landmarks: %v", err)
		http.Error(w, "Failed to get landmarks", http.StatusInternalServerError)
		return
	}

	var landmarks []Landmark
	for _, doc := range docs {
		var landmark Landmark
		if err := doc.DataTo(&landmark); err != nil {
			log.Printf("Error parsing landmark data: %v", err)
			continue
		}
		landmarks = append(landmarks, landmark)
	}

	response := map[string]interface{}{
		"landmarks": landmarks,
		"count":     len(landmarks),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getLandmarkHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	vars := mux.Vars(r)
	landmarkID := vars["id"]

	doc, err := firestoreClient.Collection("landmarks").Doc(landmarkID).Get(ctx)
	if err != nil {
		http.Error(w, "Landmark not found", http.StatusNotFound)
		return
	}

	var landmark Landmark
	if err := doc.DataTo(&landmark); err != nil {
		http.Error(w, "Failed to parse landmark data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(landmark)
}

func getLandmarksNearbyHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Parse query parameters
	lat, err := strconv.ParseFloat(r.URL.Query().Get("lat"), 64)
	if err != nil {
		http.Error(w, "Invalid lat parameter", http.StatusBadRequest)
		return
	}

	lon, err := strconv.ParseFloat(r.URL.Query().Get("lon"), 64)
	if err != nil {
		http.Error(w, "Invalid lon parameter", http.StatusBadRequest)
		return
	}

	radius := getFloatQueryParam(r, "radius", 1000) // Default 1km radius
	limit := getIntQueryParam(r, "limit", 20)

	// Create bounding box for efficient query
	bounds := calculateBoundingBox(lat, lon, radius)

	query := firestoreClient.Collection("landmarks").
		Where("is_active", "==", true).
		Where("coordinates.lat", ">=", bounds.MinLat).
		Where("coordinates.lat", "<=", bounds.MaxLat).
		Limit(limit * 2) // Get more to filter by precise distance

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting nearby landmarks: %v", err)
		http.Error(w, "Failed to get landmarks", http.StatusInternalServerError)
		return
	}

	var landmarks []map[string]interface{}
	for _, doc := range docs {
		var landmark Landmark
		if err := doc.DataTo(&landmark); err != nil {
			continue
		}

		// Calculate precise distance
		distance := calculateDistance(lat, lon, landmark.Coordinates.Lat, landmark.Coordinates.Lon)
		if distance <= radius {
			landmarkWithDistance := map[string]interface{}{
				"id":                      landmark.ID,
				"name":                    landmark.Name,
				"type":                    landmark.Type,
				"coordinates":             landmark.Coordinates,
				"precision_radius_meters": landmark.PrecisionRadiusMeters,
				"distance_meters":         int(distance),
				"achievement":             landmark.Achievement,
				"visiting_info":           landmark.VisitingInfo,
				"short_description":       landmark.ShortDescription,
			}
			landmarks = append(landmarks, landmarkWithDistance)
		}

		if len(landmarks) >= limit {
			break
		}
	}

	response := map[string]interface{}{
		"landmarks": landmarks,
		"count":     len(landmarks),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Boundaries handlers
func getBoundariesContainingHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	
	// Parse coordinates
	lat, err := strconv.ParseFloat(r.URL.Query().Get("lat"), 64)
	if err != nil {
		http.Error(w, "Invalid lat parameter", http.StatusBadRequest)
		return
	}

	lon, err := strconv.ParseFloat(r.URL.Query().Get("lon"), 64)
	if err != nil {
		http.Error(w, "Invalid lon parameter", http.StatusBadRequest)
		return
	}

	// Find containing boundaries by checking all hierarchical levels
	var boundaries []map[string]interface{}
	
	// Check sovereign states
	if states := findContainingEntities(ctx, "sovereign_states", lat, lon); len(states) > 0 {
		boundaries = append(boundaries, map[string]interface{}{
			"type":     "sovereign_state",
			"entities": states,
		})
	}
	
	// Check countries  
	if countries := findContainingEntities(ctx, "countries", lat, lon); len(countries) > 0 {
		boundaries = append(boundaries, map[string]interface{}{
			"type":     "country",
			"entities": countries,
		})
	}
	
	// Check map units
	if units := findContainingEntities(ctx, "map_units", lat, lon); len(units) > 0 {
		boundaries = append(boundaries, map[string]interface{}{
			"type":     "map_unit", 
			"entities": units,
		})
	}
	
	// Check map subunits
	if subunits := findContainingEntities(ctx, "map_subunits", lat, lon); len(subunits) > 0 {
		boundaries = append(boundaries, map[string]interface{}{
			"type":     "map_subunit",
			"entities": subunits,
		})
	}
	
	response := map[string]interface{}{
		"lat":        lat,
		"lon":        lon,
		"boundaries": boundaries,
		"count":      len(boundaries),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Batch lookup handler for Core Service integration
func batchLookupBoundariesHandler(w http.ResponseWriter, r *http.Request) {
	var request BatchLookupRequest
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	var results []SquareEnrichment
	for _, point := range request.Points {
		// Get boundaries for this point
		boundaries := getMockBoundariesForPoint(point.Lat, point.Lon)

		// Extract boundary tags and determine resolution
		var boundaryTags []string
		resolution := "1km" // default

		for _, boundary := range boundaries {
			boundaryTags = append(boundaryTags, strings.ToLower(boundary["name"].(string)))
			if boundary["resolution_requirement"] != nil {
				resolution = boundary["resolution_requirement"].(string)
			}
		}

		// Get nearby landmarks (mock for now)
		landmarksNearby := getMockLandmarksForPoint(point.Lat, point.Lon)

		result := SquareEnrichment{
			SquareID:        point.SquareID,
			BoundaryTags:    boundaryTags,
			Resolution:      resolution,
			LandmarksNearby: landmarksNearby,
		}
		results = append(results, result)
	}

	response := BatchLookupResponse{Results: results}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Achievement definitions handler
func getAchievementDefinitionsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Get achievements from landmarks
	landmarkDocs, err := firestoreClient.Collection("landmarks").
		Where("is_active", "==", true).
		Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting landmark achievements: %v", err)
		http.Error(w, "Failed to get achievements", http.StatusInternalServerError)
		return
	}

	var achievements []map[string]interface{}
	for _, doc := range landmarkDocs {
		var landmark Landmark
		if err := doc.DataTo(&landmark); err != nil {
			continue
		}

		achievement := map[string]interface{}{
			"id":                      landmark.Achievement.ID,
			"title":                   landmark.Achievement.Title,
			"description":             landmark.Achievement.Description,
			"points":                  landmark.Achievement.Points,
			"rarity":                  landmark.Achievement.Rarity,
			"category":                landmark.Achievement.Category,
			"landmark_id":             landmark.ID,
			"precision_radius_meters": landmark.PrecisionRadiusMeters,
			"unlock_message":          landmark.Achievement.UnlockMessage,
		}
		achievements = append(achievements, achievement)
	}

	// Get achievements from restaurants
	restaurantDocs, err := firestoreClient.Collection("restaurants").
		Where("is_active", "==", true).
		Documents(ctx).GetAll()
	if err == nil {
		for _, doc := range restaurantDocs {
			var restaurant Restaurant
			if err := doc.DataTo(&restaurant); err != nil {
				continue
			}

			achievement := map[string]interface{}{
				"id":                      restaurant.Achievement.ID,
				"title":                   restaurant.Achievement.Title,
				"description":             restaurant.Achievement.Description,
				"points":                  restaurant.Achievement.Points,
				"rarity":                  restaurant.Achievement.Rarity,
				"category":                restaurant.Achievement.Category,
				"restaurant_id":           restaurant.ID,
				"precision_radius_meters": restaurant.PrecisionRadiusMeters,
				"unlock_message":          restaurant.Achievement.UnlockMessage,
			}
			achievements = append(achievements, achievement)
		}
	}

	response := map[string]interface{}{
		"achievements": achievements,
		"count":        len(achievements),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Placeholder handlers for other endpoints
func getCountryStatesHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"states": []interface{}{}, "count": 0})
}

func getStateHandler(w http.ResponseWriter, r *http.Request) {
	http.Error(w, "State not found", http.StatusNotFound)
}

func getStateCitiesHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"cities": []interface{}{}, "count": 0})
}

func getCityHandler(w http.ResponseWriter, r *http.Request) {
	http.Error(w, "City not found", http.StatusNotFound)
}

func getRestaurantsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"restaurants": []interface{}{}, "count": 0})
}

func getMichelinRestaurantsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"restaurants": []interface{}{}, "count": 0})
}

func getBoundariesHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"boundaries": []interface{}{}, "count": 0})
}

func getBoundaryHandler(w http.ResponseWriter, r *http.Request) {
	http.Error(w, "Boundary not found", http.StatusNotFound)
}

func searchContentHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"results": []interface{}{}, "count": 0})
}

func createCountryHandler(w http.ResponseWriter, r *http.Request) {
	http.Error(w, "Not implemented", http.StatusNotImplemented)
}

func createLandmarkHandler(w http.ResponseWriter, r *http.Request) {
	http.Error(w, "Not implemented", http.StatusNotImplemented)
}

func createBoundaryHandler(w http.ResponseWriter, r *http.Request) {
	http.Error(w, "Not implemented", http.StatusNotImplemented)
}

// Utility functions
func getIntQueryParam(r *http.Request, param string, defaultValue int) int {
	value := r.URL.Query().Get(param)
	if value == "" {
		return defaultValue
	}

	intValue, err := strconv.Atoi(value)
	if err != nil {
		return defaultValue
	}

	return intValue
}

func getFloatQueryParam(r *http.Request, param string, defaultValue float64) float64 {
	value := r.URL.Query().Get(param)
	if value == "" {
		return defaultValue
	}

	floatValue, err := strconv.ParseFloat(value, 64)
	if err != nil {
		return defaultValue
	}

	return floatValue
}

func calculateBoundingBox(lat, lon, radiusMeters float64) Bounds {
	// Rough approximation for bounding box
	latDelta := radiusMeters / 111000.0 // ~111km per degree latitude
	lonDelta := radiusMeters / (111000.0 * math.Cos(lat*math.Pi/180.0))

	return Bounds{
		MinLat: lat - latDelta,
		MaxLat: lat + latDelta,
		MinLon: lon - lonDelta,
		MaxLon: lon + lonDelta,
	}
}

func calculateDistance(lat1, lon1, lat2, lon2 float64) float64 {
	// Haversine formula for distance calculation
	const R = 6371000 // Earth's radius in meters

	dLat := (lat2 - lat1) * math.Pi / 180.0
	dLon := (lon2 - lon1) * math.Pi / 180.0

	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180.0)*math.Cos(lat2*math.Pi/180.0)*
			math.Sin(dLon/2)*math.Sin(dLon/2)

	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

	return R * c
}

// Mock functions for demonstration (replace with real implementations)
func getMockBoundariesForPoint(lat, lon float64) []map[string]interface{} {
	// Mock boundary detection - replace with actual point-in-polygon queries
	boundaries := []map[string]interface{}{}

	// USA boundaries (very rough approximation)
	if lat >= 25.0 && lat <= 49.0 && lon >= -125.0 && lon <= -66.0 {
		boundaries = append(boundaries, map[string]interface{}{
			"id":                     "usa",
			"name":                   "United States",
			"type":                   "country",
			"level":                  0,
			"resolution_requirement": "1km",
		})

		// New York state (rough)
		if lat >= 40.4 && lat <= 45.0 && lon >= -79.8 && lon <= -71.8 {
			boundaries = append(boundaries, map[string]interface{}{
				"id":                     "ny_usa",
				"name":                   "New York",
				"type":                   "state",
				"level":                  1,
				"resolution_requirement": "100m",
			})

			// NYC (rough)
			if lat >= 40.4 && lat <= 40.9 && lon >= -74.3 && lon <= -73.7 {
				boundaries = append(boundaries, map[string]interface{}{
					"id":                     "nyc_ny_usa",
					"name":                   "New York City",
					"type":                   "city",
					"level":                  2,
					"resolution_requirement": "100m",
				})

				// Manhattan (rough)
				if lat >= 40.68 && lat <= 40.88 && lon >= -74.05 && lon <= -73.90 {
					boundaries = append(boundaries, map[string]interface{}{
						"id":                     "manhattan_core",
						"name":                   "Manhattan",
						"type":                   "borough",
						"level":                  3,
						"resolution_requirement": "100m",
					})
				}
			}
		}
	}

	return boundaries
}

func getMockLandmarksForPoint(lat, lon float64) []string {
	landmarks := []string{}

	// NYC area landmarks
	if lat >= 40.4 && lat <= 40.9 && lon >= -74.3 && lon <= -73.7 {
		landmarks = append(landmarks, "statue_of_liberty", "empire_state_building", "central_park")
	}

	return landmarks
}
