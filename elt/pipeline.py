import re
import time
from pathlib import Path

from elt.loaders.graphdb_loader import GraphDBLoader
from elt.extractors.enrich_wikidata_monuments import WikidataMonumentEnricher
from elt.extractors.extract_related_entities import RelatedEntitiesExtractor
from elt.extractors.extract_osm_districts import OSMDistrictExtractor
from elt.extractors.extract_vienna_history_wiki import ViennaHistoryWikiExtractor
from elt.extractors.extract_vienna_wiki_dump import DumpWikiExtractor
from elt.kge import run_kge_step
from elt.config import resolve_dump_path
from config import RAW_BASE, RAW_RELATED, PROCESSED_DIR, GRAPHDB_SPARQL
from elt.utils.query_loader import load_query


# (display name, bound method name) for every pipeline step, in run order.
PIPELINE_STEPS = [
    ("Extract Vienna Wiki Data", "step_1_extract_vienna_wiki"),
    ("Extract District Borders", "step_2_extract_osm_districts"),
    ("Load Raw Data", "step_3_load_raw_data"),
    ("Extract Related Entities", "step_4_extract_related_entities"),
    ("Load Related Entities Raw Data", "step_5_load_related_entities"),
    ("Enrich Data", "step_6_enrich_data"),
    ("Load Districts", "step_7_load_districts"),
    ("Transform Coordinates", "step_8_transform_coordinates"),
    ("Link Buildings to Districts", "step_9_link_buildings_to_districts"),
    ("Validate Data", "step_10_validate"),
    ("Build KGE Layer and Train Model", "step_11_build_kge")
]


def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def resolve_step(key):
    """Resolve a user-supplied step reference to ``(name, method_name)``.

    Accepts the step number (``"6"``), the method name
    (``"step_6_enrich_data"``), the display name (``"Enrich Data"``), a slug
    (``"enrich-data"``), or a unique prefix (``"enrich"``).
    """
    key = str(key).strip()
    if not key:
        raise ValueError("No step specified. Use a number, name, or method name.")

    key_lower = key.lower()
    key_slug = _slugify(key)

    # Exact match on number, method name, display name, or slug.
    for number, (name, method) in enumerate(PIPELINE_STEPS, start=1):
        if key_lower in (str(number), method, name.lower(), _slugify(name)):
            return (name, method)

    # Unique prefix match (e.g. "enrich" -> "Enrich Data").
    prefix_matches = [
        (name, method)
        for name, method in PIPELINE_STEPS
        if _slugify(name).startswith(key_slug) or method.startswith(key_lower)
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    listing = "\n".join(
        f"  {number:>2}: {name} ({method})"
        for number, (name, method) in enumerate(PIPELINE_STEPS, start=1)
    )
    if len(prefix_matches) > 1:
        ambiguous = ", ".join(name for name, _ in prefix_matches)
        raise ValueError(
            f"Ambiguous step '{key}' (matches: {ambiguous}). "
            f"Use a number, name, or method name:\n{listing}"
        )
    raise ValueError(
        f"Unknown step '{key}'. Use a number, name, or method name:\n{listing}"
    )


class ViennaDataPipeline:
    """Main pipeline orchestrator"""

    def __init__(self, clean_start=False, use_live_export=False, dump_path=None):
        self.loader = GraphDBLoader()
        self.clean_start = clean_start
        self.use_live_export = use_live_export
        self.dump_path = dump_path
        self.dump_available = (
            not use_live_export and resolve_dump_path(dump_path) is not None
        )

    def step_1_extract_vienna_wiki(self):
        """Extract vienna wiki pages (dump-first, live export fallback)"""
        print("\n" + "=" * 60)
        print("STEP 1: Extract Vienna Wiki Data")
        print("=" * 60)

        if self.dump_available:
            print("Source: local Vienna History Wiki dump")
            extractor = DumpWikiExtractor(dump_path=self.dump_path)
            extractor.extract_base_entities()
            print(f"Vienna History Wiki data extracted from {extractor.dump_path}")
        else:
            print("Source: live Vienna History Wiki RDF export")
            extractor = ViennaHistoryWikiExtractor()
            extractor.run_extraction()
            print("Vienna History Wiki data extracted via live RDF export")

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
        count = self.loader.load_directory(RAW_BASE, "**/*.rdf")

        print(f"\nLoaded {count} files into GraphDB")
        return count > 0

    def step_4_extract_related_entities(self):
        """Extract related entities (dump-first, GraphDB/live fallback)"""
        print("\n" + "=" * 60)
        print("STEP 4: Fetch related entities (architects, famous inhabitants, named after)")
        print("=" * 60)

        source = "dump" if self.dump_available else "live"
        print(f"Source: {source}")
        extractor = RelatedEntitiesExtractor(source=source, dump_path=self.dump_path)
        extractor.run_extraction()
        return True

    def step_5_load_related_entities(self):
        """Load related entities into GraphDB"""
        print("\n" + "=" * 60)
        print("STEP 5: Load Related Entities Raw Data into GraphDB")
        print("=" * 60)

        count = self.loader.load_directory(RAW_RELATED, "**/*.rdf")

        print(f"\nLoaded {count} files into GraphDB")
        return count > 0

    @staticmethod
    def step_6_enrich_data():
        """Enrich entities with cultural heritage IDs and architectural styles from Wikidata"""
        print("\n" + "=" * 60)
        print("STEP 6: Enrich data from Wikidata (heritage IDs + architectural styles)")
        print("=" * 60)

        monument_enricher = WikidataMonumentEnricher()
        monument_enricher.enrich_with_wikidata_heritage_ids()
        monument_enricher.enrich_with_wikidata_architectural_styles()
        return True

    def step_7_load_districts(self):
        """Load district borders from into GraphDB"""
        print("\n" + "=" * 60)
        print("STEP 7: Load District Borders into GraphDB")
        print("=" * 60)

        district_file = Path(PROCESSED_DIR) / "vienna_districts.ttl"

        if not district_file.exists():
            print(f"District file not found: {district_file}")
            return False

        success = self.loader.load_file(str(district_file))
        return success

    def step_8_transform_coordinates(self):
        """Transform coordinates to GeoSPARQL format"""
        print("\n" + "=" * 60)
        print("STEP 8: Transform Coordinates to GeoSPARQL")
        print("=" * 60)

        # Execute the geo transformation SPARQL update
        query = load_query("insert_geo.sparql")

        self.loader.execute_sparql_update(query)
        return True

    def step_9_link_buildings_to_districts(self):
        """Link buildings to their districts using spatial queries"""
        print("\n" + "=" * 60)
        print("STEP 9: Link Buildings to Districts")
        print("=" * 60)

        # SPARQL INSERT query to link buildings to districts
        query = load_query("link_districts.sparql")
        self.loader.execute_sparql_update(query)

        print("Executing spatial join to link buildings to districts...")

        return True

    def step_10_validate(self):
        """Validate the final data"""
        print("\n" + "=" * 60)
        print("STEP 10: Validate Data")
        print("=" * 60)

        # Get statistics
        total_triples = self.loader.get_triple_count()
        print(f"Total triples: {total_triples:,}")

        # Count specific entities
        queries = {
            "Subjects with geometry": """
                SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE {
                    ?s <http://www.opengis.net/ont/geosparql#hasGeometry> ?geom .
                }
            """,
            "Districts": """
                SELECT (COUNT(DISTINCT ?d) AS ?count) WHERE {
                    ?d a <https://schema.org/AdministrativeArea> ;
                       <https://schema.org/identifier> ?i .
                    FILTER(xsd:integer(?i) <= 23)
                }
            """,
            "Subjects linked to districts": """
                SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE {
                    ?s <https://schema.org/containedInPlace> ?district .
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

    def step_11_build_kge(self):
        """Add KGE to validated knowledge graph"""
        print("\n" + "=" * 60)
        print("STEP 11: Build KGE layer onto validated knowledge graph")
        print("=" * 60)
        run_kge_step()
        return True

    def run_full_pipeline(self):
        """Execute complete pipeline"""
        print("\n" + "=" * 60)
        print("VIENNA HISTORICAL MAP - ELT PIPELINE")
        print("=" * 60)

        start_time = time.time()

        steps = [
            (name, getattr(self, method)) for name, method in PIPELINE_STEPS
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

    def run_step(self, step_key):
        """Run a single pipeline step in isolation."""
        name, method = resolve_step(step_key)
        step_func = getattr(self, method)

        print("\n" + "=" * 60)
        print("VIENNA HISTORICAL MAP - ELT PIPELINE (single step)")
        print("=" * 60)
        print(f"Running step: {name} ({method})")

        start_time = time.time()
        try:
            success = step_func()
            result = "Success" if success else "Error"
        except Exception as e:
            result = "Error"
            print(f"\nError in {name}: {e}")
            import traceback
            traceback.print_exc()

        elapsed = time.time() - start_time

        print("\n" + "=" * 60)
        print("STEP SUMMARY")
        print("=" * 60)
        print(f"{result} {name}")
        print(f"Total time: {elapsed:.1f} seconds")
        print("=" * 60)

        return result == "Success"


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Vienna Historical Map ELT Pipeline')
    parser.add_argument('--clean', action='store_true',
                        help='Clear GraphDB before loading (WARNING: deletes all data)')
    parser.add_argument('--skip-extract', action='store_true',
                        help='Skip extraction steps (use existing data)')
    parser.add_argument('--step', default=None,
                        help='Run a single step by number, name, or method name '
                             '(e.g. "6", "Enrich Data", "step_6_enrich_data")')
    parser.add_argument('--list-steps', action='store_true',
                        help='List available pipeline steps and exit')
    parser.add_argument('--use-live-export', action='store_true',
                        help='Force live Vienna History Wiki RDF export instead of the dump')
    parser.add_argument('--dump-path', default=None,
                        help='Override the Vienna History Wiki dump path')

    args = parser.parse_args()

    if args.list_steps:
        for number, (name, method) in enumerate(PIPELINE_STEPS, start=1):
            print(f"{number:>2}: {name} ({method})")
        sys.exit(0)

    pipeline = ViennaDataPipeline(
        clean_start=args.clean,
        use_live_export=args.use_live_export,
        dump_path=args.dump_path,
    )

    if args.step is not None:
        try:
            ok = pipeline.run_step(args.step)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        sys.exit(0 if ok else 1)

    if args.skip_extract:
        print("Skipping extraction - using existing data")
        # Skip to step 3
        pipeline.step_3_load_raw_data()
        pipeline.step_5_load_related_entities()
        pipeline.step_6_enrich_data()
        pipeline.step_7_load_districts()
        pipeline.step_8_transform_coordinates()
        pipeline.step_9_link_buildings_to_districts()
        pipeline.step_10_validate()
    else:
        pipeline.run_full_pipeline()
