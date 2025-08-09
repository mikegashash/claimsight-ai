try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
except Exception:
    _analyzer = None
    _anonymizer = None

def mask_pii(text: str) -> str:
    if not text or _analyzer is None or _anonymizer is None:
        return text
    try:
        results = _analyzer.analyze(text=text, language="en")
        return _anonymizer.anonymize(text=text, analyzer_results=results).text
    except Exception:
        return text
