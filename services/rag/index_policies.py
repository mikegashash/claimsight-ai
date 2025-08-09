import os, glob, json, re
from typing import List, Dict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

BASE = os.getenv("VECTOR_DIR", "/app/vectorstore")
DATA_DIR = os.getenv("POLICY_DIR", "/app/data/policies")
INDEX_PATH = os.path.join(BASE, "policy.faiss")
DOCS_PATH = os.path.join(BASE, "policy.docs.json")
META_PATH = os.path.join(BASE, "policy.meta.json")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def _chunk(text: str, max_chars=900, overlap=120) -> List[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i+max_chars])
        nxt = i + max_chars - overlap
        if nxt <= i: break
        i = min(nxt, len(text))
    return out

def _load_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        return open(path, "r", encoding="utf-8", errors="ignore").read()
    elif ext == ".pdf":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(open(path, "rb"))
            return "\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception:
            return ""
    return ""

def build_index() -> Dict[str, int]:
    os.makedirs(BASE, exist_ok=True)
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*")))
    docs, metas = [], []

    if not files:
        # create an empty index that won't crash the app
        dim = 384  # all-MiniLM-L6-v2
        faiss.write_index(faiss.IndexFlatIP(dim), INDEX_PATH)
        json.dump(docs, open(DOCS_PATH, "w"))
        json.dump(metas, open(META_PATH, "w"))
        return {"files": 0, "docs": 0}

    for fp in files:
        policy_id = os.path.splitext(os.path.basename(fp))[0]
        text = _load_text(fp)
        if not text.strip():
            continue
        sections = re.split(r"\n(?=Section\s+\d+:)", text, flags=re.IGNORECASE)
        for s in (sections if len(sections) > 1 else [text]):
            section_title = (s.splitlines()[0].strip() if s.strip() else "unknown")[:120]
            for ch in _chunk(s):
                docs.append(ch)
                metas.append({"policy_id": policy_id, "section": section_title})

    model = SentenceTransformer(MODEL_NAME)
    vecs = model.encode(docs, normalize_embeddings=True).astype("float32")

    index = faiss.IndexFlatIP(vecs.shape[1])
    if len(vecs):
        index.add(vecs)

    faiss.write_index(index, INDEX_PATH)
    json.dump(docs, open(DOCS_PATH, "w", encoding="utf-8"))
    json.dump(metas, open(META_PATH, "w", encoding="utf-8"))

    return {"files": len(files), "docs": len(docs)}
