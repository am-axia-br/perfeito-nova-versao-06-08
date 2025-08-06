# =============================
# schemas/pjecalc_schema.py
# =============================

pjecalc_schema = {
    "type": "object",
    "properties": {
        "dados_processuais": {
            "type": "object",
            "properties": {
                "numero_processo": {"type": "string"},
                "vara": {"type": "string"},
                "tribunal": {"type": "string"},
                "data_distribuicao": {"type": "string"},
                "valor_causa": {"type": "string"},
                "fase_processual": {"type": "string"},
                "ultima_decisao": {
                    "type": "object",
                    "properties": {
                        "tipo": {"type": "string"},
                        "data": {"type": "string"},
                        "resumo": {"type": "string"}
                    },
                    "required": ["tipo", "data", "resumo"]
                }
            },
            "required": ["numero_processo", "vara", "tribunal", "data_distribuicao", "valor_causa", "fase_processual"]
        },
        "partes": {
            "type": "object",
            "properties": {
                "reclamante": {"type": "string"},
                "reclamada": {"type": "string"},
                "cpf_reclamante": {"type": "string"},
                "cnpj_reclamada": {"type": "string"},
                "advogados": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["reclamante", "reclamada"]
        },
        "contrato_trabalho": {
            "type": "object",
            "properties": {
                "cargo": {"type": "string"},
                "data_admissao": {"type": "string"},
                "data_demissao": {"type": "string"},
                "tipo_contrato": {"type": "string"},
                "salario_base": {"type": "string"},
                "jornada_semanal": {"type": "string"}
            },
            "required": ["cargo", "data_admissao", "data_demissao", "salario_base"]
        },
        "pleitos": {
            "type": "array",
            "items": {"type": "string"}
        },
        "decisao": {
            "type": "object"
        },
        "observacoes": {
            "type": "string"
        }
    },
    "required": ["dados_processuais", "partes", "contrato_trabalho", "pleitos"]
}
