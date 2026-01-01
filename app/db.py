import json
from pathlib import Path
from typing import Dict, List

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "foods_and_sports.json"

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        DB = json.load(f)
except Exception:
    DB = {"foods": [], "exercises": []}


def get_relevant_foods_and_exercises(query: str, top_k: int = 10) -> Dict:
    """
    Simple retrieval: filtre les données par mots-clés présents dans la query.
    Pour un vrai RAG, remplace par un index vectoriel (FAISS, Milvus) ou MongoDB.
    """
    q = query.lower()

    foods = [
        f
        for f in DB.get("foods", [])
        if any(tok in q for tok in f.get("name", "").lower().split())
    ][:top_k]

    exercises = [
        e
        for e in DB.get("exercises", [])
        if any(tok in q for tok in e.get("name", "").lower().split())
    ][:top_k]

    if not foods:
        foods = DB.get("foods", [])[:5]
    if not exercises:
        exercises = DB.get("exercises", [])[:5]

    return {"foods": foods, "exercises": exercises}
