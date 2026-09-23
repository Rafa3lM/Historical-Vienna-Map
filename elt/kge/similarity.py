from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans
from SPARQLWrapper import SPARQLWrapper, JSON

from elt.kge.trainer import load_and_split
from elt.kge.predictor import load_trained_model
from elt.kge.exporter import GRAPHDB_URL, GRAPHDB_REPO

TOP_K_NEIGHBORS = 5
NUM_CLUSTERS = 10
SIMILARITY_OUTPUT = Path("data/processed/similar_buildings.tsv")
CLUSTERS_OUTPUT = Path("data/processed/building_clusters.tsv")


def get_all_buildings(sparql: SPARQLWrapper) -> list[str]:
    query = """
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    SELECT DISTINCT ?building WHERE {
      ?building geo:hasGeometry ?g .
    }
    """
    sparql.setQuery(query)
    results = sparql.query().convert()
    return [row["building"]["value"] for row in results["results"]["bindings"]]


def extract_building_embeddings(model, training_tf, buildings: list[str]):
    entity_embeddings = model.entity_representations[0]().detach().cpu().numpy()

    labels, vectors = [], []
    skipped = 0
    for building in buildings:
        entity_id = training_tf.entity_to_id.get(building)
        if entity_id is None:
            skipped += 1
            continue
        labels.append(building)
        vectors.append(entity_embeddings[entity_id])

    if skipped:
        print(f"Skipped {skipped} buildings (not included in training graph).")

    return labels, np.vstack(vectors)


def compute_similarity(labels: list[str], vectors: np.ndarray) -> pd.DataFrame:
    nn = NearestNeighbors(n_neighbors=TOP_K_NEIGHBORS + 1, metric="cosine")
    nn.fit(vectors)
    distances, indices = nn.kneighbors(vectors)

    rows = []
    for i, building in enumerate(labels):
        for dist, j in zip(distances[i][1:], indices[i][1:]):
            rows.append(
                {
                    "building": building,
                    "similar_to": labels[j],
                    "similarity": 1 - dist,  # cosine distance -> similarity
                }
            )
    return pd.DataFrame(rows)


def compute_clusters(labels: list[str], vectors: np.ndarray) -> pd.DataFrame:
    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(vectors)
    print(f"KMenas inertia (k={NUM_CLUSTERS}): {kmeans.inertia_:.1f}")
    return pd.DataFrame({"building": labels, "cluster_id": cluster_ids})


if __name__ == "__main__":
    sparql = SPARQLWrapper(f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}")
    sparql.setReturnFormat(JSON)

    training_tf, _, _ = load_and_split()
    model = load_trained_model()

    buildings = get_all_buildings(sparql)
    print(f"Number of buildings: {len(buildings)}.")

    labels, vectors = extract_building_embeddings(model, training_tf, buildings)
    print(f"Extracted {len(buildings)} building embeddings.")

    similarity_df = compute_similarity(labels, vectors)
    SIMILARITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    similarity_df.to_csv(SIMILARITY_OUTPUT, sep="\t", index=False)
    print(f"Similarity table saved to {SIMILARITY_OUTPUT}")

    clusters_df = compute_clusters(labels, vectors)
    clusters_df.to_csv(CLUSTERS_OUTPUT, sep="\t", index=False)
    print(f"Cluster assignment saved to {CLUSTERS_OUTPUT}")