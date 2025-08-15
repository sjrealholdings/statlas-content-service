#!/usr/bin/env python3
"""
Generate OpenAPI specification from the Content Service endpoints.
This creates machine-readable API documentation that other services can consume.
"""

import json
import yaml
from datetime import datetime

def generate_openapi_spec():
    """Generate OpenAPI 3.0 specification for the Content Service."""
    
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Statlas Content Service API",
            "description": "Geographic reference data, landmarks, and polygon endpoints for the Statlas platform",
            "version": "1.0.0",
            "contact": {
                "name": "Statlas Team",
                "url": "https://github.com/sjrealholdings/statlas-content-service"
            }
        },
        "servers": [
            {
                "url": "https://statlas-content-service-1064925383001.us-central1.run.app",
                "description": "Production server"
            }
        ],
        "paths": {
            "/countries/bulk": {
                "get": {
                    "summary": "Get bulk country data with continent and territory info",
                    "description": "Returns enhanced country data including continent, territory relationships, and sovereignty information",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "User ID for personalized data (optional)"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/BulkCountriesResponse"
                                    }
                                }
                            }
                        }
                    },
                    "tags": ["Countries"]
                }
            },
            "/polygons/country/{id}": {
                "get": {
                    "summary": "Get polygon geometry for a specific country",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Country ID (e.g., 'australia', 'france')"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Country polygon data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/CountryPolygon"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "Country not found"
                        }
                    },
                    "tags": ["Polygons"]
                }
            },
            "/polygons/continent/{continent}": {
                "get": {
                    "summary": "Get all country polygons for a continent",
                    "parameters": [
                        {
                            "name": "continent",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Continent name (e.g., 'Europe', 'Asia')"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Continent polygon data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ContinentPolygons"
                                    }
                                }
                            }
                        }
                    },
                    "tags": ["Polygons"]
                }
            },
            "/polygons/world": {
                "get": {
                    "summary": "Get all country polygons in the world",
                    "responses": {
                        "200": {
                            "description": "World polygon data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/WorldPolygons"
                                    }
                                }
                            }
                        }
                    },
                    "tags": ["Polygons"]
                }
            }
        },
        "components": {
            "schemas": {
                "Country": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "continent": {"type": "string"},
                        "is_territory": {"type": "boolean"},
                        "sovereign_state_name": {"type": "string", "nullable": True},
                        "iso_alpha2": {"type": "string"},
                        "iso_alpha3": {"type": "string"},
                        "population": {"type": "integer"},
                        "area_km2": {"type": "number"},
                        "bounds": {"$ref": "#/components/schemas/Bounds"}
                    }
                },
                "BulkCountriesResponse": {
                    "type": "object",
                    "properties": {
                        "countries": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Country"}
                        },
                        "user_id": {"type": "string"},
                        "visited_count": {"type": "integer"},
                        "total_count": {"type": "integer"}
                    }
                },
                "CountryPolygon": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "geometry": {"type": "string", "description": "GeoJSON string"},
                        "bounds": {"$ref": "#/components/schemas/Bounds"}
                    }
                },
                "ContinentPolygons": {
                    "type": "object",
                    "properties": {
                        "continent": {"type": "string"},
                        "count": {"type": "integer"},
                        "polygons": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/CountryPolygon"}
                        }
                    }
                },
                "WorldPolygons": {
                    "type": "object",
                    "properties": {
                        "world": {"type": "boolean"},
                        "count": {"type": "integer"},
                        "polygons": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/CountryPolygon"}
                        }
                    }
                },
                "Bounds": {
                    "type": "object",
                    "properties": {
                        "min_lat": {"type": "number"},
                        "max_lat": {"type": "number"},
                        "min_lon": {"type": "number"},
                        "max_lon": {"type": "number"}
                    }
                }
            },
            "securitySchemes": {
                "ServiceAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Service-to-service authentication token"
                }
            }
        },
        "security": [{"ServiceAuth": []}],
        "tags": [
            {"name": "Countries", "description": "Country and territory data"},
            {"name": "Polygons", "description": "Geographic polygon data for mapping"}
        ]
    }
    
    return spec

def save_api_spec():
    """Save the API specification in multiple formats."""
    spec = generate_openapi_spec()
    
    # Save as JSON
    with open('api-spec.json', 'w') as f:
        json.dump(spec, f, indent=2)
    
    # Save as YAML
    with open('api-spec.yaml', 'w') as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
    
    # Generate timestamp
    timestamp = datetime.now().isoformat()
    
    print(f"✅ API specification generated at {timestamp}")
    print("📁 Files created:")
    print("   - api-spec.json (machine-readable)")
    print("   - api-spec.yaml (human-readable)")
    print()
    print("🔗 Usage:")
    print("   - Import into Postman/Insomnia for testing")
    print("   - Generate client SDKs with openapi-generator")
    print("   - Share with other services for integration")

if __name__ == "__main__":
    save_api_spec()
