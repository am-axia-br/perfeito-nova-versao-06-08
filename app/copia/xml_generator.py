# =============================
# app/xml_generator.py (VALIDAÇÃO XSD INCLUÍDA)
# =============================

from lxml import etree
import os

XSD_PATH = "schemas/pjecalc.xsd"  # Caminho fixo do schema XSD

def gerar_xml_pjecalc(dados):
    root = etree.Element("PjeCalc")

    # 1. Identificação do Processo
    identificacao = etree.SubElement(root, "Identificacao")
    etree.SubElement(identificacao, "NumeroProcesso").text = dados.get("dados_processuais", {}).get("numero_processo", "")
    etree.SubElement(identificacao, "Vara").text = dados.get("dados_processuais", {}).get("vara", "")
    etree.SubElement(identificacao, "Tribunal").text = dados.get("dados_processuais", {}).get("tribunal", "")
    etree.SubElement(identificacao, "DataDistribuicao").text = dados.get("dados_processuais", {}).get("data_distribuicao", "")
    etree.SubElement(identificacao, "ValorCausa").text = dados.get("dados_processuais", {}).get("valor_causa", "")
    etree.SubElement(identificacao, "FaseProcessual").text = dados.get("dados_processuais", {}).get("fase_processual", "")

    # 2. Partes
    partes = etree.SubElement(root, "Partes")
    etree.SubElement(partes, "Reclamante").text = dados.get("partes", {}).get("reclamante", "")
    etree.SubElement(partes, "Reclamada").text = dados.get("partes", {}).get("reclamada", "")
    etree.SubElement(partes, "CPFReclamante").text = dados.get("partes", {}).get("cpf_reclamante", "")
    etree.SubElement(partes, "CNPJReclamada").text = dados.get("partes", {}).get("cnpj_reclamada", "")
    
    advs = dados.get("partes", {}).get("advogados", [])
    if isinstance(advs, list):
        advogados_el = etree.SubElement(partes, "Advogados")
        for adv in advs:
            etree.SubElement(advogados_el, "Advogado").text = str(adv)

    # 3. Contrato de Trabalho
    contrato = etree.SubElement(root, "ContratoTrabalho")
    ct = dados.get("contrato_trabalho", {})
    etree.SubElement(contrato, "DataAdmissao").text = ct.get("data_admissao", "")
    etree.SubElement(contrato, "DataDemissao").text = ct.get("data_demissao", "")
    etree.SubElement(contrato, "Cargo").text = ct.get("cargo", "")
    etree.SubElement(contrato, "TipoContrato").text = ct.get("tipo_contrato", "")
    etree.SubElement(contrato, "SalarioBase").text = ct.get("salario_base", "")
    etree.SubElement(contrato, "JornadaSemanal").text = ct.get("jornada_semanal", "")

    # 4. Pleitos
    pleitos_el = etree.SubElement(root, "Pleitos")
    for pleito in dados.get("pleitos", []):
        etree.SubElement(pleitos_el, "VerbaReclamada").text = str(pleito)

    # 5. Decisão
    decisao = etree.SubElement(root, "Decisao")
    dec = dados.get("decisao", {})
    for k, v in dec.items():
        if isinstance(v, list):
            sub = etree.SubElement(decisao, k)
            for item in v:
                etree.SubElement(sub, "Item").text = str(item)
        else:
            etree.SubElement(decisao, k).text = str(v)

    # 6. Observações
    etree.SubElement(root, "Observacoes").text = dados.get("observacoes", "")

    # Escrita do XML
    if not os.path.exists("export"):
        os.makedirs("export")
    tree = etree.ElementTree(root)
    xml_path = "export/saida_pjecalc.xml"
    tree.write(xml_path, pretty_print=True, xml_declaration=True, encoding="utf-8")

    # Validação com XSD
    validar_xml_pjecalc(xml_path)


def validar_xml_pjecalc(xml_path):
    try:
        xsd_schema = etree.XMLSchema(file=XSD_PATH)
        xml_doc = etree.parse(xml_path)

        if xsd_schema.validate(xml_doc):
            print("✅ XML validado com sucesso pelo XSD.")
        else:
            print("❌ Erros de validação no XML:")
            for error in xsd_schema.error_log:
                print(f" - {error.message}")
    except Exception as e:
        print(f"⚠️ Erro ao validar o XML: {e}")
