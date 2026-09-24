from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import DBSCAN
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

    if np.iscomplexobj(entity_embeddings):
        entity_embeddings = np.concatenate(
            [entity_embeddings.real, entity_embeddings.imag], axis=-1
        )

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
    dbscan = DBSCAN(eps=0.5, min_samples=6, metric="cosine")
    cluster_ids = dbscan.fit_predict(vectors)

    n_clusters = len(set(cluster_ids)) - (1 if -1 in cluster_ids else 0)
    noise_ratio = (cluster_ids == -1).mean()
    print(f"DBSCAN (eps={dbscan.eps}, min_samples={dbscan.min_samples}): {n_clusters} Cluster, {noise_ratio:.1%} Noise")
    return pd.DataFrame({"building": labels, "cluster_id": cluster_ids})


def grid_search_dbscan(
        vectors: np.ndarray,
        eps_values=(0.45, 0.46, 0.47, 0.48, 0.49, 0.5, 0.51, 0.52, 0.53, 0.54, 0.55, 0.56, 0.57, 0.58, 0.59),
        min_samples_values=(4, 5, 6, 7, 8, 9, 10),
        #eps_values=(0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.45, 0.5, 0.6),
        #min_samples_values=(4, 6, 8, 10),
) -> pd.DataFrame:
    rows = []
    for min_samples in min_samples_values:
        for eps in eps_values:
            labels = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit_predict(vectors)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            noise_ratio = (labels == -1).mean()
            rows.append(
                {
                    "min_samples": min_samples,
                    "eps": eps,
                    "n_clusters": n_clusters,
                    "noise_ratio": round(noise_ratio, 3),
                }
            )
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    return df


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

    #grid_search_dbscan(vectors)
    clusters_df = compute_clusters(labels, vectors)
    clusters_df.to_csv(CLUSTERS_OUTPUT, sep="\t", index=False)
    print(f"Cluster assignment saved to {CLUSTERS_OUTPUT}")