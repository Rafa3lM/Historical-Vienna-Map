# Vienna Historical Map - ELT Pipeline

Extract, Load, and Transform pipeline for Vienna's historical building data.

## Overview

This pipeline extracts historical data about Vienna's buildings, events, and related entities from multiple sources, loads them into a GraphDB RDF triple store, and transforms them into a queryable knowledge graph with spatial relationships.

## Data Sources

1. **Vienna History Wiki** (`geschichtewiki.wien.gv.at`)
   - Historical buildings and monuments
   - Events and their locations
   - People (architects, notable residents)
   - Exported as RDF/XML via Wien Geschichte Wiki's RDF export

2. **OpenStreetMap** (via Overpass API)
   - Vienna district boundaries (23 districts)
   - Geographic polygons in GeoJSON format

3. **Wikidata** 
   - Cultural heritage identifiers
   - Monument database IDs

## Pipeline Steps

### Extraction (Steps 1, 2, 4)

**Step 1: Extract Vienna Wiki Data**
- Queries Vienna History Wiki for categories (buildings, places, events)
- Downloads RDF/XML data via Wien Geschichte Wiki's RDF export
- Saves to `data/raw/base/`

**Step 2: Extract OSM District Boundaries**
- Queries Overpass API for Vienna's 23 administrative districts
- Converts GeoJSON to GeoSPARQL-compatible WKT format
- Saves as RDF Turtle to `data/processed/vienna_districts.ttl`

**Step 4: Extract Related Entities**
- Identifies architects, known residents, and namesakes from loaded buildings
- Fetches their Vienna Wiki pages
- Saves to `data/raw/related/`

### Loading (Steps 3, 5, 6, 7)

**Step 3: Load Raw Data**
- Uploads all RDF files from `data/raw/base/` to GraphDB
- Optional: Clears existing data with `--clean` flag
- Uses GraphDB REST API for batch loading

**Step 5: Load Related Entities**
- Uploads related entity RDF files to GraphDB

**Step 6: Enrich with Wikidata**
- Reads loaded entities with Wikidata links from GraphDB
- Queries Wikidata directly for cultural heritage IDs (P2951/P9154) and
  architectural styles (P149)
- Inserts the results into GraphDB

**Step 7: Load District Boundaries**
- Loads district polygon geometries into GraphDB
- Creates `schema:AdministrativeArea` entities for each district

### Transformation (Steps 8, 9, 10)

**Step 8: Transform Coordinates to GeoSPARQL**
- Converts `schema:geo` latitude/longitude to GeoSPARQL Point geometries
- Creates `geo:hasGeometry` relationships
- Enables spatial querying capabilities

**Step 9: Link Buildings to Districts**
- Performs spatial join using GeoSPARQL `geof:sfWithin`
- Links each building to its containing district
- Adds `schema:containedInPlace` relationships

**Step 10: Validate Data**
- Counts total triples in the database
- Verifies entities with geometries
- Confirms district linkages
- Reports final statistics

## Usage

### Full Pipeline
```bash
docker-compose exec elt python -m elt.pipeline
```

Downloads all data from sources, loads into GraphDB, and performs transformations.
Skips downloads for already existing files.

**Expected duration:** 10-20 minutes

### Skip Extraction (Subsequent Runs)
```bash
docker-compose exec elt python -m elt.pipeline --skip-extract
```

Uses previously downloaded data files. Useful for:
- Re-running transformations
- Testing changes to loading/transformation logic
- Recovering from errors in later steps

**Expected duration:** 2-5 minutes

### Clean Start
```bash
docker-compose exec elt python -m elt.pipeline --clean
```

Clears all data from GraphDB before loading. Prompts for confirmation.

### Run a Single Step
Re-run one step in isolation by number, name, method name, or unique prefix:
```bash
python -m elt.pipeline --list-steps

docker-compose exec elt python -m elt.pipeline --step 6
docker-compose exec elt python -m elt.pipeline --step "Enrich Data"
docker-compose exec elt python -m elt.pipeline --step enrich
```

### Combined Options
```bash
docker-compose exec elt python -m elt.pipeline --clean --skip-extract
```

Clears database and reloads from existing files.