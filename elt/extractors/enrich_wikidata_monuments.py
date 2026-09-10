import requests
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDFS
from SPARQLWrapper import SPARQLWrapper, JSON

from elt.config import GRAPHDB_UPDATE, GRAPHDB_SPARQL, WIKIDATA_SPARQL, WIKIDATA_USER_AGENT
from elt.utils.query_loader import load_query

PROPERTY = Namespace("http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A")

# Placeholder replaced with a VALUES block built from the local GraphDB mappings.
VALUES_PLACEHOLDER = "__VALUES__"

# Wikidata has no hard row limit for VALUES clauses, but chunking keeps the
# individual requests small enough to avoid timeouts.
WIKIDATA_CHUNK_SIZE = 250


def _to_term(binding):
    """Convert a SPARQL JSON result binding into an rdflib term."""
    if binding.get("type") == "uri":
        return URIRef(binding["value"])

    value = binding["value"]
    lang = binding.get("xml:lang")
    datatype = binding.get("datatype")

    if lang:
        return Literal(value, lang=lang)
    if datatype:
        return Literal(value, datatype=URIRef(datatype))
    return Literal(value)


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


class WikidataMonumentEnricher:
    """Extract Wikidata entities with cultural heritage IDs and architectural
    styles for all loaded Vienna History Wiki entities.

    Wikidata rejects requests without a descriptive User-Agent, so the
    enrichment no longer relies on GraphDB's federated ``SERVICE`` clause
    (whose outbound request we cannot control). Instead we:

    1. read the local entity -> Wikidata URI mappings from GraphDB,
    2. query Wikidata directly from Python with a compliant User-Agent,
    3. insert the resulting triples back into GraphDB.
    """

    def __init__(self):
        self.graphdb_sparql = GRAPHDB_SPARQL
        self.graphdb_update = GRAPHDB_UPDATE

    # --- GraphDB helpers -------------------------------------------------

    def _graphdb_select(self, query):
        sparql = SPARQLWrapper(self.graphdb_sparql)
        sparql.setReturnFormat(JSON)
        sparql.setQuery(query)
        results = sparql.query().convert()
        return results["results"]["bindings"]

    # --- Wikidata helpers -------------------------------------------------

    def _wikidata_select(self, query):
        sparql = SPARQLWrapper(WIKIDATA_SPARQL)
        sparql.agent = WIKIDATA_USER_AGENT
        sparql.setReturnFormat(JSON)
        sparql.setMethod("POST")
        sparql.setQuery(query)
        results = sparql.query().convert()
        return results["results"]["bindings"]

    @staticmethod
    def _values_block(uris):
        return "\n".join(f"        <{uri}>" for uri in uris)

    # --- Shared flow ------------------------------------------------------

    def _local_mappings(self, include_objects=True):
        """Return ``{wikidata_uri: local_entity_uri}`` for enriched entities."""
        type_clauses = "{ ?entity property:Art_des_Bauwerks ?t }"
        if include_objects:
            type_clauses += " UNION { ?entity property:Art_des_Objekts ?t }"

        query = f"""
            PREFIX property: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?entity ?wikidataUri WHERE {{
                {type_clauses}
                ?entity skos:exactMatch ?wikidataUri .
                FILTER(STRSTARTS(STR(?wikidataUri), "http://www.wikidata.org/entity/"))
            }}
        """

        bindings = self._graphdb_select(query)
        mapping = {}
        for binding in bindings:
            mapping[binding["wikidataUri"]["value"]] = binding["entity"]["value"]
        return mapping

    def _wikidata_rows(self, query_template, wikidata_uris):
        rows = []
        for chunk in _chunks(wikidata_uris, WIKIDATA_CHUNK_SIZE):
            query = query_template.replace(
                VALUES_PLACEHOLDER, self._values_block(chunk)
            )
            rows.extend(self._wikidata_select(query))
        return rows

    def _insert_graph(self, graph, description):
        if len(graph) == 0:
            print(f"No new {description} to insert")
            return

        # Wrap the N-Triples in INSERT DATA and use GraphDB's SPARQL update
        # endpoint (the same path the pipeline already uses for transformations).
        ntriples = graph.serialize(format="nt")
        query = f"INSERT DATA {{\n{ntriples}\n}}"
        headers = {
            "Content-Type": "application/sparql-update",
            "Accept": "application/json",
        }
        response = requests.post(
            self.graphdb_update,
            data=query.encode("utf-8"),
            headers=headers,
            timeout=120,
        )

        if response.status_code in (200, 201, 204):
            print(f"{description} complete ({len(graph)} triples)")
        else:
            raise RuntimeError(
                f"Failed to insert {description}: "
                f"HTTP {response.status_code} {response.text[:200]}"
            )

    # --- Enrichment steps -------------------------------------------------

    def enrich_with_wikidata_heritage_ids(self):
        """Add Wikidata cultural heritage (P2951) and HERIS (P9154) IDs."""

        print("Executing query to Wikidata: Inserted monument IDs...")

        mapping = self._local_mappings(include_objects=True)
        if not mapping:
            print("No entities with Wikidata links found; skipping monument IDs")
            return

        template = load_query("enrich_monuments.sparql")
        graph = Graph()

        for row in self._wikidata_rows(template, list(mapping)):
            entity = mapping[row["wikidataUri"]["value"]]

            if row.get("cultId"):
                graph.add((
                    URIRef(entity),
                    PROPERTY.WikidataCulturalHeritageID,
                    _to_term(row["cultId"]),
                ))
            if row.get("herisId"):
                graph.add((
                    URIRef(entity),
                    PROPERTY.WikidataHERISID,
                    _to_term(row["herisId"]),
                ))

        self._insert_graph(graph, "monument IDs")

    def enrich_with_wikidata_architectural_styles(self):
        """Add architectural styles (Wikidata P149) for buildings."""

        print("Executing query to Wikidata: Inserted architectural styles...")

        mapping = self._local_mappings(include_objects=False)
        if not mapping:
            print("No buildings with Wikidata links found; skipping architectural styles")
            return

        template = load_query("enrich_architectural_styles.sparql")
        graph = Graph()

        for row in self._wikidata_rows(template, list(mapping)):
            entity = mapping[row["wikidataUri"]["value"]]
            style = _to_term(row["style"])  # Wikidata style entity URI

            graph.add((URIRef(entity), PROPERTY.WikidataArchitecturalStyle, style))
            graph.add((style, RDFS.label, _to_term(row["styleLabel"])))

        self._insert_graph(graph, "architectural styles")
