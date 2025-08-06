# ===================================================================
# app/interface.py (VERSÃO COM VERIFICAÇÃO DE ESTADO CORRIGIDA)
#
# O que mudou:
# - Removida a função `verificar_conexao_rag` e o seu decorador
#   `@st.cache_resource`, que era a causa do erro.
# - A lógica da barra lateral foi atualizada para usar a função
#   `get_rag_status` do `rag_manager.py`, que verifica a conexão
#   em tempo real e fornece um feedback mais detalhado.
# ===================================================================

import streamlit as st
import os
import json
import traceback
import pandas as pd
import time
from ocr import aplicar_ocr
from extrator import dividir_em_chunks, extrair_dados_parciais, consolidar_resultados
from xml_generator import gerar_xml_pjecalc
from exportador_docx import gerar_docx_resumo
from exportadores_completo import gerar_excel_processo


# A importação foi ajustada para usar a função de status correta

from rag_manager import adicionar_documento_ao_rag, consultar_rag, get_rag_status, zerar_base_rag, get_chroma_content

import datetime  # Adicione também esta importação para o botão de exportação

from auth_manager import configure_gemini_auth
configure_gemini_auth()

# --- CONFIGURAÇÃO DA PÁGINA E ESTADO INICIAL ---

st.set_page_config(page_title="PJe-Calc Automático com IA", layout="wide")
st.cache_data.clear()




def inicializar_estado():
    """Define o estado inicial da aplicação se não existir."""
    if "estado_app" not in st.session_state:
        st.session_state.estado_app = "inicial"
    if "dados_completos" not in st.session_state:
        st.session_state.dados_completos = None
    if "log_detalhado" not in st.session_state:
        st.session_state.log_detalhado = None
    if "error_message" not in st.session_state:
        st.session_state.error_message = None
    if "error_details" not in st.session_state:
        st.session_state.error_details = None
    if "pagina_atual" not in st.session_state:
        st.session_state.pagina_atual = "Analisar Processo"

def reiniciar_analise():
    """Reseta a aplicação para a tela de análise inicial."""
    keys_to_clear = ["estado_app", "dados_completos", "log_detalhado", "error_message", "error_details"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    temp_pdf_path = os.path.join("export", "temp.pdf")
    if os.path.exists(temp_pdf_path):
        os.remove(temp_pdf_path)
    
    inicializar_estado()
    st.session_state.pagina_atual = "Analisar Processo"

# --- FUNÇÃO DE VERIFICAÇÃO REMOVIDA ---
# A função `verificar_conexao_rag` foi removida pois causava o erro de cache.

def executar_analise_completa(caminho_pdf, rag_is_active):
    """Orquestra todo o processo: OCR, RAG, Extração e Consolidação."""
    try:
        # Etapa 1: OCR (sem alterações)
        with st.spinner("🔍 Etapa 1/4: A ler e a preparar o documento..."):
            texto_processo = aplicar_ocr(caminho_pdf)
            # ADICIONADO: Armazenar o texto para uso na análise de verbas
            st.session_state.texto_processo = texto_processo
            chunks = dividir_em_chunks(texto_processo)
        st.success(f"✅ Documento preparado e dividido em {len(chunks)} partes.")

        # Etapa 2: Consulta ao RAG (se disponível) - MODIFICAÇÃO: TRATAMENTO DE ERRO
        contexto_rag = ""
        if rag_is_active:
            try:
                with st.spinner("🧠 Etapa 2/4: A consultar a base de conhecimento (RAG)..."):
                    # Limitando o tamanho do texto para consulta ao RAG
                    texto_consulta = texto_processo[:5000] if len(texto_processo) > 5000 else texto_processo
                    contexto_rag = consultar_rag(texto_consulta, n_results=3)  # Limitado a 3 resultados
                    # Limitando tamanho do contexto RAG para evitar sobrecarga
                    if contexto_rag and len(contexto_rag) > 8000:
                        contexto_rag = contexto_rag[:8000] + "... (truncado para melhor desempenho)"
                st.success("✅ Consulta à base de conhecimento finalizada.")
            except Exception as e:
                st.warning(f"⚠️ Erro ao consultar a base de conhecimento: {str(e)}. A análise prosseguirá sem contexto adicional.")
                contexto_rag = ""
        else:
            st.warning("⚠️ Base de conhecimento (RAG) indisponível. A análise prosseguirá sem contexto adicional.", icon="🔌")

        # Etapa 3: Extração de Dados Parciais - MODIFICAÇÃO: RESILIÊNCIA MELHORADA
        progresso_extracaao = st.progress(0, text="A analisar parte 1...")
        with st.spinner(f"🤖 Etapa 3/4: A extrair dados de cada uma das {len(chunks)} partes..."):
            log_detalhado_chunks = extrair_dados_parciais(chunks, progresso_extracaao)
            st.session_state.log_detalhado = log_detalhado_chunks
            
            resultados_parciais_sucesso = [
                item.get("resultado_recebido")
                for item in log_detalhado_chunks
                if isinstance(item, dict) and item.get("status") == "Sucesso"
            ]
            
            # MODIFICAÇÃO: Feedback detalhado sobre falhas
            sucessos = len(resultados_parciais_sucesso)
            total = len(log_detalhado_chunks)
            falhas = total - sucessos
            
            if not resultados_parciais_sucesso:
                # Mostrar detalhes dos erros para diagnóstico
                st.error(f"❌ Falha na extração de dados. Todas as {total} partes falharam.")
                
                with st.expander("Detalhes dos erros (para diagnóstico técnico)"):
                    for i, item in enumerate(log_detalhado_chunks):
                        if item.get("status") != "Sucesso":
                            st.markdown(f"**Falha na parte {i+1}:**")
                            st.code(str(item.get("erro", "Erro desconhecido")))
                            if "resposta_bruta" in item:
                                st.text(str(item.get("resposta_bruta", ""))[:500] + "..." if len(str(item.get("resposta_bruta", ""))) > 500 else item.get("resposta_bruta", ""))
                
                # OPÇÃO DE CONTINUAR OU TENTAR NOVAMENTE
                if st.button("🔄 Tentar novamente sem RAG", key="retry_without_rag"):
                    st.warning("Reiniciando análise sem usar base de conhecimento...")
                    # Simula um processamento sem RAG na próxima iteração
                    st.session_state['tentativa_sem_rag'] = True
                    st.rerun()
                    
                if st.button("⚠️ Forçar continuação com dados incompletos", key="force_continue"):
                    # Tenta continuar mesmo sem sucessos - usando dados simulados mínimos
                    st.warning("Tentando prosseguir com processamento resiliente (não recomendado)...")
                    resultados_parciais_sucesso = [
                        {"documento": "processo trabalhista", "observacoes": "Dados limitados devido a falhas de extração."}
                    ]
                else:
                    st.warning("Tentando continuar mesmo com falhas totais. Dados simulados mínimos serão gerados.")
                    resultados_parciais_sucesso = [
                        {"documento": "processo trabalhista", "observacoes": "Falha geral na extração. Dados simulados adicionados."}
                    ]
            elif falhas > 0:
                # Mostra estatísticas de sucesso/falha
                print(f"⚠️ LOG: {falhas} de {total} partes tiveram erro de processamento. Continuando com {sucessos} partes válidas.")
            else:
                print(f"✅ Extração de dados parciais concluída com sucesso para todas as {total} partes.")

        # Etapa 4: Consolidação com Inteligência Aumentada
        with st.spinner("✨ Etapa 4/4: A consolidar dados com IA e a gerar resumo..."):
            try:
                dados_completos = consolidar_resultados(resultados_parciais_sucesso, contexto_rag)
                if not dados_completos or not isinstance(dados_completos, dict):
                    st.warning("⚠️ A consolidação produziu um resultado inesperado. Tentando formato alternativo...")
                    # Tenta criar dados mínimos para evitar quebrar a aplicação
                    dados_completos = {
                        "observacoes_gerais": "Consolidação parcial. Os dados podem estar incompletos devido a limitações no processamento.",
                        "dados_pessoais": {"reclamante": "Não identificado", "reclamada": "Não identificado"},
                        "informacoes_pjecalc": {"numero_processo": "Não identificado"},
                        "verbas_pleiteadas": [],
                        "bases_tecnicas_calculo": {},
                        "resultado_liquidacao": {}
                    }
            except Exception as e:
                st.error(f"Erro na consolidação final: {str(e)}")
                # Tenta criar dados mínimos para evitar quebrar a aplicação
                dados_completos = {
                    "observacoes_gerais": f"Não foi possível processar o documento completamente. Erro: {str(e)}",
                    "dados_pessoais": {},
                    "informacoes_pjecalc": {},
                    "verbas_pleiteadas": [],
                    "bases_tecnicas_calculo": {},
                    "resultado_liquidacao": {}
                }
                
            st.session_state.dados_completos = dados_completos
        st.success("🎉 Análise finalizada!")
        st.session_state.estado_app = "finalizado"

    except Exception as e:
        st.session_state.estado_app = "erro"
        st.session_state.error_message = f"Ocorreu um erro durante o processamento: {str(e)}"
        st.session_state.error_details = traceback.format_exc()
        
        # Opção para tentar novamente sem o RAG
        if "A extração de dados parciais falhou" in str(e) and not st.session_state.get('tentativa_sem_rag', False):
            st.info("💡 Dica: O erro pode estar relacionado à integração com o RAG (base de conhecimento).")
            if st.button("🔄 Tentar novamente sem usar o RAG"):
                st.session_state['tentativa_sem_rag'] = True
                st.rerun()

def exibir_resultados_formatados():
    """Mostra os resultados finais de forma estruturada para o PJe-Calc."""
    st.header("✅ Análise Concluída", divider="rainbow")
    
    dados = st.session_state.dados_completos
    
    # --- Resumo Geral ---
    st.subheader("📝 Observações Gerais e Resumo do Processo")
    resumo = dados.get("observacoes_gerais", "Nenhum resumo foi gerado.")

    # Remover "**Resumo Técnico do Processo:**" do texto
    resumo = resumo.replace("**Resumo Técnico do Processo:**", "").replace("**Resumo Técnico do Processo**", "")

    # Atualizar os dados com o resumo corrigido
    dados["observacoes_gerais"] = resumo
    st.session_state.dados_completos = dados

    st.markdown(f"<div style='text-align: justify;'>{resumo}</div>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        # --- Dados Pessoais ---
        st.subheader("📌 Dados Pessoais e Contratuais")
        pessoais = dados.get("dados_pessoais", {})
        if pessoais:
            st.markdown(f"**Reclamante:** {pessoais.get('reclamante', 'N/A')}")
            st.markdown(f"**Reclamada:** {pessoais.get('reclamada', 'N/A')}")
            st.markdown(f"**Data de Admissão:** {pessoais.get('data_admissao', 'N/A')}")
            st.markdown(f"**Data de Demissão:** {pessoais.get('data_demissao', 'N/A')}")
            st.markdown(f"**Último Salário:** {pessoais.get('ultimo_salario', 'N/A')}")
        else:
            st.info("Nenhum dado pessoal encontrado.")

    with col2:
        # --- Informações para PJe-Calc ---
        st.subheader("🗂️ Informações para Preenchimento no PJe-Calc")
        info_pjecalc = dados.get("informacoes_pjecalc", {})
        if info_pjecalc:
            st.markdown(f"**Nº do Processo:** {info_pjecalc.get('numero_processo', 'N/A')}")
            st.markdown(f"**TRT Região:** {info_pjecalc.get('trt_regiao', 'N/A')}")
            st.markdown(f"**Jurisdição:** {info_pjecalc.get('jurisdicao', 'N/A')}")
            st.markdown(f"**Data da Liquidação:** {info_pjecalc.get('data_liquidacao', 'N/A')}")
            st.markdown(f"**Índices de Correção:** {info_pjecalc.get('indices_correcao', 'N/A')}")
            st.markdown(f"**Honorários Periciais:** {info_pjecalc.get('honorarios_periciais', 'N/A')}")
        else:
            st.info("Nenhuma informação para o PJe-Calc encontrada.")

    st.markdown("---")

    # --- Verbas Pleiteadas ---
    st.subheader("📑 Verbas Pleiteadas e Parâmetros")
    verbas = dados.get("verbas_pleiteadas", [])
    if verbas:
        df_verbas = pd.DataFrame(verbas)
        df_verbas.rename(columns={
            'verba': 'Verba', 
            'periodo': 'Período', 
            'valor_base': 'Valor Base', 
            'percentual_quantidade': 'Percentual / Quantidade', 
            'reflexos': 'Reflexos'
        }, inplace=True)
        st.dataframe(df_verbas, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma verba pleiteada foi encontrada.")

    # --- Análise Comparativa de Verbas ---
    st.subheader("🔍 Análise Inteligente de Verbas")

    if "texto_processo" in st.session_state:
        try:
            from analise_verbas import analisar_processo_trabalhista, gerar_quadro_calculo_completo
            
            # Preparar dados no formato esperado pela função de análise
            dados_planilha = {
                "Verbas Resumidas": dados.get("verbas_pleiteadas", []),
                "Verbas Detalhadas": dados.get("verbas_pleiteadas", [])
            }
            
            # Realizar análise automática
            resultado_analise = analisar_processo_trabalhista(
                st.session_state.texto_processo, 
                dados_planilha
            )
            
            # Gerar quadro de cálculo inteligente
            quadro_calculo_completo = gerar_quadro_calculo_completo(
                st.session_state.texto_processo,
                dados
            )
            
            # Exibir resultado da análise
            st.markdown(resultado_analise, unsafe_allow_html=True)
            
            # Exibir quadro de cálculo completo
            if quadro_calculo_completo:
                st.subheader("📊 Quadro para Cálculo Completo (Inteligente)")
                df_completo = pd.DataFrame(quadro_calculo_completo)
                st.dataframe(df_completo, use_container_width=True, hide_index=True)
            
            # Oferecer opção para substituir os dados atuais
            if st.button("💾 Usar este quadro inteligente"):
                dados["verbas_pleiteadas"] = quadro_calculo_completo
                st.session_state.dados_completos = dados
                st.success("✅ Quadro de cálculo atualizado com análise inteligente!")
                st.rerun()
                
        except Exception as e:
            st.warning(f"Não foi possível realizar a análise comparativa: {e}")
    else:
        st.info("📝 O texto completo do processo não está disponível para análise comparativa.")
        if st.button("📎 Adicionar texto para análise"):
            st.session_state.texto_processo = ""  # Inicializar
            st.text_area("Cole o texto da petição inicial:", key="texto_processo", height=200)

    st.markdown("---")
    
    col3, col4 = st.columns(2)

    with col3:
        # --- Bases Técnicas ---
        st.subheader("⚖️ Bases Técnicas para o Cálculo")
        bases = dados.get("bases_tecnicas_calculo", {})
        if bases:
            st.markdown(f"**Prescrição:** {bases.get('prescricao', 'N/A')}")
            st.markdown(f"**FGTS:** {bases.get('fgts', 'N/A')}")
            formulas = bases.get("formulas", [])
            if formulas:
                st.markdown("**Fórmulas:**")
                for f in formulas:
                    st.markdown(f"- **{f.get('verba')}:** `{f.get('formula')}`")
        else:
            st.info("Nenhuma base técnica de cálculo encontrada.")

    with col4:
        # --- Resultado da Liquidação ---
        st.subheader("🟢 Resultado Final da Liquidação")
        liquidacao = dados.get("resultado_liquidacao", {})
        if liquidacao:
            st.success(f"**Valor Bruto Total:** {liquidacao.get('valor_bruto_total', 'N/A')}")
            st.warning(f"**Descontos (IR e INSS):** {liquidacao.get('descontos_ir_inss', 'N/A')}")
            st.info(f"**Líquido Devido à Reclamante:** {liquidacao.get('liquido_devido_reclamante', 'N/A')}")
        else:
            st.info("Nenhum resultado de liquidação encontrado.")


    st.header("⬇️ Exportar Resultados", divider="rainbow")
    try:
        # Importar as novas funções de exportação
        from json_generator import gerar_json_bytes
        from xml_generator import gerar_xml_pjecalc
        
        # Gerar arquivos de exportação
        json_data = gerar_json_bytes(dados)
        caminho_xml = os.path.join("export", "saida_pjecalc.xml")
        gerar_xml_pjecalc(dados, caminho_xml)
        caminho_docx = os.path.join("export", "resumo_processo.docx")
        gerar_docx_resumo(dados, caminho_docx)

        # Modificado para 4 colunas
        col1_exp, col2_exp, col3_exp, col4_exp = st.columns(4)
        with col1_exp:
            st.download_button("📥 Baixar JSON", json_data, "resumo.json", "application/json", use_container_width=True)
        with col2_exp:
            with open(caminho_xml, "rb") as f:
                st.download_button("📥 Baixar XML PJe-Calc", f, "saida_pjecalc.xml", "application/xml", use_container_width=True)
        with col3_exp:
            with open(caminho_docx, "rb") as f:
                st.download_button("📄 Baixar Resumo Word", f, "resumo.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        with col4_exp:
            # Novo botão para Excel com análise de verbas
            with st.spinner("Gerando planilha Excel..."):
                texto_atual = st.session_state.get("texto_processo", "")
                excel_data = gerar_excel_processo(dados, texto_atual)
            st.download_button("📊 Baixar Excel", excel_data, "processo_resumo.xlsx", 
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                              use_container_width=True)
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar os ficheiros para download: {e}")

# --- PÁGINAS DA APLICAÇÃO ---

def pagina_analise(rag_is_active):
    """Página principal para análise de processos."""
    st.title("📄 PJe-Calc Automático com IA Jurídica")
    st.markdown("Faça o upload de um processo trabalhista em formato PDF para extrair e organizar os dados automaticamente.")

    if st.session_state.estado_app != "inicial":
        if st.button("↻ Analisar Outro Documento", use_container_width=True):
            reiniciar_analise()
            st.rerun()
    
    if st.session_state.estado_app == "finalizado":
        exibir_resultados_formatados()
    elif st.session_state.estado_app == "erro":
        st.error(st.session_state.error_message, icon="🚨")
        if st.session_state.error_details:
            with st.expander("Ver detalhes técnicos do erro"):
                st.code(st.session_state.error_details, language="python")
    elif st.session_state.estado_app == "processando":
        caminho_temp_pdf = os.path.join("export", "temp.pdf")
        if os.path.exists(caminho_temp_pdf):
             executar_analise_completa(caminho_temp_pdf, rag_is_active)
             st.rerun()
        else:
            st.error("Ficheiro PDF não encontrado. Por favor, faça o upload novamente.")
            reiniciar_analise()
            st.rerun()
    elif st.session_state.estado_app == "inicial":
        pdf_file = st.file_uploader(label="**Faça o upload do processo (PDF)**", type="pdf")
        if pdf_file:
            os.makedirs("export", exist_ok=True)
            caminho_temp_pdf = os.path.join("export", "temp.pdf")
            with open(caminho_temp_pdf, "wb") as f:
                f.write(pdf_file.getbuffer())
            st.session_state.estado_app = "processando"
            st.rerun()

def pagina_treinamento(rag_is_active: bool):
    """Página para alimentar e consultar a base de conhecimento do RAG."""
    st.title("🧠 Treinar IA com Documentos")
    
    # Dividir a interface em abas para melhor organização
    tab1, tab2, tab3 = st.tabs(["📤 Upload de Documentos", "🔎 Consultar Base", "📊 Documentos Treinados"])
    
    # === ABA 1: UPLOAD E PROCESSAMENTO ===
    with tab1:
        st.header("Adicionar Documentos à Base de Conhecimento")
        
        st.write("""
        Faça upload de documentos para treinar a IA. Documentos processados enriquecem 
        a base de conhecimento, melhorando a precisão dos resumos e análises futuras.
        """)
        
        # Card explicativo com destaque
        with st.expander("ℹ️ Como funciona o treinamento", expanded=False):
            st.info("""
            **Processo de treinamento:**
            1. Selecione um ou mais arquivos nos formatos suportados
            2. Clique em "Processar documentos" para iniciar o treinamento
            3. A IA extrairá e armazenará o conhecimento contido nos documentos
            4. Os documentos processados ficam disponíveis para consulta futura
            
            Formatos suportados: PDF, Word, Excel, PowerPoint, HTML, TXT, JSON e CSV
            """)
        
        # Uploader sempre visível, com espaço dedicado
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded_files = st.file_uploader(
                "Selecione os documentos para treinar a IA",
                type=["pdf", "docx", "txt", "xlsx", "pptx", "html", "csv", "json", "odt"],
                accept_multiple_files=True,
                disabled=not rag_is_active,
                help="Arraste ou clique para selecionar arquivos"
            )
        
        # Botão de processamento destacado
        with col2:
            process_button = st.button(
                "🚀 Processar documentos", 
                type="primary",
                disabled=not uploaded_files or not rag_is_active,
                use_container_width=True
            )
        
        # Área de processamento
        if uploaded_files and process_button:
            st.markdown("---")
            st.subheader("📊 Progresso do Processamento")
            
            progress_container = st.container()
            with st.spinner("Iniciando processamento..."):
                had_error = False
                processed_files = 0
                
                # Barra de progresso visual
                progress_bar = st.progress(0)
                total_files = len(uploaded_files)
                
                # Área para exibir resultados do processamento
                results_area = st.container()
                
                for idx, file in enumerate(uploaded_files):
                    # Atualiza barra de progresso
                    progress_bar.progress((idx) / total_files)
                    
                    with results_area:
                        st.write(f"Processando: **{file.name}**")
                        
                        try:
                            file_bytes = file.getvalue()
                            with st.spinner(f"Analisando `{file.name}`..."):
                                resultado = adicionar_documento_ao_rag(file_bytes, file.name)
    
                            if "Treinamento concluído" in resultado or "Sucesso" in resultado:
                                st.success(resultado, icon="✅")
                                processed_files += 1
                            elif "já foi processado" in resultado:
                                st.info(resultado, icon="ℹ️")
                            else:
                                st.error(resultado, icon="❌")
                                had_error = True
                                
                        except Exception as e:
                            st.error(f"❌ Erro ao processar '{file.name}': {str(e)}")
                            had_error = True
                
                # Atualiza barra para completa
                progress_bar.progress(1.0)
                
                # Feedback final do processamento
                if processed_files > 0:
                    with st.spinner("Atualizando base de conhecimento..."):
                        # Força reconexão para atualizar contagem
                        import rag_manager
                        rag_manager._chroma_client = None
                        import time
                        time.sleep(1)
                    
                    st.success(f"✅ {processed_files} documento(s) processado(s) com sucesso!")
                    
                    # Botão claro para reiniciar
                    if st.button("📄 Processar mais documentos", key="more_docs"):
                        st.rerun()
                        
                elif had_error:
                    st.warning("⚠️ Processamento concluído com erros. Verifique os detalhes acima.")
                    if st.button("🔄 Tentar novamente", key="retry_btn"):
                        st.rerun()
        
        # ÁREA DE GERENCIAMENTO (opção avançada)
        with st.expander("⚙️ Gerenciamento da Base de Conhecimento", expanded=False):
            st.warning("⚠️ Esta seção é apenas para administradores. Use com cautela!")
            st.info("Esta ação removerá **TODOS** os documentos treinados da base de conhecimento.")
            
            if st.button("🗑️ ZERAR BASE DE CONHECIMENTO", 
                         type="primary", 
                         key="reset_db_btn", 
                         use_container_width=True):
                with st.spinner("Zerando base de conhecimento..."):
                    resultado = zerar_base_rag()
                    if resultado["success"]:
                        st.success(resultado["message"])
                    else:
                        st.error(resultado["message"])
                    time.sleep(2)
                    st.rerun()
    
    # === ABA 2: CONSULTA ===
    with tab2:
        st.header("Consultar Base de Conhecimento")
        st.write("Digite uma pergunta para buscar informações na base de conhecimento.")
        
        query = st.text_input("Digite sua pergunta:", 
                            placeholder="Ex: Qual o procedimento para cálculo de horas extras?",
                            disabled=not rag_is_active)

        if query:
            with st.spinner("Buscando na base de conhecimento..."):
                contexto = consultar_rag(query)
                
                if contexto.strip():
                    st.success("🎯 Informações encontradas:")
                    st.text_area("Resultado da consulta:", 
                                value=contexto, 
                                height=400,
                                disabled=True)
                else:
                    st.warning("Nenhuma informação relevante encontrada. Tente reformular sua pergunta ou adicionar mais documentos à base de conhecimento.")

    # === ABA 3: DOCUMENTOS TREINADOS ===
    with tab3:
        st.header("Documentos na Base de Conhecimento")
        
        # Botão para atualizar a lista
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🔄 Atualizar lista", use_container_width=True):
                st.rerun()
        
        st.write("Documentos já processados e disponíveis na base de conhecimento:")
        
        log_path = "logs/treinamentos.jsonl"
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                linhas = f.readlines()

            if not linhas:
                st.info("🔍 Nenhum documento treinado ainda. Utilize a aba 'Upload de Documentos' para adicionar conteúdo.")
            else:
                # Criar uma tabela mais organizada
                dados_tabela = []
                for linha in reversed(linhas):  # Mostrar os mais recentes primeiro
                    try:
                        registro = json.loads(linha)
                        # Converter timestamp para data formatada
                        data_formatada = datetime.datetime.fromisoformat(registro['data']).strftime('%d/%m/%Y %H:%M')
                        
                        dados_tabela.append({
                            "Documento": registro['arquivo'],
                            "Data": data_formatada,
                            "Chunks": registro['quantidade_chunks']
                        })
                    except Exception as e:
                        continue  # Ignora linhas com erro
                
                if dados_tabela:
                    # Exibir como DataFrame estilizado
                    df = pd.DataFrame(dados_tabela)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum documento válido encontrado no histórico.")
        else:
            st.info("🔍 Nenhum documento treinado ainda. Utilize a aba 'Upload de Documentos' para adicionar conteúdo.")

def pagina_visualizar_base():
    """Página para visualizar o conteúdo do ChromaDB."""
    st.title("📊 Base de Conhecimento - Visualização")
    
    # Verificar conexão
    rag_status = get_rag_status()
    if not rag_status["connected"]:
        st.error("❌ ChromaDB indisponível")
        return
    
    # Botão para atualizar dados manualmente
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Obter dados
    with st.spinner("Carregando dados do ChromaDB..."):
        result = get_chroma_content()
    
    if not result["success"]:
        st.error(f"❌ Erro: {result['message']}")
        return
    
    # Estatísticas
    st.subheader("📈 Estatísticas Gerais")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Chunks", result["count"])
    with col2:
        st.metric("Documentos Únicos", len(result["sources"]))
    with col3:
        st.metric("Média de Chunks/Doc", round(result["count"] / max(len(result["sources"]), 1), 1))
    
    # Filtros
    st.subheader("🔍 Filtrar e Explorar")
    fonte_selecionada = st.selectbox(
        "Filtrar por documento:",
        ["Todos os documentos"] + sorted(list(result["sources"].keys()))
    )
    
    # Aplicar filtro
    if fonte_selecionada != "Todos os documentos":
        with st.spinner(f"Filtrando por '{fonte_selecionada}'..."):
            filtered_result = get_chroma_content(filter_source=fonte_selecionada)
            if not filtered_result["success"]:
                st.error(f"❌ Erro ao filtrar: {filtered_result['message']}")
                return
            display_data = filtered_result["data"]
    else:
        display_data = result["data"]
    
    # Tabela de documentos
    st.subheader("📄 Conteúdo da Base")
    
    # Preparar dados para tabela
    table_data = []
    for i, doc_id in enumerate(display_data.get("ids", [])):
        meta = display_data["metadatas"][i] if i < len(display_data.get("metadatas", [])) else {}
        doc = display_data["documents"][i] if i < len(display_data.get("documents", [])) else ""
        
        # Truncar conteúdo para exibição
        preview = doc[:100] + "..." if len(doc) > 100 else doc
        
        # Adicionar timestamp formatado se disponível
        timestamp = meta.get("timestamp", "")
        timestamp_str = ""
        if timestamp:
            try:
                timestamp_str = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M')
            except:
                timestamp_str = str(timestamp)
        
        table_data.append({
            "ID": doc_id,
            "Documento": meta.get("source", "Desconhecido"),
            "Data": timestamp_str,
            "Conteúdo": preview
        })
    
    # Exibir tabela
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum documento encontrado com estes filtros.")
    
    # Visualizar documento específico
    st.subheader("🔎 Visualizar Documento Completo")
    if display_data.get("ids"):
        col1, col2 = st.columns([3, 1])
        with col1:
            doc_index = st.selectbox(
                "Selecione um documento para visualizar:",
                range(len(display_data["ids"])),
                format_func=lambda i: f"{display_data['ids'][i]} - {display_data['metadatas'][i].get('source', 'N/A')}"
            )
        
        with col2:
            st.download_button(
                "📥 Exportar todos",
                data=json.dumps(display_data, indent=2),
                file_name=f"chromadb_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # Exibir conteúdo completo
        if doc_index is not None:
            with st.expander("Conteúdo completo", expanded=True):
                st.text_area(
                    "Texto completo", 
                    value=display_data["documents"][doc_index],
                    height=400
                )
                
                # Corrigido: Usar st.code() em vez de st.json() para exibir metadados formatados corretamente
                st.subheader("Metadados")
                # Garantindo que o JSON seja formatado corretamente
                metadata = display_data["metadatas"][doc_index]
                # Usando a função json.dumps para garantir uma serialização correta
                formatted_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                st.code(formatted_json, language="json")
                
                # Adicionar botão para navegação entre documentos
                col1, col2 = st.columns(2)
                with col1:
                    if doc_index > 0 and st.button("⬅️ Anterior"):
                        st.session_state['selected_doc_index'] = doc_index - 1
                        st.rerun()
                with col2:
                    if doc_index < len(display_data["ids"]) - 1 and st.button("Próximo ➡️"):
                        st.session_state['selected_doc_index'] = doc_index + 1
                        st.rerun()
    else:
        st.info("Sem documentos para visualizar.")

def main():
    inicializar_estado()
    
    # Garantir que o diretório de exportação existe
    os.makedirs("export", exist_ok=True)
    
    with st.sidebar:
        st.header("Navegação")
        st.session_state.pagina_atual = st.radio(
            "Escolha uma opção:",
            ["Analisar Processo", "Treinar IA", "Visualizar Base"],
            key="navigation_radio"
        )

        st.markdown("---")
        
        # LÓGICA DE VERIFICAÇÃO DE STATUS CORRIGIDA
        rag_status = get_rag_status() # Chama a função diretamente e sem cache
        
        if rag_status["connected"]:
            if rag_status["doc_count"] > 0:
                st.success(f"RAG Ativo ({rag_status['doc_count']} docs)", icon="🧠")
            else:
                st.warning("RAG Conectado (Vazio)", icon="ℹ️")
        else:
            st.error("RAG Desconectado", icon="🔌")
            st.caption(rag_status.get("message", "Falha na conexão."))

        st.info("Projeto desenvolvido para automatizar a análise de processos trabalhistas.")

    # A variável agora reflete o estado real da conexão

    rag_is_active = rag_status["connected"]

    # Navegar para a página selecionada

    if st.session_state.pagina_atual == "Analisar Processo":
        pagina_analise(rag_is_active)
    elif st.session_state.pagina_atual == "Treinar IA":
        pagina_treinamento(rag_is_active)
    elif st.session_state.pagina_atual == "Visualizar Base":
        pagina_visualizar_base()

if __name__ == "__main__":
    main()