# Publicar o painel no Streamlit Community Cloud

Custo zero, cerca de 10 minutos. O app lê os CSVs versionados em `dados/`, então não depende de banco nem de segredos.

## Pré-requisitos
1. **Repositório público.** Em *Settings → General → Danger Zone → Change repository visibility → Public*.
   Antes, confirme que nada sensível está versionado. Neste repositório só há dados simulados e fontes públicas.
2. O código do app precisa estar na branch que será publicada (normalmente `main`, depois do merge do PR).

## Passo a passo
1. Acesse **https://share.streamlit.io** e entre com a conta do GitHub (`fabiojmjr-oss`).
2. **Create app → Deploy a public app from GitHub**.
3. Preencha:
   | Campo | Valor |
   |---|---|
   | Repository | `fabiojmjr-oss/KPIs-OKRs-SLAs` |
   | Branch | `main` |
   | Main file path | `app/streamlit_app.py` |
   | App URL | sugestão: `vertice-kpis` → `https://vertice-kpis.streamlit.app` |
4. Em **Advanced settings**, escolha **Python 3.11** ou superior (o código usa sintaxe de tipos do 3.10+).
5. **Deploy.** A primeira instalação leva de 2 a 4 minutos (`requirements.txt` contém só dependências de execução).

## Depois de publicar
- Cada `push` na `main` republica o app automaticamente.
- Apps gratuitos "dormem" após um período sem acesso. O primeiro visitante vê um botão para acordá-lo (~30 s). Antes de uma entrevista ou de um post, abra o link para aquecer.
- Adicione ao README o selo:
  `[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://vertice-kpis.streamlit.app)`

## Uso no LinkedIn
- Seção **Destaques (Featured)**: link do app + link do notebook no GitHub.
- No post, mostre **um achado**, não a ferramenta. Exemplo: "Na semana da Black Friday, um pedido a mais custa ~6× a média. Veja o modelo."
