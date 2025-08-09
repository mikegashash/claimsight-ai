from sentence_transformers import CrossEncoder
import threading

_model = None
_lock = threading.Lock()

def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    global _model
    with _lock:
        if _model is None:
            _model = CrossEncoder(model_name)
        return _model

def rerank(query: str, passages: list, top_n: int = 5):
    """
    passages: list[dict] with 'text' key (plus meta)
    returns same list sorted by score desc (with 'rerank_score')
    """
    if not passages:
        return []
    model = get_reranker()
    pairs = [(query, p["text"]) for p in passages]
    scores = model.predict(pairs).tolist()
    for p, s in zip(passages, scores):
        p["rerank_score"] = float(s)
    passages.sort(key=lambda x: x["rerank_score"], reverse=True)
    return passages[:top_n]
