from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()

def mask_pii(text: str) -> str:
    if not text:
        return text
    results = _analyzer.analyze(text=text, language="en")
    return _anonymizer.anonymize(text=text, analyzer_results=results).text
