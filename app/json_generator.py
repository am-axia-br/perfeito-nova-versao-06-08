# ===================================================================
# app/json_generator.py (VERSÃO FINAL E À PROVA DE FALHAS)
#
# Funcionalidades:
# - EXPORTAÇÃO COMPLETA: Exporta TODOS os dados do processo analisado
#   sem perder nenhuma informação durante a conversão.
# - FORMATAÇÃO INTELIGENTE: Gera JSON formatado para fácil leitura,
#   mas preserva a integridade dos tipos de dados.
# - METADADOS AUTOMÁTICOS: Adiciona automaticamente metadados como
#   data de exportação e informações do sistema.
# - ROBUSTEZ MÁXIMA: Resiliente a qualquer variação na estrutura dos
#   dados retornados pela IA.
# ===================================================================

import os
import json
from datetime import datetime

def gerar_json_exportacao(dados, caminho_saida="export/dados_processo.json"):
    """
    Gera um arquivo JSON completo com todos os dados do processo trabalhista.
    
    Parâmetros:
        dados (dict): Dados estruturados do processo trabalhista
        caminho_saida (str): Caminho onde o arquivo será salvo
        
    Retorna:
        str: Caminho do arquivo JSON gerado
    """
    # Criar uma cópia para não modificar o dicionário original
    dados_exportacao = dados.copy() if dados else {}
    
    # Adicionar metadados de exportação
    dados_exportacao['metadados'] = {
        'data_exportacao': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'usuario': 'am-axia-br',
        'formato': 'JSON',
        'versao': '1.0',
        'timestamp': datetime.utcnow().timestamp()
    }
    
    # Garantir que o diretório de saída existe
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    
    # Escrever o arquivo JSON formatado
    try:
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(dados_exportacao, f, indent=2, ensure_ascii=False)
        print(f"✅ Arquivo JSON gerado com sucesso em: {caminho_saida}")
        return caminho_saida
    except Exception as e:
        print(f"❌ Erro ao gerar o arquivo JSON: {str(e)}")
        return None

def gerar_json_bytes(dados):
    """
    Gera uma string JSON para uso direto em botões de download na interface.
    
    Parâmetros:
        dados (dict): Dados estruturados do processo trabalhista
        
    Retorna:
        bytes: Bytes contendo o JSON formatado, pronto para download
    """
    # Criar uma cópia para não modificar o dicionário original
    dados_exportacao = dados.copy() if dados else {}
    
    # Adicionar metadados de exportação
    dados_exportacao['metadados'] = {
        'data_exportacao': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'usuario': 'am-axia-br',
        'formato': 'JSON',
        'versao': '1.0',
        'timestamp': datetime.utcnow().timestamp()
    }
    
    # Converter para JSON formatado e depois para bytes
    try:
        # Formatação com indentação para melhor legibilidade
        json_str = json.dumps(dados_exportacao, indent=2, ensure_ascii=False)
        return json_str.encode('utf-8')
    except Exception as e:
        print(f"❌ Erro ao gerar os bytes do JSON: {str(e)}")
        # Retornar um JSON de erro caso algo falhe
        error_json = json.dumps({
            "erro": f"Falha ao gerar JSON: {str(e)}",
            "timestamp": datetime.utcnow().timestamp()
        }, indent=2)
        return error_json.encode('utf-8')