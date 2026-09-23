from pathlib import Path

import pandas as pd
from SPARQLWrapper import SPARQLWrapper, POST

from elt.kge.exporter import GRAPHDB_URL, GRAPHDB_REPO

KGE_NS = "http://example.org/vienna/kge/"
KGE_GRAPH = "http://www.geschiechtewiki.wien.gv.at/kge-derived"
BATCH_SIZE = 4000

PREDICTED_STYLES_PATH = Path("data/processed/predicted_styles.tsv")
SIMILAR_BUILDINGS_PATH = Path("data/processed/similar_buildings.tsv")
CLUSTERS_PATH = Path("data/processed/building_clusters.tsv")


def _update_client() -> SPARQLWrapper:
    sparql = SPARQLWrapper(f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}/statements")
    sparql.setMethod(POST)
    return sparql


def _uri(value: str) -> str:
    return f"<{value}>"


def build_style_triples(df: pd.DataFrame) -> list[str]:
    triples = []
    for _, row in df.iterrows():
        b = _uri(row["building"])
        triples.append(
            f'{b} <{KGE_NS}predictedArchitecturalStyle> {_uri(row["predicted_style"])} .'
        )
        triples.append(
            f'{b} <{KGE_NS}predictionConfidence> '
            f'"{row["score"]:.4f}"^^<http://www.w3.org/2001/XMLSchema#float> .'
        )
    return triples


def build_similarity_triples(df: pd.DataFrame) -> list[str]:
    triples = []
    for i, row in df.iterrows():
        bnode = f"_:sim{i}"
        b = _uri(row["building"])
        triples.append(f"{b} <{KGE_NS}hasSimilarBuilding> {bnode} .")
        triples.append(f'{bnode} <{KGE_NS}similarBuilding> {_uri(row["similar_to"])} .')
        triples.append(
            f'{bnode} <{KGE_NS}similarityScore> '
            f'"{row["similarity"]:.4f}"^^<http://www.w3.org/2001/XMLSchema#float> .'
        )
    return triples


def build_cluster_triples(df: pd.DataFrame) -> list[str]:
    triples = []
    seen_clusters = set()
    for _, row in df.iterrows():
        b = _uri(row["building"])
        cluster_uri = f"{KGE_NS}cluster/{row['cluster_id']}"
        triples.append(f"{b} <{KGE_NS}hasCluster> {_uri(cluster_uri)} .")
        if cluster_uri not in seen_clusters:
            triples.append(f"{_uri(cluster_uri)} a <{KGE_NS}BuildingCluster> .")
            seen_clusters.add(cluster_uri)
    return triples


def write_to_graphdb(triples: list[str]) -> None:
    """Deletes the current KGE-derived-graph once (idempotent on re-runs) and fills it in batches."""
    sparql = _update_client()

    sparql.setQuery(f"DROP SILENT GRAPH <{KGE_GRAPH}>")
    sparql.query()

    for i in range(0, len(triples), BATCH_SIZE):
        batch = triples[i: i + BATCH_SIZE]
        triples_block = "\n        ".join(batch)
        update = f"""
        INSERT DATA {{
          GRAPH <{KGE_GRAPH}> {{
            {triples_block}
          }}
        }}
        """
        sparql.setQuery(update)
        sparql.query()
        print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} triples written.")


if __name__ == "__main__":
    all_triples = []

    if PREDICTED_STYLES_PATH.exists():
        styles_df = pd.read_csv(PREDICTED_STYLES_PATH, sep="\t")
        all_triples += build_style_triples(styles_df)
        print(f"{len(styles_df)} style-predictions prepared.")

    if SIMILAR_BUILDINGS_PATH.exists():
        sim_df = pd.read_csv(SIMILAR_BUILDINGS_PATH, sep="\t")
        all_triples += build_similarity_triples(sim_df)
        print(f"{len(sim_df)} similarity-pairs prepared.")

    if CLUSTERS_PATH.exists():
        cluster_df = pd.read_csv(CLUSTERS_PATH, sep="\t")
        all_triples += build_cluster_triples(cluster_df)
        print(f"{len(cluster_df)} cluster-assignments prepared.")

    write_to_graphdb(all_triples)
    print(f"{len(all_triples)} triples written to graph <{KGE_GRAPH}>.")