# Shopee Cupom Monitor

Sistema automatizado para monitorar e extrair cupons promocionais da Shopee a partir de stories do Instagram e sites de promoções.

## Funcionalidades

- Monitoramento automático de stories do Instagram da Shopee
- Extração de códigos de cupom usando OpenAI Vision API
- Web scraping de sites de promoções
- Interface web para gerenciamento e visualização de cupons
- Ferramentas administrativas para testes e adição manual

## Configuração Local

1. Clone o repositório
2. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```
   RAPIDAPI_KEY=sua_chave_da_rapidapi
   RAPIDAPI_HOST=mediafy-api.p.rapidapi.com
   INSTAGRAM_USERNAME=shopee_br
   URL_EMBED_SAFE=true
   OPENAI_API_KEY=sua_chave_da_openai
   ```
3. Instale as dependências: `pip install -r requirements.txt`
4. Execute o servidor: `python app.py`

## Configuração no Render

Ao implantar no Render, configure as seguintes variáveis de ambiente no painel de configuração:

1. Acesse o dashboard do Render
2. Selecione o serviço do aplicativo
3. Vá para "Environment"
4. Adicione as seguintes variáveis:
   - `RAPIDAPI_KEY` - Sua chave API da RapidAPI (MediaFy API)
   - `RAPIDAPI_HOST` - mediafy-api.p.rapidapi.com
   - `INSTAGRAM_USERNAME` - shopee_br
   - `URL_EMBED_SAFE` - true
   - `OPENAI_API_KEY` - Sua chave API da OpenAI

## Notas de Versão (Maio 2025)

A aplicação foi atualizada para usar os modelos mais recentes da OpenAI:
* O modelo `gpt-4-vision-preview` foi descontinuado e substituído por `gpt-4o` para análise de imagens
* Foi adicionado tratamento de erro para lidar com as mudanças na API da OpenAI

## Endpoints da API

- `/` - Status do servidor
- `/cupons` - Interface web para visualização de cupons
- `/monitor` - Trigger manual para verificação de stories
- `/scrape` - Trigger manual para scraping de sites
- `/api/cupons` - Lista de cupons em formato JSON
- `/test-image-direct` - Testar extração diretamente de uma imagem
- `/test-vision` - Testar extração usando OpenAI Vision API
- `/add-cupom` - Adicionar cupom manualmente
- `/status` - Status detalhado do servidor e tarefas agendadas

## Troubleshooting

Se encontrar o erro "UTF-8 codec can't decode byte 0xff" no Render:
1. Verifique se configurou todas as variáveis de ambiente corretamente no painel do Render
2. Não é necessário fazer upload de arquivo `.env` no Render, o sistema usará as variáveis de ambiente configuradas na plataforma

Se encontrar o erro "The model `gpt-4-vision-preview` has been deprecated":
1. O código já foi atualizado para usar o novo modelo `gpt-4o`
2. Verifique se você tem acesso a este modelo em sua conta OpenAI
3. A chave OPENAI_API_KEY deve ser de uma conta com acesso ao modelo `gpt-4o`

## Tecnologias Utilizadas

- FastAPI - Framework web
- OpenAI Vision API - Extração de texto das imagens
- RapidAPI (MediaFy API) - Acesso aos stories do Instagram
- APScheduler - Agendamento de tarefas
- SQLAlchemy - ORM para banco de dados
- BeautifulSoup - Web scraping 