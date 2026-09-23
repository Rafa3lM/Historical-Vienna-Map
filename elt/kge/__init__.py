from SPARQLWrapper import SPARQLWrapper, JSON

from elt.kge.exporter import (
    export_triples,
    check_predicate_value_types,
    GRAPHDB_URL,
    GRAPHDB_REPO,
)
from elt.kge.trainer import (
    load_and_split,
    train_model,
    compare_metrics,
    TRIPLES_PATH,
    MODELS_TO_COMPARE,
)
from elt.kge.predictor import (
    load_trained_model,
    get_valid_style_values,
    find_buildings_missing_style,
    predict_styles,
    OUTPUT_PATH as PREDICTED_STYLES_PATH,
)
from elt.kge.similarity import (
    get_all_buildings,
    extract_building_embeddings,
    compute_similarity,
    compute_clusters,
    SIMILARITY_OUTPUT,
    CLUSTERS_OUTPUT,
)
from elt.kge.writer import (
    build_style_triples,
    build_similarity_triples,
    build_cluster_triples,
    write_to_graphdb,
)


def _sparql_client() -> SPARQLWrapper:
    sparql = SPARQLWrapper(f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}")
    sparql.setReturnFormat(JSON)
    return sparql


def run_kge_step(skip_export: bool = False, skip_training: bool = False):
    sparql = _sparql_client()

    # --- Export ---
    if not skip_export:
        print("=== KGE: Diagnose value-types ===")
        check_predicate_value_types()
        print("\n=== KGE: Export ===")
        n = export_triples(TRIPLES_PATH)
        print(f"{n} triples exported to {TRIPLES_PATH}")
    else:
        print("=== KGE: Export skipped (skip_export=True) ===")

    # --- Training ---
    training_tf, testing_tf, validation_tf = load_and_split()

    if not skip_training:
        print("\n=== KGE: Training ===")
        results = {}
        for model_name in MODELS_TO_COMPARE:
            print(f"--- Training {model_name} ---")
            results[model_name] = train_model(
                model_name, training_tf, testing_tf, validation_tf
            )
        compare_metrics(results)
    else:
        print("=== KGE: Training skipped (skip_training=True) ===")

    # --- Prediction: Architectural Style ---
    print("\n=== KGE: Architectural Style Predictions ===")
    model = load_trained_model()
    valid_styles = get_valid_style_values()
    buildings_missing_style = find_buildings_missing_style(sparql)
    print(f"{len(buildings_missing_style)} buildings missing architectural styles.")
    styles_df = predict_styles(model, training_tf, buildings_missing_style, valid_styles)
    PREDICTED_STYLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    styles_df.to_csv(PREDICTED_STYLES_PATH, sep="\t", index=False)
    print(f"{len(styles_df)} Predictions saved to {PREDICTED_STYLES_PATH}")

    # --- Similarity & Clustering ---
    print("\n=== KGE: Similarity & Clustering ===")
    all_buildings = get_all_buildings(sparql)
    labels, vectors = extract_building_embeddings(model, training_tf, all_buildings)
    print(f"Extracted embeddings for {len(labels)} buildings.")

    similarity_df = compute_similarity(labels, vectors)
    SIMILARITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    similarity_df.to_csv(SIMILARITY_OUTPUT, sep="\t", index=False)

    clusters_df = compute_clusters(labels, vectors)
    clusters_df.to_csv(CLUSTERS_OUTPUT, sep="\t", index=False)

    # --- Writeback ---
    print("\n=== KGE: Writeback to GraphDB ===")
    all_triples = []
    all_triples += build_style_triples(styles_df)
    all_triples += build_similarity_triples(similarity_df)
    all_triples += build_cluster_triples(clusters_df)
    write_to_graphdb(all_triples)
    print(f"{len(all_triples)} triples written. KGE-step completed.")

if __name__ == "__main__":
    run_kge_step()