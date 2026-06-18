import streamlit as st
import pandas as pd
import re
import json
import os
import io
from openai import OpenAI

st.set_page_config(page_title="Gerador de Casos de Teste", layout="wide")

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
        content: "Requer arquivo JSON válido • Limite de 200MB";
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

def gerar_casos_teste(historia_json, score_minimo=0.7):
    chave_api = "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"
    os.environ["OPENAI_API_KEY"] = chave_api
    client = OpenAI(api_key=chave_api)

    prompt_partes = []

    for historia in historia_json:
        if not historia["valida"]:
            continue
        apps_confiaveis = [a["nome"] for a in historia["apps"]
                           if a["score"] is None or a["score"] >= score_minimo]
        apps_str = ", ".join(apps_confiaveis) if apps_confiaveis else "Nenhum app identificado"
        trecho = f"""
História de Usuário:
Ator: {historia['ator']}
Ação: {historia['acao']}
Benefício: {historia['beneficio']}
Aplicativos/Recursos: {apps_str}
"""
        prompt_partes.append(trecho)

    prompt = "\n".join(prompt_partes)
    prompt_completo = f"""
Você é um especialista em QA e geração de casos de teste de software.

A partir das Histórias de Usuário abaixo, gere para cada uma:

- Um caso de teste em formato estruturado com Título, Pré-condições, Passos, Entrada e Resultado Esperado.
- Certifique-se de que cada caso cobre a funcionalidade descrita na história.
- Use linguagem clara e objetiva.

{prompt}
"""
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um especialista em QA e geração de casos de teste."},
            {"role": "user", "content": prompt_completo}
        ],
        temperature=0.3
    )

    return resposta.choices[0].message.content

def limpar_saida(texto):
    texto = re.sub(r'\*\*', '', texto)
    texto = re.sub(r'###\s*', '', texto)
    texto = re.sub(r'^\s*---\s*$', '', texto, flags=re.MULTILINE)
    return texto.strip()

def limpar_titulo(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto)
    match = re.search(r'Título:\s*(.*)', texto)
    if match:
        return match.group(1).strip()
    return texto.split("\n")[0].strip()

st.title("Gerador de Casos de Teste")

with st.sidebar:
    st.header("Entrada de Dados")
    uploaded_file = st.file_uploader("Upload do Backlog", type=["json"], label_visibility="collapsed")
    if not uploaded_file:
        st.caption("O arquivo de upload deve estar em formato json com o nome saida.")
    else:
        st.success("Arquivo pronto para análise")

if not uploaded_file:
    st.markdown("### Gere Casos de Teste estruturados a partir do seu Backlog")
    st.markdown("Submeta o arquivo **saida.json** vindo do processamento da história de usuário para elaborar cenários detalhados com pré-condições, passos e resultados esperados.")
    
    st.markdown("#### Como começar?")
    st.markdown("""
    1. Na barra lateral esquerda, clique em **Procurar arquivos** ou arraste seu arquivo estruturado.
    2. O arquivo de upload deve ser o resultado do processamento anterior, em formato **.json** com o nome exato de **saida**.
    3. Acompanhe a matriz técnica detalhada e os arquivos gerados dinamicamente nesta área.
    """)

else:
    if uploaded_file.name != "saida.json":
        st.error("Erro: O arquivo enviado deve se chamar exatamente 'saida.json'")
    else:
        st.subheader("Console de Monitoramento")
        log_terminal = st.empty()
        log_terminal.code("Iniciando geração de casos de teste textuais...\nEnviando prompt ao GPT-4o-Mini...")

        with st.spinner("Processando histórias e gerando casos de teste..."):
            historias = json.load(uploaded_file)
            
            casos_teste = gerar_casos_teste(historias)
            casos_teste = limpar_saida(casos_teste)
            
            log_terminal.code("Geração finalizada.\nEstruturando dados e aplicando expressões regulares...")

            blocos = re.split(r'(?=Caso de Teste \d+:)', casos_teste)
            lista_csv = []

            for bloco in blocos:
                if "Caso de Teste" in bloco:
                    titulo = re.search(r'Caso de Teste \d+: (.*?)(?=\nPré-condições:|$)', bloco, re.S)
                    pre = re.search(r'Pré-condições:(.*?)(?=Passos:|$)', bloco, re.S)
                    passos = re.search(r'Passos:(.*?)(?=Entrada:|$)', bloco, re.S)
                    entrada = re.search(r'Entrada:(.*?)(?=Resultado Esperado:|$)', bloco, re.S)
                    resultado = re.search(r'Resultado Esperado:(.*?)$', bloco, re.S)

                    lista_csv.append({
                        "Título": titulo.group(1).strip() if titulo else "",
                        "Pré-condições": pre.group(1).strip() if pre else "",
                        "Passos": passos.group(1).strip() if passos else "",
                        "Entrada": entrada.group(1).strip() if entrada else "",
                        "Resultado Esperado": resultado.group(1).strip() if resultado else ""
                    })

            df = pd.DataFrame(lista_csv)
            df["Titulo_Limpo"] = df["Título"].apply(limpar_titulo)

            log_terminal.code("Processo finalizado.")

            if len(df) > 0:
                st.subheader("Resultado do Script (Terminal)")
                texto_saida_original = f"Total de casos: {len(df)}\n\nCasos por tela:\n{df['Titulo_Limpo'].value_counts().to_string()}\n"
                st.code(texto_saida_original)

                st.subheader("📋 Matriz de Casos de Teste Gerados (GPT)")
                
                def colorir_e_alinhar_linhas(dataframe):
                    estilos = pd.DataFrame('', index=dataframe.index, columns=dataframe.columns)
                    for idx, row in dataframe.iterrows():
                        cor = '#e2f0d9' if idx % 2 == 0 else '#f2f2f2'
                        estilos.loc[idx, :] = f'background-color: {cor}; vertical-align: top; color: #000000;'
                    return estilos

                df_exibicao = df[["Título", "Pré-condições", "Passos", "Entrada", "Resultado Esperado"]]
                st.dataframe(
                    df_exibicao.style.apply(colorir_e_alinhar_linhas, axis=None),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Nenhum bloco válido de 'Caso de Teste' pôde ser segmentado a partir da resposta obtida.")

            st.markdown("<br>", unsafe_allow_html=True)
            
            st.info("⚠️ **Atenção:** Para realizar as próximas etapas e execuções do sistema, é obrigatório fazer o download do arquivo **CSV** abaixo. O download do arquivo TXT é opcional.")
            
            col_down1, col_down2 = st.columns(2)
            
            with col_down1:
                st.download_button(
                    label="Baixar TXT dos Casos de Teste",
                    data=casos_teste,
                    file_name="casos_teste_gerados.txt",
                    mime="text/plain"
                )
                
            with col_down2:
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
                st.download_button(
                    label="Baixar CSV dos Casos de Teste",
                    data=csv_buffer.getvalue(),
                    file_name="casos_de_teste_GPT.csv",
                    mime="text/csv",
                    type="primary"
                )
