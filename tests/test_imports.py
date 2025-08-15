import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports_ok():
    import claimsight_ai.api.main as api
    import claimsight_ai.rag.index_policies as ip
    import claimsight_ai.rag.retriever as rt
    import claimsight_ai.rag.reranker as rr
    import claimsight_ai.ocr.pii as pii
    import claimsight_ai.integrations.models as im
    import claimsight_ai.integrations.guidewire_adapter as gw
    import claimsight_ai.integrations.duckcreek_adapter as dc
