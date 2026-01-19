from pathlib import Path
from fastapi import HTTPException
from SPARQLWrapper import SPARQLWrapper, JSON

from elt.utils.query_loader import load_query
from .extract_vienna_history_wiki import ViennaHistoryWikiExtractor
from elt.loaders.graphdb_loader import GraphDBLoader

from elt.config import EXPORT_URL, RAW_RELATED, GRAPHDB_SPARQL, RATE_LIMIT_DELAY


HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded"
}


class RelatedEntitiesExtractor:
    """
    Extract related entities: Architects (Artists), Famous Inhabitants, Named After
    """

    def __init__(self):
        self.export_url = EXPORT_URL
        self.graphdb_url = GRAPHDB_SPARQL
        self.raw_related = RAW_RELATED
        self.extract_vienna = ViennaHistoryWikiExtractor()
        self.graphdb_loader = GraphDBLoader()

    def get_related_entities(self) -> dict:
        """Query GraphDB for all related entity pages"""

        print("Querying GraphDB for related entities...")

        sparql = SPARQLWrapper(self.graphdb_url)
        query = load_query("extract_related_entities.sparql")

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        try:
            results = sparql.query().convert()

            entities_by_type = {
                'architect': set(),
                'inhabitant': set(),
                'namedAfter': set()
            }

            for b in results["results"]["bindings"]:
                entities_by_type[b["type"]["value"]].add(b["entity"]["value"])

            total = sum(len(entities) for entities in entities_by_type.values())
            print(f"Found {total} related entities:")
            print(f" - Architects: {len(entities_by_type['architect'])}")
            print(f" - Famous Inhabitants: {len(entities_by_type['inhabitant'])}")
            print(f" - Named After: {len(entities_by_type['namedAfter'])}")

            return entities_by_type
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SPARQL query failed: {str(e)}")

    def fetch_entities_batch(self, pages: list, batch_name: str, batch_size=100):
        """Fetch entities in batches"""
        total = len(pages)
        print(f"\nFetching {total} entities for {batch_name}...")

        page_names = [
            uri.split("/Special:URIResolver/")[-1]
            for uri in pages
        ]

        path = Path(RAW_RELATED)

        return self.extract_vienna.fetch_details(
            path=path,
            prefix=batch_name,
            entity_urls=page_names,
            batch_size=batch_size,
        )

    def run_extraction(self):
        """Main extraction workflow"""

        # Get pages to extract from GraphDB
        entities_by_type = self.get_related_entities()

        if not entities_by_type:
            print("No related entities found or error querying GraphDB")
            return

        # Fetch each type and load into graphDB
        if entities_by_type['architect']:
            self.fetch_entities_batch(entities_by_type['architect'], 'architects')

        if entities_by_type['inhabitant']:
            self.fetch_entities_batch(entities_by_type['inhabitant'], 'inhabitants')

        if entities_by_type['namedAfter']:
            self.fetch_entities_batch(entities_by_type['namedAfter'], 'named_after')

        # self.graphdb_loader.load_directory(str(self.raw_dir))


if __name__ == "__main__":
    extractor = RelatedEntitiesExtractor()
    extractor.run_extraction()
