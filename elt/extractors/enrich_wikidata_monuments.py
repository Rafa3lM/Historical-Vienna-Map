from SPARQLWrapper import SPARQLWrapper
from elt.config import GRAPHDB_UPDATE
from elt.utils.query_loader import load_query


class WikidataMonumentEnricher:
    """Extract Wikidata entities with cultural heritage IDs for all loaded Vienna History Wiki entities"""

    def __init__(self):
        self.graphdb_update = GRAPHDB_UPDATE

    def enrich_with_wikidata_heritage_ids(self):
        """
        Federated SPARQL query to enrich entities with Wikidata heritage IDs

        The query:
        1. Finds Vienna entities with Wikidata links
        2. Queries Wikidata for cultural heritage IDs
        3. Inserts the IDs back into the GraphDB
        """

        print("Executing federated query to Wikidata...")

        sparql = SPARQLWrapper(self.graphdb_update)
        query = load_query("enrich_monuments.sparql")

        sparql.setQuery(query)
        sparql.method = "POST"
        sparql.query()

        print("Inserted monument IDs")
