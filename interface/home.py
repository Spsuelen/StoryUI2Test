import streamlit as st
import os

st.set_page_config(page_title="Pipeline de Engenharia de Requisitos e QA", layout="wide")

if "tela_ativa" not in st.session_state:
    st.session_state.tela_ativa = "Home"

if "passo_atual" not in st.session_state:
    st.session_state.passo_atual = 1

st.markdown("""
    <style>
    html, body, [class*="css"], .stButton button {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    .titulo-painel {
        text-align: center;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #1E3A8A;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .sub-painel {
        text-align: center;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #4B5563;
        margin-bottom: 3rem;
    }
    div[data-testid="stColumn"] {
        background-color: #F8FAFC;
        border-top: 4px solid #1E3A8A;
        border-radius: 0px 0px 10px 10px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        transition: all 0.2s ease-in-out;
        text-align: center;
        margin-bottom: 20px;
    }
    div[data-testid="stColumn"]:hover {
        transform: translateY(-2px);
        background-color: #F1F5F9;
        box-shadow: 0 10px 15px -3px rgba(30, 58, 138, 0.1);
    }
    .card-title {
        font-size: 18px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 10px;
        min-height: 50px;
    }
    .card-desc {
        font-size: 14px;
        color: #475569;
        margin-bottom: 20px;
        min-height: 60px;
    }
    div.stButton > button {
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover:not(:disabled) {
        border-color: #1E3A8A !important;
        color: #FFFFFF !important;
        background-color: #1E3A8A !important;
    }
    </style>
""", unsafe_allow_html=True)

if st.session_state.tela_ativa != "Home":
    if st.button("Prosseguir para a próxima etapa"):
        st.session_state.tela_ativa = "Home"
        st.rerun()
    st.markdown("---")

if st.session_state.tela_ativa == "Home":
    st.markdown("<h1 class='titulo-painel'>Matriz de Inteligência, Engenharia e Validação</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-painel'>Selecione o módulo que deseja executar para iniciar o processo automatizado.</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")
    col3, col4 = st.columns(2, gap="large")

    with col1:
        st.markdown("<div class='card-title'>1. Analisador de Histórias de Usuário</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Validação gramatical, conformidade técnica, deteção de duplicados e conflitos lógicos em Requisitos.</div>", unsafe_allow_html=True)
        if st.button("Abrir Módulo Texto", use_container_width=True, key="btn1"):
            if st.session_state.passo_atual == 1:
                st.session_state.passo_atual = 2
            st.session_state.tela_ativa = "VerificadorHistoriaDeUsuario.py"
            st.rerun()

    with col2:
        st.markdown("<div class='card-title'>2. Gerador de Casos de Teste (Textual)</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Geração automática de casos de teste estruturados via GPT com base na lista de histórias validadas.</div>", unsafe_allow_html=True)
        bloqueado_btn2 = st.session_state.passo_atual < 2
        if st.button("Gerar Testes (Texto)", use_container_width=True, key="btn2", disabled=bloqueado_btn2):
            if st.session_state.passo_atual == 2:
                st.session_state.passo_atual = 3
            st.session_state.tela_ativa = "VerificadorGeracaoCasodeTesteTextual.py"
            st.rerun()

    with col3:
        st.markdown("<div class='card-title'>3. Gerador de Casos de Teste (Imagem)</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Processamento visual de capturas de tela (ZIP) para inferir e estruturar cenários de teste de UI.</div>", unsafe_allow_html=True)
        bloqueado_btn3 = st.session_state.passo_atual < 3
        if st.button("Gerar Testes (Imagem)", use_container_width=True, key="btn3", disabled=bloqueado_btn3):
            if st.session_state.passo_atual == 3:
                st.session_state.passo_atual = 4
            st.session_state.tela_ativa = "VerificadorGeracaoCasodeTesteImagem.py"
            st.rerun()

    with col4:
        st.markdown("<div class='card-title'>4. Matriz de Rastreabilidade Semântica</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-desc'>Cruzamento semântico avançado entre requisitos, testes textuais e testes de imagem.</div>", unsafe_allow_html=True)
        bloqueado_btn4 = st.session_state.passo_atual < 4
        if st.button("Verificar Rastreabilidade", use_container_width=True, key="btn4", disabled=bloqueado_btn4):
            st.session_state.tela_ativa = "VerificadorMapeamento.py"
            st.rerun()

else:
    MODULOS_PERMITIDOS = {
        "VerificadorHistoriaDeUsuario.py",
        "VerificadorGeracaoCasodeTesteTextual.py",
        "VerificadorGeracaoCasodeTesteImagem.py",
        "VerificadorMapeamento.py",
    }
    caminho_arquivo = os.path.basename(st.session_state.tela_ativa)
    if caminho_arquivo not in MODULOS_PERMITIDOS:
        st.error(f"Módulo não autorizado: {caminho_arquivo}")
        st.stop()
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            codigo_da_tela = f.read()
        codigo_da_tela = codigo_da_tela.replace("st.set_page_config", "# st.set_page_config")
        exec(codigo_da_tela, {})
    except FileNotFoundError:
        st.error(f"Erro Crítico: O script `{caminho_arquivo}` não foi encontrado no diretório atual.")
    except Exception as e:
        st.error(f"Erro na execução interna do script: {e}")