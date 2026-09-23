from pathlib import Path
from collections import Counter

from SPARQLWrapper import SPARQLWrapper, JSON

from elt.config import GRAPHDB_URL, GRAPHDB_REPO

PREFIXES = """
PREFIX schema: <https://schema.org/>
PREFIX property: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A>
"""

RELEVANT_PREDICATES = [
    "schema:artist",
    "schema:relatedTo",
    "property:Benannt_nach",
    "property:Art_des_Bauwerks",
    "property:Art_des_Objekts",
    "property:Art_des_Ereignisses",
    "property:Historisch",
    "property:WikidataArchitecturalStyle",
    "schema:containedInPlace",
    "schema:relatedLink",
]


def _client() -> SPARQLWrapper:
    sparql = SPARQLWrapper(f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}")
    sparql.setReturnFormat(JSON)
    return sparql


def check_predicate_value_types() -> None:
    """Shows for every predicate if the objects are URIs or literals."""

    sparql = _client()
    for predicate in RELEVANT_PREDICATES:
        query = f"""
        {PREFIXES}
        SELECT ?o WHERE {{ ?s {predicate} ?o . }} LIMIT 20 
        """
        sparql.setQuery(query)
        results = sparql.query().convert()
        types = Counter(
            row["o"]["type"] for row in results["results"]["bindings"]
        )
        print(f"{predicate:35s} -> {dict(types)}")


def export_triples(output_path: Path) -> int:
    """Exports all relevant triples (only URI-objects) as TSV for PyKeen. Returns the number of written triples."""
    sparql = _client()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for predicate in RELEVANT_PREDICATES:
            query = f"""
            {PREFIXES}
            SELECT ?s ?o WHERE {{
              ?s {predicate} ?o .
              FILTER(isURI(?o))
            }}
            """
            sparql.setQuery(query)
            results = sparql.query().convert()

            for row in results["results"]["bindings"]:
                head = row["s"]["value"]
                tail = row["o"]["value"]
                f.write(f"{head}\t{predicate}\t{tail}\n")
                count += 1

        return count


if __name__ == "__main__":
    print("""Diagnose: Value types of relevant predicates""")
    check_predicate_value_types()

    print("\n=== Export ===")
    out = Path("data/processed/kge_triples.tsv")
    n = export_triples(out)
    print(f"{n} triples written to {out}")