def test_imports_ok():
    import claimsight_ai.api.main as api
    import claimsight_ai.rag.index_policies as ip
    import claimsight_ai.rag.retriever as rt
    import claimsight_ai.rag.reranker as rr
    import claimsight_ai.ocr.pii as pii
    import claimsight_ai.integrations.models as im
    import claimsight_ai.integrations.guidewire_adapter as gw
    import claimsight_ai.integrations.duckcreek_adapter as dc
    import claimsight_ai.snowflake_io as sf
    assert callable(pii.mask_pii)
