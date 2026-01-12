import requests
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OSM_OVERPASS_URL, GEO, SCHEMA, PROCESSED_DIR


class OSMDistrictExtractor:
    """Extract Vienna district borders from OpenStreetMap"""

    def __init__(self):
        self.overpass_url = OSM_OVERPASS_URL
        self.geo = GEO
        self.schema = SCHEMA
        self.processed_dir = Path(PROCESSED_DIR)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def fetch_districts(self) -> dict:
        """Fetch Vienna districts from Overpass API"""

        # Query for Vienna's 23 districts (Bezirke)
        query = """
        [out:json][timeout:90];
        area["name"="Wien"]["admin_level"="4"]->.vienna;
        (
          relation["boundary"="administrative"]["admin_level"="9"](area.vienna);
        );
        out geom;
        """

        print("Fetching Vienna districts from OpenStreetMap...")

        try:
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                num_districts = len(data.get('elements', []))
                print(f"Fetched {num_districts} districts from OSM")

                if num_districts == 0:
                    print("Warning: No districts found. Check OSM query.")

                return data
            else:
                print(f"Failed to fetch districts: HTTP {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            print("Request timed out. Overpass API might be busy. Try again later.")
            return None
        except Exception as e:
            print(f"Error fetching districts: {str(e)}")
            return None

    @staticmethod
    def polygon_to_wkt(coordinates: list) -> str:
        """Convert list of [lon, lat] coordinates to WKT POLYGON"""
        if not coordinates:
            return None

        # Ensure polygon is closed (first point == last point)
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])

        coords_str = ", ".join([f"{lon} {lat}" for lon, lat in coordinates])
        return f"POLYGON(({coords_str}))"

    @staticmethod
    def multipolygon_to_wkt(members: list) -> str:
        """Convert OSM relation members to WKT MULTIPOLYGON or POLYGON"""
        outer_rings = []

        for member in members:
            # Only process outer rings (boundaries)
            if member.get('role') != 'outer':
                continue

            geometry = member.get('geometry', [])
            if not geometry:
                continue

            # Extract coordinates
            coords = [(node['lon'], node['lat']) for node in geometry]

            if not coords:
                continue

            # Close polygon if needed
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            coords_str = ", ".join([f"{lon} {lat}" for lon, lat in coords])
            outer_rings.append(f"(({coords_str}))")

        if not outer_rings:
            return None

        # Single polygon or multipolygon?
        if len(outer_rings) == 1:
            return f"POLYGON{outer_rings[0]}"
        else:
            return f"MULTIPOLYGON({', '.join(outer_rings)})"

    def convert_to_rdf(self, osm_data: dict) -> Graph:
        """Convert OSM district data to RDF graph"""
        g = Graph()

        # Bind namespaces
        g.bind('geo', self.geo)
        g.bind('schema', self.schema)
        g.bind('rdfs', RDFS)

        VIENNA_DISTRICT = Namespace("http://example.org/vienna/district/")
        g.bind('district', VIENNA_DISTRICT)

        print("\nConverting districts to RDF with GeoSPARQL geometries...")

        elements = osm_data.get('elements', [])

        if not elements:
            print("No elements to convert")
            return g

        converted_count = 0

        for element in elements:
            if element['type'] != 'relation':
                continue

            tags = element.get('tags', {})
            district_name = tags.get('name', 'Unknown')

            # Extract district number (1-23)
            district_ref = tags.get('ref', '')
            if not district_ref and district_name:
                # Try to extract from name (e.g., "1. Innere Stadt" -> "1")
                parts = district_name.split('.')
                if parts and parts[0].strip().isdigit():
                    district_ref = parts[0].strip()

            if not district_ref:
                district_ref = f"unknown_{element.get('id', 'x')}"

            # Create URI for district
            district_uri = VIENNA_DISTRICT[f"district_{district_ref}"]

            # Basic properties
            g.add((district_uri, RDF.type, self.schema.Place))
            g.add((district_uri, RDF.type, self.schema.AdministrativeArea))
            g.add((district_uri, RDFS.label, Literal(district_name, lang='de')))
            g.add((district_uri, self.schema.name, Literal(district_name)))
            g.add((district_uri, self.schema.identifier, Literal(district_ref)))

            # Add OSM ID
            osm_id = element.get('id')
            if osm_id:
                g.add((district_uri, self.schema.sameAs,
                       URIRef(f"https://www.openstreetmap.org/relation/{osm_id}")))

            # Generate WKT geometry
            try:
                members = element.get('members', [])
                if members:
                    wkt = self.multipolygon_to_wkt(members)

                    if wkt:
                        # Create geometry node
                        geom_uri = URIRef(f"{district_uri}_geometry")
                        g.add((district_uri, self.geo.hasGeometry, geom_uri))
                        g.add((geom_uri, RDF.type, self.geo.Geometry))
                        g.add((geom_uri, self.geo.asWKT,
                               Literal(wkt, datatype=self.geo.wktLiteral)))

                        converted_count += 1
                        print(f"{district_ref:>2}. {district_name}")
                    else:
                        print(f"{district_ref:>2}. {district_name} - No valid geometry")
                else:
                    print(f"{district_ref:>2}. {district_name} - No members")

            except Exception as e:
                print(f"Error processing {district_name}: {e}")
                continue

        print(f"\nSuccessfully converted {converted_count} districts to RDF")

        if converted_count == 0:
            print("Warning: No districts were converted. Check OSM data structure.")

        return g

    def save_rdf(self, graph: Graph, filename: str = "vienna_districts.ttl") -> str:
        """Save RDF graph to file"""
        filepath = self.processed_dir / filename

        try:
            # Serialize to Turtle format (more readable)
            graph.serialize(destination=str(filepath), format='turtle')

            # Get file size
            size_kb = filepath.stat().st_size / 1024

            print(f"Saved RDF to {filepath}")
            print(f"File size: {size_kb:.1f} KB")
            print(f"Triples: {len(graph)}")

            return str(filepath)

        except Exception as e:
            print(f"Error saving RDF: {e}")
            return None

    def extract_and_save(self) -> str:
        """Complete extraction pipeline"""
        print("=" * 60)
        print("OSM District Extraction Pipeline")
        print("=" * 60)

        # Check if file already exists
        output_file = self.processed_dir / "vienna_districts.ttl"
        if output_file.exists():
            print(f"\nDistrict file already exists: {output_file}")
            response = input("Re-download and overwrite? (yes/no): ")
            if response.lower() != 'yes':
                print("Using existing file.")
                return str(output_file)
            print("Proceeding with download...\n")

        # Step 1: Fetch data from OSM
        osm_data = self.fetch_districts()
        if not osm_data:
            print("\nFailed to fetch OSM data")
            return None

        # Step 2: Convert to RDF
        graph = self.convert_to_rdf(osm_data)

        if len(graph) == 0:
            print("\nNo RDF data generated")
            return None

        # Step 3: Save to file
        filepath = self.save_rdf(graph)

        if filepath:
            print("\n" + "=" * 60)
            print("District extraction complete!")
            print("=" * 60)
            print(f"File: {filepath}")
            print("Next step: Load into GraphDB using pipeline.py")

        return filepath


if __name__ == "__main__":
    print("Vienna District Extractor")
    print("=" * 60)

    extractor = OSMDistrictExtractor()
    result = extractor.extract_and_save()

    if result:
        print(f"\nSuccess! District borders saved to:")
        print(f"{result}")
    else:
        print("\nExtraction failed. Check errors above.")
