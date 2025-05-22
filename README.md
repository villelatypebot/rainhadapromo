# Sistema de Monitoramento de Cupons da Shopee

Este sistema monitora os stories do Instagram da Shopee Brasil, identifica cupons de desconto e os envia para um webhook do n8n para processamento adicional.

## Funcionalidades

- Monitoramento automático dos stories da Shopee em horários específicos
- Extração de códigos de cupom usando OpenAI Vision API
- Armazenamento dos cupons em banco de dados SQLite
- Envio dos códigos via webhook para n8n
- Evita duplicação de cupons
- API REST para monitoramento manual e visualização de cupons

## Requisitos

- Python 3.9+
- Chave de API do RapidAPI para MediaFy (API do Instagram)
- Chave de API do OpenAI (ChatGPT Vision)
- URL do webhook n8n

## Estrutura do Projeto

```
shopee-cupom/
├── app.py            # Ponto de entrada principal / FastAPI
├── monitor.py        # Lógica de monitoramento dos stories
├── coupon_extractor.py # Extração de códigos via ChatGPT Vision
├── database.py       # Gerenciamento do banco SQLite
├── webhook.py        # Envio de dados para n8n
├── requirements.txt  # Dependências
├── .env              # Variáveis de ambiente (criar a partir do .env.example)
├── README.md         # Este arquivo
└── Procfile          # Para deployment no Render
```

## Configuração

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/shopee-cupom.git
cd shopee-cupom
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` com as seguintes variáveis:
```
# API de Instagram (RapidAPI)
RAPIDAPI_KEY=sua_chave_rapid_api
RAPIDAPI_HOST=mediafy-api.p.rapidapi.com

# Configuração do ChatGPT Vision
OPENAI_API_KEY=sua_chave_openai

# Webhook n8n
WEBHOOK_URL=https://n8n.zapgrana.online/webhook-test/82616fd6-e936-45fd-a2e3-ab7c5ef60629

# Instagram user para monitorar
INSTAGRAM_USERNAME=shopee_brasil

# Database
DATABASE_URL=sqlite:///cupons.db
```

## Uso Local

Para iniciar o servidor localmente:

```bash
uvicorn app:app --reload
```

O servidor estará disponível em `http://localhost:8000`.

## Endpoints da API

- `GET /`: Status do serviço
- `POST /monitor`: Iniciar monitoramento manual
- `GET /cupons`: Listar todos os cupons encontrados
- `GET /status`: Status do scheduler

## Deploy no Render

1. Conecte seu repositório GitHub ao Render
2. Crie um novo Web Service
3. Selecione seu repositório
4. Configure:
   - Nome: `shopee-cupom`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Adicione as variáveis de ambiente do arquivo `.env`
6. Clique em "Create Web Service"

## Notas de Funcionamento

- O sistema monitora os stories da Shopee 10 minutos antes, durante, e 10 minutos depois de cada hora, entre 9h e 0h
- Utiliza ChatGPT Vision para identificar códigos de cupom nas imagens
- Salva todos os cupons em banco de dados e envia via webhook apenas uma vez
- Imagens são armazenadas temporariamente para processamento

## Licença

Este projeto está licenciado sob a MIT License. 