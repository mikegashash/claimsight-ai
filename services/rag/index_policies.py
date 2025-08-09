import os, re, uuid, glob
import chromadb
from chromadb.config import Settings
from .embeddings import embed_texts

CHROMA_PATH = os.getenv("CHROMA_PATH", "/app/vectorstore")
DATA_DIR = os.getenv("POLICY_DIR", "/app/data/policies")

def chunk_text(text, max_chars=900, overlap=120):
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0: start = 0
        if start >= len(text): break
    return chunks

def load_policy_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt" or ext == ".md":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        import PyPDF2
        txt = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for p in reader.pages:
                txt.append(p.extract_text() or "")
        return "\n".join(txt)
    else:
        return ""

def build_index():
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(allow_reset=True))
    coll = client.get_or_create_collection(name="policies", metadata={"hnsw:space": "cosine"})

    # clear to rebuild (idempotent dev)
    try:
        coll.delete(ids=coll.get()["ids"])
    except Exception:
        pass

    files = glob.glob(os.path.join(DATA_DIR, "*"))
    docs, metadatas, ids = [], [], []
    for fp in files:
        policy_id = os.path.splitext(os.path.basename(fp))[0]
        text = load_policy_text(fp)
        if not text.strip(): continue
        sections = re.split(r"\n(?=Section\s+\d+:)", text, flags=re.IGNORECASE)
        if len(sections) < 2:
            chunks = chunk_text(text)
            for i, c in enumerate(chunks):
                ids.append(f"{policy_id}-{i}-{uuid.uuid4().hex[:8]}")
                docs.append(c)
                metadatas.append({"policy_id": policy_id, "section": "unknown"})
        else:
            for s in sections:
                if not s.strip(): continue
                sec_id = s.splitlines()[0].strip()
                chunks = chunk_text(s)
                for i, c in enumerate(chunks):
                    ids.append(f"{policy_id}-{i}-{uuid.uuid4().hex[:8]}")
                    docs.append(c)
                    metadatas.append({"policy_id": policy_id, "section": sec_id})

    embeddings = embed_texts(docs)
    coll.add(documents=docs, metadatas=metadatas, ids=ids, embeddings=embeddings)
    return {"indexed_docs": len(docs), "files": len(files)}

if __name__ == "__main__":
    out = build_index()
    print(out)
