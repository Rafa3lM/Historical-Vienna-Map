# Interactive Historical Map of Vienna

## Quick Start

### Prerequisites
- Docker
- Docker Compose 2.0

### Running the Application

1. **Start all services**
```bash
   docker-compose up --build
```
2. **Load the data**
```bash
   # Full pipeline (extracts data from sources and loads into GraphDB)
   docker-compose exec elt python -m elt.pipeline
   
   # OR if you already have extracted data files
   docker-compose exec elt python -m elt.pipeline --skip-extract
```

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - GraphDB: http://localhost:7200

### Stopping the Application
```bash
# Stop all services
docker-compose down

# Stop and remove all data (clean slate)
docker-compose down -v
```

## ELT Pipeline Options

The ELT pipeline supports different execution modes:

### Full Pipeline
Extracts data from all sources and loads it into GraphDB:
```bash
docker-compose exec elt python -m elt.pipeline
```

### Dump-first Extraction (default)
The Vienna History Wiki extraction is dump-first. If a wiki dump is present at
`data/dump/ViennaHistoryWiki.rdf.gz` (the legacy location
`data/raw/dump/ViennaHistoryWiki.rdf.gz` is also accepted), the pipeline streams
it directly without any HTTP requests:
```bash
# Default: uses data/dump/ViennaHistoryWiki.rdf.gz if present
docker-compose exec elt python -m elt.pipeline
```

To force the live Vienna History Wiki RDF export (HTTP POST to
`Spezial:RDF_exportieren`) instead, use:
```bash
docker-compose exec elt python -m elt.pipeline --use-live-export
```

A different dump file can be selected with:
```bash
docker-compose exec elt python -m elt.pipeline --dump-path /path/to/ViennaHistoryWiki.rdf.gz
```

Both base entities (step 1) and related entities (step 4) use the dump when it
is available, so dump mode does not depend on GraphDB for step 4.

### Skip Extraction (Use Existing Data)
Uses previously extracted data files without re-downloading:
```bash
docker-compose exec elt python -m elt.pipeline --skip-extract
```

### Clean Start (Reset Database)
Clears all data from GraphDB before loading:
```bash
docker-compose exec elt python -m elt.pipeline --clean
```

### Run a Single Step
Re-run one pipeline step in isolation (e.g. after fixing step 6) without
replaying the earlier steps. Steps can be addressed by number, name, method
name, or a unique prefix:
```bash
# List all steps
python -m elt.pipeline --list-steps

# Equivalent ways to run only step 6 (Wikidata enrichment)
docker-compose exec elt python -m elt.pipeline --step 6
docker-compose exec elt python -m elt.pipeline --step "Enrich Data"
docker-compose exec elt python -m elt.pipeline --step enrich
```

### Combined Options
```bash
docker-compose exec elt python -m elt.pipeline --clean --skip-extract
```

## Architecture

- **Frontend**: Vue.js + Vite + Leaflet (interactive map)
- **Backend**: FastAPI (Python)
- **Database**: GraphDB (RDF triple store)
- **ELT**: Python with RDFLib and SPARQLWrapper

### Data Sources
- **Vienna History Wiki**: Historical buildings, events, and people
- **OpenStreetMap**: Vienna district boundaries
- **Wikidata**: Monument protection database IDs and architectural styles

Step 6 also derives categorical time labels in the project namespace
`http://example.org/vienna/`: `startDateCentury`, `endDateCentury`, and
`activeDuringCentury`. Labels use the form `century1`, `century2`, etc.; the
same active-century labels are generated for dated entities, artists, and the
curated architectural-style periods.
