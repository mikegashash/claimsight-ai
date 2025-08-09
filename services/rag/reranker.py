from sentence_transformers import CrossEncoder
import threading

_model = None
_lock = threading.Lock()

def _get():
    global _model
    with _lock:
        if _model is None:
            _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return _model

def rerank(query: str, passages: list, top_n: int = 5):
    if not passages:
        return []
    model = _get()
    pairs = [(query, p["text"]) for p in passages]
    scores = model.predict(pairs).tolist()
    for p, s in zip(passages, scores):
        p["rerank_score"] = float(s)
    passages.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    return passages[:top_n]
