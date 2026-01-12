import requests
import time
from pathlib import Path
from rdflib import Graph, RDF, RDFS

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BASE_URL, EXPORT_URL, RAW_DIR, CATEGORIES, RATE_LIMIT_DELAY, SWIVT

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded"
}


class ViennaHistoryWikiExtractor:
    """Extract data from Vienna History Wiki"""

    def __init__(self):
        self.base_url = BASE_URL
        self.export_url = EXPORT_URL
        self.raw_dir = RAW_DIR

    @staticmethod
    def fetch_pages(page_names, filename, backlinks=True):
        payload = {
            "postform": "1",
            "pages": "\n".join(page_names),
            "backlinks": "1" if backlinks else "0",
        }

        print(f"Fetching {len(page_names)} pages")

        r = requests.post(EXPORT_URL, data=payload, headers=HEADERS)
        r.raise_for_status()

        path = Path(RAW_DIR)
        path.mkdir(parents=True, exist_ok=True)

        out = path / filename
        out.write_bytes(r.content)

        print(f"Saved to {filename}")

        return out

    def fetch_details(self, prefix, building_urls, batch_size=100):
        all_files = []

        for i in range(0, len(building_urls), batch_size):
            batch = building_urls[i:i + batch_size]

            pages = [
                url.split("/Special:ExportRDF/")[-1]
                for url in batch
            ]

            base_path = Path(RAW_DIR)
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
                    rdf_file = self.fetch_pages(pages, filename, backlinks=False)
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
                pages.add(str(defined_by))

        print(f"Found {len(pages)} unique RDF pages")

        return sorted(pages)

    def run_extraction(self):
        buildings_file = self.fetch_pages(CATEGORIES["buildings"], "bauwerke_subcategories.rdf")
        buildings = self.extract_entities_from_category(buildings_file)
        building_rdf_files = self.fetch_details("buildings", buildings)

        places_file = self.fetch_pages(CATEGORIES["places"], "topographische_objekte_subcategories.rdf")
        places = self.extract_entities_from_category(places_file)
        places_rdf_files = self.fetch_details("places", places)

        events_file = self.fetch_pages(CATEGORIES["events"], "ereignisse_subcategories.rdf")
        events = self.extract_entities_from_category(events_file)
        events_rdf_files = self.fetch_details("events", events)

        print(f"Import complete")


if __name__ == "__main__":
    extractor = ViennaHistoryWikiExtractor()
    extractor.run_extraction()
