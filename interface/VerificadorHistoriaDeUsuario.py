import streamlit as st
import pandas as pd
import re
import zipfile
import json
import io
import spacy
from transformers import pipeline
from dataclasses import dataclass, asdict
from typing import List, Optional
from difflib import SequenceMatcher
from itertools import combinations
import pypdf
import docx
import csv

st.set_page_config(page_title="Analisador de Histórias de Usuário", layout="wide")

st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
    }
    [data-testid="stFileUploadDropzone"] div div span::after {
        content: "Arraste e solte o arquivo aqui";
        font-size: 16px;
    }
    [data-testid="stFileUploadDropzone"] div div span {
        font-size: 0px;
    }
    [data-testid="stFileUploadDropzone"] button {
        font-size: 0px;
    }
    [data-testid="stFileUploadDropzone"] button::after {
        content: "Procurar arquivos";
        font-size: 14px;
    }
    [data-testid="stFileUploadDropzone"] div div small {
        font-size: 0px;
    }
    [data-testid="stFileUploadDropzone"] div div small::after {
        content: "Requer arquivo ZIP válido • Limite de 200MB";
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def inicializar_modelos():
    nlp_model = spacy.load("pt_core_news_sm")
    ner_pipe = pipeline(
        "ner",
        model="Jean-Baptiste/roberta-large-ner-english",
        aggregation_strategy="simple"
    )
    return nlp_model, ner_pipe


nlp, ner_model = inicializar_modelos()

@dataclass
class AppExtraido:
    nome: str
    score: Optional[float]

@dataclass
class HistoriaUsuarioEstruturada:
    texto: str
    ator: str
    acao: str
    beneficio: str
    apps: List[AppExtraido]
    score_confianca: float
    valida: bool
    diagnostico: str
    sugestao_melhoria: str

def limpeza_moderada(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = re.sub(r"[^\w\sÀ-ú]", "", texto)
    return texto

def extrair_entidades(texto: str, score_min: float = 0.7) -> list:
    resultados = ner_model(texto)
    return [
        {"nome": r["word"].strip(), "score": float(r["score"])}
        for r in resultados
        if r["score"] >= score_min
    ]

def entity_type(texto: str, entidade: str) -> bool:
    padroes = [
        rf"(no|na|em|através de|via|usando)\s+{re.escape(entidade)}",
        rf"{re.escape(entidade)}\s+(para|a fim de|visando)"
    ]
    return any(re.search(p, texto, re.IGNORECASE) for p in padroes)

def parece_app(candidato: str, texto_original: str) -> bool:
    stopwords = {
        "conta", "senha", "produtos", "pedido",
        "compras", "relatórios", "dados", "minha", "meu",
        "mesma", "sistema", "plataforma"
    }

    if candidato.lower() in stopwords:
        return False
    if len(candidato) < 4:
        return False

    doc = nlp(texto_original)
    for token in doc:
        if token.text.lower() == candidato.lower():
            if token.pos_ in ["PRON", "DET", "ADV", "ADP", "ADJ", "VERB", "AUX"]:
                if not token.text[0].isupper():
                    return False
            if token.pos_ == "NOUN" and not token.text[0].isupper():
                return False
    return True

def extrair_apps(texto: str, entidades_ner: list) -> List[AppExtraido]:
    apps = {}
    for e in entidades_ner:
        if entity_type(texto, e["nome"]):
            if parece_app(e["nome"], texto):
                apps[e["nome"]] = e["score"]

    padrao = r"(?:no|na|em|através de|via|usando)\s+([\wÀ-ú]+)"
    matches = re.findall(padrao, texto)

    padrao_app = re.compile(r"([\wÀ-ú]+)\s+do\s+aplicativo\s+[\wÀ-ú]+", re.IGNORECASE)
    for m in matches:
        if m not in apps and parece_app(m, texto):
            if padrao_app.search(texto):
                continue
            apps[m] = None

    return [AppExtraido(nome=k, score=v) for k, v in apps.items()]

def extrair_partes_historia(texto: str):
    padrao = re.compile(
        r"como\s+(?P<ator>.*?)\s+"
        r"(?:eu\s+)?"
        r"(?:quero|gostaria(?:\s+de)?|desejo|preciso(?:\s+de)?|necessito(?:\s+de)?)\s+"
        r"(?P<acao>.*?)(?:\s+para\s+(?P<beneficio>.*))?$",
        re.IGNORECASE
    )

    match = padrao.search(texto)

    if not match:
        return "Desconhecido", "", ""

    ator = match.group("ator").strip()
    ator = re.sub(r"\s+eu$", "", ator, flags=re.IGNORECASE)

    return (
        ator,
        match.group("acao").strip(),
        (match.group("beneficio") or "").strip()
    )

def validar_historia(ator: str, acao: str, beneficio: str) -> bool:
    return bool(ator and acao and beneficio)

def calcular_score_confianca(apps: List[AppExtraido]) -> float:
    if not apps:
        return 0.4
    scores = [a.score for a in apps if a.score is not None]
    if not scores:
        return 0.4
    return round(sum(scores) / len(scores), 3)

def processar_historia(texto: str) -> HistoriaUsuarioEstruturada:
    texto_limpo = limpeza_moderada(texto)
    entidades = extrair_entidades(texto_limpo)
    apps = extrair_apps(texto_limpo, entidades)
    ator, acao, beneficio = extrair_partes_historia(texto_limpo)

    erros = []
    if not ator or ator == "Desconhecido": erros.append("Ator ausente")
    if not acao: erros.append("Ação ausente")
    if not beneficio: erros.append("Benefício ausente")

    valida = validar_historia(ator, acao, beneficio)
    diagnostico = "CONFORME" if valida else f"ERRO DE HEURÍSTICA: {', '.join(erros)}"

    score_confianca = calcular_score_confianca(apps)
    sugestao = ""
    if score_confianca <= 0.4 and apps:
        termos = [a.nome for a in apps]
        sugestao = f"Ambiguidade detectada nos termos: {termos}. Especificar o sistema alvo."
    elif not apps and valida:
        sugestao = "Nenhum aplicativo identificado no contexto da história."

    return HistoriaUsuarioEstruturada(
        texto=texto_limpo,
        ator=ator,
        acao=acao,
        beneficio=beneficio,
        apps=apps,
        score_confianca=score_confianca,
        valida=valida,
        diagnostico=diagnostico,
        sugestao_melhoria=sugestao
    )

def similaridade(texto1, texto2):
    return SequenceMatcher(None, texto1, texto2).ratio()

st.title("Analisador de Histórias de Usuário")

with st.sidebar:
    st.header("Entrada de Dados")
    uploaded_file = st.file_uploader("Upload do Backlog", type=["zip"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Arquivo pronto para análise")

if not uploaded_file:
    st.markdown("### Analisador de Histórias de Usuário")
    st.markdown("#### Valide a conformidade do seu backlog de forma automatizada")
    st.markdown("Monitore a estrutura gramatical das suas histórias de usuário, detecte redundâncias e evite conflitos de escrita em poucos segundos.")
    st.markdown("#### Como começar?")
    st.markdown("Na barra lateral esquerda, clique em Procurar arquivos ou arraste seu arquivo compactado.")
    st.markdown("O upload deve ser um arquivo compactado formato .zip com qualquer nome, contendo arquivos nos formatos .txt, .csv, .pdf ou .docx.")
    st.markdown("Acompanhe o relatório analítico detalhado que será gerado dinamicamente nesta área.")
else:
    with st.spinner("Analisando..."):
        historias_usuario = []
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            for nome_arquivo in zip_ref.namelist():
                if nome_arquivo.startswith('__MACOSX') or nome_arquivo.endswith('/'):
                    continue
                
                extensao = nome_arquivo.lower()
                
                if extensao.endswith('.txt'):
                    conteudo = zip_ref.read(nome_arquivo).decode("utf-8", errors="ignore")
                    for linha in conteudo.splitlines():
                        if linha.strip():
                            historias_usuario.append(linha.strip())
                            
                elif extensao.endswith('.csv'):
                    conteudo = zip_ref.read(nome_arquivo).decode("utf-8", errors="ignore")
                    f_buffer = io.StringIO(conteudo)
                    leitor_csv = csv.reader(f_buffer)
                    for linha_csv in leitor_csv:
                        linha_texto = " ".join(linha_csv).strip()
                        if linha_texto:
                            historias_usuario.append(linha_texto)
                            
                elif extensao.endswith('.pdf'):
                    try:
                        conteudo_bytes = zip_ref.read(nome_arquivo)
                        f_buffer = io.BytesIO(conteudo_bytes)
                        leitor_pdf = pypdf.PdfReader(f_buffer)
                        
                        for pagina in leitor_pdf.pages:
                            texto_pag = pagina.extract_text()
                            if texto_pag:
                                texto_corrido = " ".join(texto_pag.splitlines())
                                blocos = re.split(r'(?=Como\s)', texto_corrido, flags=re.IGNORECASE)
                                for bloco in blocos:
                                    if bloco.strip():
                                        historias_usuario.append(bloco.strip())
                    except Exception as e:
                        st.error(f"ERRO ao ler o PDF {nome_arquivo}: {e}")
                        
                elif extensao.endswith('.docx') or extensao.endswith('.doc'):
                    try:
                        conteudo_bytes = zip_ref.read(nome_arquivo)
                        f_buffer = io.BytesIO(conteudo_bytes)
                        doc_word = docx.Document(f_buffer)
                        for paragrafo in doc_word.paragraphs:
                            if paragrafo.text.strip():
                                historias_usuario.append(paragrafo.text.strip())
                    except Exception as e:
                        st.error(f"ERRO ao ler o arquivo Word {nome_arquivo}: {e}")

        resultados = [asdict(processar_historia(h)) for h in historias_usuario]
        df = pd.DataFrame(resultados)

        total = len(resultados)
        conforme = sum(1 for r in resultados if r['valida'])
        nao_conforme = total - conforme

        st.subheader("Resumo Executivo")
        c_tot, c_conf, c_nconf = st.columns(3)
        c_tot.metric("Total Analisado", total)
        c_conf.metric("Em Conformidade", conforme)
        c_nconf.metric("Não Conforme", nao_conforme)

        st.subheader("Detecção de Ambiguidade e Redundância")
        
        duplicatas_encontradas = False
        LIMITE_DUPLICATA = 0.85
        lista_duplicatas = []
        
        for i, j in combinations(range(len(resultados)), 2):
            sim = similaridade(resultados[i]['texto'], resultados[j]['texto'])
            if sim > LIMITE_DUPLICATA:
                duplicatas_encontradas = True
                lista_duplicatas.append(f"**Similaridade ({sim:.2f})**:\n- **História 1**: {resultados[i]['texto']}\n- **História 2**: {resultados[j]['texto']}")
        
        if duplicatas_encontradas:
            for d in lista_duplicatas:
                st.warning(d)
        else:
            st.success("Nenhuma duplicata gramatical ou história redundante detectada no lote.")

        conflitos_encontrados = False
        pares_opostos = [
            ("ativar", "desativar"),
            ("permitir", "bloquear"),
            ("habilitar", "desabilitar"),
            ("criar", "excluir"),
            ("ligar", "desligar")
        ]
        lista_conflitos = []

        for h1, h2 in combinations(resultados, 2):
            if h1['ator'] != h2['ator']:
                continue

            apps_h1 = set(a['nome'] for a in h1['apps'])
            apps_h2 = set(a['nome'] for a in h2['apps'])
            apps_comuns = apps_h1 & apps_h2

            if not apps_comuns:
                continue

            a1 = h1['acao'].lower()
            a2 = h2['acao'].lower()

            for p1, p2 in pares_opostos:
                if (p1 in a1 and p2 in a2) or (p2 in a1 and p1 in a2):
                    conflitos_encontrados = True
                    lista_conflitos.append(f"**Conflito funcional nos apps {apps_comuns}**:\n- {h1['acao']}\n- {h2['acao']}")

        if conflitos_encontrados:
            for c in lista_conflitos:
                st.error(c)
        else:
            st.success("Nenhum conflito de regras ou ações contraditórias identificado.")

        st.subheader("Lista de Histórias Processadas")

        def colorir_e_alinhar_linhas(dataframe):
            estilos = pd.DataFrame('', index=dataframe.index, columns=dataframe.columns)
            for idx, row in dataframe.iterrows():
                cor = '#e2f0d9' if df.loc[idx, 'valida'] else '#fce4d6'
                estilos.loc[idx, :] = f'background-color: {cor}; vertical-align: top; color: #000000;'
            return estilos

        df_visualizacao = df.copy()
        df_visualizacao['apps'] = df_visualizacao['apps'].apply(lambda x: [a['nome'] for a in x])

        df_tabela = df_visualizacao[['texto', 'ator', 'acao', 'beneficio', 'apps', 'score_confianca', 'diagnostico']].copy()
        df_tabela.columns = ['Texto', 'Ator', 'Ação', 'Benefício', 'Apps Identificados', 'Confiança', 'Diagnóstico']

        st.dataframe(
            df_tabela.style.apply(colorir_e_alinhar_linhas, axis=None),
            use_container_width=True,
            hide_index=True
        )

        st.info("⚠️ **Atenção:** Para realizar as próximas etapas e execuções do sistema, é obrigatório fazer o download do arquivo **JSON** abaixo. O download do arquivo CSV é opcional.")

        col_down1, col_down2 = st.columns(2)
        with col_down1:
            st.download_button(
                label="Baixar JSON da Análise",
                data=json.dumps(resultados, indent=4, ensure_ascii=False),
                file_name="saida.json",
                mime="application/json",
                type="primary"
            )
        with col_down2:
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding="utf-8")
            st.download_button(
                label="Baixar CSV da Análise",
                data=csv_buffer.getvalue(),
                file_name="saida.csv",
                mime="text/csv"
            )