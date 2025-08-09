import os, glob
import chromadb
from chromadb.config import Settings
from .embeddings import embed_texts

CHROMA_PATH = os.getenv("CHROMA_PATH", "/app/vectorstore")

class PolicyRetriever:
    def __init__(self, k=5):
        self.k = k
        self.client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings())
        self.coll = self.client.get_or_create_collection(name="policies", metadata={"hnsw:space":"cosine"})
        # minimal bootstrap if empty: add any .txt in data/policies
        if not self.coll.count():
            docs, metas, ids = [], [], []
            for i, fp in enumerate(sorted(glob.glob("/app/data/policies/*.txt"))):
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                if not txt.strip(): continue
                ids.append(f"boot-{i}")
                docs.append(txt[:900])
                metas.append({"policy_id": os.path.basename(fp).replace(".txt",""), "section":"bootstrap"})
            if docs:
                embs = embed_texts(docs)
                self.coll.add(documents=docs, metadatas=metas, ids=ids, embeddings=embs)

    def search(self, query: str, where=None):
        qvec = embed_texts([query])[0]
        res = self.coll.query(query_embeddings=[qvec], n_results=self.k, where=where)
        out = []
        for i in range(len(res["ids"][0])):
            out.append({
                "id": res["ids"][0][i],
                "distance": res["distances"][0][i],
                "text": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
            })
        return out
