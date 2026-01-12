from rdflib import Namespace
import os

# === Wien Geschichte Wiki Configuration ===
BASE_URL = "https://www.geschichtewiki.wien.gv.at/"
EXPORT_URL = "https://www.geschichtewiki.wien.gv.at/Spezial:RDF_exportieren"

# === Data Directories ===
DATA_DIR = "../data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Create directories if they don't exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# === GraphDB Configuration ===
GRAPHDB_URL = "http://localhost:7200"
GRAPHDB_REPO = "vienna"
GRAPHDB_SPARQL = f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}"
GRAPHDB_UPDATE = f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}/statements"

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

        "Kategorie:Stiege"

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
OSM_QUERY_VIENNA_DISTRICTS = """
[out:json];
area["name"="Wien"]["admin_level"="4"]->.vienna;
(
  relation["admin_level"="9"](area.vienna);
);
out geom;
"""

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
BATCH_SIZE = 50
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1
