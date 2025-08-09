from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# lazy singletons
_analyzer = None
_anonymizer = None

def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()  # uses default recognizers
    return _analyzer

def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

def mask_pii(text: str) -> str:
    if not text:
        return text
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()
    results = analyzer.analyze(text=text, language="en")
    # default anonymization: <ENTITY_TYPE>
    return anonymizer.anonymize(text=text, analyzer_results=results).text
