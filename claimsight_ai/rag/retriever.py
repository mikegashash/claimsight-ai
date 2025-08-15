import os, json
from typing import List, Dict, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

BASE = os.getenv("VECTOR_DIR", "/app/vectorstore")
INDEX_PATH = os.path.join(BASE, "policy.faiss")
DOCS_PATH = os.path.join(BASE, "policy.docs.json")
META_PATH = os.path.join(BASE, "policy.meta.json")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

class PolicyRetriever:
    def __init__(self, k: int = 5):
        self.k = k
        self.model = SentenceTransformer(MODEL_NAME)
        self.docs = json.load(open(DOCS_PATH, "r", encoding="utf-8")) if os.path.exists(DOCS_PATH) else []
        self.meta = json.load(open(META_PATH, "r", encoding="utf-8")) if os.path.exists(META_PATH) else []
        dim = 384
        if os.path.exists(INDEX_PATH):
            self.index = faiss.read_index(INDEX_PATH)
        else:
            self.index = faiss.IndexFlatIP(dim)

    def search(self, query: str, where: Optional[Dict] = None) -> List[Dict]:
        if not self.docs:
            return []
        qv = self.model.encode([query], normalize_embeddings=True).astype("float32")
        k = min(self.k * 5, len(self.docs))
        sims, idxs = self.index.search(qv, k)
        hits = []
        for sim, idx in zip(sims[0], idxs[0]):
            if idx < 0:
                continue
            m = self.meta[idx] if idx < len(self.meta) else {}
            if where:
                ok = all(str(m.get(k)) == str(v) for k, v in where.items())
                if not ok: 
                    continue
            hits.append({"id": int(idx), "distance": float(sim), "text": self.docs[idx], "meta": m})
            if len(hits) >= self.k:
                break
        return hits
