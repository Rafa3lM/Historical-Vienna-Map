from pathlib import Path
from rdflib import Namespace
import os

# === Wien Geschichte Wiki Configuration ===
BASE_URL = "https://www.geschichtewiki.wien.gv.at/"
EXPORT_URL = "https://www.geschichtewiki.wien.gv.at/Spezial:RDF_exportieren"

# === Data Directories ===
DATA_DIR = "./data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
RAW_BASE = os.path.join(RAW_DIR, "base")
RAW_RELATED = os.path.join(RAW_DIR, "related")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# === Wiki Dump Configuration ===
DUMP_DIR = os.path.join(DATA_DIR, "dump")
DEFAULT_DUMP_FILE = os.path.join(DUMP_DIR, "ViennaHistoryWiki.rdf.gz")
# Older location kept for backwards compatibility.
LEGACY_DUMP_FILE = os.path.join(RAW_DIR, "dump", "ViennaHistoryWiki.rdf.gz")

# Create directories if they don't exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(RAW_BASE, exist_ok=True)
os.makedirs(RAW_RELATED, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(DUMP_DIR, exist_ok=True)


def resolve_dump_path(override=None):
    """Return the Vienna History Wiki dump path if one exists, else None.

    An explicit override is used verbatim.  Otherwise the canonical
    ``data/dump`` location is checked first, then the legacy
    ``data/raw/dump`` location.
    """
    if override:
        path = Path(override)
        return path if path.is_file() else None

    for path in (Path(DEFAULT_DUMP_FILE), Path(LEGACY_DUMP_FILE)):
        if path.is_file():
            return path
    return None

# === GraphDB Configuration ===
GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
GRAPHDB_REPO = os.getenv("GRAPHDB_REPO", "vienna")
GRAPHDB_SPARQL = os.getenv("GRAPHDB_SPARQL", f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}")
GRAPHDB_UPDATE = f"{GRAPHDB_SPARQL}/statements"

# === Categories to Extract ===
CATEGORIES = {
    "buildings": [
        "Kategorie:Bauwerke",

        "Kategorie:Bad",

        "Kategorie:Brücke",

        "Kategorie:Gebäude",
        "Kategorie:Gemeindebau",

        "Kategorie:Kanalisation",

        "Kategorie:Kunst im öffentlichen Raum",

        "Kategorie:Sakralbau",
        "Kategorie:Altkatholische Kirche",
        "Kategorie:Evangelische Kirche A.B.",
        "Kategorie:Evangelische Kirche H.B.",
        "Kategorie:Griechisch-katholische Kirche",
        "Kategorie:Griechisch-orthodoxe Kirche",
        "Kategorie:Kapelle",
        "Kategorie:Katholische Kirche",
        "Kategorie:Sakrale Freiplastik",
        "Kategorie:Synagoge",

        "Kategorie:Sonstiges Bauwerk",

        "Kategorie:Stiege",

        "Kategorie:Wasserbauwerk",
        "Kategorie:Brunnen",
        "Kategorie:Kanal",
        "Kategorie:Wasserbehälter",
        "Kategorie:Wasserleitung",
    ],
    "places": [
        "Kategorie:Friedhof",

        "Kategorie:Grünfläche",

        "Kategorie:Passage",

        "Kategorie:Markt",
    ],
    "events": [
        "Kategorie:Anschlag",

        "Kategorie:Besetzung",

        "Kategorie:Brand",
        "Kategorie:Demonstration",

        "Kategorie:Kundgebung",

        "Kategorie:Protestaktion",

        "Kategorie:Streik",

        "Kategorie:Veranstaltung",
        "Kategorie:Feier",
        "Kategorie:Sportveranstaltung",

        "Kategorie:Versammlung",
    ]
}

# === Filtering Strategy ===
REQUIRED_PROPERTIES = {
    "buildings": ["schema:geo"],
    "places": ["schema:geo"],
    "events": ["schema:geo"],
}

# === OSM Configuration ===
# Vienna district borders from Overpass API
OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# === Wikidata Configuration ===
# Wikidata now rejects requests without a descriptive User-Agent
# (see https://w.wiki/4wJS and https://phabricator.wikimedia.org/T400119).
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT = os.getenv(
    "WIKIDATA_USER_AGENT",
    "Historical-Vienna-Map-ELT/1.0 "
    "(https://github.com/Rafa3lM/Historical-Vienna-Map; "
    "contact: rafael.milchram@gmail.com)",
)

# === Namespaces ===
SCHEMA = Namespace("https://schema.org/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
SWIVT = Namespace("http://semantic-mediawiki.org/swivt/1.0#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PROPERTY = Namespace("http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A")
WIKI = Namespace("http://www.geschichtewiki.wien.gv.at/Special:URIResolver/")

# === Pipeline Settings ===
RATE_LIMIT_DELAY = 1
