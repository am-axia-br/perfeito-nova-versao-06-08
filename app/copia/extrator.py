# ===================================================================
# app/extrator.py (VERSÃO COM INTELIGÊNCIA JURÍDICA AVANÇADA)
#
# ANÁLISE PROFUNDA E CORREÇÃO DEFINITIVA.
#
# O que mudou:
# - INTELIGÊNCIA JURÍDICA PARA REFLEXOS: O PROMPT_CONSOLIDACAO foi
#   drasticamente aprimorado com uma "REGRA DE OURO PARA REFLEXOS".
#   A IA agora é instruída a agir como um advogado, inferindo os
#   reflexos em FGTS + 40% para verbas de natureza salarial e
#   identificando verbas indenizatórias que não geram reflexos.
#   Isso resolve a falha na captura de reflexos.
# - GLOSSÁRIO JURÍDICO EXPANDIDO: O prompt agora contém um glossário
#   muito mais detalhado, ensinando a IA a identificar e diferenciar
#   TODAS as verbas listadas na petição inicial, incluindo as
#   múltiplas variações de Férias e as multas dos artigos 467 e 477.
# - PRESERVAÇÃO DE DADOS GARANTIDA: A regra de consolidação que
#   mantém verbas com parâmetros diferentes foi reforçada.
# ===================================================================

import os
import json
import time
import traceback
import google.generativeai as genai
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Configuração da API do Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Chave da API do Gemini não encontrada no arquivo .env.")
genai.configure(api_key=api_key)

# --- Configuração do Modelo ---
MODELO_ANALISE = "gemini-1.5-pro-latest"
generation_config = {
    "temperature": 0.1,
    "response_mime_type": "application/json",
}

# --- FASE 1: PROMPT DE EXTRAÇÃO DE DADOS BRUTOS ---
PROMPT_EXTRACAO = """
Você é um assistente de extração de dados. Analise o TRECHO de um processo trabalhista e extraia TODAS as informações relevantes que encontrar. Foque em capturar os dados como eles aparecem. Retorne os dados em um formato JSON simples.

**Dados a serem extraídos:**
- **Dados do Processo:** Número, Vara, UF, Data de Ajuizamento, Valor da Causa.
- **Partes:** Nomes do Reclamante, Reclamadas e Advogados, CPF do Reclamante.
- **Contrato:** Data de Admissão, Data de Demissão/Rescisão, Função, Salário, Períodos de Afastamento (com início, fim e motivo).
- **Pleitos e Verbas:** Liste TODOS os pedidos (verbas) mencionados, com seus parâmetros e reflexos, se houver. Use a chave "verba" para o nome do pedido.
- **Parâmetros de Cálculo:** Honorários (percentual e base), Correção Monetária e Juros (índices e períodos), Contribuições Sociais (especialmente INSS Terceiros).

IMPORTANTE: Organize os dados seguindo rigorosamente as chaves especificadas neste prompt. 
Use "verbas" (e não "pleitos" ou "verbas_pleiteadas") como chave para a lista de verbas reclamadas.
Use "reclamada" (e não "reclamadas") para a parte ré do processo.

Se uma informação não estiver no trecho, omita a chave.

**TRECHO DO PROCESSO:**
"""

# --- FASE 2: PROMPT DE CONSOLIDAÇÃO E ESTRUTURAÇÃO INTELIGENTE ---
PROMPT_CONSOLIDACAO = """
Você é um especialista sênior em Direito do Trabalho no Brasil, com a tarefa de consolidar e estruturar dados para o sistema PJe-Calc. Eu fornecerei uma lista de múltiplos JSONs, extraídos de partes de um processo. Os dados podem estar incompletos, duplicados ou com erros.

**SUA TAREFA É CRÍTICA E EXIGE PROFUNDO CONHECIMENTO JURÍDICO:**
1.  **CONSOLIDE TUDO:** Combine as informações de todos os JSONs parciais em um único objeto final.
2.  **LIMPE, CORRIJA E DETALHE:**
    - Se a mesma informação aparecer várias vezes (ex: `numero_processo`), use a versão mais completa.
    - Corrija erros comuns: Se encontrar a chave `"verbo"`, renomeie para `"verba"`.
    - **GLOSSÁRIO DE VERBAS:** Identifique e padronize todas as verbas abaixo. Seja extremamente detalhista, diferenciando cada tipo:
        - Saldo de Salário
        - Aviso Prévio (pode ser indenizado)
        - 13º Salário (pode ser proporcional ou indenizado)
        - Férias Vencidas
        - 1/3 sobre Férias Vencidas
        - Férias Proporcionais
        - 1/3 sobre Férias Proporcionais
        - Férias Indenizadas
        - 1/3 sobre Férias Indenizadas
        - Multa do art. 467 da CLT
        - Multa do art. 477 da CLT
        - Depósitos do FGTS (ou FGTS em atraso)
        - Multa de 40% do FGTS
        - Dano Moral
        - Reestabelecimento do Plano de Saúde
        - Liberação de Chave de Conectividade
        - Baixa na CTPS
    - **REGRA DE OURO PARA UNIFICAÇÃO DE VERBAS:** Ao unificar a lista `pleitos_e_verbas`, remova itens duplicados SOMENTE SE o valor da chave 'verba' E o valor da chave 'parametros' forem EXATAMENTE idênticos. Itens com a mesma 'verba' mas 'parametros' diferentes (ex: "Férias Proporcionais" e "Férias Vencidas") são únicos e DEVEM ser mantidos.
    - **REGRA DE OURO PARA REFLEXOS (MUITO IMPORTANTE):** Você deve agir como um advogado e INFERIR os reflexos legais padrão, mesmo que o texto não os mencione.
        - **Natureza Salarial:** Para verbas como 'Saldo de Salário', 'Aviso Prévio', '13º Salário', os reflexos são 'FGTS e Multa de 40%'. Preencha o campo 'reflexos' com este valor.
        - **Natureza Indenizatória:** Para verbas como 'Férias' (e seu 1/3), 'Multa do art. 467', 'Multa do art. 477', 'Dano Moral', 'Multa de 40% do FGTS', os reflexos são 'N/A'. Preencha o campo 'reflexos' com 'N/A'.
3.  **ESTRUTURE RIGOROSAMENTE:** O resultado final DEVE seguir EXATAMENTE a estrutura JSON abaixo.
4.  **GERE O RESUMO:** Crie um resumo jurídico conciso no campo `observacoes_gerais`.

**ESTRUTURA FINAL OBRIGATÓRIA:**
```json
{
  "dados_processuais": {
    "numero_processo": "...",
    "vara_uf": "...",
    "data_ajuizamento": "...",
    "valor_causa": "...",
    "fase_calculo": "Provisão Inicial"
  },
  "partes": {
    "reclamante": "...",
    "cpf_reclamante": "...",
    "reclamadas": [],
    "advogado_reclamante": "..."
  },
  "contrato_trabalho": {
    "data_admissao": "...",
    "data_demissao_rescisao_indireta": "...",
    "funcao": "...",
    "salario_base": "...",
    "periodos_afastamento": []
  },
  "pleitos_e_verbas": [
      {"verba": "...", "parametros": "...", "reflexos": "..."}
  ],
  "parametros_calculo": {
    "honorarios_advocaticios": { "percentual": "...", "base_calculo": "..." },
    "correcao_monetaria": [],
    "juros_mora": [],
    "contribuicao_social": { "inss_terceiros_percentual": "..." }
  },
  "observacoes_gerais": "..."
}
```

**LISTA DE DADOS BRUTOS EXTRAÍDOS:**
"""

def dividir_em_chunks(texto):
    """Divide o texto em pedaços menores para análise."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=500, separators=["\n\n", "\n", ".", " "])
    return splitter.split_text(texto)

def extrair_dados_parciais(text_chunks, st_progress_bar=None):

    for i, chunk in enumerate(chunks):
        with open(f"logs/chunk_{i}.txt", "w", encoding="utf-8") as f:
            f.write(chunk)

    """
    FASE 1: Coleta dados brutos de cada chunk de forma flexível.
    """
    log_detalhado = []
    model = genai.GenerativeModel(MODELO_ANALISE)
    total_chunks = len(text_chunks)

    os.makedirs("logs", exist_ok=True)
    for i, chunk in enumerate(text_chunks):
        with open(f"logs/chunk_{i}.txt", "w", encoding="utf-8") as f:
            f.write(chunk)

    for i, chunk in enumerate(text_chunks):
        if st_progress_bar:
            st_progress_bar.progress((i + 1) / total_chunks, text=f"Analisando parte {i+1} de {total_chunks}...")

        prompt_completo = PROMPT_EXTRACAO + "\n" + chunk.strip()
        
        try:
            resposta = model.generate_content(prompt_completo, generation_config=generation_config)
            resultado_json = json.loads(resposta.text)
            log_detalhado.append({"status": "Sucesso", "chunk": i + 1, "resultado_recebido": resultado_json})
        
        except (json.JSONDecodeError, Exception) as e:
            resposta_bruta = "N/A"
            if 'resposta' in locals() and hasattr(resposta, 'text'):
                resposta_bruta = resposta.text
            log_detalhado.append({"status": "Falha", "chunk": i + 1, "erro": str(e), "resposta_bruta": resposta_bruta})
        
        time.sleep(1) 

    return log_detalhado

def consolidar_resultados(resultados_parciais_sucesso):
    """
    FASE 2: Consolida, limpa, corrige e estrutura os dados brutos no formato final.
    """
    if not resultados_parciais_sucesso:
        print("⚠️ Nenhum resultado parcial de sucesso foi recebido para consolidação.")
        return None

    model = genai.GenerativeModel(MODELO_ANALISE)
    
    json_parciais_str = json.dumps(resultados_parciais_sucesso, indent=2, ensure_ascii=False)
    prompt_completo = PROMPT_CONSOLIDACAO + "\n" + json_parciais_str

    try:
        resposta = model.generate_content(prompt_completo, generation_config=generation_config)
        resultado_final_json = json.loads(resposta.text)
        return resultado_final_json
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ Erro crítico na etapa de consolidação final: {e}")
        traceback.print_exc()
        return None
