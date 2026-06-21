import streamlit as st
import pandas as pd
import zipfile
import json
import os
import io
import time
import base64
from openai import OpenAI
import pypdf

st.set_page_config(page_title="Gerador de Casos de Teste baseados em Imagens", layout="wide")


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


client = OpenAI()
MODEL_NAME = "gpt-4o-mini"

def normalize_text(text):
    stop_words = ["de", "do", "da", "no", "na", "o", "a", "em", "sistema", "plataforma"]
    words = text.lower().strip().split()
    return " ".join([w for w in words if w not in stop_words])

def analyze_screen(image_bytes):
    if len(image_bytes) < 5000:
        return None

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "Analise esta screenshot de interface e descreva objetivamente o que voce observa.\n"
        "Identifique os elementos interativos (campos, botoes, icones) e proponha casos de teste baseados exclusivamente no que esta visivel.\n"
        "Use os nomes e labels exatamente como aparecem na tela.\n"
        "Responda APENAS em JSON valido, sem markdown, seguindo esta estrutura:\n\n"
        "{\n"
        '  "finalidade": "string",\n'
        '  "casos_teste": [\n'
        '    {\n'
        '      "id": "CT_V01",\n'
        '      "tipo": "string",\n'
        '      "elemento_observado": "string",\n'
        '      "descricao": "string",\n'
        '      "resultado_esperado": "string"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    for i in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            if "429" in str(e):
                time.sleep(60)
            else:
                raise e
    raise Exception("Falha por limite de requisicoes")

st.title("Gerador de Casos de Teste baseados em Imagens")

with st.sidebar:
    st.header("Entrada de Dados")
    uploaded_file = st.file_uploader("Upload do Backlog", type=["zip"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Arquivo pronto para análise")

if not uploaded_file:
    st.markdown("### Mapeie telas e gere casos de teste de forma automatizada")
    st.markdown("Submeta pacotes de capturas de tela e gere de maneira padronizada as matrizes de verificação, identificando elementos interativos e cenários ideais em segundos.")
    
    st.markdown("#### Como começar?")
    st.markdown("""
    1. Na barra lateral esquerda, clique em **Procurar arquivos** ou arraste seu arquivo compactado.
    2. O upload deve ser um arquivo compactado formato **.zip** com qualquer nome, contendo as capturas de tela nos formatos de imagem suportados (.png, .jpg, .jpeg, .webp, .bmp) ou arquivos em formato .pdf.
    3. Acompanhe o relatório analítico detalhado que será gerado dinamicamente nesta área.
    """)
    
else:
    with st.spinner("Analisando o lote de interfaces enviado..."):
        json_final = []
        csv_casos = []
        historico_elementos = {}
        
        st.subheader("Console de Monitoramento")
        log_terminal = st.empty()
        texto_logs = ""

        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            extensoes_suportadas = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pdf")
            arquivos = [f for f in zip_ref.namelist() if f.lower().endswith(extensoes_suportadas) and not f.startswith("__MACOSX") and not f.endswith("/")]
            arquivos.sort(key=lambda x: os.path.basename(x).lower())

            for nome in arquivos:
                nome_arquivo_limpo = os.path.basename(nome)
                
                if nome.lower().endswith('.pdf'):
                    try:
                        texto_logs += f"Observando documento PDF: {nome_arquivo_limpo}\n"
                        log_terminal.code(texto_logs)
                        
                        pdf_bytes = zip_ref.read(nome)
                        f_buffer = io.BytesIO(pdf_bytes)
                        leitor_pdf = pypdf.PdfReader(f_buffer)
                        
                        for idx_pag, pagina in enumerate(leitor_pdf.pages):
                            
                            if "/XObject" in pagina["/Resources"]:
                                x_object = pagina["/Resources"]["/XObject"].get_object()
                                for obj in x_object:
                                    if x_object[obj]["/Subtype"] == "/Image":
                                        image_bytes = x_object[obj].get_data()
                                        identificador_tela = f"{nome_arquivo_limpo} (Pág. {idx_pag+1} - {obj})"
                                        
                                        texto_logs += f"Processando elemento visual do PDF: {identificador_tela}\n"
                                        log_terminal.code(texto_logs)
                                        
                                        dados = analyze_screen(image_bytes)
                                        if dados:
                                            finalidade_pura = dados.get("finalidade", "")
                                            finalidade_chave = normalize_text(finalidade_pura)
                                            elementos_atuais = set(ct.get("elemento_observado", "").lower() for ct in dados.get("casos_teste", []))

                                            if finalidade_chave in historico_elementos:
                                                if elementos_atuais.issubset(historico_elementos[finalidade_chave]):
                                                    texto_logs += f"Heurística: Tela '{finalidade_pura}' já mapeada com os mesmos elementos. Pulando.\n"
                                                    log_terminal.code(texto_logs)
                                                    continue
                                                else:
                                                    historico_elementos[finalidade_chave].update(elementos_atuais)
                                            else:
                                                historico_elementos[finalidade_chave] = elementos_atuais

                                            json_final.append({
                                                "arquivo": identificador_tela,
                                                "analise": dados
                                            })

                                            for ct in dados.get("casos_teste", []):
                                                csv_casos.append({
                                                    "Arquivo": identificador_tela,
                                                    "Finalidade_Tela": dados.get("finalidade"),
                                                    "Caso_Teste_ID": ct.get("id"),
                                                    "Tipo": ct.get("tipo"),
                                                    "Elemento": ct.get("elemento_observado"),
                                                    "Descricao": ct.get("descricao"),
                                                    "Resultado_Esperado": ct.get("resultado_esperado")
                                                })
                    except Exception as err_pdf:
                        texto_logs += f"Aviso ao processar extrator visual do PDF {nome_arquivo_limpo}: {err_pdf}\n"
                        log_terminal.code(texto_logs)
                else:
                    texto_logs += f"Observando interface: {nome_arquivo_limpo}\n"
                    log_terminal.code(texto_logs)

                    image_bytes = zip_ref.read(nome)
                    dados = analyze_screen(image_bytes)

                    if dados:
                        finalidade_pura = dados.get("finalidade", "")
                        finalidade_chave = normalize_text(finalidade_pura)
                        elementos_atuais = set(ct.get("elemento_observado", "").lower() for ct in dados.get("casos_teste", []))

                        if finalidade_chave in historico_elementos:
                            if elementos_atuais.issubset(historico_elementos[finalidade_chave]):
                                texto_logs += f"Heurística: Tela '{finalidade_pura}' já mapeada com os mesmos elementos. Pulando.\n"
                                log_terminal.code(texto_logs)
                                continue
                            else:
                                historico_elementos[finalidade_chave].update(elementos_atuais)
                        else:
                            historico_elementos[finalidade_chave] = elementos_atuais

                        json_final.append({
                            "arquivo": nome_arquivo_limpo,
                            "analise": dados
                        })

                        for ct in dados.get("casos_teste", []):
                            csv_casos.append({
                                "Arquivo": nome_arquivo_limpo,
                                "Finalidade_Tela": dados.get("finalidade"),
                                "Caso_Teste_ID": ct.get("id"),
                                "Tipo": ct.get("tipo"),
                                "Elemento": ct.get("elemento_observado"),
                                "Descricao": ct.get("descricao"),
                                "Resultado_Esperado": ct.get("resultado_esperado")
                            })
            
            texto_logs += "Processo finalizado.\n"
            log_terminal.code(texto_logs)

        if csv_casos:
            df = pd.DataFrame(csv_casos)


            st.subheader("Resultado do Script")
            texto_saida_original = f"Total de casos: {len(df)}\n\nCasos por tela:\n{df['Arquivo'].value_counts().to_string()}\n"
            st.code(texto_saida_original)

            st.subheader("📋 Matriz de Casos de Teste Gerados")
            
            def colorir_e_alinhar_linhas(dataframe):
                estilos = pd.DataFrame('', index=dataframe.index, columns=dataframe.columns)
                for idx, row in dataframe.iterrows():
                    cor = '#e2f0d9' if idx % 2 == 0 else '#f2f2f2'
                    estilos.loc[idx, :] = f'background-color: {cor}; vertical-align: top; color: #000000;'
                return estilos

            st.dataframe(
                df.style.apply(colorir_e_alinhar_linhas, axis=None),
                use_container_width=True,
                hide_index=True
            )

            st.info("⚠️ **Atenção:** Para realizar as próximas etapas e execuções do sistema, é obrigatório fazer o download do arquivo **CSV** abaixo. O download do arquivo JSON é opcional.")

            col_down1, col_down2 = st.columns(2)
            
            with col_down1:
                st.download_button(
                    label="Baixar JSON da Análise",
                    data=json.dumps(json_final, indent=2, ensure_ascii=False),
                    file_name="mapeamento_completo.json",
                    mime="application/json"
                )
                
            with col_down2:
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, encoding="utf-8")
                st.download_button(
                    label="Baixar CSV da Análise",
                    data=csv_buffer.getvalue(),
                    file_name="casos_de_teste_Imagem.csv",
                    mime="text/csv",
                    type="primary"
                )
