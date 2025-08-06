# ===================================================================
# app/ocr.py (Refatorado com Estratégia Híbrida)
#
# O que mudou:
# - Utiliza a biblioteca `fitz` (PyMuPDF) em vez de `pdf2image`.
# - Adota uma estratégia híbrida:
#   1. Tenta extrair texto digital diretamente da página.
#   2. Se a página for uma imagem (pouco ou nenhum texto digital),
#      aí sim ela é convertida para imagem e o OCR é aplicado.
# - É significativamente mais rápido e mais preciso para PDFs mistos.
# ===================================================================

import fitz  # PyMuPDF, já está no seu requirements.txt
import pytesseract
from PIL import Image, ImageFilter, ImageOps
import io

def _preprocessar_imagem(imagem_pil):
    """
    Aplica filtros de pré-processamento a uma imagem para melhorar a qualidade do OCR.
    Esta é a sua lógica original de tratamento de imagem, agora em uma função auxiliar.
    """
    try:
        # Converte para escala de cinza, um passo comum para OCR
        img = imagem_pil.convert("L")
        
        # As linhas a seguir (inversão, binarização) podem ser ajustadas ou removidas
        # dependendo da qualidade e do tipo dos seus documentos escaneados.
        # Para alguns documentos, elas podem piorar o resultado.
        img = ImageOps.invert(img)
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # Redução de ruído
        img = img.filter(ImageFilter.MedianFilter())
        return img
    except Exception as e:
        print(f"⚠️  Aviso: Falha no pré-processamento da imagem. Usando imagem original. Erro: {e}")
        return imagem_pil # Retorna a imagem original em caso de erro

def aplicar_ocr(caminho_pdf):
    """
    Extrai texto de um arquivo PDF usando uma estratégia híbrida.

    Args:
        caminho_pdf (str): O caminho para o arquivo PDF a ser processado.

    Returns:
        str: O texto completo extraído do documento.
    """
    print("🚀 Iniciando extração de texto com estratégia híbrida...")
    texto_completo = []
    documento = fitz.open(caminho_pdf)

    # Itera por cada página do documento
    for num_pagina, pagina in enumerate(documento):
        # --- Passo 1: Tenta extrair o texto diretamente ---
        # Isso funciona para páginas que foram geradas digitalmente (ex: de um Word)
        texto_direto = pagina.get_text("text")

        # --- Passo 2: Decide se usa OCR ---
        # Se a página tem pouco ou nenhum texto (< 100 caracteres),
        # consideramos que é uma imagem que precisa de OCR.
        if len(texto_direto.strip()) < 100:
            print(f"   - Página {num_pagina + 1}/{len(documento)}: Texto não encontrado. Aplicando OCR...")
            
            # Renderiza a página como uma imagem de alta resolução (300 DPI)
            pix = pagina.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            imagem_pil = Image.open(io.BytesIO(img_bytes))

            # Aplica o pré-processamento na imagem
            imagem_processada = _preprocessar_imagem(imagem_pil)

            # Usa o Tesseract para extrair texto da imagem
            try:
                texto_da_pagina = pytesseract.image_to_string(imagem_processada, lang='por')
                texto_completo.append(texto_da_pagina)
            except pytesseract.TesseractError as e:
                print(f"❌ Erro de OCR na página {num_pagina + 1}: {e}")
                texto_completo.append(f"\n[ERRO DE OCR NA PÁGINA {num_pagina + 1}]\n")
        
        # Se a página já continha texto digital, usa-o diretamente
        else:
            print(f"   - Página {num_pagina + 1}/{len(documento)}: Texto digital extraído diretamente.")
            texto_completo.append(texto_direto)

    documento.close()
    print("✅ Extração de texto finalizada.")
    
    # Junta o texto de todas as páginas, separando-as com um marcador de quebra de página
    return "\n\f\n".join(texto_completo)
