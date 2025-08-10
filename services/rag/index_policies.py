# services/rag/index_policies.py
import os, glob, json, re
from pathlib import Path
from typing import List, Dict

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ---- Portable paths (work on GH Actions + Docker) ----
APP_HOME   = Path(os.environ.get("APP_HOME", Path.cwd()))
VECTOR_DIR = Path(os.environ.get("VECTOR_DIR", APP_HOME / ".cache" / "vectorstore"))
POLICY_DIR = Path(os.environ.get("POLICY_DIR", APP_HOME / "data" / "policies"))

INDEX_PATH = VECTOR_DIR / "policy.faiss"
DOCS_PATH  = VECTOR_DIR / "policy.docs.json"
META_PATH  = VECTOR_DIR / "policy.meta.json"

MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIM  = 384  # all-MiniLM-L6-v2 output size


def _chunk(text: str, max_chars=900, overlap=120) -> List[str]:
    out, i = [], 0
    n = len(text)
    while i < n:
        out.append(text[i:i+max_chars])
        nxt = i + max_chars - overlap
        if nxt <= i:
            break
        i = min(nxt, n)
    return out


def _load_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            import PyPDF2
            with path.open("rb") as fh:
                reader = PyPDF2.PdfReader(fh)
                return "\n".join([(p.extract_text() or "") for p in reader.pages])
        except Exception:
            return ""
    return ""


def build_index() -> Dict[str, int]:
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted([Path(p) for p in glob.glob(str(POLICY_DIR / "*"))])
    docs, metas = [], []

    if not files:
        # Write an empty but valid index + metadata so the app won't crash
        index = faiss.IndexFlatIP(EMBED_DIM)
        faiss.write_index(index, str(INDEX_PATH))
        DOCS_PATH.write_text(json.dumps(docs), encoding="utf-8")
        META_PATH.write_text(json.dumps(metas), encoding="utf-8")
        return {"files": 0, "docs": 0}

    for fp in files:
        policy_id = fp.stem
        text = _load_text(fp)
        if not text.strip():
            continue

        sections = re.split(r"\n(?=Section\s+\d+:)", text, flags=re.IGNORECASE)
        blocks = sections if len(sections) > 1 else [text]

        for s in blocks:
            section_title = (s.splitlines()[0].strip() if s.strip() else "unknown")[:120]
            for ch in _chunk(s):
                docs.append(ch)
                metas.append({"policy_id": policy_id, "section": section_title})

    model = SentenceTransformer(MODEL_NAME)
    vecs = model.encode(docs, normalize_embeddings=True).astype("float32")

    index = faiss.IndexFlatIP(vecs.shape[1] if len(vecs) else EMBED_DIM)
    if len(vecs):
        index.add(vecs)

    faiss.write_index(index, str(INDEX_PATH))
    DOCS_PATH.write_text(json.dumps(docs), encoding="utf-8")
    META_PATH.write_text(json.dumps(metas), encoding="utf-8")

    return {"files": len(files), "docs": len(docs)}
