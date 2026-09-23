from pathlib import Path

import torch
from pykeen.triples import TriplesFactory
from pykeen.pipeline import pipeline

TRIPLES_PATH = Path("data/processed/kge_triples.tsv")
MODELS_OUTPUT_DIR = Path("data/processed/kge_models")

NUM_EPOCHS = 500
RANDOM_SEED = 42
MODELS_TO_COMPARE = ["TransE"] #"ComplEx"


def load_and_split():
    """Load and split the exported triples 80/10/10 in train/test/validation."""
    tf = TriplesFactory.from_path(str(TRIPLES_PATH))
    training, testing, validation = tf.split(
        [0.8, 0.1, 0.1], random_state=RANDOM_SEED
    )
    print(
        f"Entities: {tf.num_entities}, Relations: {tf.num_relations}, "
        f"Triples total: {tf.num_triples} "
        f"(Train: {training.num_triples}, Test: {testing.num_triples}, "
        f"Val: {validation.num_triples})"
    )
    return training, testing, validation


def train_model(model_name: str, training, testing, validation):
    """Trains a single KGE-model and evaluates it"""
    device = "cuda" if torch.cuda.is_available() else "cpu"

    result = pipeline(
        training=training,
        testing=testing,
        validation=validation,
        model=model_name,
        training_kwargs=dict(num_epochs=NUM_EPOCHS),
        random_seed=RANDOM_SEED,
        device=device,
    )

    out_dir = MODELS_OUTPUT_DIR / model_name.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    result.save_to_directory(str(out_dir))

    return result


def compare_metrics(results: dict) -> None:
    """Prints a compact comparison table for the most important metrics."""
    print(f"\n{'Model':10s} {'MRR':>8s} {'Hits@1':>8s} {'Hits@3':>8s} {'Hits@10':>8s}")
    for model_name, result in results.items():
        mr = result.metric_results
        mrr = mr.get_metric("both.realistic.inverse_harmonic_mean_rank")
        h1 = mr.get_metric("both.realistic.hits_at_1")
        h3 = mr.get_metric("both.realistic.hits_at_3")
        h10 = mr.get_metric("both.realistic.hits_at_10")
        print(f"{model_name:10s} {mrr:8.3f} {h1:8.3f} {h3:8.3f} {h10:8.3f}")


if __name__ == "__main__":
    training, testing, validation = load_and_split()

    results = {}
    for model_name in MODELS_TO_COMPARE:
        print(f"\n=== Training {model_name} ===")
        results[model_name] = train_model(model_name, training, testing, validation)

    compare_metrics(results)