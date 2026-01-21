# Interactive Historical Map of Vienna

## Quick Start

### Prerequisites
- Docker
- Docker Compose

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
- **Wikidata**: Monument protection database IDs
