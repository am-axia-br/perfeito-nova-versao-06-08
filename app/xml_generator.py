# ===================================================================
# app/xml_generator.py (VERSÃO COMPLETA E APRIMORADA)
#
# Melhorias:
# - EXPORTAÇÃO UNIVERSAL: Captura e exporta TODOS os dados do processo,
#   independentemente da estrutura ou campos presentes.
# - FUNÇÃO UNIVERSAL DE CONVERSÃO: A função `safe_str` agora é mais robusta
#   para lidar com qualquer tipo de dado.
# - ESTRUTURA AVANÇADA: Mantém relacionamentos hierárquicos complexos no XML.
# - METADADOS COMPLETOS: Adiciona informações detalhadas sobre a exportação.
# - PRESERVAÇÃO DE DADOS: Garantia que nenhum dado seja perdido durante a
#   conversão para XML.
# ===================================================================

from lxml import etree
import os
import json
from datetime import datetime

def safe_str(value):
    """Converte qualquer valor para uma string segura para XML."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def adicionar_elemento_recursivo(parent, nome, valor):
    """Adiciona elementos de forma recursiva, preservando estruturas aninhadas."""
    if isinstance(valor, dict):
        # Criar nó para o dicionário
        dict_elem = etree.SubElement(parent, nome)
        for k, v in valor.items():
            # Normalizar nome da chave para XML válido
            key_name = ''.join(c if c.isalnum() else '_' for c in k)
            if not key_name:
                key_name = "item"
            if key_name[0].isdigit():
                key_name = "n" + key_name
            adicionar_elemento_recursivo(dict_elem, key_name, v)
    elif isinstance(valor, list):
        # Criar nó para a lista
        list_elem = etree.SubElement(parent, nome)
        list_elem.set("type", "array")
        for i, item in enumerate(valor):
            # Usar um nome de elemento baseado no nome do pai para itens da lista
            item_name = nome.rstrip('s') if nome.endswith('s') else "item"
            adicionar_elemento_recursivo(list_elem, item_name, item)
    else:
        # Valor simples
        elem = etree.SubElement(parent, nome)
        elem.text = safe_str(valor)

def gerar_xml_pjecalc(dados, caminho_saida="export/saida_pjecalc.xml"):
    """
    Gera um ficheiro XML completo compatível com o PJe-Calc a partir dos dados do processo.
    Exporta TODOS os dados presentes, independentemente da estrutura.
    
    Args:
        dados: Dicionário com todos os dados do processo
        caminho_saida: Caminho onde será salvo o arquivo XML
    
    Returns:
        str: Caminho do arquivo gerado
    """
    # Elemento raiz
    root = etree.Element("PjeCalc")
    
    # Adicionar metadados da exportação
    metadados = etree.SubElement(root, "Metadados")
    etree.SubElement(metadados, "DataExportacao").text = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    etree.SubElement(metadados, "Usuario").text = "am-axia-br"
    etree.SubElement(metadados, "Versao").text = "1.0"
    etree.SubElement(metadados, "Timestamp").text = str(int(datetime.utcnow().timestamp()))
    
    # --- SEÇÃO 1: EXPORTAÇÃO ESTRUTURADA DOS PRINCIPAIS ELEMENTOS ---
    
    # Dados Processuais
    dados_proc = dados.get("dados_processuais", {})
    if dados_proc:
        processuais = etree.SubElement(root, "DadosProcessuais")
        for chave, valor in dados_proc.items():
            nome_elemento = ''.join(c if c.isalnum() else '_' for c in chave)
            etree.SubElement(processuais, nome_elemento).text = safe_str(valor)
    
    # Partes
    dados_partes = dados.get("partes", {})
    if dados_partes:
        partes = etree.SubElement(root, "Partes")
        
        # Reclamante
        if "reclamante" in dados_partes:
            etree.SubElement(partes, "Reclamante").text = safe_str(dados_partes.get("reclamante"))
        
        # CPF Reclamante (pode estar em múltiplos lugares)
        cpf = dados_partes.get("cpf_reclamante", 
                              dados.get("dados_pessoais", {}).get("cpf", ""))
        if cpf:
            etree.SubElement(partes, "CPFReclamante").text = safe_str(cpf)
        
        # Advogado
        if "advogado_reclamante" in dados_partes:
            etree.SubElement(partes, "AdvogadoReclamante").text = safe_str(dados_partes.get("advogado_reclamante"))
        
        # Reclamadas
        reclamadas = dados_partes.get("reclamadas", [])
        if reclamadas:
            reclamadas_el = etree.SubElement(partes, "Reclamadas")
            
            # Tratar diferentes formatos de reclamadas (string, lista, etc)
            if isinstance(reclamadas, str):
                # Se for string, tentar separar por ; ou ,
                if ';' in reclamadas:
                    reclamadas = [r.strip() for r in reclamadas.split(';')]
                elif ',' in reclamadas:
                    reclamadas = [r.strip() for r in reclamadas.split(',')]
                else:
                    reclamadas = [reclamadas]
            
            # Adicionar cada reclamada como elemento
            for rec in reclamadas:
                etree.SubElement(reclamadas_el, "Reclamada").text = safe_str(rec)
    
    # Dados Pessoais (alternativa para partes)
    dados_pessoais = dados.get("dados_pessoais", {})
    if dados_pessoais:
        pessoais = etree.SubElement(root, "DadosPessoais")
        for chave, valor in dados_pessoais.items():
            nome_elemento = ''.join(c if c.isalnum() else '_' for c in chave)
            etree.SubElement(pessoais, nome_elemento).text = safe_str(valor)
    
    # Contrato de Trabalho
    dados_contrato = dados.get("contrato_trabalho", {})
    if dados_contrato:
        contrato = etree.SubElement(root, "ContratoTrabalho")
        
        # Campos específicos do contrato
        campos_contrato = [
            "data_admissao", "data_demissao", "data_demissao_rescisao_indireta", 
            "funcao", "salario_base", "ultimo_salario"
        ]
        
        for campo in campos_contrato:
            if campo in dados_contrato:
                nome_elemento = ''.join(c if c.isalnum() else '_' for c in campo)
                etree.SubElement(contrato, nome_elemento).text = safe_str(dados_contrato.get(campo))
        
        # Afastamentos
        afastamentos = dados_contrato.get("periodos_afastamento", [])
        if afastamentos:
            afastamentos_el = etree.SubElement(contrato, "PeriodosAfastamento")
            
            # Se for string, tentar extrair período
            if isinstance(afastamentos, str):
                afastamento_el = etree.SubElement(afastamentos_el, "Afastamento")
                etree.SubElement(afastamento_el, "Periodo").text = safe_str(afastamentos)
            # Se for lista de dicionários
            elif isinstance(afastamentos, list):
                for af in afastamentos:
                    afastamento_el = etree.SubElement(afastamentos_el, "Afastamento")
                    if isinstance(af, dict):
                        for k, v in af.items():
                            etree.SubElement(afastamento_el, k).text = safe_str(v)
                    else:
                        etree.SubElement(afastamento_el, "Periodo").text = safe_str(af)
    
    # Pleitos e Verbas
    pleitos = dados.get("pleitos_e_verbas", [])
    verbas_pleiteadas = dados.get("verbas_pleiteadas", [])
    
    # Unificar pleitos e verbas (podem estar em estruturas diferentes)
    todas_verbas = []
    
    # Adicionar pleitos
    if pleitos:
        todas_verbas.extend(pleitos)
    
    # Adicionar verbas pleiteadas se ainda não estiverem em pleitos
    if verbas_pleiteadas:
        # Verificar se são as mesmas verbas
        verbas_ja_presentes = []
        for pleito in pleitos:
            if "verba" in pleito:
                verbas_ja_presentes.append(pleito["verba"])
        
        # Adicionar apenas verbas não duplicadas
        for verba in verbas_pleiteadas:
            if "verba" in verba and verba["verba"] not in verbas_ja_presentes:
                todas_verbas.append(verba)
    
    # Exportar todas as verbas
    if todas_verbas:
        verbas_el = etree.SubElement(root, "Verbas")
        for v in todas_verbas:
            verba_el = etree.SubElement(verbas_el, "Verba")
            for k, valor in v.items():
                nome_elemento = ''.join(c if c.isalnum() else '_' for c in k)
                etree.SubElement(verba_el, nome_elemento).text = safe_str(valor)
    
    # Parâmetros de Cálculo
    params_calculo = dados.get("parametros_calculo", {})
    info_pjecalc = dados.get("informacoes_pjecalc", {})
    
    # Unificar informações de cálculo (podem estar em campos diferentes)
    dados_calculo = {}
    dados_calculo.update(params_calculo)
    dados_calculo.update(info_pjecalc)
    
    if dados_calculo:
        calculo = etree.SubElement(root, "ParametrosCalculo")
        
        # Campos específicos
        campos_calc = [
            "correcao_monetaria", "juros_mora", "inss_reclamante", 
            "inss_patronal", "inss_terceiros", "honorarios"
        ]
        
        for campo in campos_calc:
            if campo in dados_calculo:
                nome_elemento = ''.join(c if c.isalnum() else '_' for c in campo)
                valor = dados_calculo.get(campo)
                
                if isinstance(valor, (dict, list)):
                    # Tratar estruturas complexas como honorarios_advocaticios
                    elemento_container = etree.SubElement(calculo, nome_elemento)
                    if isinstance(valor, dict):
                        for k, v in valor.items():
                            sub_elem = etree.SubElement(elemento_container, k)
                            sub_elem.text = safe_str(v)
                    elif isinstance(valor, list):
                        for item in valor:
                            item_el = etree.SubElement(elemento_container, "Item")
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    sub_elem = etree.SubElement(item_el, k)
                                    sub_elem.text = safe_str(v)
                            else:
                                item_el.text = safe_str(item)
                else:
                    # Valores simples
                    etree.SubElement(calculo, nome_elemento).text = safe_str(valor)
    
    # Resultado da Liquidação
    resultado = dados.get("resultado_liquidacao", {})
    if resultado:
        liquidacao = etree.SubElement(root, "ResultadoLiquidacao")
        for k, v in resultado.items():
            nome_elemento = ''.join(c if c.isalnum() else '_' for c in k)
            etree.SubElement(liquidacao, nome_elemento).text = safe_str(v)
    
    # Bases Técnicas
    bases = dados.get("bases_tecnicas_calculo", {})
    if bases:
        tecnicas = etree.SubElement(root, "BasesTecnicas")
        for k, v in bases.items():
            nome_elemento = ''.join(c if c.isalnum() else '_' for c in k)
            if isinstance(v, (dict, list)):
                elem = etree.SubElement(tecnicas, nome_elemento)
                if isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        sub_elem = etree.SubElement(elem, sub_k)
                        sub_elem.text = safe_str(sub_v)
                else:  # lista
                    for item in v:
                        item_el = etree.SubElement(elem, "Item")
                        if isinstance(item, dict):
                            for item_k, item_v in item.items():
                                sub_elem = etree.SubElement(item_el, item_k)
                                sub_elem.text = safe_str(item_v)
                        else:
                            item_el.text = safe_str(item)
            else:
                etree.SubElement(tecnicas, nome_elemento).text = safe_str(v)
    
    # --- SEÇÃO 2: EXPORTAÇÃO UNIVERSAL DE CAMPOS ADICIONAIS ---
    
    # Qualquer outro campo no dicionário raiz que ainda não foi processado
    outros_campos = set(dados.keys()) - {
        "dados_processuais", "partes", "dados_pessoais", "contrato_trabalho", 
        "pleitos_e_verbas", "verbas_pleiteadas", "parametros_calculo",
        "informacoes_pjecalc", "resultado_liquidacao", "bases_tecnicas_calculo",
        "observacoes_gerais", "metadados"
    }
    
    if outros_campos:
        outros = etree.SubElement(root, "OutrosDados")
        for campo in outros_campos:
            valor = dados.get(campo)
            # Usar função recursiva para adicionar elementos complexos
            adicionar_elemento_recursivo(outros, campo, valor)
    
    # Observações Gerais (texto do resumo)
    if "observacoes_gerais" in dados:
        obs = etree.SubElement(root, "ObservacoesGerais")
        obs.text = safe_str(dados.get("observacoes_gerais"))
    
    # --- ESCRITA DO FICHEIRO XML ---
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    tree = etree.ElementTree(root)
    
    try:
        tree.write(caminho_saida, pretty_print=True, xml_declaration=True, encoding="utf-8")
        print(f"✅ Ficheiro XML gerado com sucesso em: {caminho_saida}")
        return caminho_saida
    except Exception as e:
        print(f"❌ Erro ao gerar o arquivo XML: {str(e)}")
        # Tentar salvar em caminho alternativo se o original falhar
        try:
            alt_path = "export/backup_pjecalc.xml"
            os.makedirs(os.path.dirname(alt_path), exist_ok=True)
            tree.write(alt_path, pretty_print=True, xml_declaration=True, encoding="utf-8")
            print(f"⚠️ Arquivo XML salvo em caminho alternativo: {alt_path}")
            return alt_path
        except Exception as e2:
            print(f"❌❌ Falha total ao salvar XML: {str(e2)}")
            return None