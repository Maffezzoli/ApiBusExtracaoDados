# Processador API Ônibus Rio (Trabalho N8N)

## Objetivo do Projeto

Este projeto foi desenvolvido como parte de um trabalho acadêmico para demonstrar a integração entre uma API externa e a ferramenta de automação N8N.

O objetivo principal é contornar a limitação de processamento do N8N ao lidar com grandes volumes de dados retornados pela API de GPS dos ônibus do Rio de Janeiro (`https://dados.mobilidade.rio/gps/sppo`).

## O Que Faz?

Este script Python (usando Flask) atua como um **intermediário inteligente**:

1.  **Busca os Dados:** Ele chama a API oficial da prefeitura.
2.  **Processa e Filtra:**
    *   Remove os ônibus que estão parados (velocidade = 0).
    *   Formata as coordenadas (latitude/longitude).
    *   Converte a data/hora para um formato legível.
    *   Calcula o atraso de transmissão (diferença entre a hora do GPS e a hora do servidor).
3.  **Entrega Dados Prontos:** Disponibiliza uma nova API (endpoint `/processed_data`) que retorna apenas os dados dos ônibus em movimento, já limpos e formatados em JSON.

Isso permite que o N8N chame *esta* API e receba um volume de dados muito menor e já pronto para uso.

## Como Funciona a API Criada

*   **URL Base (Exemplo):** `https://<nome-do-seu-app>.onrender.com`
*   **Endpoint Principal:** `GET /processed_data`
    *   Retorna a lista de ônibus processados.
*   **Endpoint com Limite:** `GET /processed_data?limit=N`
    *   Retorna no máximo `N` resultados (ex: `?limit=50`).

## Tecnologias

*   Python 3
*   Flask (para criar a API)
*   Requests (para chamar a API da prefeitura)
*   Gunicorn (servidor para produção)
*   Render.com (plataforma de hospedagem gratuita)

## Como Rodar Localmente (Para Testes)

1.  Clone este repositório.
2.  Crie e ative um ambiente virtual (`venv`).
3.  Instale as dependências: `pip install -r requirements.txt`
4.  Execute: `python app.py`
5.  A API estará rodando em `http://127.0.0.1:5000`.

## Hospedagem (Render)

Este projeto está configurado para deploy fácil na plataforma Render:
*   Conecte seu repositório GitHub ao Render.
*   Crie um "Web Service" no Render.
*   Render usará o `requirements.txt` para instalar dependências e o `Procfile` para saber como iniciar (`gunicorn`).
*   Utilize o plano gratuito do Render.
