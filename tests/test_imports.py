def test_import_packages():
    import services.api.main as api
    import services.rag.embeddings as emb
    import services.rag.retriever as rtr
    import services.rag.reranker as rr
    import services.ocr.pii as pii
    assert callable(pii.mask_pii)
