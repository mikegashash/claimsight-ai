def test_imports_ok():
    import services.api.main as api
    import services.rag.index_policies as ip
    import services.rag.retriever as rt
    import services.rag.reranker as rr
    import services.ocr.pii as pii
    import services.integrations.models as im
    import services.integrations.guidewire_adapter as gw
    import services.integrations.duckcreek_adapter as dc
    import services.snowflake_io as sf
    assert callable(pii.mask_pii)
