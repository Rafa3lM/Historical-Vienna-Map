import time
from pathlib import Path
from loaders.graphdb_loader import GraphDBLoader
from extractors.extract_osm_districts import OSMDistrictExtractor
from extractors.extract_vienna_history_wiki import ViennaHistoryWikiExtractor
from config import RAW_DIR, PROCESSED_DIR, GRAPHDB_SPARQL


class ViennaDataPipeline:
    """Main pipeline orchestrator"""

    def __init__(self, clean_start=False):
        self.loader = GraphDBLoader()
        self.clean_start = clean_start

    @staticmethod
    def step_1_extract_vienna_wiki():
        """Extract vienna wiki pages"""
        print("\n" + "=" * 60)
        print("STEP 1: Extract Vienna Wiki Data")
        print("=" * 60)

        extractor = ViennaHistoryWikiExtractor()
        filepath = extractor.run_extraction()

        print(f"Vienna History Wiki data extracted to {filepath}")
        return True

    @staticmethod
    def step_2_extract_osm_districts():
        """Extract district borders from OSM"""
        print("\n" + "=" * 60)
        print("STEP 2: Extract District Borders from OSM")
        print("=" * 60)

        extractor = OSMDistrictExtractor()
        filepath = extractor.extract_and_save()

        if filepath:
            print(f"Districts extracted to {filepath}")
            return True
        else:
            print("Failed to extract districts")
            return False

    def step_3_load_raw_data(self):
        """Load raw Vienna Wiki data into GraphDB"""
        print("\n" + "=" * 60)
        print("STEP 3: Load Raw Data into GraphDB")
        print("=" * 60)

        if self.clean_start:
            confirm = input("Clear all data from GraphDB? (yes/no): ")
            if confirm.lower() == 'yes':
                self.loader.clear_repository(confirm=True)
            else:
                print("Keeping existing data")

        # Load all raw RDF files
        count = self.loader.load_directory(RAW_DIR, "**/*.rdf")

        print(f"\nLoaded {count} files into GraphDB")
        return count > 0

    def step_4_load_districts(self):
        """Load district borders from into GraphDB"""
        print("\n" + "=" * 60)
        print("STEP 4: Load District Borders into GraphDB")
        print("=" * 60)

        district_file = Path(PROCESSED_DIR) / "vienna_districts.ttl"

        if not district_file.exists():
            print(f"District file not found: {district_file}")
            return False

        success = self.loader.load_file(str(district_file))
        return success

    def step_5_transform_coordinates(self):
        """Transform coordinates to GeoSPARQL format"""
        print("\n" + "=" * 60)
        print("STEP 5: Transform Coordinates to GeoSPARQL")
        print("=" * 60)

        # Execute the geo transformation SPARQL update
        sparql_file = Path("queries/insert_geo.sparql")

        if not sparql_file.exists():
            print(f"SPARQL file not found: {sparql_file}")
            return False

        success = self.loader.execute_sparql_file(str(sparql_file))
        return success

    def step_6_link_buildings_to_districts(self):
        """Link buildings to their districts using spatial queries"""
        print("\n" + "=" * 60)
        print("STEP 6: Link Buildings to Districts")
        print("=" * 60)

        # SPARQL INSERT query to link buildings to districts
        sparql_file = Path("queries/link_districts.sparql")

        if not sparql_file.exists():
            print(f"SPARQL file not found: {sparql_file}")
            return False

        print("Executing spatial join to link buildings to districts...")
        success = self.loader.execute_sparql_file(str(sparql_file))

        return success

    def step_7_validate(self):
        """Validate the final data"""
        print("\n" + "=" * 60)
        print("STEP 7: Validate Data")
        print("=" * 60)

        # Get statistics
        total_triples = self.loader.get_triple_count()
        print(f"Total triples: {total_triples:,}")

        # Count specific entities
        queries = {
            "Buildings with geometry": """
                SELECT (COUNT(DISTINCT ?b) AS ?count) WHERE {
                    ?b <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A/Art_des_Bauwerks> ?type ;
                       <http://www.opengis.net/ont/geosparql#hasGeometry> ?geom .
                }
            """,
            "Districts": """
                SELECT (COUNT(DISTINCT ?d) AS ?count) WHERE {
                    ?d a <https://schema.org/AdministrativeArea> .
                }
            """,
            "Buildings linked to districts": """
                SELECT (COUNT(DISTINCT ?b) AS ?count) WHERE {
                    ?b <https://schema.org/containedInPlace> ?district .
                }
            """
        }

        import requests

        for label, query in queries.items():
            try:
                params = {'query': query}
                headers = {'Accept': 'application/sparql-results+json'}
                response = requests.get(GRAPHDB_SPARQL, params=params, headers=headers)

                if response.status_code == 200:
                    results = response.json()
                    count = int(results['results']['bindings'][0]['count']['value'])
                    print(f"  {label}: {count:,}")
                else:
                    print(f"  {label}: Error querying")
            except Exception as e:
                print(f"  {label}: Error - {e}")

        return True

    def run_full_pipeline(self):
        """Execute complete pipeline"""
        print("\n" + "=" * 60)
        print("VIENNA HISTORICAL MAP - ELT PIPELINE")
        print("=" * 60)

        start_time = time.time()

        steps = [
            ("Extract Vienna Wiki Data", self.step_1_extract_vienna_wiki),
            ("Extract District Borders", self.step_2_extract_osm_districts()),
            ("Load Raw Data", self.step_3_load_raw_data),
            ("Load Districts", self.step_4_load_districts),
            ("Transform Coordinates", self.step_5_transform_coordinates),
            ("Link Buildings to Districts", self.step_6_link_buildings_to_districts),
            ("Validate Data", self.step_7_validate),
        ]

        results = {}

        for step_name, step_func in steps:
            try:
                success = step_func()
                results[step_name] = "Success" if success else "Error"

                if not success:
                    print(f"\nStep failed: {step_name}")
                    print("Pipeline stopped. Fix the error and re-run.")
                    break

            except Exception as e:
                results[step_name] = "Error"
                print(f"\nError in {step_name}: {e}")
                import traceback
                traceback.print_exc()
                break

        # Summary
        elapsed = time.time() - start_time

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)

        for step_name, result in results.items():
            print(f"{result} {step_name}")

        print(f"\nTotal time: {elapsed:.1f} seconds")
        print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Vienna Historical Map ELT Pipeline')
    parser.add_argument('--clean', action='store_true',
                        help='Clear GraphDB before loading (WARNING: deletes all data)')
    parser.add_argument('--skip-extract', action='store_true',
                        help='Skip extraction steps (use existing data)')

    args = parser.parse_args()

    pipeline = ViennaDataPipeline(clean_start=args.clean)

    if args.skip_extract:
        print("Skipping extraction - using existing data")
        # Skip to step 3
        #pipeline.step_3_load_raw_data()
        pipeline.step_4_load_districts()
        #pipeline.step_5_transform_coordinates()
        pipeline.step_6_link_buildings_to_districts()
        pipeline.step_7_validate()
    else:
        pipeline.run_full_pipeline()