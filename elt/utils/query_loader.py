from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
QUERIES_DIR = BASE_DIR / "queries"

def load_query(name: str) -> str:
    path = QUERIES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"SPARQL query not found: {path}")
    return path.read_text(encoding="utf-8")
