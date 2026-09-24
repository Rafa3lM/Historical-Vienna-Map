from pathlib import Path

import pandas as pd
import torch
from pykeen.predict import predict_target
from SPARQLWrapper import SPARQLWrapper, JSON

from elt.kge.trainer import load_and_split, MODELS_OUTPUT_DIR, TRIPLES_PATH

from elt.kge.exporter import GRAPHDB_URL, GRAPHDB_REPO

MODEL_NAME = "RotatE"
STYLE_RELATION = "property:WikidataArchitecturalStyle"
TOP_K = 1
OUTPUT_PATH = Path("data/processed/predicted_styles.tsv")


def load_trained_model():
    model_path = MODELS_OUTPUT_DIR / MODEL_NAME / "trained_model.pkl"
    return torch.load(model_path, weights_only=False)


def get_valid_style_values() -> list[str]:
    df = pd.read_csv(TRIPLES_PATH, sep="\t", names=["head", "relation", "tail"])
    styles = df.loc[df["relation"] == STYLE_RELATION, "tail"].unique().tolist()
    print(f"{len(styles)} known building styles found")
    return styles


def find_buildings_missing_style(sparql: SPARQLWrapper) -> list[str]:
    """Queries GraphDB for buildings/places with geometry and missing WikidataArchitecturalStyle property."""
    query = """
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX property: <http://www.geschichtewiki.wien.gv.at/Special:URIResolver/Property-3A>
    SELECT DISTINCT ?building WHERE {
      ?building geo:hasGeometry ?g .
      FILTER NOT EXISTS { ?building property:WikidataArchitecturalStyle ?type }
    }
    """
    sparql.setQuery(query)
    results = sparql.query().convert()
    return [row["building"]["value"] for row in results["results"]["bindings"]]


def predict_styles(model, training_tf, buildings: list[str], valid_styles: list[str]) -> pd.DataFrame:
    """Creates a Top-k architectural style prediction and a confidence score for every building."""
    predictions = []
    skipped = 0
    for building in buildings:
        try:
            result = predict_target(
                model=model,
                head=building,
                relation=STYLE_RELATION,
                triples_factory=training_tf,
                targets=valid_styles,
            )
        except KeyError:
            skipped += 1
            continue

        top = result.df.head(TOP_K)
        for _, row in top.iterrows():
            predictions.append(
                {
                    "building": building,
                    "predicted_style": row["tail_label"],
                    "score": float(row["score"]),
                }
            )

    if skipped:
        print(f"Skipped {skipped} buildings (not included in training graph).")
    return pd.DataFrame(predictions)


if __name__ == "__main__":
    sparql = SPARQLWrapper(f"{GRAPHDB_URL}/repositories/{GRAPHDB_REPO}")
    sparql.setReturnFormat(JSON)

    training_tf, _, _ = load_and_split()
    model = load_trained_model()
    valid_styles = get_valid_style_values()
    buildings = find_buildings_missing_style(sparql)
    print(f"Found {len(buildings)} building without architectural style.")

    df = predict_styles(model, training_tf, buildings, valid_styles)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, sep="\t", index=False)
    print(f"{len(df)} predictions saved to {OUTPUT_PATH}")
