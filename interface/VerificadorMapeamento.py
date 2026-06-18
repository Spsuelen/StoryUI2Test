import streamlit as st
import pandas as pd
import json
import io
import os
import re
import torch
from sentence_transformers import SentenceTransformer, util

st.set_page_config(page_title="Rastreador de Casos de Teste", layout="wide")

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
        content: "Limite de 200MB por arquivo";
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def carregar_modelo():
    return SentenceTransformer('all-mpnet-base-v2')

modelo_semantico = carregar_modelo()

def limpar_ruido(texto):
    if not isinstance(texto, str): return ""
    termos_ruido = [r"Como usuário", r"para que", r"a fim de", r"quer clicar no", r"quero", r"deve ser"]
    for padrao in termos_ruido:
        texto = re.sub(padrao, "", texto, flags=re.IGNORECASE)
    return " ".join(texto.split()).strip()

def definir_status(score):
    if score > 0.65: return "VALIDADO"
    if score > 0.40: return "POTENCIAL"
    return "SEM CORRESPONDÊNCIA"

st.title("Rastreador de Casos de Teste")

with st.sidebar:
    st.header("Entrada de Dados")
    
    file_json = st.file_uploader("Upload do arquivo saida.json", type=["json"])
    if file_json:
        if file_json.name == "saida.json":
            st.success("saida.json carregado")
        else:
            st.error("Renomeie para saida.json")
            
    file_gpt = st.file_uploader("Upload do arquivo casos_de_teste_GPT.csv", type=["csv"])
    if file_gpt:
        if file_gpt.name == "casos_de_teste_GPT.csv":
            st.success("casos_de_teste_GPT.csv carregado")
        else:
            st.error("Renomeie para casos_de_teste_GPT.csv")
            
    file_img = st.file_uploader("Upload do arquivo casos_de_teste_Imagem.csv", type=["csv"])
    if file_img:
        if file_img.name == "casos_de_teste_Imagem.csv":
            st.success("casos_de_teste_Imagem.csv carregado")
        else:
            st.error("Renomeie para casos_de_teste_Imagem.csv")

if not (file_json and file_gpt and file_img):
    st.markdown("### Rastreabilidade e Correspondência Semântica de Testes")
    st.markdown("Esta interface realiza a validação cruzada cruzando os requisitos textuais originais com os cenários gerados por IA e elementos identificados visualmente nas imagens de telas.")
    
    st.markdown("#### Como começar?")
    st.markdown("""
    1. Na barra lateral esquerda, faça o upload dos **três arquivos obrigatórios** gerados nas etapas anteriores.
    2. Certifique-se de manter os nomes exatos:
        * **saida.json**
        * **casos_de_teste_GPT.csv**
        * **casos_de_teste_Imagem.csv**
    3. O sistema computará as matrizes de similaridade semântica e exibirá os resultados consolidados em tempo real.
    """)

else:
    if file_json.name != "saida.json" or file_gpt.name != "casos_de_teste_GPT.csv" or file_img.name != "casos_de_teste_Imagem.csv":
        st.error("Erro: Um ou mais arquivos possuem nomes inválidos. Ajuste as entradas na barra lateral.")
    else:
        with st.spinner("Computando embeddings e calculando correspondências semânticas..."):
            historias = json.load(file_json)
            df_gpt = pd.read_csv(file_gpt)
            df_img = pd.read_csv(file_img)

            frases_gpt = (df_gpt['Título'] + " " + df_gpt['Passos'] + " " + df_gpt['Resultado Esperado']).apply(limpar_ruido).tolist()
            frases_img = (df_img['Elemento'] + " " + df_img['Descricao'] + " " + df_img['Resultado_Esperado']).apply(limpar_ruido).tolist()

            embeddings_gpt = modelo_semantico.encode(frases_gpt, convert_to_tensor=True)
            embeddings_img = modelo_semantico.encode(frases_img, convert_to_tensor=True)

            relatorio = []

            for h in historias:
                acao_limpa = limpar_ruido(h['acao'])
                emb_req = modelo_semantico.encode(acao_limpa, convert_to_tensor=True)

                scores_gpt = util.cos_sim(emb_req, embeddings_gpt)[0]
                idx_gpt = torch.argmax(scores_gpt).item()
                sim_gpt = scores_gpt[idx_gpt].item()

                scores_img = util.cos_sim(emb_req, embeddings_img)[0]
                idx_img = torch.argmax(scores_img).item()
                sim_img = scores_img[idx_img].item()

                relatorio.append({
                    "requisito": h['acao'][:30] + "...",
                    "id_img": df_img.iloc[idx_img]['Caso_Teste_ID'],
                    "score_gpt": round(sim_gpt, 4),
                    "status_gpt": definir_status(sim_gpt),
                    "score_img": round(sim_img, 4),
                    "status_img": definir_status(sim_img),
                    "concordancia": f"{definir_status(sim_gpt)}/{definir_status(sim_img)}"
                })

            df_final = pd.DataFrame(relatorio)

            total_validado = len(df_final[df_final['concordancia'] == "VALIDADO/VALIDADO"])
            total_potencial = len(df_final[df_final['concordancia'].str.contains("POTENCIAL")])
            total_sem = len(df_final[df_final['concordancia'].str.contains("SEM CORRESPONDÊNCIA")])

            st.subheader("Resultado do Script (Terminal)")
            tabela_string = df_final.to_string(index=False)
            texto_saida_original = f"{tabela_string}\n\nTotal VALIDADO: {total_validado}\nTotal POTENCIAL: {total_potencial}\nTotal SEM CORRESPONDÊNCIA: {total_sem}\n"
            st.code(texto_saida_original)
            
            st.subheader("📊 Matriz de Rastreabilidade Semântica Consolidada")

            def colorir_e_alinhar_linhas(dataframe):
                estilos = pd.DataFrame('', index=dataframe.index, columns=dataframe.columns)
                for idx, row in dataframe.iterrows():
                    cor = '#e2f0d9' if idx % 2 == 0 else '#f2f2f2'
                    estilos.loc[idx, :] = f'background-color: {cor}; vertical-align: top; color: #000000;'
                return estilos

            if len(df_final) > 0:
                st.dataframe(
                    df_final.style.apply(colorir_e_alinhar_linhas, axis=None),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Nenhum dado pôde ser mapeado a partir das entradas fornecidas.")

            st.markdown("<br>", unsafe_allow_html=True)
            csv_buffer = io.StringIO()
            df_final.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            
            st.info("⚠️ **Atenção:** Para realizar a avaliação dos resultados obtidos é obrigatório fazer o download do arquivo **CSV** abaixo.")
            
            st.download_button(
                label="Baixar Mapeamento de Rastreabilidade (CSV)",
                data=csv_buffer.getvalue(),
                file_name="mapeamento.csv",
                mime="text/csv",
                type="primary"
            )