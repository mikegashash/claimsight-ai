try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None

from .pii import mask_pii

def ocr_and_mask(file_bytes: bytes) -> str:
    if pytesseract is None:
        return mask_pii("")  # OCR not configured; return empty masked text
    import io
    img = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(img) or ""
    return mask_pii(text)
