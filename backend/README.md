# Vienna Historical Map - Backend API

FastAPI-based REST API for querying Vienna's historical building data from GraphDB.

## Overview

This backend provides HTTP endpoints that translate user requests into SPARQL queries, execute them against GraphDB, and return formatted JSON responses for the frontend.

## API Endpoints

### GET `/entities`

Search for buildings, events, and places within a spatial-temporal range.

**Query Parameters:**
- `lat`, `lng` (required) - Center point coordinates
- `radius` (optional, default: 500) - Search radius in meters (50-15000)
- `from_year`, `to_year` (optional) - Time range (0-2026)
- `building_types[]` - Filter by building types (e.g., "Kirche", "Palais")
- `event_types[]` - Filter by event types (e.g., "Brand", "Demonstration")
- `place_types[]` - Filter by place types (e.g., "Markt", "Grünfläche")
- `only_historical` (bool) - Only demolished/historical buildings
- `has_artists` (bool) - Only buildings with known architects
- `related_to` (bool) - Only entities with famous inhabitants
- `named_after` (bool) - Only entities named after someone
- `has_events` (bool) - Only entities with related events
- `only_monuments` (bool) - Only protected monuments (HERIS/Cultural Heritage DB)

**Example:**
```
GET /entities?lat=48.2082&lng=16.3738&radius=1000&from_year=1800&to_year=1900&building_types=Kirche
```

### GET `/entity-geo/{uri}`

Get detailed information about a geo-locatable entity (building, place, or event).

**Example:**
```
GET /entity-geo/http://www.geschichtewiki.wien.gv.at/Stephansdom
```

### GET `/entity-details/{uri}`

Get detailed information about a person or non-geo entity.

**Example:**
```
GET /entity-details/http://www.geschichtewiki.wien.gv.at/Otto_Wagner
```

## Architecture
```
Frontend Request
    ↓
FastAPI Endpoint (app.py)
    ↓
Query Builder (queries.py) → Generates SPARQL
    ↓
SPARQLWrapper → Executes against GraphDB
    ↓
JSON Response → Parsed and formatted
    ↓
Frontend
```

## Key Components

### `app.py`
- FastAPI application setup
- CORS middleware for frontend communication
- Endpoint definitions and request validation
- Response formatting and error handling

### `queries.py`
- `SparqlQueries` class with static methods
- Parameterized SPARQL query generation
- Dynamic filtering based on user input
- GeoSPARQL spatial queries

## SPARQL Query Features

### Spatial Queries (GeoSPARQL)
```sparql
FILTER (
    geof:distance(?wkt, "POINT(16.3738 48.2082)"^^geo:wktLiteral,
                  <http://www.opengis.net/def/uom/OGC/1.0/metre>) <= 1000
)
```

### Temporal Queries
```sparql
FILTER (
    (!BOUND(?startDate) || YEAR(?startDate) <= 1900) &&
    (!BOUND(?endDate) || YEAR(?endDate) >= 1800)
)
```

### Type Filtering
```sparql
{ ?sub property:Art_des_Bauwerks ?type }  # Buildings
UNION
{ ?sub property:Art_des_Ereignisses ?type }  # Events
UNION
{ ?sub property:Art_des_Objekts ?type }  # Places
```

## Configuration

Environment variables (set in `docker-compose.yml`):
```bash
GRAPHDB_URL=http://graphdb:7200/repositories/vienna
```

Local development default: `http://localhost:7200/repositories/vienna`

## Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python app.py

# Or with uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Interactive API documentation (Swagger UI): http://localhost:8000/docs

## Error Handling

- **400 Bad Request**: Invalid query parameters
- **404 Not Found**: Entity URI doesn't exist
- **500 Internal Server Error**: SPARQL query execution failed

All errors return JSON with detailed error messages.