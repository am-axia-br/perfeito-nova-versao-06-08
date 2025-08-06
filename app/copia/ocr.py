# =============================
# app/ocr.py
# =============================
from pdf2image import convert_from_path
import pytesseract

def aplicar_ocr(pdf_file):
    imagens = convert_from_path(pdf_file, dpi=300)
    texto = ""
    for img in imagens:
        texto += pytesseract.image_to_string(img, lang='por') + "\n"
    return texto