# StoryUI2Test

Pipeline automatizado de Engenharia de Requisitos e QA. Transforma histórias de usuário em casos de teste via IA com suporte a análise textual e visual de interfaces.

## Funcionalidades

- **Analisador de Histórias de Usuário** — valida estrutura gramatical, detecta duplicatas e conflitos lógicos
- **Gerador de Casos de Teste (Texto)** — gera casos de teste estruturados via GPT-4o a partir das histórias validadas
- **Gerador de Casos de Teste (Imagem)** — analisa screenshots/PDFs e infere cenários de teste de UI
- **Matriz de Rastreabilidade Semântica** — cruza requisitos com testes textuais e visuais usando similaridade semântica

## Pré-requisitos

- **Python 3.11**
- **Conta OpenAI** com chave de API (modelo `gpt-4o-mini`)
- **Docker** (recomendado) ou **Docker Desktop**

---

## Setup rápido (local)

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd StoryUI2Test

# 2. Configure a chave da OpenAI
cp .env.template .env
# Edite .env e coloque sua chave: OPENAI_API_KEY=sk-...

# 3. Execute o setup
chmod +x setup.sh
./setup.sh

# 4. Ative o ambiente virtual e inicie
source .venv/bin/activate
streamlit run interface/home.py
```

Acesse em **http://localhost:8501**

---

## Setup com Docker

```bash
# 1. Configure a chave da OpenAI
cp .env.template .env
# Edite .env e coloque sua chave: OPENAI_API_KEY=sk-...

# 2. Suba o container
docker compose up -d
```

Acesse em **http://localhost:8501**

Para parar:
```bash
docker compose down
```

---

## Como usar o pipeline

O pipeline tem **4 etapas sequenciais**. Cada etapa depende do output da anterior.

### 1. Analisador de Histórias de Usuário
- Faça upload de um arquivo **ZIP** contendo histórias de usuário
- Formatos aceitos: `.txt`, `.csv`, `.pdf`, `.docx`
- Baixe o arquivo **`saida.json`** gerado (obrigatório para a próxima etapa)

### 2. Gerador de Casos de Teste (Texto)
- Faça upload do arquivo **`saida.json`** (deve ter exatamente este nome)
- Baixe o arquivo **`casos_de_teste_GPT.csv`** gerado

### 3. Gerador de Casos de Teste (Imagem) — opcional
- Faça upload de um **ZIP** com screenshots (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`) ou PDFs
- Baixe o arquivo **`casos_de_teste_Imagem.csv`** gerado

### 4. Matriz de Rastreabilidade Semântica
- Faça upload dos **3 arquivos obrigatórios** com os nomes exatos:
  - `saida.json`
  - `casos_de_teste_GPT.csv`
  - `casos_de_teste_Imagem.csv`
- Baixe o arquivo **`mapeamento.csv`** com os resultados

---

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | Sim | Chave de API da OpenAI |

> **Importante:** sem a chave da OpenAI o app não funciona. Nenhum dos módulos opera localmente.

---

## Estrutura do projeto

```
StoryUI2Test/
├── interface/
│   ├── home.py                                      # Ponto de entrada / navegação
│   ├── VerificadorHistoriaDeUsuario.py              # Etapa 1
│   ├── VerificadorGeracaoCasodeTesteTextual.py      # Etapa 2
│   ├── VerificadorGeracaoCasodeTesteImagem.py       # Etapa 3
│   ├── VerificadorMapeamento.py                     # Etapa 4
│   └── requirements.txt                             # Dependências Python
├── Dockerfile                                       # Imagem Docker
├── docker-compose.yml                               # Orquestração Docker
├── setup.sh                                         # Setup local automatizado
├── .env.template                                    # Template de variáveis de ambiente
└── .gitignore
```

---

## Limitações conhecidas

- **Conexão com internet obrigatória** — todas as análises dependem da API da OpenAI
- **Modelos pesados** — na primeira execução, ~1GB de modelos (spaCy, transformers, sentence-transformers) são baixados automaticamente
- **Nomes de arquivo fixos** — as etapas 2, 3 e 4 exigem nomes exatos de arquivo
- **Pipeline não persistente** — recarregar a página no navegador reinicia o progresso
- **Idioma** — interface e prompts em português brasileiro
