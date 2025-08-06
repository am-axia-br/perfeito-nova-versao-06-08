"""
Módulo de análise inteligente de verbas trabalhistas.
Criado por: am-axia-br
Data: 2025-08-05
"""

import re
import unicodedata
import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation
import logging
import difflib
from rag_manager import consultar_rag

# Tentar importar pacotes NLTK, mas fornecer fallback se não estiver disponível
try:
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    NLTK_DISPONIVEL = True
except ImportError:
    NLTK_DISPONIVEL = False

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analise_verbas")

def aprimorar_padroes_verbas(analisador):
    """
    Melhora os padrões de detecção para verbas problemáticas.
    Modifica o analisador passado como parâmetro.
    """
    # 1. Padrões aprimorados para FGTS
    analisador.categorias_verbas["fgts"].extend([
        r"saldo[s]?\s+de\s+fgts", r"fgts\s+n[aã]o\s+recolhido",
        r"dep[óo]sito[s]?\s+do\s+fgts", r"fgts\s+em\s+atraso",
        r"parcela[s]?\s+do\s+fgts", r"recolhimento[s]?\s+fundi[áa]rio[s]?",
        r"dep[óo]sito[s]?\s+mensais\s+(?:d[eo]|no)?\s+fgts",
        r"fgts\s+não\s+depositado", r"obrigação\s+de\s+recolher\s+(?:o\s+)?fgts"
    ])
    
    # 2. Padrões aprimorados para Intervalo Intrajornada
    analisador.categorias_verbas["intervalo"].extend([
        r"hora\s+extra\s+intervalar", r"não\s+concess[ãa]o\s+de\s+intervalo", 
        r"intervalo\s+para\s+alimenta[çc][ãa]o", r"ausência\s+de\s+intervalo",
        r"intervalo\s+aliment[aá]rio", r"suprimido\s+o\s+intervalo",
        r"intervalo\s+m[íi]nimo", r"intervalo\s+legal", r"pausa\s+para\s+refeição",
        r"direito\s+[ao]o?\s+intervalo", r"horário\s+de\s+almo[çc]o"
    ])
    
    # 3. Padrões aprimorados para Verbas por Acidente de Trabalho
    analisador.categorias_verbas["verbas_acidente"].extend([
        r"acidente[s]?(?:\s+de)?\s+trabalho", r"doen[çc]a[s]?\s+profission[ai][li]s?",
        r"c[âa]ncer", r"aux[íi]lio-?doen[çc]a\s+acidentário",
        r"B9[12]", r"atestado\s+m[ée]dico", r"afastamento\s+m[ée]dico",
        r"benef[íi]cio\s+previdenci[áa]rio", r"INSS\s+(?:por|devido\s+a)\s+doen[çc]a",
        r"afastamento\s+(?:por|devido\s+a)\s+doen[çc]a", r"CID\s*-?\s*[A-Z]\d+"
    ])
    
    # 4. Padrões aprimorados para Rescisão Indireta
    analisador.categorias_verbas["rescisao_indireta"].extend([
        r"rescis[ãa]o\s+por\s+culpa\s+d[ao](?:\s+parte)?\s+empregador[a]?",
        r"rescindir\s+indiretamente", r"rescis[ãa]o\s+contratual\s+indireta",
        r"rescis[ãa]o\s+do\s+contrato\s+por\s+culpa\s+d[ao](?:\s+parte)?\s+empregador[a]?",
        r"rescis[ãa]o\s+(?:por\s+meio|através)\s+d[ao]\s+art(?:igo)?\.?\s*483",
        r"rompimento\s+contratual\s+por\s+culpa\s+d[ao](?:\s+parte)?\s+empregador[a]?"
    ])
    
    # 5. Padrões aprimorados para Obrigações Documentais
    analisador.categorias_verbas["obrigacoes_documentos"].extend([
        r"carteira\s+de\s+trabalho", r"CTPS", 
        r"assinatura\s+d[ae](?:\s+carteira|\s+CTPS)", r"assinar\s+a\s+carteira",
        r"entrega\s+d[eo]s?\s+PPP", r"guias\s+d[eo]\s+seguro",
        r"fornec(?:er|imento)\s+d[eo]s?\s+documentos?",
        r"libera[çc][ãa]o\s+d[eo]s?\s+documentos?", r"comunicado\s+de\s+dispensa", 
        r"documenta[çc][ãa]o\s+rescis[óo]ria", r"anotação\s+n[ao]\s+registro"
    ])
    
    # 6. Padrões aprimorados para Tutelas de Urgência
    analisador.categorias_verbas["liminares_tutelas"].extend([
        r"provimento\s+jurisdicional\s+(?:de|em)?\s+urg[êe]ncia", 
        r"art\.?\s*300", r"C[óo]digo\s+de\s+Processo\s+Civil", 
        r"tutela\s+provis[óo]ria", r"medida\s+liminar",
        r"suspens[ãa]o\s+d[eo]", r"determin(?:e|ar|ação)\s+imediata",
        r"provimento\s+liminar", r"pedido\s+de\s+urg[êe]ncia"
    ])
    
    # 7. Aumentar o contexto de análise
    original_detectar_verbas = analisador.detectar_verbas
    
    def detectar_verbas_melhorado(texto):
        """Detecta todas as verbas mencionadas no texto com seu contexto ampliado."""
        texto_norm = analisador.normalizar_texto(texto)
        resultado = {}
        
        for categoria, patterns in analisador.categorias_verbas.items():
            matches = []
            for pattern in patterns:
                for match in re.finditer(pattern, texto_norm):
                    # Captura contexto: 250 caracteres antes e depois da menção (aumentado de 150)
                    inicio = max(0, match.start() - 250)
                    fim = min(len(texto_norm), match.end() + 250)
                    
                    matches.append({
                        "termo": match.group(0),
                        "contexto": texto_norm[inicio:fim],
                        "posicao": match.start()
                    })
            
            if matches:
                resultado[categoria] = matches
                
        return resultado

    # Substituir o método original pelo melhorado
    analisador.detectar_verbas = detectar_verbas_melhorado

    return analisador

def implementar_dicionario_verbas(analisador):
    """
    Implementa um sistema de reconhecimento por dicionário de sinônimos para verbas trabalhistas.
    """
    # Dicionário de sinônimos baseado no compartilhado
    analisador.dicionario_verbas = {
        "13_salario": [
            "13º salário indenizado", "13º proporcional", "décimo terceiro proporcional", 
            "pagamento de 13º", "indenização de 13º", "gratificação natalina", 
            "13º salário proporcional"
        ],
        "ferias_vencidas": [
            "férias vencidas", "férias não gozadas vencidas", 
            "férias vencidas acrescidas de 1/3", "férias + 1/3 constitucional (vencidas)",
            "férias vencidas + terço constitucional"
        ],
        "ferias_indenizadas": [
            "férias proporcionais", "férias proporcionais + 1/3", "férias não gozadas proporcionais", 
            "indenização de férias", "férias proporcionais acrescidas de 1/3",
            "férias indenizadas"
        ],
        "fgts_multa": [
            "fgts + 40%", "depósitos do fgts", "multa de 40% sobre o fgts", 
            "liberação das guias do fgts", "recolhimentos fundiários", "fgts rescisório",
            "multa de 40% do fgts", "fgts e multa de 40%"
        ],
        "multa_477": [
            "multa do art. 477 da clt", "multa do artigo 477", "multa por atraso na rescisão", 
            "multa por verbas rescisórias fora do prazo", "multa rescisória"
        ],
        "multa_467": [
            "multa do art. 467 da clt", "multa do artigo 467", "multa por verbas incontroversas",
            "multa por verbas não pagas na 1ª audiência", "multa incontroversas"
        ]
    }
    
    # Adicionar método para correspondência por dicionário
    def correspondencia_por_dicionario(self, verba_texto, verbas_planilha):
        """Identifica correspondências usando o dicionário de sinônimos."""
        correspondencias = []
        
        # Normalizar verba do texto
        texto_norm = self.normalizar_texto(verba_texto.get("verba", ""))
        categoria = verba_texto.get("categoria", "")
        
        # Para cada verba da planilha
        for verba_planilha in verbas_planilha:
            planilha_norm = self.normalizar_texto(verba_planilha.get("verba", ""))
            
            # Verificar correspondências de dicionário
            for cat_dict, sinonimos in self.dicionario_verbas.items():
                # Se a categoria da verba texto tem correspondência no dicionário
                if (cat_dict == categoria or 
                    (cat_dict == "ferias_vencidas" and categoria == "ferias") or
                    (cat_dict == "ferias_indenizadas" and categoria == "ferias") or
                    (cat_dict == "fgts_multa" and categoria == "fgts")):
                    
                    # Verificar se a verba da planilha é um dos sinônimos desta categoria
                    sinonimos_norm = [self.normalizar_texto(s) for s in sinonimos]
                    if any(s in planilha_norm or planilha_norm in s for s in sinonimos_norm):
                        correspondencias.append({
                            "verba_texto": verba_texto,
                            "verba_planilha": verba_planilha,
                            "pontuacao": 0.9,  # Alta pontuação para correspondências de dicionário
                            "via_dicionario": True
                        })
        
        return correspondencias
    
    # Adicionar o método ao analisador
    analisador.correspondencia_por_dicionario = correspondencia_por_dicionario.__get__(analisador, type(analisador))
    
    return analisador

class AnalisadorVerbasInteligente:
    """
    Classe principal que implementa a análise inteligente de verbas trabalhistas.
    Combina NLP, regras especializadas e consulta à base de conhecimento.
    """
    
    def __init__(self):
        # Dicionário com categorias de verbas e expressões regulares correspondentes
        self.categorias_verbas = {
            # VERBAS PRINCIPAIS (EXPANDIDAS)
            "salario": [
                r"sal[aá]rio.*base", r"remunera[cç][aã]o", r"saldo\s+de\s+sal[aá]rio",
                r"diferen[çc]as?\s+salaria(l|is)", r"desvio\s+de\s+fun[çc][ãa]o",
                r"acúmulo\s+de\s+fun[çc][ãa]o", r"equipara[çc][ãa]o\s+salarial",
                r"sal[aá]rio.*substitui[çc][ãa]o", r"comiss[õo]es", r"sal[aá]rio\s+por\s+fora",
                r"gorjetas", r"ajuda\s+de\s+custo", r"vantagens?\s+salaria(l|is)",
                r"parcela\s+salarial", r"verbas?\s+salaria(l|is)"
            ],
            
            "ferias": [
                r"f[eé]rias", r"1/?3\s+(de|sobre)\s+f[eé]rias", r"adicional\s+de\s+f[eé]rias",
                r"f[eé]rias\s+(?:em\s+)?dobro", r"f[eé]rias\s+proporcionais",
                r"f[eé]rias\s+vencidas", r"f[eé]rias\s+n[ãa]o\s+gozadas",
                r"indeniza[çc][ãa]o\s+de\s+f[eé]rias", r"abono\s+pecuni[aá]rio",
                r"dobra\s+de\s+f[eé]rias", r"terço\s+constitucional"
            ],
            
            "13_salario": [
                r"13[\.º°]?\s*sal[aá]rio", r"d[eé]cimo\s+terceiro", r"gratifica[çc][ãa]o\s+natalina",
                r"13[\.º°]?\s*proporcional", r"13[\.º°]?\s*integral"
            ],
            
            "aviso_previo": [
                r"aviso\s+pr[eé]vio", r"pr[eé]\s+aviso", r"indeniza[çc][ãa]o\s+de\s+aviso",
                r"aviso\s+pr[eé]vio\s+proporcional", r"aviso\s+pr[eé]vio\s+trabalhado",
                r"aviso\s+pr[eé]vio\s+indenizado", r"trintídio", r"projeta[çc][ãa]o\s+do\s+aviso",
                r"proporcionalidade\s+do\s+aviso", r"lei\s+12\.506"
            ],
            
            "fgts": [
                r"fgts", r"fundo\s+de\s+garantia", r"dep[oó]sitos?\s+fundi[aá]rio",
                r"diferen[çc]as?\s+de\s+fgts", r"corre[çc][ãa]o\s+do\s+fgts",
                r"libera[çc][ãa]o\s+do\s+fgts", r"chave\s+de\s+conectividade",
                r"tr\s+sobre\s+fgts", r"multa\s+do\s+fgts", r"40%\s+do\s+fgts",
                r"saque\s+do\s+fgts", r"recolhimentos?\s+do\s+fgts"
            ],
            
            # MULTAS (SEPARADAS)
            "multa_477": [
                r"multa\s+(do\s+)?art\.?\s*47[7]", r"multa\s+rescis[oó]ria", 
                r"pagamento\s+fora\s+do\s+prazo\s+legal", r"atraso\s+nas?\s+verbas?\s+rescis[óo]rias?",
                r"multa\s+por\s+atraso\s+no\s+pagamento\s+das\s+verbas", r"multa\s+pela\s+rescis[ãa]o",
                r"penalidade\s+do\s+art\.?\s*47[7]"
            ],
            
            "multa_467": [
                r"multa\s+(do\s+)?art\.?\s*46[7]", r"multa\s+por\s+verbas\s+incontroversas", 
                r"acr[ée]scimo\s+de\s+50\s*%", r"parcelas\s+incontroversas",
                r"multa\s+de\s+50%", r"dobra\s+das\s+verbas\s+incontroversas"
            ],
            
            "outras_multas": [
                r"multa\s+(do\s+)?art\.?\s*47[9]", r"multa\s+(do\s+)?art\.?\s*48[0]",
                r"multa\s+por\s+atraso\s+salarial", r"multa\s+convencional",
                r"multa\s+normativa", r"multa\s+do\s+art\.?\s*47[4]-?A",
                r"multa\s+diária", r"astreintes", r"multa\s+por\s+embargos\s+protelatórios",
                r"multa\s+por\s+litigância\s+de\s+má-?fé"
            ],
            
            # DANOS E INDENIZAÇÕES (EXPANDIDOS)
            "dano_moral": [
                r"danos?\s+mora(l|is)", r"indeniza[çc][ãa]o\s+por\s+dano\s+moral",
                r"repara[çc][ãa]o\s+por\s+danos?\s+morais", r"abalo\s+moral",
                r"sofrimento\s+moral", r"ofensa\s+[aà]\s+dignidade"
            ],
            
            "dano_material": [
                r"danos?\s+materia(l|is)", r"indeniza[çc][ãa]o\s+por\s+danos?\s+materiais",
                r"ressarcimento\s+de\s+despesas", r"reembolso\s+de\s+gastos",
                r"danos?\s+emergentes?", r"lucros?\s+cessantes?"
            ],
            
            "dano_estetico": [
                r"danos?\s+est[eé]ticos?", r"indeniza[çc][ãa]o\s+por\s+danos?\s+est[eé]ticos?",
                r"altera[çc][ãa]o\s+est[eé]tica", r"deformidade\s+f[ií]sica",
                r"cicatri(z|zes)", r"marca\s+permanente"
            ],
            
            "dano_existencial": [
                r"danos?\s+existencia(l|is)", r"indeniza[çc][ãa]o\s+por\s+danos?\s+existencia(l|is)",
                r"projeto\s+de\s+vida", r"vida\s+de\s+rela[çc][ãa]o"
            ],
            
            "assedio": [
                r"ass[eé]dio\s+mora(l|is)", r"ass[eé]dio\s+sexua(l|is)",
                r"ass[eé]dio\s+processual", r"persegui[çc][ãa]o\s+no\s+trabalho",
                r"press[ãa]o\s+psicol[óo]gica", r"ambiente\s+t[óo]xico"
            ],
            
            # BENEFÍCIOS E ADICIONAIS
            "plano_saude": [
                r"plano\s+de\s+sa[uú]de", r"unimed", r"assist[eê]ncia\s+m[eé]dica",
                r"reintegra[çc][ãa]o\s+a[o]?\s+plano", r"extens[ãa]o\s+do\s+plano",
                r"manuten[çc][ãa]o\s+do\s+plano", r"seguro\s+sa[úu]de",
                r"conv[êe]nio\s+m[ée]dico", r"benef[íi]cio\s+de\s+sa[úu]de",
                # Novos padrões
                r"reembolso\s+(?:de\s+)?plano\s+de\s+sa[uú]de", r"despesas?\s+m[ée]dicas",
                r"gastos\s+(?:com\s+)?sa[uú]de", r"assist[êe]ncia\s+médica\s+hospitalar"
            ],
            
            "horas_extras": [
                r"hora(s)?\s+extra(s)?", r"sobrejornada", r"adicional\s+de\s+horas?",
                r"labor\s+extraordin[áa]rio", r"horas?\s+excedentes?", 
                r"jornada\s+extraordin[aá]ria", r"adicional\s+de\s+50%",
                r"adicional\s+de\s+100%", r"reflexos?\s+de\s+horas?\s+extras?", 
                r"minutos?\s+residuais?",
                # Novos padrões
                r"horas?\s+home\s+office", r"trabalho\s+remoto\s+extraordin[áa]rio",
                r"jornada\s+exaustiva", r"excesso\s+de\s+jornada",
                r"horas?\s+(?:aos|em)\s+s[áa]bados", r"horas?\s+(?:aos|em)\s+domingos"
            ],
            
            "adicional_noturno": [
                r"adicional\s+noturno", r"trabalho\s+noturno", r"hora\s+noturna",
                r"jornada\s+noturna", r"prorroga[çc][ãa]o\s+noturna", 
                r"20%\s+noturno", r"per[íi]odo\s+noturno", r"labor\s+noturno"
            ],
            
            "adicional_periculosidade": [
                r"periculosidade", r"adicional\s+de\s+periculosidade",
                r"trabalho\s+perigoso", r"atividade\s+de\s+risco",
                r"30%\s+de\s+periculosidade", r"atividade\s+perigosa",
                r"energia\s+el[ée]trica", r"combust[íi]veis?", r"explosivos", 
                r"radia[çc][ãa]o\s+ionizante",
                # Novos padrões
                r"30%\s+sobre\s+o\s+sal[áa]rio", r"adicional\s+de\s+30%",
                r"risco\s+de\s+vida", r"NR-16"
            ],
            
            "adicional_insalubridade": [
                r"insalubridade", r"adicional\s+de\s+insalubridade",
                r"trabalho\s+insalubre", r"grau\s+m[áa]ximo", r"grau\s+m[ée]dio", 
                r"grau\s+m[íi]nimo", r"40%\s+de\s+insalubridade",
                r"20%\s+de\s+insalubridade", r"10%\s+de\s+insalubridade", 
                r"agentes?\s+qu[íi]micos?", r"agentes?\s+f[íi]sicos?", 
                r"agentes?\s+biol[óo]gicos?",
                # Novos padrões
                r"laudo\s+pericial\s+de\s+insalubridade", r"NR-15",
                r"per[íi]cia\s+de\s+insalubridade", r"agentes\s+nocivos"
            ],
            
            "outros_adicionais": [
                r"adicional\s+de\s+transfer[êe]ncia", r"adicional\s+de\s+sobreaviso",
                r"adicional\s+de\s+prontid[ãa]o", r"adicional\s+de\s+acúmulo",
                r"adicional\s+de\s+risco", r"adicional\s+de\s+confinamento",
                r"adic\s+de\s+campo", r"adicional\s+de\s+fronteira",
                # Novos padrões
                r"sobreaviso", r"regime\s+de\s+plant[ãa]o", r"1/3\s+do\s+sal[áa]rio-hora",
                r"OJ\s+394", r"disponibilidade\s+(?:ao|para)\s+empregador"
            ],
            
            # INTERVALOS
            "intervalo": [
                r"intervalo(\s+de\s+)?intrajornada", r"intrajornada", 
                r"hora\s+intervalar", r"supressão\s+d[eo]\s+intervalo",
                r"violação\s+d[eo]\s+intervalo", r"não\s+usufruto\s+d[oe]\s+intervalo",
                r"intervalos?\s+(para\s+)?(refeição|descanso|alimentação)",
                r"art\.?\s*71\s*d[a|e]\s*CLT", r"supressão\s+intervalar",
                r"pausas?\s+para\s+alimenta[çc][ãa]o",
                # Novos padrões
                r"ausência\s+de\s+intervalo", r"intervalo\s+para\s+refeição\s+e\s+descanso",
                r"não\s+concess[ãa]o\s+de\s+intervalo", r"sonegação\s+d[oe]\s+intervalo",
                r"hora\s+extra\s+intervalar"
            ],
            
            "intervalo_interjornada": [
                r"intervalo\s+interjornada", r"interjornada", r"entre\s+jornadas",
                r"descanso\s+entre\s+jornadas", r"art\.?\s*66\s*d[a|e]\s*CLT",
                r"onze\s+horas\s+consecutivas", r"11\s+horas\s+de\s+descanso"
            ],
            
            # VERBAS ESPECÍFICAS DE CATEGORIAS E SITUAÇÕES
            "verbas_acidente": [
                r"acidente\s+de\s+trabalho", r"doen[çc]a\s+ocupacional",
                r"les[ãa]o\s+por\s+esfor[çc]o\s+repetitivo", r"LER", r"DORT",
                r"estabilidade\s+acidentária", r"indeniza[çc][ãa]o\s+acidente",
                r"CAT", r"aux[íi]lio-?acidente", r"pens[ãa]o\s+vital[íi]cia",
                r"aux[íi]lio-?doen[çc]a", r"responsabilidade\s+civil\s+acidente",
                # Novos padrões
                r"sequelas\s+permanentes", r"agravamento\s+de\s+doen[çc]a",
                r"afastamento\s+por\s+acidente", r"patologia\s+laboral",
                r"nexo\s+causal", r"adoecimento\s+ocupacional",
                r"perícia\s+médica", r"laudo\s+pericial"
            ],
            
            "reintegracao": [
                r"reintegra[çc][ãa]o", r"estabilidade", r"garantia\s+de\s+emprego",
                r"anula[çc][ãa]o\s+da\s+demiss[ãa]o", r"revers[ãa]o\s+da\s+justa\s+causa",
                r"indeniza[çc][ãa]o\s+substitutiva", r"restitui[çc][ãa]o\s+ao\s+emprego"
            ],
            
            "verbas_gestante": [
                r"estabilidade\s+gestante", r"licen[çc]a-?maternidade",
                r"sal[áa]rio-?maternidade", r"amamenta[çc][ãa]o", 
                r"intervalo\s+para\s+amamenta[çc][ãa]o"
            ],
            
            "verbas_dirigente": [
                r"estabilidade\s+sindical", r"dirigente\s+sindical", 
                r"CIPA\s+estabilidade", r"cipeiro"
            ],
            
            "rescisao_indireta": [
                r"rescis[ãa]o\s+indireta", r"justa\s+causa\s+patronal",
                r"falta\s+grave\s+d[ao]\s+empregador", r"art\.?\s*483",
                # Novos padrões
                r"conduta\s+abusiva\s+do\s+empregador", r"dispensa\s+indireta",
                r"rescis[ãa]o\s+por\s+culpa\s+do\s+empregador", 
                r"abandono\s+de\s+emprego\s+for[çc]ado"
            ],
            
            # OBRIGAÇÕES DE FAZER
            "obrigacoes_documentos": [
                r"anota[çc][ãa]o\s+de\s+CTPS", r"baixa\s+na\s+CTPS", 
                r"retifica[çc][ãa]o\s+de\s+CTPS", r"entrega\s+de\s+guias",
                r"seguro-?desemprego", r"fornecimento\s+de\s+PPP", 
                r"emiss[ãa]o\s+de\s+CAT", r"TRCT", r"chave\s+de\s+conectividade",
                r"c[óo]digo\s+de\s+saque", r"libera[çc][ãa]o\s+de\s+FGTS", 
                r"documento", r"entrega\s+de\s+documentos",
                # Novos padrões
                r"libera[çc][ãa]o\s+da\s+chave", r"guias\s+do\s+FGTS",
                r"comunica[çc][ãa]o\s+de\s+dispensa", r"chave\s+de\s+saque",
                r"registro\s+(?:em|na|de)\s+CTPS"
            ],
            
            # TUTELAS ESPECÍFICAS
            "liminares_tutelas": [
                r"tutela\s+de\s+urg[êe]ncia", r"tutela\s+antecipada", 
                r"liminar", r"obriga[çc][ãa]o\s+de\s+fazer", 
                r"obriga[çc][ãa]o\s+de\s+n[ãa]o\s+fazer", r"medida\s+cautelar",
                # Novos padrões
                r"antecipa[çc][ãa]o\s+de\s+tutela", r"pedido\s+liminar",
                r"determina[çc][ãa]o\s+judicial\s+urgente", r"manuten[çc][ãa]o\s+de\s+plano\s+de\s+sa[úu]de",
                r"reintegra[çc][ãa]o\s+imediata", r"medida\s+de\s+urg[êe]ncia"
            ],
            
            # NOVA CATEGORIA
            "vale_transporte": [
                r"vale(?:\s+|\-)?transporte", r"VT", r"transporte\s+fornecido", 
                r"aux[íi]lio(?:\s+|\-)?transporte", r"reembolso\s+de\s+transporte",
                r"despesas?\s+com\s+transporte", r"custeio\s+de\s+transporte",
                r"lei\s+7.418"
            ]
        }
        
        # Expressões para extração de parâmetros
        self.parametros_patterns = {
            "periodo": r"per[ií]odo\s+(?:de\s+)?([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})\s+a\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
            "data": r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
            "valor_monetario": r"R\$\s*([0-9]+(?:[,.][0-9]{1,2})?)",
            "percentual": r"([0-9]+(?:[,.][0-9]{1,2})?)\s*%",
            "avos": r"([0-9]+)/([0-9]+)\s*(?:avos)?",
            "dias": r"([0-9]+)\s*(?:dias?)"
        }
        
        # Reflexos comuns por tipo de verba
        self.reflexos_por_verba = {
            # Verbas de natureza salarial - com reflexos
            "salario": "FGTS e Multa de 40%",
            "13_salario": "FGTS e Multa de 40%",
            "aviso_previo": "FGTS e Multa de 40%",
            "horas_extras": "FGTS e Multa de 40%",
            "adicional_noturno": "FGTS e Multa de 40%",
            "adicional_periculosidade": "FGTS e Multa de 40%",
            "adicional_insalubridade": "FGTS e Multa de 40%",
            "outros_adicionais": "FGTS e Multa de 40%",
            "intervalo": "FGTS e Multa de 40%",
            "intervalo_interjornada": "FGTS e Multa de 40%",
            "rescisao_indireta": "FGTS e Multa de 40%",
            
            # Verbas específicas
            "fgts": "Multa de 40%",
            
            # Verbas de natureza indenizatória - sem reflexos
            "ferias": "N/A",
            "multa_477": "N/A",
            "multa_467": "N/A",
            "outras_multas": "N/A",
            "dano_moral": "N/A",
            "dano_material": "N/A",
            "dano_estetico": "N/A",
            "dano_existencial": "N/A",
            "assedio": "N/A",
            "plano_saude": "N/A",
            "verbas_acidente": "N/A",
            "reintegracao": "N/A",
            "verbas_gestante": "N/A",
            "verbas_dirigente": "N/A",
            "obrigacoes_documentos": "N/A",
            "liminares_tutelas": "N/A"
        }
        
    def normalizar_texto(self, texto):
        """Normaliza texto removendo acentos e convertendo para minúsculas."""
        if not texto:
            return ""
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
        return texto.lower().strip()
    
    def detectar_verbas(self, texto):
        """Detecta todas as verbas mencionadas no texto com seu contexto."""
        texto_norm = self.normalizar_texto(texto)
        resultado = {}
        
        for categoria, patterns in self.categorias_verbas.items():
            matches = []
            for pattern in patterns:
                for match in re.finditer(pattern, texto_norm):
                    # Captura contexto: 150 caracteres antes e depois da menção
                    inicio = max(0, match.start() - 150)
                    fim = min(len(texto_norm), match.end() + 150)
                    
                    matches.append({
                        "termo": match.group(0),
                        "contexto": texto_norm[inicio:fim],
                        "posicao": match.start()
                    })
            
            if matches:
                resultado[categoria] = matches
                
        return resultado
    
    def extrair_parametros(self, contexto):
        """
        Extrai parâmetros relevantes do contexto de uma verba.
        Retorna dicionário com período, valores, percentuais, etc.
        """
        params = {}
        
        # Aplicar cada padrão e extrair os valores correspondentes
        for param_name, pattern in self.parametros_patterns.items():
            matches = re.findall(pattern, contexto)
            if matches:
                params[param_name] = matches
        
        return params
    
    def identificar_verbas_planilha(self, verbas_planilha):
        """Classifica as verbas da planilha nas categorias padronizadas."""
        categorias = {}
        
        for verba in verbas_planilha:
            nome_verba = self.normalizar_texto(verba.get("verba", ""))
            
            # Encontrar a categoria mais apropriada
            categoria_encontrada = None
            for categoria, patterns in self.categorias_verbas.items():
                if any(re.search(p, nome_verba) for p in patterns):
                    categoria_encontrada = categoria
                    break
            
            if categoria_encontrada:
                if categoria_encontrada not in categorias:
                    categorias[categoria_encontrada] = []
                categorias[categoria_encontrada].append(verba)
        
        return categorias
    
    def calcular_parametros_verba(self, verba, data_admissao, data_demissao, salario_base):
        """
        Calcula os parâmetros apropriados para uma verba com base nos dados do contrato.
        Retorna um dicionário com os parâmetros calculados.
        """
        categoria = None
        nome_verba = self.normalizar_texto(verba)
        
        # Identificar categoria da verba
        for cat, patterns in self.categorias_verbas.items():
            if any(re.search(p, nome_verba) for p in patterns):
                categoria = cat
                break
        
        if not categoria:
            return {"periodo": "N/A", "valor_base": "N/A", "percentual_quantidade": "N/A"}
        
        # Converter datas para objetos datetime
        try:
            dt_admissao = datetime.datetime.strptime(data_admissao, "%d/%m/%Y") if data_admissao else None
            dt_demissao = datetime.datetime.strptime(data_demissao, "%d/%m/%Y") if data_demissao else None
        except ValueError:
            logger.warning(f"Formato de data inválido: {data_admissao} ou {data_demissao}")
            dt_admissao = dt_demissao = None
        
        # Converter salário base para decimal
        try:
            if isinstance(salario_base, str):
                salario_decimal = Decimal(salario_base.replace("R$", "").replace(".", "").replace(",", ".").strip())
            else:
                salario_decimal = Decimal(str(salario_base))
        except (InvalidOperation, TypeError):
            logger.warning(f"Valor de salário inválido: {salario_base}")
            salario_decimal = Decimal("0")
        
        resultado = {
            "valor_base": f"R$ {salario_decimal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if salario_decimal else "N/A"
        }
        
        # Cálculos específicos por categoria
        if categoria == "salario" and dt_demissao:
            # Saldo de salário: dias trabalhados no mês da demissão
            dias_mes = dt_demissao.day
            dias_total = self._dias_no_mes(dt_demissao)
            resultado["periodo"] = f"{dias_mes} dias (mês com {dias_total} dias)"
            resultado["percentual_quantidade"] = f"{dias_mes} dias"
            
        elif categoria == "ferias":
            if "vencida" in nome_verba:
                resultado["periodo"] = "30 dias + 1/3"
                resultado["percentual_quantidade"] = "30 dias"
            elif "proporcion" in nome_verba:
                if dt_admissao and dt_demissao:
                    meses = self._calcular_meses_proporcao(dt_admissao, dt_demissao, 12)
                    resultado["periodo"] = f"{meses}/12 avos + 1/3"
                    resultado["percentual_quantidade"] = f"{meses}/12"
                else:
                    resultado["periodo"] = "Proporcional + 1/3"
            
        elif categoria == "13_salario" and dt_admissao and dt_demissao:
            # 13º salário: meses trabalhados no ano / 12
            meses = self._calcular_meses_proporcao(dt_admissao, dt_demissao, 12)
            resultado["periodo"] = f"{meses}/12 avos"
            resultado["percentual_quantidade"] = f"{meses}/12"
            
        elif categoria == "aviso_previo" and dt_admissao and dt_demissao:
            # Aviso prévio: 30 dias + 3 dias por ano trabalhado
            anos = self._calcular_anos_trabalhados(dt_admissao, dt_demissao)
            dias_adicionais = min(anos * 3, 60)  # Máximo de 90 dias (30 + 60)
            resultado["periodo"] = f"30 dias + {dias_adicionais} dias (proporcional a {anos} anos)"
            resultado["percentual_quantidade"] = f"30 dias"
            
        elif categoria == "fgts":
            resultado["periodo"] = "Depósitos faltantes desde admissão"
            
        elif categoria in ["multa_477", "multa_467", "outras_multas"]:
            if "477" in nome_verba or categoria == "multa_477":
                resultado["periodo"] = "1 salário base"
            elif "467" in nome_verba or categoria == "multa_467":
                resultado["periodo"] = "50% das verbas incontroversas"
        
        # Adicionar reflexos apropriados
        resultado["reflexos"] = self.reflexos_por_verba.get(categoria, "N/A")
        
        return resultado
    
    def _calcular_meses_proporcao(self, dt_inicial, dt_final, periodo_completo=12):
        """Calcula meses proporcionais entre duas datas."""
        if not dt_inicial or not dt_final:
            return periodo_completo
        
        # Cálculo de meses entre as datas
        meses = (dt_final.year - dt_inicial.year) * 12 + dt_final.month - dt_inicial.month
        if dt_final.day < dt_inicial.day:
            meses -= 1
            
        # Limitar ao período completo
        return min(max(meses, 0), periodo_completo)
    
    def _calcular_anos_trabalhados(self, dt_admissao, dt_demissao):
        """Calcula anos completos trabalhados."""
        if not dt_admissao or not dt_demissao:
            return 0
        
        anos = dt_demissao.year - dt_admissao.year
        if dt_demissao.month < dt_admissao.month or (dt_demissao.month == dt_admissao.month and dt_demissao.day < dt_admissao.day):
            anos -= 1
        
        return max(anos, 0)
    
    def _dias_no_mes(self, data):
        """Retorna o número de dias no mês da data fornecida."""
        if data.month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif data.month in [4, 6, 9, 11]:
            return 30
        else:  # Fevereiro
            # Verificação de ano bissexto
            if data.year % 4 == 0 and (data.year % 100 != 0 or data.year % 400 == 0):
                return 29
            return 28
    
    def consultar_regras_calculo(self, categoria_verba):
        """
        Consulta a base de conhecimento (RAG) para obter regras específicas de cálculo.
        Retorna um texto explicativo com as regras aplicáveis.
        """
        consulta = f"Como calcular corretamente a verba trabalhista '{categoria_verba}'? Explique a base legal e a fórmula de cálculo."
        resultado = consultar_rag(consulta)
        return resultado
    
    def gerar_quadro_calculo(self, dados_processo, verbas_detectadas):
        """
        Gera um quadro de cálculo detalhado com todas as verbas detectadas.
        
        Args:
            dados_processo: Dicionário com dados do processo (datas, valores, etc.)
            verbas_detectadas: Verbas identificadas no texto
            
        Returns:
            Lista de dicionários com estrutura formatada para o quadro de cálculo
        """
        quadro = []
        
        # Extrair informações básicas do contrato
        dados_pessoais = dados_processo.get('dados_pessoais', {})
        data_admissao = dados_pessoais.get('data_admissao', '')
        data_demissao = dados_pessoais.get('data_demissao', '')
        salario_base = dados_pessoais.get('ultimo_salario', '')
        
        # Adicionar verbas da petição que não estão na planilha
        verbas_planilha = dados_processo.get('verbas_pleiteadas', [])
        verbas_planilha_nomes = [self.normalizar_texto(v.get('verba', '')) for v in verbas_planilha]
        
        # Processar cada categoria de verba detectada
        for categoria, matches in verbas_detectadas.items():
            # Verificar se a verba já está na planilha
            categoria_na_planilha = False
            for padrao in self.categorias_verbas[categoria]:
                if any(re.search(padrao, nome) for nome in verbas_planilha_nomes):
                    categoria_na_planilha = True
                    break
            
            if not categoria_na_planilha and matches:
                # Nome padronizado da verba baseado na categoria
                nome_padronizado = self._obter_nome_padronizado(categoria)
                
                # Calcular parâmetros apropriados
                parametros = self.calcular_parametros_verba(
                    nome_padronizado, data_admissao, data_demissao, salario_base
                )
                
                # Adicionar ao quadro de cálculo
                quadro.append({
                    'verba': nome_padronizado,
                    'periodo': parametros.get('periodo', ''),
                    'valor_base': parametros.get('valor_base', ''),
                    'percentual_quantidade': parametros.get('percentual_quantidade', ''),
                    'reflexos': parametros.get('reflexos', 'N/A')
                })
        
        return quadro
    
    def _obter_nome_padronizado(self, categoria):
        """Retorna um nome padronizado para a categoria de verba."""
        mapeamento = {
            "salario": "Saldo de Salário",
            "ferias": "Férias Proporcionais",
            "13_salario": "13º Salário Proporcional",
            "aviso_previo": "Aviso Prévio Indenizado",
            "fgts": "Depósitos do FGTS",
            "multa_477": "Multa do art. 477 da CLT",
            "multa_467": "Multa do art. 467 da CLT",
            "outras_multas": "Multas Convencionais/Legais",
            "dano_moral": "Dano Moral",
            "dano_material": "Dano Material",
            "dano_estetico": "Dano Estético",
            "dano_existencial": "Dano Existencial",
            "assedio": "Assédio Moral/Sexual",
            "plano_saude": "Reestabelecimento do Plano de Saúde",
            "horas_extras": "Horas Extras",
            "adicional_noturno": "Adicional Noturno",
            "adicional_periculosidade": "Adicional de Periculosidade",
            "adicional_insalubridade": "Adicional de Insalubridade",
            "outros_adicionais": "Adicionais Diversos",
            "intervalo": "Intervalo Intrajornada",
            "intervalo_interjornada": "Intervalo Interjornada",
            "verbas_acidente": "Verbas por Acidente de Trabalho",
            "reintegracao": "Reintegração ao Emprego",
            "verbas_gestante": "Estabilidade Gestante",
            "verbas_dirigente": "Estabilidade Sindical/CIPA",
            "rescisao_indireta": "Rescisão Indireta",
            "obrigacoes_documentos": "Obrigações Documentais",
            "liminares_tutelas": "Tutelas de Urgência"
        }
        return mapeamento.get(categoria, categoria.replace("_", " ").title())

    def determinar_natureza_reflexos(self, categoria_verba):
        """
        Determina a natureza salarial ou indenizatória da verba e quais reflexos gera.
        
        Args:
            categoria_verba: Categoria da verba ou nome da verba
            
        Returns:
            Dict com informações sobre a natureza e reflexos
        """
        # Verbas de natureza salarial com reflexos FGTS+40%
        verbas_com_reflexos_fgts = {
            "salario", "13_salario", "aviso_previo", 
            "horas_extras", "adicional_noturno", 
            "adicional_periculosidade", "adicional_insalubridade", 
            "outros_adicionais", "intervalo", "intervalo_interjornada",
            "rescisao_indireta"
        }
        
        # Verbas que têm apenas reflexos na multa de 40%
        verbas_com_multa_fgts = {
            "fgts"
        }
        
        # Verificar a categoria
        if categoria_verba in verbas_com_reflexos_fgts:
            return {
                "natureza": "Salarial",
                "reflexo": "FGTS e Multa de 40%",
                "tem_reflexo": True
            }
        elif categoria_verba in verbas_com_multa_fgts:
            return {
                "natureza": "Específica",
                "reflexo": "Multa de 40%",
                "tem_reflexo": True
            }
        else:
            return {
                "natureza": "Indenizatória",
                "reflexo": "N/A",
                "tem_reflexo": False
            }


class CorrelacaoParcialMixin:
    """
    Mixin que implementa sistema de pontuação para correspondências parciais
    entre verbas mencionadas na petição e verbas da planilha.
    """
    
    def __init__(self):
        # Carregar stopwords do português
        if NLTK_DISPONIVEL:
            try:
                self.stopwords = set(stopwords.words('portuguese'))
            except:
                # Fallback se nltk não estiver configurado
                self.stopwords = set(['a', 'o', 'e', 'de', 'da', 'do', 'em', 'para', 'por', 'com'])
        else:
            # Stopwords básicas se NLTK não estiver disponível
            self.stopwords = set(['a', 'o', 'e', 'de', 'da', 'do', 'em', 'para', 'por', 'com', 'um', 'uma', 'os', 'as'])
        
        # Caracteres a remover ao normalizar textos para comparação
        self.chars_to_remove = '.,;:!?()[]{}"\'-_°º ª'
        
        # Palavras-chave importantes que não devem ser ignoradas mesmo sendo stopwords
        self.keywords_importantes = {'não', 'sobre', 'sem', 'com'}
        
        # Dicionário de sinônimos para termos jurídicos trabalhistas
        self.sinonimos = {
            'rescisão': ['rescisório', 'demissão', 'despedida', 'dispensa'],
            'indenização': ['ressarcimento', 'reparação', 'compensação'],
            'aviso': ['pré-aviso', 'comunicação prévia'],
            'verbas': ['parcelas', 'valores', 'importâncias'],
            'férias': ['descanso anual'],
            'horas extras': ['sobrejornada', 'labor extraordinário', 'jornada suplementar'],
            'dano moral': ['abalo moral', 'sofrimento moral'],
            'insalubridade': ['ambiente insalubre', 'condição insalubre'],
            'periculosidade': ['risco', 'perigo', 'atividade perigosa'],
            'intervalo': ['descanso', 'pausa', 'intrajornada'],
            'multa': ['penalidade', 'sanção']
        }
        
        # Limiares de pontuação para correspondências
        self.limiar_correspondencia_forte = 0.75
        self.limiar_correspondencia_provavel = 0.60
        self.limiar_correspondencia_possivel = 0.45
    
    def normalizar_para_comparacao(self, texto):
        """
        Normaliza texto para comparação, removendo acentos,
        caracteres especiais e stopwords menos significativas.
        """
        if not texto:
            return ""
            
        # Normalização básica (minúsculas, sem acentos)
        texto_norm = self.normalizar_texto(texto)
        
        # Remover pontuação
        for char in self.chars_to_remove:
            texto_norm = texto_norm.replace(char, ' ')
        
        # Tokenizar
        if NLTK_DISPONIVEL:
            try:
                tokens = word_tokenize(texto_norm, language='portuguese')
            except:
                # Fallback simples se nltk falhar
                tokens = texto_norm.split()
        else:
            tokens = texto_norm.split()
        
        # Remover stopwords, mas manter palavras-chave importantes
        tokens_filtrados = [token for token in tokens if 
                           token not in self.stopwords or 
                           token in self.keywords_importantes]
        
        return ' '.join(tokens_filtrados)
    
    def expandir_sinonimos(self, termos):
        """
        Expande os termos com seus sinônimos conhecidos
        para melhorar a chance de correspondência.
        """
        expandido = set(termos.split())
        
        for termo in termos.split():
            # Verifica cada palavra do termo contra o dicionário de sinônimos
            for palavra_chave, sinonimos in self.sinonimos.items():
                if palavra_chave in termo:
                    for sinonimo in sinonimos:
                        # Adiciona termos expandidos substituindo a palavra-chave pelo sinônimo
                        novo_termo = termo.replace(palavra_chave, sinonimo)
                        expandido.add(novo_termo)
                        
        return ' '.join(expandido)
    
    def calcular_similaridade(self, texto1, texto2):
        """
        Calcula similaridade entre dois textos usando múltiplos métodos
        e retorna uma pontuação composta.
        """
        # Normalizar os textos
        texto1_norm = self.normalizar_para_comparacao(texto1)
        texto2_norm = self.normalizar_para_comparacao(texto2)
        
        # Método 1: Difflib sequence matcher
        similaridade_sequencia = difflib.SequenceMatcher(None, texto1_norm, texto2_norm).ratio()
        
        # Método 2: Sobreposição de tokens
        tokens1 = set(texto1_norm.split())
        tokens2 = set(texto2_norm.split())
        
        # Expandir com sinônimos
        tokens1_expandido = set(self.expandir_sinonimos(texto1_norm).split())
        tokens2_expandido = set(self.expandir_sinonimos(texto2_norm).split())
        
        # Calcular interseção e união
        intersecao = len(tokens1.intersection(tokens2))
        intersecao_expandida = len(tokens1_expandido.intersection(tokens2_expandido))
        uniao = len(tokens1.union(tokens2))
        
        # Evitar divisão por zero
        if uniao == 0:
            similaridade_tokens = 0
            similaridade_tokens_expandida = 0
        else:
            similaridade_tokens = intersecao / uniao
            similaridade_tokens_expandida = intersecao_expandida / len(tokens1_expandido.union(tokens2_expandido))
        
        # Método 3: Presença de termos-chave específicos (números de artigos, siglas, etc.)
        padrao_artigos = re.compile(r'art\.?\s*\d+|4[67][0-9]|13[ºo]')
        artigos1 = bool(padrao_artigos.search(texto1))
        artigos2 = bool(padrao_artigos.search(texto2))
        bonus_artigos = 0.15 if artigos1 and artigos2 else 0
        
        # Composição ponderada da pontuação final
        pontuacao = (
            0.3 * similaridade_sequencia + 
            0.3 * similaridade_tokens +
            0.3 * similaridade_tokens_expandida +
            bonus_artigos
        )
        
        return min(1.0, pontuacao)  # Garantir que não exceda 1.0
    
    def correlacionar_verbas(self, verbas_texto, verbas_planilha):
        """
        Correlaciona verbas detectadas no texto com verbas da planilha
        usando o sistema de pontuação para identificar correspondências parciais.
        
        Args:
            verbas_texto: Lista de verbas detectadas no texto
            verbas_planilha: Lista de verbas na planilha
            
        Returns:
            Dict com correspondências classificadas como fortes, prováveis e possíveis
        """
        resultados = {
            "correspondencias_fortes": [],      # Quase certeza de que são as mesmas verbas
            "correspondencias_provaveis": [],   # Provavelmente são as mesmas verbas
            "correspondencias_possiveis": [],   # Possivelmente relacionadas
            "sem_correspondencia": []           # Sem correspondência encontrada
        }
        
        # Para cada verba do texto, buscar correspondências na planilha
        for verba_texto in verbas_texto:
            melhor_pontuacao = 0
            melhor_correspondencia = None
            
            for verba_planilha in verbas_planilha:
                pontuacao = self.calcular_similaridade(
                    verba_texto.get("verba", ""),
                    verba_planilha.get("verba", "")
                )
                
                if pontuacao > melhor_pontuacao:
                    melhor_pontuacao = pontuacao
                    melhor_correspondencia = {
                        "verba_texto": verba_texto,
                        "verba_planilha": verba_planilha,
                        "pontuacao": pontuacao
                    }
            
            # Classificar a correspondência com base na pontuação
            if melhor_pontuacao >= self.limiar_correspondencia_forte:
                resultados["correspondencias_fortes"].append(melhor_correspondencia)
            elif melhor_pontuacao >= self.limiar_correspondencia_provavel:
                resultados["correspondencias_provaveis"].append(melhor_correspondencia)
            elif melhor_pontuacao >= self.limiar_correspondencia_possivel:
                resultados["correspondencias_possiveis"].append(melhor_correspondencia)
            else:
                resultados["sem_correspondencia"].append({
                    "verba_texto": verba_texto,
                    "pontuacao_maxima": melhor_pontuacao
                })
        
        return resultados

    def verificar_desmembramentos_reflexos(self, verbas_planilha):
        """
        Verifica se há verbas na planilha que são reflexos desmembrados
        de verbas principais. Isso ajuda a entender por que certas verbas
        aparecem na planilha mas não no texto.
        
        Args:
            verbas_planilha: Lista de verbas na planilha
        
        Returns:
            Dict: Mapeamento de verbas reflexas para suas verbas principais
        """
        desmembramentos = {}
        
        # Padrões para identificar reflexos
        padrao_reflexos = re.compile(r'reflexo|repercuss[aã]o|sobre|incid[eê]ncia|em|integra[cç][aã]o')
        
        for verba in verbas_planilha:
            nome_verba = verba.get("verba", "").lower()
            
            # Verifica se contém padrão de reflexo
            if padrao_reflexos.search(nome_verba):
                # Tenta identificar a verba principal
                for outra_verba in verbas_planilha:
                    nome_outra = outra_verba.get("verba", "").lower()
                    
                    # Evita comparar com ela mesma
                    if nome_outra == nome_verba:
                        continue
                    
                    # Se a verba atual menciona a outra verba, provavelmente é um reflexo dela
                    if nome_outra in nome_verba or self.calcular_similaridade(nome_outra, nome_verba) > 0.4:
                        if nome_verba not in desmembramentos:
                            desmembramentos[nome_verba] = []
                        desmembramentos[nome_verba].append(nome_outra)
        
        return desmembramentos


class AnalisadorVerbasAvancado(AnalisadorVerbasInteligente, CorrelacaoParcialMixin):
    """
    Versão avançada do analisador de verbas que incorpora
    o sistema de pontuação para correlações parciais.
    """
    
    def __init__(self):
        AnalisadorVerbasInteligente.__init__(self)
        CorrelacaoParcialMixin.__init__(self)
    
    def analisar_processo_avancado(self, texto_peticao, dados_planilha):
        """
        Versão avançada da análise de processo.
        
        Args:
            texto_peticao: Texto da petição inicial
            dados_planilha: Dados da planilha com verbas pleiteadas
        
        Returns:
            str: Relatório formatado com a análise detalhada
        """
        # Detectar verbas no texto
        verbas_detectadas = self.detectar_verbas(texto_peticao)
        
        # Transformar categorias detectadas em lista de verbas
        verbas_texto = []
        for categoria, matches in verbas_detectadas.items():
            nome_padronizado = self._obter_nome_padronizado(categoria)
            verbas_texto.append({
                "verba": nome_padronizado,
                "categoria": categoria,
                "matches": matches
            })
        
        # Obter verbas da planilha
        verbas_planilha = []
        for aba in ["Verbas Resumidas", "Verbas Detalhadas"]:
            for item in dados_planilha.get(aba, []):
                if isinstance(item, dict) and "verba" in item:
                    verbas_planilha.append(item)
        
        # 1. Correlacionar verbas usando o sistema de pontuação padrão
        correlacoes = self.correlacionar_verbas(verbas_texto, verbas_planilha)
        
        # 2. Adicionar correlações por dicionário de sinônimos
        correspondencias_dicionario = []
        if hasattr(self, 'correspondencia_por_dicionario'):
            for verba_texto in verbas_texto:
                # Verificar se já tem correspondência forte
                if not any(cor["verba_texto"]["verba"] == verba_texto["verba"] 
                        for cor in correlacoes["correspondencias_fortes"]):
                    # Buscar correspondências por dicionário
                    novas_correspondencias = self.correspondencia_por_dicionario(verba_texto, verbas_planilha)
                    correspondencias_dicionario.extend(novas_correspondencias)
        
        # 3. Adicionar correspondências do dicionário às fortes
        for corr in correspondencias_dicionario:
            # Verificar se a verba já tem alguma correspondência forte
            if not any(c["verba_texto"]["verba"] == corr["verba_texto"]["verba"] 
                    for c in correlacoes["correspondencias_fortes"]):
                correlacoes["correspondencias_fortes"].append(corr)
                
                # Remover das sem correspondência
                for i, sem_corr in enumerate(correlacoes["sem_correspondencia"]):
                    if sem_corr["verba_texto"]["verba"] == corr["verba_texto"]["verba"]:
                        correlacoes["sem_correspondencia"].pop(i)
                        break
        
        # Verificar desmembramentos de reflexos
        desmembramentos = self.verificar_desmembramentos_reflexos(verbas_planilha)
        
        # 4. Verbas adicionais na planilha
        verbas_texto_nomes = [item["verba"] for item in verbas_texto]
        verbas_adicionais = []
        
        for verba_planilha in verbas_planilha:
            nome_verba = verba_planilha.get("verba", "")
            # Verificar se esta verba está entre as correspondências encontradas
            encontrada = False
            
            # Verificar em todas as correspondências
            for tipo in ["correspondencias_fortes", "correspondencias_provaveis", "correspondencias_possiveis"]:
                if any(item["verba_planilha"].get("verba") == nome_verba for item in correlacoes[tipo]):
                    encontrada = True
                    break
                    
            # Verificar se é um reflexo desmembrado
            if self.normalizar_texto(nome_verba) in desmembramentos:
                encontrada = True
            
            if not encontrada:
                verbas_adicionais.append(nome_verba)
        
        # Gerar relatório detalhado como antes
        relatorio = []
        relatorio.append("# 📊 RELATÓRIO AVANÇADO DE ANÁLISE DE VERBAS TRABALHISTAS\n")
        
        # 1. Verbas com correspondência forte
        relatorio.append("## ✅ Verbas Corretas (presentes na planilha e na petição)\n")
        if correlacoes["correspondencias_fortes"]:
            for item in correlacoes["correspondencias_fortes"]:
                verba_texto = item["verba_texto"]["verba"]
                verba_planilha = item["verba_planilha"]["verba"]
                via_dic = item.get("via_dicionario", False)
                
                if via_dic:
                    relatorio.append(f"* **{verba_texto}** ↔ **{verba_planilha}** *(via dicionário de sinônimos)*\n")
                else:
                    relatorio.append(f"* **{verba_planilha}**\n")
        else:
            relatorio.append("* Nenhuma correspondência forte encontrada\n")
        
        # 2. Verbas com nomenclatura diferente
        relatorio.append("\n## 🟨 Verbas com Nomenclatura Ligeiramente Diferente\n")
        if correlacoes["correspondencias_provaveis"]:
            for item in correlacoes["correspondencias_provaveis"]:
                verba_texto = item["verba_texto"]["verba"]
                verba_planilha = item["verba_planilha"]["verba"]
                pontuacao = item["pontuacao"] * 100
                relatorio.append(f"* **Na petição:** '{verba_texto}' ↔ **Na planilha:** '{verba_planilha}' (Similaridade: {pontuacao:.1f}%)\n")
        else:
            relatorio.append("* Nenhuma correspondência provável encontrada\n")
        
        # 3. Verbas sem correspondência (faltando na planilha)
        relatorio.append("\n## ❌ Verbas Pleiteadas, mas Faltando na Planilha\n")
        relatorio.append("Essas verbas foram claramente solicitadas na ação, mas não constam como título principal:\n\n")
        verbas_sem_correspondencia = [item["verba_texto"]["verba"] for item in correlacoes["sem_correspondencia"]]
        
        if verbas_sem_correspondencia:
            for verba in verbas_sem_correspondencia:
                relatorio.append(f"* **{verba}**\n")
        else:
            relatorio.append("* Todas as verbas da petição foram encontradas na planilha\n")
        
        # 4. Verbas adicionais na planilha
        if verbas_adicionais:
            relatorio.append("\n## ⚠️ Verbas Adicionais ou com Nomenclatura Diferente\n")
            relatorio.append("Essas verbas aparecem na planilha, mas não foram identificadas com certeza na petição inicial. Podem ser:\n\n")
            relatorio.append("* Reflexos técnicos\n* Desmembramentos\n* Compensações automáticas\n* Verbas com nomenclatura muito diferente\n\n")
            
            for verba in verbas_adicionais:
                relatorio.append(f"* **{verba}**\n")
        
        # 5. Recomendações
        relatorio.append("\n## 🔍 Recomendações Inteligentes\n")
        
        if correlacoes["sem_correspondencia"]:
            relatorio.append("1. **Adicione as verbas ausentes** na aba 'Verbas Resumidas' para garantir conformidade com a petição.\n")
        
        if correlacoes["correspondencias_provaveis"] or correlacoes["correspondencias_possiveis"]:
            relatorio.append("2. **Revise as nomenclaturas divergentes** para garantir correspondência exata com a petição inicial.\n")
        
        if verbas_adicionais:
            relatorio.append("3. **Verifique as verbas adicionais** e confirme se são desmembramentos de verbas principais ou reflexos.\n")
        
        relatorio.append("4. **Padronize os termos** entre a petição e a planilha para garantir análises automáticas mais precisas.\n")
        
        return "\n".join(relatorio)

def mapear_verbas_trabalhistas(texto_peticao, verbas_planilha):
    """
    Função legada mantida para compatibilidade.
    Agora usa o novo AnalisadorVerbasInteligente.
    """
    analisador = AnalisadorVerbasInteligente()
    verbas_detectadas = analisador.detectar_verbas(texto_peticao)
    verbas_categorizadas = analisador.identificar_verbas_planilha(verbas_planilha)
    
    # Mapear para o formato de retorno original
    resultado = {
        "presentes": [],
        "ausentes": [],
        "nomenclatura_diferente": []
    }
    
    # Processar verbas presentes e ausentes
    for categoria, matches in verbas_detectadas.items():
        nome_padronizado = analisador._obter_nome_padronizado(categoria)
        
        # Verificar se existe na planilha
        if categoria in verbas_categorizadas:
            for verba in verbas_categorizadas[categoria]:
                resultado["presentes"].append({
                    "nome_original": verba.get("verba", ""),
                    "nome_normalizado": nome_padronizado
                })
        else:
            resultado["ausentes"].append(nome_padronizado)
    
    # Processar verbas com nomenclatura diferente
    for categoria, verbas in verbas_categorizadas.items():
        if categoria not in verbas_detectadas and verbas:
            for verba in verbas:
                resultado["nomenclatura_diferente"].append(verba.get("verba", ""))
    
    return resultado


def analisar_processo_trabalhista(texto_peticao, dados_planilha):
    """
    Analisa inteligentemente um processo trabalhista, comparando a petição com a planilha.
    Usa o sistema avançado de correlação parcial e dicionário de sinônimos.
    
    Parâmetros:
        texto_peticao (str): Texto completo da petição inicial
        dados_planilha (dict): Dados extraídos da planilha Excel com todas as abas
        
    Retorna:
        str: Relatório detalhado da análise
    """
    # Instanciar o analisador avançado
    analisador = AnalisadorVerbasAvancado()
    
    # Aplicar melhorias aos padrões de detecção
    analisador = aprimorar_padroes_verbas(analisador)
    
    # Aplicar o dicionário de sinônimos
    analisador = implementar_dicionario_verbas(analisador)
    
    # Usar diretamente o método da classe
    resultado = analisador.analisar_processo_avancado(texto_peticao, dados_planilha)
    
    # Retornar a string formatada
    return resultado

def gerar_quadro_calculo_completo(texto_processo, dados_processo):
    """
    Função principal para gerar um quadro de cálculo completo com reflexos corretos.
    
    Args:
        texto_processo: Texto completo do processo
        dados_processo: Dados extraídos do processo
        
    Returns:
        List[Dict]: Lista de verbas com parâmetros calculados
    """
    analisador = AnalisadorVerbasAvancado()
    
    # Aplicar melhorias aos padrões de detecção
    analisador = aprimorar_padroes_verbas(analisador)
    
    # 1. Detectar verbas no texto
    verbas_detectadas = analisador.detectar_verbas(texto_processo)
    
    # 2. Obter verbas já existentes na planilha
    verbas_existentes = dados_processo.get('verbas_pleiteadas', [])
    
    # 3. Gerar quadro de cálculo com verbas detectadas mas ausentes na planilha
    quadro_verbas_ausentes = analisador.gerar_quadro_calculo(dados_processo, verbas_detectadas)
    
    # 4. Juntar com as verbas existentes
    quadro_final = verbas_existentes.copy()
    
    # Adicionar apenas verbas não duplicadas
    verbas_existentes_nomes = [v.get('verba', '').lower() for v in verbas_existentes]
    for verba in quadro_verbas_ausentes:
        if verba['verba'].lower() not in verbas_existentes_nomes:
            quadro_final.append(verba)
    
    # 5. Verificar e ajustar reflexos para todas as verbas
    for i, verba in enumerate(quadro_final):
        nome_verba = verba.get('verba', '').lower()
        
        # Encontrar a categoria da verba
        categoria = None
        for cat, patterns in analisador.categorias_verbas.items():
            nome_norm = analisador.normalizar_texto(nome_verba)
            if any(re.search(pattern, nome_norm) for pattern in patterns):
                categoria = cat
                break
        
        # Determinar reflexos conforme a natureza da verba
        if categoria:
            info_reflexo = analisador.determinar_natureza_reflexos(categoria)
            quadro_final[i]['reflexos'] = info_reflexo["reflexo"]
    
    # Adicionar seção para pedidos processuais/obrigações de fazer
    pedidos_processuais = []
    categorias_especiais = ['obrigacoes_documentos', 'liminares_tutelas', 'plano_saude']
    for categoria in categorias_especiais:
        if categoria in verbas_detectadas and verbas_detectadas[categoria]:
            nome_padronizado = analisador._obter_nome_padronizado(categoria)
            pedidos_processuais.append({
                'verba': nome_padronizado,
                'periodo': 'Pedido processual - não calculável',
                'valor_base': 'N/A',
                'percentual_quantidade': 'N/A',
                'reflexos': 'N/A'
            })

    # Adicionar à lista final
    quadro_final.extend(pedidos_processuais)
    
    return quadro_final

# Adicione esta função ao arquivo analise_verbas.py
def gerar_resumo_pjecalc(dados_processo, resultado_analise):
    """
    Gera o resumo completo para o PJE-CALC com todas as seções necessárias.
    
    Args:
        dados_processo: Dicionário com os dados do processo
        resultado_analise: Resultado da análise de verbas
        
    Returns:
        Dict: Estrutura completa do resumo PJE-CALC
    """
    resumo = {
        "Análise Concluída": {
            "status": "Concluído",
            "data": datetime.datetime.now().strftime("%d/%m/%Y"),
            "observações": "Análise realizada com sucesso"
        },
        "Observações Gerais e Resumo do Processo": {
            "número_processo": dados_processo.get("numero_processo", ""),
            "vara": dados_processo.get("vara", ""),
            "reclamante": dados_processo.get("reclamante", ""),
            "reclamada": dados_processo.get("reclamada", ""),
            "resumo_pleitos": "Verbas rescisórias, horas extras, danos morais e outras verbas trabalhistas"
        },
        "Verbas Pleiteadas (Petição Inicial)": {
            "verbas": [v.get("verba", "") for v in dados_processo.get("verbas_pleiteadas", [])]
        },
        "Atualização Monetária e Parâmetros": {
            "índice": dados_processo.get("parametros_calculo", {}).get("indice", "IPCA-E + 1% a.m."),
            "termo_inicial": dados_processo.get("parametros_calculo", {}).get("termo_inicial", "Data da exigibilidade"),
            "juros": dados_processo.get("parametros_calculo", {}).get("juros", "1% a.m., simples"),
            "termo_final": "Data do efetivo pagamento"
        },
        "Revisão Final – Quadro para Cálculo": {
            "verbas_calculadas": [
                {
                    "verba": v.get("verba", ""),
                    "valor": v.get("valor_calculado", "A calcular"),
                    "periodo": v.get("periodo", ""),
                    "base_calculo": v.get("valor_base", "")
                } for v in dados_processo.get("verbas_pleiteadas", [])
            ]
        },
        "Modelo Laudo Técnico para Pje-Calc": {
            "blocos": "Blocos de 1 a 5 conforme especificação PJE-CALC"
        },
        "Dados Pessoais e Contratuais": dados_processo.get("dados_pessoais", {}),
        "Informações para Preenchimento no Pje-Calc": {
            "data_admissao": dados_processo.get("dados_pessoais", {}).get("data_admissao", ""),
            "data_demissao": dados_processo.get("dados_pessoais", {}).get("data_demissao", ""),
            "ultimo_salario": dados_processo.get("dados_pessoais", {}).get("ultimo_salario", ""),
            "funcao": dados_processo.get("dados_pessoais", {}).get("funcao", "")
        },
        "Resultado Final da Liquidação": {
            "valor_principal": dados_processo.get("resultado_calculo", {}).get("valor_principal", "A calcular"),
            "juros": dados_processo.get("resultado_calculo", {}).get("juros", "A calcular"),
            "correcao": dados_processo.get("resultado_calculo", {}).get("correcao", "A calcular"),
            "valor_total": dados_processo.get("resultado_calculo", {}).get("valor_total", "A calcular"),
            "data_atualizacao": datetime.datetime.now().strftime("%d/%m/%Y")
        }
    }
    
    return resumo

def analisar_processo_avancado(analisador, texto_peticao, dados_planilha):
    """
    Versão avançada da análise de processo como função auxiliar.
    
    Args:
        analisador: Instância de AnalisadorVerbasAvancado
        texto_peticao: Texto da petição inicial
        dados_planilha: Dados da planilha com verbas pleiteadas
    
    Returns:
        Dict com resultado detalhado da análise
    """
    # Detectar verbas no texto
    verbas_detectadas = analisador.detectar_verbas(texto_peticao)
    
    # Transformar categorias detectadas em lista de verbas
    verbas_texto = []
    for categoria, matches in verbas_detectadas.items():
        nome_padronizado = analisador._obter_nome_padronizado(categoria)
        verbas_texto.append({
            "verba": nome_padronizado,
            "categoria": categoria,
            "matches": matches
        })
    
    # Obter verbas da planilha
    verbas_planilha = []
    for aba in ["Verbas Resumidas", "Verbas Detalhadas"]:
        for item in dados_planilha.get(aba, []):
            if isinstance(item, dict) and "verba" in item:
                verbas_planilha.append(item)
    
    # 1. Correlacionar verbas usando o sistema de pontuação padrão
    correlacoes = analisador.correlacionar_verbas(verbas_texto, verbas_planilha)
    
    # 2. Adicionar correlações por dicionário de sinônimos
    correspondencias_dicionario = []
    if hasattr(analisador, 'correspondencia_por_dicionario'):
        for verba_texto in verbas_texto:
            # Verificar se já tem correspondência forte
            if not any(cor.get("verba_texto", {}).get("verba") == verba_texto["verba"] 
                    for cor in correlacoes["correspondencias_fortes"]):
                # Buscar correspondências por dicionário
                novas_correspondencias = analisador.correspondencia_por_dicionario(verba_texto, verbas_planilha)
                correspondencias_dicionario.extend(novas_correspondencias)
    
    # 3. Adicionar correspondências do dicionário às fortes
    for corr in correspondencias_dicionario:
        # Verificar se a verba já tem alguma correspondência forte
        if not any(c.get("verba_texto", {}).get("verba") == corr["verba_texto"]["verba"] 
                for c in correlacoes["correspondencias_fortes"]):
            correlacoes["correspondencias_fortes"].append(corr)
            
            # Remover das sem correspondência
            for i, sem_corr in enumerate(correlacoes["sem_correspondencia"]):
                if sem_corr["verba_texto"]["verba"] == corr["verba_texto"]["verba"]:
                    correlacoes["sem_correspondencia"].pop(i)
                    break
    
    # Verificar desmembramentos de reflexos
    desmembramentos = analisador.verificar_desmembramentos_reflexos(verbas_planilha)
    
    # 4. Verbas adicionais na planilha
    verbas_adicionais = []
    
    for verba_planilha in verbas_planilha:
        nome_verba = verba_planilha.get("verba", "")
        # Verificar se esta verba está entre as correspondências encontradas
        encontrada = False
        
        # Verificar em todas as correspondências
        for tipo in ["correspondencias_fortes", "correspondencias_provaveis", "correspondencias_possiveis"]:
            if any(item.get("verba_planilha", {}).get("verba") == nome_verba for item in correlacoes[tipo]):
                encontrada = True
                break
                
        # Verificar se é um reflexo desmembrado
        if analisador.normalizar_texto(nome_verba) in desmembramentos:
            encontrada = True
        
        if not encontrada:
            verbas_adicionais.append(nome_verba)
    
    # Retornar resultado estruturado
    return {
        "verbas_detectadas": verbas_detectadas,
        "verbas_texto": verbas_texto, 
        "verbas_planilha": verbas_planilha,
        "correlacoes": correlacoes,
        "verbas_adicionais": verbas_adicionais,
        "desmembramentos": desmembramentos
    }

def gerar_resumo_pjecalc_formatado(dados_processo):
    """
    Gera um resumo formatado para o PJE-CALC no formato esperado pela interface.
    
    Args:
        dados_processo: Dicionário com dados do processo
        
    Returns:
        str: Texto formatado para exibição no resumo PJE-CALC
    """
    # Extrair dados importantes
    dados_pessoais = dados_processo.get("dados_pessoais", {})
    verbas_pleiteadas = dados_processo.get("verbas_pleiteadas", [])
    parametros = dados_processo.get("parametros_calculo", {})
    
    # Formatar verbas pleiteadas para exibição
    verbas_str = ", ".join([v.get("verba", "") for v in verbas_pleiteadas[:5]])
    if len(verbas_pleiteadas) > 5:
        verbas_str += ", entre outras"
    
    # Construir texto formatado
    resumo = []
    
    # Seção: Verbas Pleiteadas
    resumo.append("✅ Verbas Pleiteadas (Petição Inicial)\n")
    resumo.append(f"Verbas Rescisórias: {verbas_str}")
    
    # Encontrar valores específicos nas verbas existentes
    multa_477_verba = next((v for v in verbas_pleiteadas if "477" in v.get("verba", "")), None)
    multa_477 = multa_477_verba.get("periodo", "1 salário base") if multa_477_verba else "1 salário base"
    
    multa_467_verba = next((v for v in verbas_pleiteadas if "467" in v.get("verba", "")), None)
    multa_467 = multa_467_verba.get("periodo", "50% das verbas incontroversas") if multa_467_verba else "50% das verbas incontroversas"
    
    fgts_verba = next((v for v in verbas_pleiteadas if "FGTS" in v.get("verba", "")), None)
    fgts = fgts_verba.get("periodo", "Depósitos faltantes desde admissão") if fgts_verba else "Depósitos faltantes desde admissão"
    
    dano_moral_verba = next((v for v in verbas_pleiteadas if "Dano Moral" in v.get("verba", "")), None)
    dano_moral = dano_moral_verba.get("periodo", "Valor a apurar") if dano_moral_verba else "Valor a apurar"
    
    # Adicionar detalhes de multas e outros valores específicos com valores reais
    resumo.append(f"Multa Art. 477 CLT (motivo): {multa_477}")
    resumo.append(f"Multa Art. 467 CLT (motivo): {multa_467}")
    resumo.append(f"FGTS + 40% (motivo): {fgts}")
    resumo.append(f"Dano Moral (valor e fundamento): {dano_moral}")
    resumo.append(f"Honorários Advocatícios (percentual): 15%")
    
    # Seção: Atualização Monetária
    resumo.append("\n✅ Atualização Monetária e Parâmetros\n")
    resumo.append(f"Índice Monetário (com período): {parametros.get('indice', 'IPCA-E + 1% a.m.')}")
    resumo.append(f"Juros de Mora (tipo e marco): {parametros.get('juros', '1% a.m., simples')}")
    resumo.append(f"INSS – Terceiros (percentual): {parametros.get('inss', '0%')}")
    
    # Seção: Quadro para Cálculo
    resumo.append("\n✅ Revisão Final – Quadro para Cálculo\n")
    resumo.append("Verba\tParâmetro\tReflexos")
    
    # Gerar linhas para cada verba usando os valores reais do objeto
    for verba in verbas_pleiteadas:
        nome = verba.get("verba", "")
        parametro = verba.get("periodo", "")  # Usa o valor real sem fallback para [NÃO INFORMADO]
        reflexos = verba.get("reflexos", "N/A")
        resumo.append(f"{nome}\t{parametro}\t{reflexos}")
    
    # Seções adicionais
    resumo.append("\n✅ Modelo Laudo Técnico para PJe-Calc (com BLOCOS 1 a 5)\n")
    resumo.append("BLOCO 1 – Dados Cadastrais (todos os itens): Reclamante, Reclamado, Período Contratual")
    resumo.append(f"BLOCO 2 – Afastamentos (períodos e motivos): {dados_pessoais.get('afastamentos', 'Nenhum afastamento registrado')}")
    resumo.append("BLOCO 3 – Verbas a Apurar (tabela de configuração): Configurado conforme quadro de cálculo acima")
    resumo.append("BLOCO 4 – Honorários / Custas / Encargos: Honorários: 15%, Custas: Base de cálculo")
    resumo.append("BLOCO 5 – Liquidação e Impressão: Resumo com valores brutos, descontos e líquidos")
    
    # Adicionar timestamp de processamento
    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resumo.append(f"Processado por am-axia-br em {data_atual} UTC.")
    
    return "\n".join(resumo)

def gerar_dados_pjecalc(dados_processo):
    """
    Gera dados formatados para a aba RESUMO PJE-CALC.
    
    Args:
        dados_processo: Dicionário com dados do processo
        
    Returns:
        dict: Dados formatados para cada seção do resumo
    """
    # Extrair dados importantes
    dados_pessoais = dados_processo.get("dados_pessoais", {})
    verbas_pleiteadas = dados_processo.get("verbas_pleiteadas", [])
    parametros = dados_processo.get("parametros_calculo", {})
    
    # Estruturar os dados para cada seção diretamente, sem depender do split
    dados_resumo = {
        "Análise Concluída": "Análise realizada com sucesso em " + datetime.datetime.now().strftime("%d/%m/%Y"),
        
        "Observações Gerais e Resumo do Processo": 
            f"Processo: {dados_processo.get('numero_processo', 'N/A')}\n" +
            f"Reclamante: {dados_processo.get('reclamante', 'N/A')}\n" +
            f"Reclamada: {dados_processo.get('reclamada', 'N/A')}\n" +
            f"Período contratual: {dados_pessoais.get('data_admissao', 'N/A')} a {dados_pessoais.get('data_demissao', 'N/A')}",
        
        "Verbas Pleiteadas (Petição Inicial)": 
            "Verbas identificadas na petição inicial:\n" +
            "\n".join([f"• {v.get('verba', '')}" for v in verbas_pleiteadas]),
        
        "Atualização Monetária e Parâmetros": 
            f"Índice Monetário: {parametros.get('indice', 'IPCA-E + 1% a.m.')}\n" +
            f"Juros de Mora: {parametros.get('juros', '1% a.m., simples')}\n" +
            f"INSS – Terceiros: {parametros.get('inss', '0%')}",
        
        "Revisão Final – Quadro para Cálculo": 
            "Verba | Parâmetro | Reflexos\n" +
            "\n".join([f"{v.get('verba', '')} | {v.get('periodo', '')} | {v.get('reflexos', 'N/A')}" for v in verbas_pleiteadas]),
        
        "Modelo Laudo Técnico para Pje-Calc (com BLOCOS 1 a 5)": 
            "BLOCO 1 – Dados Cadastrais: Reclamante, Reclamado, Período\n" +
            "BLOCO 2 – Afastamentos: Períodos documentados\n" +
            "BLOCO 3 – Verbas a Apurar: Conforme quadro de cálculo\n" +
            "BLOCO 4 – Honorários e Custas: 15% de honorários\n" +
            "BLOCO 5 – Liquidação e Impressão: Resumo de valores",
        
        "Dados Pessoais e Contratuais": 
            f"Nome: {dados_pessoais.get('nome', 'N/A')}\n" +
            f"CPF: {dados_pessoais.get('cpf', 'N/A')}\n" +
            f"Admissão: {dados_pessoais.get('data_admissao', 'N/A')}\n" +
            f"Demissão: {dados_pessoais.get('data_demissao', 'N/A')}\n" +
            f"Salário: {dados_pessoais.get('ultimo_salario', 'N/A')}\n" +
            f"Função: {dados_pessoais.get('funcao', 'N/A')}",
        
        "Informações para Preenchimento no Pje-Calc": 
            "Dados de configuração para PJE-CALC:\n" +
            "• Utilizar índice IPCA-E + juros simples de 1% a.m.\n" +
            "• Considerar os parâmetros de cada verba conforme quadro\n" +
            "• Aplicar reflexos nas verbas de natureza salarial",
        
        "Resultado Final da Liquidação": 
            f"Valor Principal Estimado: {dados_processo.get('resultado_calculo', {}).get('valor_principal', 'Pendente de cálculo')}\n" +
            f"Juros: {dados_processo.get('resultado_calculo', {}).get('juros', 'Pendente de cálculo')}\n" +
            f"Correção: {dados_processo.get('resultado_calculo', {}).get('correcao', 'Pendente de cálculo')}\n" +
            f"Valor Total: {dados_processo.get('resultado_calculo', {}).get('valor_total', 'Pendente de cálculo')}\n" +
            f"Processado por am-axia-br em {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    }
    
    return dados_resumo