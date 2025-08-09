import os
import chromadb
from chromadb.config import Settings
from .embeddings import embed_texts

CHROMA_PATH = os.getenv("CHROMA_PATH", "/app/vectorstore")

class PolicyRetriever:
    def __init__(self, k=5):
        self.k = k
        self.client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings())
        self.coll = self.client.get_or_create_collection(name="policies", metadata={"hnsw:space":"cosine"})

    def search(self, query: str, where=None):
        qvec = embed_texts([query])[0]
        res = self.coll.query(query_embeddings=[qvec], n_results=self.k, where=where)
        hits = []
        for i in range(len(res["ids"][0])):
            hits.append({
                "id": res["ids"][0][i],
                "distance": res["distances"][0][i],
                "text": res["documents"][0][i],
                "meta": res["metadatas"][0][i],
            })
        return hits
