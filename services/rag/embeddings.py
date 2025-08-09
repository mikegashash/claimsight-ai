from sentence_transformers import SentenceTransformer
import threading

_model = None
_lock = threading.Lock()

def get_model():
    global _model
    with _lock:
        if _model is None:
            _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return _model

def embed_texts(texts):
    model = get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()
