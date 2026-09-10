import requests
import time
from pathlib import Path
from rdflib import Graph, RDF, RDFS

import sys

from elt.utils.wiki import extract_page_name

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BASE_URL, EXPORT_URL, RAW_BASE, CATEGORIES, RATE_LIMIT_DELAY, SWIVT

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded"
}


class ViennaHistoryWikiExtractor:
    """Extract data from Vienna History Wiki via the live RDF export.

    This is the fallback path when no local wiki dump is available (or when
    ``--use-live-export`` is requested).  It POSTs page names to
    ``Spezial:RDF_exportieren`` over HTTP.
    """

    def __init__(self):
        self.base_url = BASE_URL
        self.export_url = EXPORT_URL
        self.raw_base = RAW_BASE

    @staticmethod
    def fetch_pages(path, page_names, filename, backlinks=True):
        payload = {
            "postform": "1",
            "pages": "\n".join(page_names),
            "backlinks": "1" if backlinks else "0",
        }

        print(f"Fetching {len(page_names)} pages")

        r = requests.post(EXPORT_URL, data=payload, headers=HEADERS)
        r.raise_for_status()

        base_path = Path(path)
        base_path.mkdir(parents=True, exist_ok=True)

        out = base_path / filename
        out.write_bytes(r.content)

        print(f"Saved to {filename}")

        return out

    def fetch_details(self, path, prefix, entity_urls, batch_size=100):
        all_files = []

        for i in range(0, len(entity_urls), batch_size):
            batch = entity_urls[i:i + batch_size]

            pages = [
                extract_page_name(url)
                for url in batch
            ]

            base_path = Path(path)
            base_path.mkdir(parents=True, exist_ok=True)
            filename = f"{prefix}_{i}_{i + len(pages) - 1}.rdf"
            filepath = base_path / filename

            if filepath.exists():
                print(f"Skipping already downloaded batch: {filename}")
                all_files.append(filepath)
                continue

            success = False
            attempts = 0
            while not success and attempts < 5:
                try:
                    rdf_file = self.fetch_pages(path, pages, filename, backlinks=False)
                    all_files.append(rdf_file)
                    success = True
                except Exception as e:
                    attempts += 1
                    print(f"Error fetching batch {filename}: {e}")
                    wait_time = RATE_LIMIT_DELAY * 5 * attempts
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

            if not success:
                print(f"Failed to fetch batch {filename} after {attempts} attempts. Skipping.")

            time.sleep(RATE_LIMIT_DELAY)

        return all_files

    @staticmethod
    def extract_entities_from_category(filename):
        print(f"Extracting buildings from {filename}")

        g = Graph()
        g.parse(filename)

        pages = set()

        for subj in g.subjects(RDF.type, None):
            ns = g.value(subj, SWIVT.wikiNamespace)
            if ns is None or str(ns) != "0":
                continue

            defined_by = g.value(subj, RDFS.isDefinedBy)
            if defined_by:
                # ExportRDF fails for -28 / -29 encoded parentheses.
                # Replace them with literal '(' and ')'.
                pages.add(str(defined_by)
                          .replace("-28", "(")
                          .replace("-29", ")")
                          )

        print(f"Found {len(pages)} unique RDF pages")

        return sorted(pages)

    def run_extraction(self):
        """Run the live wiki RDF export for all configured categories."""
        buildings_file = self.fetch_pages(self.raw_base, CATEGORIES["buildings"], "bauwerke_subcategories.rdf")
        buildings = self.extract_entities_from_category(buildings_file)
        building_rdf_files = self.fetch_details(self.raw_base, "buildings", buildings)

        places_file = self.fetch_pages(self.raw_base, CATEGORIES["places"], "topographische_objekte_subcategories.rdf")
        places = self.extract_entities_from_category(places_file)
        places_rdf_files = self.fetch_details(self.raw_base, "places", places)

        events_file = self.fetch_pages(self.raw_base, CATEGORIES["events"], "ereignisse_subcategories.rdf")
        events = self.extract_entities_from_category(events_file)
        events_rdf_files = self.fetch_details(self.raw_base, "events", events)

        print(f"Import complete")


if __name__ == "__main__":
    extractor = ViennaHistoryWikiExtractor()
    extractor.run_extraction()
