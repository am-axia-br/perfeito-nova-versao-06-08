# =============================
# app/interface.py (FINAL AJUSTADO)
# =============================

import time
import streamlit as st
from ocr import aplicar_ocr
from extrator import dividir_em_chunks, gerar_resumo_juridico
from xml_generator import gerar_xml_pjecalc
import json
import os

# Configurações iniciais
st.set_page_config(page_title="PJe-Calc Automático", layout="wide")
st.title("📄 PJe-Calc Automático com IA Jurídica")

# Upload do PDF
pdf_file = st.file_uploader(
    label="📤 Faça o upload do processo trabalhista (formato PDF)",
    type="pdf",
    help="Arraste o PDF do processo ou clique para selecionar. Tamanho máximo: 1GB."
)

if pdf_file:
    with open("temp.pdf", "wb") as f:
        f.write(pdf_file.read())

    st.info("🔍 Executando OCR no arquivo... Aguarde alguns segundos.")
    progress_bar = st.progress(0)

    try:
        for pct in range(0, 90, 10):
            progress_bar.progress(pct)
            time.sleep(0.2)

        texto = aplicar_ocr("temp.pdf")

        progress_bar.progress(100)
        st.success("✅ OCR finalizado com sucesso.")
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ Erro ao aplicar OCR: {str(e)}")
        st.stop()

    # IA Jurídica
    st.info("🧠 Analisando o conteúdo com IA Jurídica...")
    try:
        chunks = dividir_em_chunks(texto)
        resumo = gerar_resumo_juridico(chunks)
    except Exception as e:
        st.error(f"❌ Erro durante análise com IA: {str(e)}")
        st.stop()

    if not resumo or not isinstance(resumo[-1], str):
        st.error("❌ A análise com IA não retornou dados válidos.")
        st.stop()

    # Backup do JSON para debug
    try:
        with open("resumo_backup.json", "w", encoding="utf-8") as f:
            json.dump(resumo, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"⚠️ Não foi possível salvar o backup do resumo: {str(e)}")

    # Interpretar JSON final
    try:
        dados_completos = json.loads(resumo[-1])

        tabs = st.tabs([
            "📌 Dados Processuais",
            "👤 Partes Envolvidas",
            "💼 Contrato de Trabalho",
            "📑 Pleitos Reclamados",
            "⚖️ Decisão Judicial",
            "📝 Observações Gerais"
        ])

        with tabs[0]:
            st.markdown("### 📌 Dados Processuais")
            for k, v in dados_completos.get("dados_processuais", {}).items():
                st.text(f"{k}: {v}")

        with tabs[1]:
            st.markdown("### 👤 Partes Envolvidas")
            for k, v in dados_completos.get("partes", {}).items():
                if isinstance(v, list):
                    st.markdown(f"**{k}:**")
                    for item in v:
                        st.text(f" - {item}")
                else:
                    st.text(f"{k}: {v}")

        with tabs[2]:
            st.markdown("### 💼 Informações Contratuais")
            for k, v in dados_completos.get("contrato_trabalho", {}).items():
                st.text(f"{k}: {v}")

        with tabs[3]:
            st.markdown("### 📑 Pleitos do Reclamante")
            for i in dados_completos.get("pleitos", []):
                st.text(f" - {i}")

        with tabs[4]:
            st.markdown("### ⚖️ Decisão Judicial")
            for k, v in dados_completos.get("decisao", {}).items():
                if isinstance(v, list):
                    st.markdown(f"**{k}:**")
                    for item in v:
                        st.text(f" - {item}")
                else:
                    st.text(f"{k}: {v}")

        with tabs[5]:
            st.markdown("### 📝 Observações Gerais")
            st.text(dados_completos.get("observacoes", ""))

        # Downloads
        st.markdown("---")
        st.download_button("📥 Baixar JSON Resumo", json.dumps(dados_completos, indent=2), "resumo.json")

        gerar_xml_pjecalc(dados_completos)

        if os.path.exists("export/saida_pjecalc.xml"):
            with open("export/saida_pjecalc.xml", "rb") as xml_file:
                st.download_button("📥 Baixar XML PJe-Calc", xml_file, file_name="saida_pjecalc.xml")
        else:
            st.warning("⚠️ O XML não foi gerado corretamente.")
    except Exception as e:
        st.error(f"❌ Erro ao processar ou exibir os dados: {str(e)}")
