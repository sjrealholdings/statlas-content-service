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
	Continent    string    `firestore:"continent" json:"continent"` // e.g. "Europe", "North America"
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
	Continent        string    `firestore:"continent" json:"continent"`   // e.g. "Europe", "North America"
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
	Continent        string    `firestore:"continent" json:"continent"` // e.g. "North America", "Oceania"
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

// AdminLevel1 represents first-level administrative divisions (states, provinces, regions)
type AdminLevel1 struct {
	ID          string    `firestore:"id" json:"id"`                   // GADM GID_1 (e.g. "USA.1_1")
	Name        string    `firestore:"name" json:"name"`               // e.g. "California"
	CountryGID  string    `firestore:"country_gid" json:"country_gid"` // GADM GID_0 (e.g. "USA")
	CountryName string    `firestore:"country_name" json:"country_name"`
	AdminType   string    `firestore:"admin_type" json:"admin_type"`       // Local type name
	AdminTypeEN string    `firestore:"admin_type_en" json:"admin_type_en"` // English type name (State, Province, etc.)
	Bounds      Bounds    `firestore:"bounds" json:"bounds"`
	Geometry    string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt   time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt   time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive    bool      `firestore:"is_active" json:"is_active"`
}

// AdminLevel2 represents second-level administrative divisions (counties, districts)
type AdminLevel2 struct {
	ID          string    `firestore:"id" json:"id"`                   // GADM GID_2
	Name        string    `firestore:"name" json:"name"`               // e.g. "Los Angeles County"
	CountryGID  string    `firestore:"country_gid" json:"country_gid"` // GADM GID_0
	CountryName string    `firestore:"country_name" json:"country_name"`
	StateGID    string    `firestore:"state_gid" json:"state_gid"` // GADM GID_1
	StateName   string    `firestore:"state_name" json:"state_name"`
	AdminType   string    `firestore:"admin_type" json:"admin_type"`
	AdminTypeEN string    `firestore:"admin_type_en" json:"admin_type_en"` // County, District, etc.
	Bounds      Bounds    `firestore:"bounds" json:"bounds"`
	Geometry    string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt   time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt   time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive    bool      `firestore:"is_active" json:"is_active"`
}

// AdminLevel3 represents third-level administrative divisions (municipalities, cities)
type AdminLevel3 struct {
	ID          string    `firestore:"id" json:"id"`                   // GADM GID_3
	Name        string    `firestore:"name" json:"name"`               // e.g. "Los Angeles"
	CountryGID  string    `firestore:"country_gid" json:"country_gid"` // GADM GID_0
	CountryName string    `firestore:"country_name" json:"country_name"`
	StateGID    string    `firestore:"state_gid" json:"state_gid"` // GADM GID_1
	StateName   string    `firestore:"state_name" json:"state_name"`
	CountyGID   string    `firestore:"county_gid" json:"county_gid"` // GADM GID_2
	CountyName  string    `firestore:"county_name" json:"county_name"`
	AdminType   string    `firestore:"admin_type" json:"admin_type"`
	AdminTypeEN string    `firestore:"admin_type_en" json:"admin_type_en"` // Municipality, City, etc.
	Bounds      Bounds    `firestore:"bounds" json:"bounds"`
	Geometry    string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt   time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt   time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive    bool      `firestore:"is_active" json:"is_active"`
}

// AdminLevel4 represents fourth-level administrative divisions (wards, villages)
type AdminLevel4 struct {
	ID               string    `firestore:"id" json:"id"`                   // GADM GID_4
	Name             string    `firestore:"name" json:"name"`               // e.g. "Downtown Ward"
	CountryGID       string    `firestore:"country_gid" json:"country_gid"` // GADM GID_0
	CountryName      string    `firestore:"country_name" json:"country_name"`
	StateGID         string    `firestore:"state_gid" json:"state_gid"` // GADM GID_1
	StateName        string    `firestore:"state_name" json:"state_name"`
	CountyGID        string    `firestore:"county_gid" json:"county_gid"` // GADM GID_2
	CountyName       string    `firestore:"county_name" json:"county_name"`
	MunicipalityGID  string    `firestore:"municipality_gid" json:"municipality_gid"` // GADM GID_3
	MunicipalityName string    `firestore:"municipality_name" json:"municipality_name"`
	AdminType        string    `firestore:"admin_type" json:"admin_type"`
	AdminTypeEN      string    `firestore:"admin_type_en" json:"admin_type_en"` // Ward, Village, etc.
	Bounds           Bounds    `firestore:"bounds" json:"bounds"`
	Geometry         string    `firestore:"geometry" json:"geometry"` // GeoJSON geometry as string
	CreatedAt        time.Time `firestore:"created_at" json:"created_at"`
	UpdatedAt        time.Time `firestore:"updated_at" json:"updated_at"`
	IsActive         bool      `firestore:"is_active" json:"is_active"`
}

// AdminLevel5 represents fifth-level administrative divisions (neighborhoods, sub-villages)
type AdminLevel5 struct {
	ID               string    `firestore:"id" json:"id"`                   // GADM GID_5
	Name             string    `firestore:"name" json:"name"`               // e.g. "Financial District"
	CountryGID       string    `firestore:"country_gid" json:"country_gid"` // GADM GID_0
	CountryName      string    `firestore:"country_name" json:"country_name"`
	StateGID         string    `firestore:"state_gid" json:"state_gid"` // GADM GID_1
	StateName        string    `firestore:"state_name" json:"state_name"`
	CountyGID        string    `firestore:"county_gid" json:"county_gid"` // GADM GID_2
	CountyName       string    `firestore:"county_name" json:"county_name"`
	MunicipalityGID  string    `firestore:"municipality_gid" json:"municipality_gid"` // GADM GID_3
	MunicipalityName string    `firestore:"municipality_name" json:"municipality_name"`
	WardGID          string    `firestore:"ward_gid" json:"ward_gid"` // GADM GID_4
	WardName         string    `firestore:"ward_name" json:"ward_name"`
	AdminType        string    `firestore:"admin_type" json:"admin_type"`
	AdminTypeEN      string    `firestore:"admin_type_en" json:"admin_type_en"` // Neighborhood, Sub-village, etc.
	Bounds           Bounds    `firestore:"bounds" json:"bounds"`
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

// Helper function to find entities containing a point (EFFICIENT VERSION - USES COMPOSITE INDEXES)
func findContainingEntities(ctx context.Context, collection string, lat, lon float64) []map[string]interface{} {
	var results []map[string]interface{}

	// Stage 1: Bounding box pre-filter (efficient query using composite indexes)
	// This dramatically reduces the number of documents we need to check
	query := firestoreClient.Collection(collection).
		Where("is_active", "==", true).
		Where("bounds.min_lat", "<=", lat).
		Where("bounds.max_lat", ">=", lat).
		Where("bounds.min_lon", "<=", lon).
		Where("bounds.max_lon", ">=", lon)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error querying %s collection: %v", collection, err)
		return results
	}

	log.Printf("Bounding box filter for %s: %d candidates (lat=%.6f, lon=%.6f)",
		collection, len(docs), lat, lon)

	// Stage 2: Precise point-in-polygon check on candidates only
	for _, doc := range docs {
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

	log.Printf("Point-in-polygon results for %s: %d matches", collection, len(results))
	return results
}

// getCountryPolygonHandler returns the polygon geometry for a specific country or territory
func getCountryPolygonHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	countryID := vars["id"]

	ctx := context.Background()

	// Only search in countries collection to avoid double-counting
	doc, err := firestoreClient.Collection("countries").Doc(countryID).Get(ctx)
	if err != nil {
		http.Error(w, "Country not found", http.StatusNotFound)
		return
	}

	var data map[string]interface{}
	if err := doc.DataTo(&data); err != nil {
		http.Error(w, "Failed to parse country data", http.StatusInternalServerError)
		return
	}

	// Check if this document is active and has geometry
	if active, ok := data["is_active"].(bool); !ok || !active {
		http.Error(w, "Country not active", http.StatusNotFound)
		return
	}

	geometry, ok := data["geometry"].(string)
	if !ok || geometry == "" {
		http.Error(w, "Country geometry not available", http.StatusNotFound)
		return
	}

	// Return the geometry as GeoJSON
	response := map[string]interface{}{
		"id":       countryID,
		"name":     data["name"],
		"type":     "country",
		"geometry": geometry,
		"bounds":   data["bounds"],
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// getContinentPolygonsHandler returns all country polygons for a specific continent
func getContinentPolygonsHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	continent := vars["continent"]

	ctx := context.Background()
	var allPolygons []map[string]interface{}

	// Only search in countries collection to avoid double-counting
	query := firestoreClient.Collection("countries").
		Where("is_active", "==", true).
		Where("continent", "==", continent)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error querying countries collection: %v", err)
		http.Error(w, "Failed to fetch continent data", http.StatusInternalServerError)
		return
	}

	for _, doc := range docs {
		var data map[string]interface{}
		if err := doc.DataTo(&data); err != nil {
			continue
		}

		geometry, ok := data["geometry"].(string)
		if !ok || geometry == "" {
			continue
		}

		polygon := map[string]interface{}{
			"id":       data["id"],
			"name":     data["name"],
			"type":     "country",
			"geometry": geometry,
			"bounds":   data["bounds"],
		}

		allPolygons = append(allPolygons, polygon)
	}

	response := map[string]interface{}{
		"continent": continent,
		"count":     len(allPolygons),
		"polygons":  allPolygons,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// getWorldPolygonsHandler returns all country polygons in the world
func getWorldPolygonsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()
	var allPolygons []map[string]interface{}

	// Only search in countries collection to avoid double-counting
	query := firestoreClient.Collection("countries").
		Where("is_active", "==", true)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error querying countries collection: %v", err)
		http.Error(w, "Failed to fetch world data", http.StatusInternalServerError)
		return
	}

	for _, doc := range docs {
		var data map[string]interface{}
		if err := doc.DataTo(&data); err != nil {
			continue
		}

		geometry, ok := data["geometry"].(string)
		if !ok || geometry == "" {
			continue
		}

		polygon := map[string]interface{}{
			"id":        data["id"],
			"name":      data["name"],
			"type":      "country",
			"continent": data["continent"],
			"geometry":  geometry,
			"bounds":    data["bounds"],
		}

		allPolygons = append(allPolygons, polygon)
	}

	response := map[string]interface{}{
		"world":    true,
		"count":    len(allPolygons),
		"polygons": allPolygons,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// classifyPointHandler classifies a point as land or ocean and determines grid resolution
func classifyPointHandler(w http.ResponseWriter, r *http.Request) {
	// Parse query parameters
	latStr := r.URL.Query().Get("lat")
	lonStr := r.URL.Query().Get("lon")
	
	if latStr == "" || lonStr == "" {
		http.Error(w, "Missing lat or lon parameters", http.StatusBadRequest)
		return
	}
	
	lat, err := strconv.ParseFloat(latStr, 64)
	if err != nil {
		http.Error(w, "Invalid lat parameter", http.StatusBadRequest)
		return
	}
	
	lon, err := strconv.ParseFloat(lonStr, 64)
	if err != nil {
		http.Error(w, "Invalid lon parameter", http.StatusBadRequest)
		return
	}
	
	// Validate coordinates
	if lat < -90 || lat > 90 || lon < -180 || lon > 180 {
		http.Error(w, "Coordinates out of valid range", http.StatusBadRequest)
		return
	}
	
	ctx := context.Background()
	
	// Classify point and calculate distance to coast
	isLand, distanceToCoast, err := classifyPoint(ctx, lat, lon)
	if err != nil {
		log.Printf("Error classifying point: %v", err)
		http.Error(w, "Failed to classify point", http.StatusInternalServerError)
		return
	}
	
	// Determine grid resolution based on location and distance
	gridResolution := determineGridResolution(isLand, distanceToCoast)
	
	response := map[string]interface{}{
		"lat": lat,
		"lon": lon,
		"result": map[string]interface{}{
			"type":                "land",
			"distance_to_coast_km": distanceToCoast,
			"grid_resolution":     gridResolution,
		},
	}
	
	if !isLand {
		response["result"].(map[string]interface{})["type"] = "ocean"
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// distanceToCoastHandler calculates distance to nearest coastline
func distanceToCoastHandler(w http.ResponseWriter, r *http.Request) {
	// Parse query parameters
	latStr := r.URL.Query().Get("lat")
	lonStr := r.URL.Query().Get("lon")
	
	if latStr == "" || lonStr == "" {
		http.Error(w, "Missing lat or lon parameters", http.StatusBadRequest)
		return
	}
	
	lat, err := strconv.ParseFloat(latStr, 64)
	if err != nil {
		http.Error(w, "Invalid lat parameter", http.StatusBadRequest)
		return
	}
	
	lon, err := strconv.ParseFloat(lonStr, 64)
	if err != nil {
		http.Error(w, "Invalid lon parameter", http.StatusBadRequest)
		return
	}
	
	ctx := context.Background()
	
	// Calculate distance to coast
	distance, nearestPoint, err := calculateDistanceToCoast(ctx, lat, lon)
	if err != nil {
		log.Printf("Error calculating distance to coast: %v", err)
		http.Error(w, "Failed to calculate distance", http.StatusInternalServerError)
		return
	}
	
	response := map[string]interface{}{
		"lat": lat,
		"lon": lon,
		"result": map[string]interface{}{
			"distance_to_coast_km": distance,
			"nearest_coast_point": nearestPoint,
		},
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// batchClassifyHandler processes multiple points for grid generation
func batchClassifyHandler(w http.ResponseWriter, r *http.Request) {
	var request struct {
		Points []struct {
			Lat float64 `json:"lat"`
			Lon float64 `json:"lon"`
		} `json:"points"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, "Invalid JSON body", http.StatusBadRequest)
		return
	}
	
	if len(request.Points) == 0 {
		http.Error(w, "No points provided", http.StatusBadRequest)
		return
	}
	
	if len(request.Points) > 1000 {
		http.Error(w, "Too many points (max 1000)", http.StatusBadRequest)
		return
	}
	
	ctx := context.Background()
	results := make([]map[string]interface{}, 0, len(request.Points))
	
	for _, point := range request.Points {
		// Validate coordinates
		if point.Lat < -90 || point.Lat > 90 || point.Lon < -180 || point.Lon > 180 {
			results = append(results, map[string]interface{}{
				"error": "Invalid coordinates",
			})
			continue
		}
		
		// Classify point
		isLand, distanceToCoast, err := classifyPoint(ctx, point.Lat, point.Lon)
		if err != nil {
			log.Printf("Error classifying point (%f, %f): %v", point.Lat, point.Lon, err)
			results = append(results, map[string]interface{}{
				"error": "Classification failed",
			})
			continue
		}
		
		// Determine grid resolution
		gridResolution := determineGridResolution(isLand, distanceToCoast)
		
		result := map[string]interface{}{
			"type":                "ocean",
			"distance_to_coast_km": distanceToCoast,
			"grid_resolution":     gridResolution,
		}
		
		if isLand {
			result["type"] = "land"
		}
		
		results = append(results, result)
	}
	
	response := map[string]interface{}{
		"results": results,
		"count":   len(results),
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// classifyPoint determines if a point is on land or in ocean and calculates distance to coast
func classifyPoint(ctx context.Context, lat, lon float64) (isLand bool, distanceToCoast float64, err error) {
	// First try to use land polygons for direct classification
	isLand, err = isPointOnLand(ctx, lat, lon)
	if err != nil {
		// Fallback to coastline-based classification
		log.Printf("Land polygon classification failed, using coastline fallback: %v", err)
		distanceToCoast, _, err = calculateDistanceToCoast(ctx, lat, lon)
		if err != nil {
			return false, 0, err
		}
		// Assume land if very close to coast (within 1km)
		isLand = distanceToCoast < 1.0
	} else {
		// Calculate distance to coast for grid resolution determination
		distanceToCoast, _, err = calculateDistanceToCoast(ctx, lat, lon)
		if err != nil {
			// Use default distance if calculation fails
			distanceToCoast = 10.0
		}
	}
	
	return isLand, distanceToCoast, nil
}

// isPointOnLand checks if a point is within any land polygon
func isPointOnLand(ctx context.Context, lat, lon float64) (bool, error) {
	// Query land polygons that might contain this point
	// This is a simplified implementation - in production you'd use spatial indexing
	collection := firestoreClient.Collection("land_polygons")
	
	// Get all land polygons (this should be optimized with spatial indexing)
	docs, err := collection.Where("is_active", "==", true).Documents(ctx).GetAll()
	if err != nil {
		return false, err
	}
	
	// Check if point is in any land polygon
	for _, doc := range docs {
		data := doc.Data()
		geometryStr, ok := data["geometry"].(string)
		if !ok {
			continue
		}
		
		// This is a placeholder - you'd need to implement actual point-in-polygon
		// using a geometry library like go-geom or by calling a spatial service
		_ = geometryStr
		
		// For now, return a simple heuristic based on bounds
		if bounds, ok := data["bounds"].(map[string]interface{}); ok {
			minLat, _ := bounds["min_lat"].(float64)
			maxLat, _ := bounds["max_lat"].(float64)
			minLon, _ := bounds["min_lon"].(float64)
			maxLon, _ := bounds["max_lon"].(float64)
			
			if lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon {
				// Point is within bounds - would need actual point-in-polygon test
				return true, nil
			}
		}
	}
	
	return false, nil
}

// calculateDistanceToCoast calculates distance to nearest coastline
func calculateDistanceToCoast(ctx context.Context, lat, lon float64) (distance float64, nearestPoint map[string]float64, err error) {
	// Query coastlines near this point
	collection := firestoreClient.Collection("coastlines")
	
	// Get all coastlines (this should be optimized with spatial indexing)
	docs, err := collection.Where("is_active", "==", true).Documents(ctx).GetAll()
	if err != nil {
		return 0, nil, err
	}
	
	minDistance := float64(99999999) // Very large number
	var closestPoint map[string]float64
	
	// Find closest point on any coastline
	for _, doc := range docs {
		data := doc.Data()
		
		// Check if point is within reasonable bounds of this coastline
		if bounds, ok := data["bounds"].(map[string]interface{}); ok {
			minLat, _ := bounds["min_lat"].(float64)
			maxLat, _ := bounds["max_lat"].(float64)
			minLon, _ := bounds["min_lon"].(float64)
			maxLon, _ := bounds["max_lon"].(float64)
			
			// Expand bounds by ~2 degrees for distance calculations
			if lat < minLat-2 || lat > maxLat+2 || lon < minLon-2 || lon > maxLon+2 {
				continue
			}
		}
		
		// This is a simplified distance calculation
		// In production, you'd calculate actual distance to the coastline geometry
		if bounds, ok := data["bounds"].(map[string]interface{}); ok {
			centerLat := (bounds["min_lat"].(float64) + bounds["max_lat"].(float64)) / 2
			centerLon := (bounds["min_lon"].(float64) + bounds["max_lon"].(float64)) / 2
			
			dist := haversineDistance(lat, lon, centerLat, centerLon)
			if dist < minDistance {
				minDistance = dist
				closestPoint = map[string]float64{
					"lat": centerLat,
					"lon": centerLon,
				}
			}
		}
	}
	
	if closestPoint == nil {
		return 0, nil, fmt.Errorf("no coastlines found")
	}
	
	return minDistance, closestPoint, nil
}

// determineGridResolution determines appropriate grid resolution based on location
func determineGridResolution(isLand bool, distanceToCoast float64) string {
	if isLand {
		// On land: use urban density when available, default to 1x1km
		// TODO: Integrate with urban density data
		return "1x1km" // Will be "100x100m" in urban areas
	} else {
		// In ocean: use distance from coast
		if distanceToCoast > 1000 {
			return "100x100km"
		} else {
			return "10x10km"
		}
	}
}

// haversineDistance calculates the distance between two points using the Haversine formula
func haversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371 // Earth's radius in kilometers
	
	dLat := (lat2 - lat1) * math.Pi / 180
	dLon := (lon2 - lon1) * math.Pi / 180
	
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180)*math.Cos(lat2*math.Pi/180)*
		math.Sin(dLon/2)*math.Sin(dLon/2)
	
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	
	return R * c
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
	router.HandleFunc("/countries/bulk", requireServiceAuth(getBulkCountriesHandler)).Methods("GET", "OPTIONS")
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

	// Administrative Boundaries endpoints (GADM data)
	router.HandleFunc("/admin/level-1", requireServiceAuth(getAdminLevel1Handler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-1/{id}", requireServiceAuth(getAdminLevel1ByIdHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-2", requireServiceAuth(getAdminLevel2Handler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-2/{id}", requireServiceAuth(getAdminLevel2ByIdHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-3", requireServiceAuth(getAdminLevel3Handler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-3/{id}", requireServiceAuth(getAdminLevel3ByIdHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-4", requireServiceAuth(getAdminLevel4Handler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-4/{id}", requireServiceAuth(getAdminLevel4ByIdHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-5", requireServiceAuth(getAdminLevel5Handler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/admin/level-5/{id}", requireServiceAuth(getAdminLevel5ByIdHandler)).Methods("GET", "OPTIONS")

	// Comprehensive location lookup
	router.HandleFunc("/location/lookup", requireServiceAuth(getLocationLookupHandler)).Methods("GET", "OPTIONS")

	// Boundaries & Geographic Features endpoints
	router.HandleFunc("/boundaries", requireServiceAuth(getBoundariesHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/boundaries/containing", requireServiceAuth(getBoundariesContainingHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/boundaries/{id}", requireServiceAuth(getBoundaryHandler)).Methods("GET", "OPTIONS")

	// Bulk & Integration APIs
	router.HandleFunc("/boundaries/batch-lookup", requireServiceAuth(batchLookupBoundariesHandler)).Methods("POST", "OPTIONS")
	router.HandleFunc("/achievements/definitions", requireServiceAuth(getAchievementDefinitionsHandler)).Methods("GET", "OPTIONS")

	// Search & Discovery endpoints
	router.HandleFunc("/search", requireServiceAuth(searchContentHandler)).Methods("GET", "OPTIONS")

	// Polygon/Geometry endpoints for frontend mapping
	router.HandleFunc("/polygons/country/{id}", requireServiceAuth(getCountryPolygonHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/polygons/continent/{continent}", requireServiceAuth(getContinentPolygonsHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/polygons/world", requireServiceAuth(getWorldPolygonsHandler)).Methods("GET", "OPTIONS")

	// Coastline detection endpoints for grid generation
	router.HandleFunc("/coastline/classify", requireServiceAuth(classifyPointHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/coastline/distance", requireServiceAuth(distanceToCoastHandler)).Methods("GET", "OPTIONS")
	router.HandleFunc("/coastline/batch-classify", requireServiceAuth(batchClassifyHandler)).Methods("POST", "OPTIONS")

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

// Bulk countries handler for Core Service integration
func getBulkCountriesHandler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Get all sovereign states
	sovereignQuery := firestoreClient.Collection("sovereign_states").
		Where("is_active", "==", true)

	sovereignDocs, err := sovereignQuery.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting sovereign states: %v", err)
		http.Error(w, "Failed to get sovereign states", http.StatusInternalServerError)
		return
	}

	// Get all countries
	countriesQuery := firestoreClient.Collection("countries").
		Where("is_active", "==", true)

	countryDocs, err := countriesQuery.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting countries: %v", err)
		http.Error(w, "Failed to get countries", http.StatusInternalServerError)
		return
	}

	// Note: We don't include map_units in the countries endpoint
	// Map units are separate territorial entities and should be accessed via /map-units endpoint

	// Build maps for lookups
	sovereignMap := make(map[string]SovereignState)
	for _, doc := range sovereignDocs {
		var sovereign SovereignState
		if err := doc.DataTo(&sovereign); err != nil {
			continue
		}
		sovereignMap[sovereign.ID] = sovereign
	}

	// Track processed entities to avoid duplicates
	processedEntities := make(map[string]bool)
	var result []map[string]interface{}

	// Process sovereign states first
	for _, doc := range sovereignDocs {
		var sovereign SovereignState
		if err := doc.DataTo(&sovereign); err != nil {
			continue
		}

		// Mark as processed
		processedEntities[sovereign.ID] = true

		entry := map[string]interface{}{
			"code":                 sovereign.ISOAlpha2,
			"name":                 sovereign.Name,
			"continent":            sovereign.Continent,
			"sovereign_state_name": nil, // null for sovereign states
			"is_territory":         false,
			"id":                   sovereign.ID,
			"official_name":        sovereign.OfficialName,
			"type":                 "sovereign_state",
			"iso_alpha2":           sovereign.ISOAlpha2,
			"iso_alpha3":           sovereign.ISOAlpha3,
			"flag_emoji":           sovereign.FlagEmoji,
			"capital":              sovereign.Capital,
			"population":           sovereign.Population,
			"area_km2":             sovereign.AreaKM2,
			"bounds":               sovereign.Bounds,
		}

		result = append(result, entry)
	}

	// Process countries that aren't sovereign states
	for _, doc := range countryDocs {
		var country Country
		if err := doc.DataTo(&country); err != nil {
			continue
		}

		// Skip if already processed (sovereign state or duplicate)
		if processedEntities[country.ID] {
			continue
		}

		// Determine if it's a territory and get sovereign state name
		isTerritory := country.SovereignStateID != country.ID && country.SovereignStateID != ""
		var sovereignStateName interface{} = nil
		if isTerritory {
			if sovereignState, exists := sovereignMap[country.SovereignStateID]; exists {
				sovereignStateName = sovereignState.Name
			}
		}

		entry := map[string]interface{}{
			"code":                 country.ISOAlpha2,
			"name":                 country.Name,
			"continent":            country.Continent,
			"sovereign_state_name": sovereignStateName,
			"is_territory":         isTerritory,
			"id":                   country.ID,
			"official_name":        country.OfficialName,
			"type":                 "country",
			"iso_alpha2":           country.ISOAlpha2,
			"iso_alpha3":           country.ISOAlpha3,
			"capital":              country.Capital,
			"population":           country.Population,
			"area_km2":             country.AreaKM2,
			"bounds":               country.Bounds,
		}

		// Mark as processed
		processedEntities[country.ID] = true
		result = append(result, entry)
	}

	// Note: Map units are not included in the countries endpoint
	// They are separate territorial entities available via the /map-units endpoint

	// TODO: Get user_id and visited_count from request parameters or user context
	// For now, using placeholder values as the user context integration is not implemented
	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		userID = "unknown"
	}

	response := map[string]interface{}{
		"countries":     result,
		"user_id":       userID,
		"visited_count": 0, // TODO: Calculate based on user's visited countries
		"total_count":   len(result),
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

// Administrative Level 1 (States/Provinces) handlers
func getAdminLevel1Handler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Query parameters
	countryGID := r.URL.Query().Get("country")
	limit := 100
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 && l <= 1000 {
			limit = l
		}
	}

	// Build query
	query := firestoreClient.Collection("admin_level_1").Where("is_active", "==", true)
	if countryGID != "" {
		query = query.Where("country_gid", "==", countryGID)
	}
	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting admin level 1: %v", err)
		http.Error(w, "Failed to get administrative divisions", http.StatusInternalServerError)
		return
	}

	var adminUnits []AdminLevel1
	for _, doc := range docs {
		var unit AdminLevel1
		if err := doc.DataTo(&unit); err != nil {
			continue
		}
		adminUnits = append(adminUnits, unit)
	}

	response := map[string]interface{}{
		"admin_level_1": adminUnits,
		"count":         len(adminUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getAdminLevel1ByIdHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	ctx := context.Background()
	doc, err := firestoreClient.Collection("admin_level_1").Doc(id).Get(ctx)
	if err != nil {
		http.Error(w, "Administrative division not found", http.StatusNotFound)
		return
	}

	var adminUnit AdminLevel1
	if err := doc.DataTo(&adminUnit); err != nil {
		http.Error(w, "Failed to parse administrative division", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(adminUnit)
}

// Administrative Level 2 (Counties/Districts) handlers
func getAdminLevel2Handler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Query parameters
	countryGID := r.URL.Query().Get("country")
	stateGID := r.URL.Query().Get("state")
	limit := 100
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 && l <= 1000 {
			limit = l
		}
	}

	// Build query
	query := firestoreClient.Collection("admin_level_2").Where("is_active", "==", true)
	if countryGID != "" {
		query = query.Where("country_gid", "==", countryGID)
	}
	if stateGID != "" {
		query = query.Where("state_gid", "==", stateGID)
	}
	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting admin level 2: %v", err)
		http.Error(w, "Failed to get administrative divisions", http.StatusInternalServerError)
		return
	}

	var adminUnits []AdminLevel2
	for _, doc := range docs {
		var unit AdminLevel2
		if err := doc.DataTo(&unit); err != nil {
			continue
		}
		adminUnits = append(adminUnits, unit)
	}

	response := map[string]interface{}{
		"admin_level_2": adminUnits,
		"count":         len(adminUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getAdminLevel2ByIdHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	ctx := context.Background()
	doc, err := firestoreClient.Collection("admin_level_2").Doc(id).Get(ctx)
	if err != nil {
		http.Error(w, "Administrative division not found", http.StatusNotFound)
		return
	}

	var adminUnit AdminLevel2
	if err := doc.DataTo(&adminUnit); err != nil {
		http.Error(w, "Failed to parse administrative division", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(adminUnit)
}

// Administrative Level 3 (Municipalities/Cities) handlers
func getAdminLevel3Handler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Query parameters
	countryGID := r.URL.Query().Get("country")
	stateGID := r.URL.Query().Get("state")
	countyGID := r.URL.Query().Get("county")
	limit := 100
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 && l <= 1000 {
			limit = l
		}
	}

	// Build query
	query := firestoreClient.Collection("admin_level_3").Where("is_active", "==", true)
	if countryGID != "" {
		query = query.Where("country_gid", "==", countryGID)
	}
	if stateGID != "" {
		query = query.Where("state_gid", "==", stateGID)
	}
	if countyGID != "" {
		query = query.Where("county_gid", "==", countyGID)
	}
	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting admin level 3: %v", err)
		http.Error(w, "Failed to get administrative divisions", http.StatusInternalServerError)
		return
	}

	var adminUnits []AdminLevel3
	for _, doc := range docs {
		var unit AdminLevel3
		if err := doc.DataTo(&unit); err != nil {
			continue
		}
		adminUnits = append(adminUnits, unit)
	}

	response := map[string]interface{}{
		"admin_level_3": adminUnits,
		"count":         len(adminUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getAdminLevel3ByIdHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	ctx := context.Background()
	doc, err := firestoreClient.Collection("admin_level_3").Doc(id).Get(ctx)
	if err != nil {
		http.Error(w, "Administrative division not found", http.StatusNotFound)
		return
	}

	var adminUnit AdminLevel3
	if err := doc.DataTo(&adminUnit); err != nil {
		http.Error(w, "Failed to parse administrative division", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(adminUnit)
}

// Administrative Level 4 (Wards/Villages) handlers
func getAdminLevel4Handler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Query parameters
	municipalityGID := r.URL.Query().Get("municipality")
	limit := 100
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 && l <= 1000 {
			limit = l
		}
	}

	// Build query
	query := firestoreClient.Collection("admin_level_4").Where("is_active", "==", true)
	if municipalityGID != "" {
		query = query.Where("municipality_gid", "==", municipalityGID)
	}
	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting admin level 4: %v", err)
		http.Error(w, "Failed to get administrative divisions", http.StatusInternalServerError)
		return
	}

	var adminUnits []AdminLevel4
	for _, doc := range docs {
		var unit AdminLevel4
		if err := doc.DataTo(&unit); err != nil {
			continue
		}
		adminUnits = append(adminUnits, unit)
	}

	response := map[string]interface{}{
		"admin_level_4": adminUnits,
		"count":         len(adminUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getAdminLevel4ByIdHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	ctx := context.Background()
	doc, err := firestoreClient.Collection("admin_level_4").Doc(id).Get(ctx)
	if err != nil {
		http.Error(w, "Administrative division not found", http.StatusNotFound)
		return
	}

	var adminUnit AdminLevel4
	if err := doc.DataTo(&adminUnit); err != nil {
		http.Error(w, "Failed to parse administrative division", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(adminUnit)
}

// Administrative Level 5 (Neighborhoods) handlers
func getAdminLevel5Handler(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	// Query parameters
	wardGID := r.URL.Query().Get("ward")
	limit := 100
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 && l <= 1000 {
			limit = l
		}
	}

	// Build query
	query := firestoreClient.Collection("admin_level_5").Where("is_active", "==", true)
	if wardGID != "" {
		query = query.Where("ward_gid", "==", wardGID)
	}
	query = query.Limit(limit)

	docs, err := query.Documents(ctx).GetAll()
	if err != nil {
		log.Printf("Error getting admin level 5: %v", err)
		http.Error(w, "Failed to get administrative divisions", http.StatusInternalServerError)
		return
	}

	var adminUnits []AdminLevel5
	for _, doc := range docs {
		var unit AdminLevel5
		if err := doc.DataTo(&unit); err != nil {
			continue
		}
		adminUnits = append(adminUnits, unit)
	}

	response := map[string]interface{}{
		"admin_level_5": adminUnits,
		"count":         len(adminUnits),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getAdminLevel5ByIdHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id := vars["id"]

	ctx := context.Background()
	doc, err := firestoreClient.Collection("admin_level_5").Doc(id).Get(ctx)
	if err != nil {
		http.Error(w, "Administrative division not found", http.StatusNotFound)
		return
	}

	var adminUnit AdminLevel5
	if err := doc.DataTo(&adminUnit); err != nil {
		http.Error(w, "Failed to parse administrative division", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(adminUnit)
}

// Comprehensive location lookup handler
func getLocationLookupHandler(w http.ResponseWriter, r *http.Request) {
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

	// Find containing administrative boundaries at all levels
	response := map[string]interface{}{
		"lat":      lat,
		"lon":      lon,
		"location": map[string]interface{}{},
	}

	// Natural Earth hierarchy (countries, map units, etc.)
	naturalEarthBoundaries := []map[string]interface{}{}

	// Check sovereign states
	if states := findContainingEntities(ctx, "sovereign_states", lat, lon); len(states) > 0 {
		naturalEarthBoundaries = append(naturalEarthBoundaries, map[string]interface{}{
			"type":     "sovereign_state",
			"entities": states,
		})
		if len(states) > 0 {
			response["location"].(map[string]interface{})["sovereign_state"] = states[0]
		}
	}

	// Check countries
	if countries := findContainingEntities(ctx, "countries", lat, lon); len(countries) > 0 {
		naturalEarthBoundaries = append(naturalEarthBoundaries, map[string]interface{}{
			"type":     "country",
			"entities": countries,
		})
		if len(countries) > 0 {
			response["location"].(map[string]interface{})["country"] = countries[0]
		}
	}

	// Check map units
	if units := findContainingEntities(ctx, "map_units", lat, lon); len(units) > 0 {
		naturalEarthBoundaries = append(naturalEarthBoundaries, map[string]interface{}{
			"type":     "map_unit",
			"entities": units,
		})
		if len(units) > 0 {
			response["location"].(map[string]interface{})["map_unit"] = units[0]
		}
	}

	// Check map subunits
	if subunits := findContainingEntities(ctx, "map_subunits", lat, lon); len(subunits) > 0 {
		naturalEarthBoundaries = append(naturalEarthBoundaries, map[string]interface{}{
			"type":     "map_subunit",
			"entities": subunits,
		})
		if len(subunits) > 0 {
			response["location"].(map[string]interface{})["map_subunit"] = subunits[0]
		}
	}

	// GADM administrative hierarchy
	gadmBoundaries := []map[string]interface{}{}

	// Check administrative levels 1-5
	adminCollections := []string{"admin_level_1", "admin_level_2", "admin_level_3", "admin_level_4", "admin_level_5"}
	adminTypes := []string{"state_province", "county_district", "municipality_city", "ward_village", "neighborhood"}

	for i, collection := range adminCollections {
		if adminUnits := findContainingEntities(ctx, collection, lat, lon); len(adminUnits) > 0 {
			gadmBoundaries = append(gadmBoundaries, map[string]interface{}{
				"type":     adminTypes[i],
				"entities": adminUnits,
			})

			// Add to structured location
			levelKey := adminTypes[i]
			if len(adminUnits) > 0 {
				response["location"].(map[string]interface{})[levelKey] = adminUnits[0]
			}
		}
	}

	// Combine all boundaries
	response["natural_earth_boundaries"] = naturalEarthBoundaries
	response["gadm_boundaries"] = gadmBoundaries
	response["total_boundaries"] = len(naturalEarthBoundaries) + len(gadmBoundaries)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
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
