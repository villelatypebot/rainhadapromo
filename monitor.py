import os
import time
import json
import requests
import logging
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv

from coupon_extractor import extract_with_vision
from database import save_cupom, cupom_exists, mark_cupom_sent
from webhook import send_to_webhook

load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shopee_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("shopee_monitor")

# Variáveis de configuração
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "mediafy-api.p.rapidapi.com")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "shopee_br")

# Fuso horário de Brasília
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

def check_is_monitoring_time():
    """
    Verifica se o horário atual é adequado para monitoramento
    Monitora:
    - 10 min antes e 10 min depois de cada hora cheia
    - Entre 9h e 00h
    """
    # Usar o fuso horário do Brasil
    now = datetime.now(BRAZIL_TZ)
    
    # Se for entre 1h e 8h, não monitora
    if 1 <= now.hour < 9:
        return False
    
    # Verifica se estamos próximos de uma hora cheia
    minutes = now.minute
    return minutes >= 50 or minutes <= 10

def get_stories():
    """
    Busca os stories do perfil configurado
    
    Returns:
        list: Lista de itens de stories ou None em caso de erro
    """
    url = f"https://mediafy-api.p.rapidapi.com/v1/stories"
    
    querystring = {"username_or_id_or_url": INSTAGRAM_USERNAME}
    
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        data = response.json()
        
        if "data" in data and "items" in data["data"]:
            return data["data"]["items"]
        else:
            logger.error(f"Formato de resposta inesperado: {data}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao buscar stories: {str(e)}")
        return None

def process_story_item(item):
    """
    Processa um item de story para extrair o cupom
    
    Args:
        item: Item do story do Instagram
        
    Returns:
        dict: Informações do cupom encontrado ou None se não houver cupom
    """
    try:
        # Verificar se é uma imagem (não vídeo)
        if item.get("is_video") or item.get("media_type") != 1:
            logger.info("Item ignorado: não é uma imagem")
            return None
        
        # Obter URL da imagem de melhor qualidade
        image_url = None
        image_versions = item.get("image_versions", {}).get("items", [])
        
        if image_versions:
            # Pegar a versão de maior resolução
            image_url = image_versions[0].get("url")
        
        if not image_url:
            logger.warning("URL da imagem não encontrada")
            return None
            
        # Extrair o código do cupom da imagem usando Vision
        extraction_result = extract_with_vision(image_url)
        
        if not extraction_result.get("success"):
            logger.info(f"Nenhum cupom encontrado na imagem ou erro na extração: {extraction_result.get('error')}")
            return None
            
        # Obter o código e horário do cupom
        codigo = extraction_result.get("codigo")
        horario = extraction_result.get("horario")
        
        if not codigo:
            logger.info("Código do cupom não encontrado na imagem")
            return None
            
        # Verificar se o cupom já existe no banco de dados
        if cupom_exists(codigo):
            logger.info(f"Cupom {codigo} já processado anteriormente")
            return None
            
        # Salvar o novo cupom no banco de dados
        cupom_data = save_cupom(
            codigo=codigo,
            horario=horario,
            imagem_url=image_url,
            detalhes=json.dumps({"story_id": item.get("id"), "taken_at": item.get("taken_at")})
        )
        
        if cupom_data:
            logger.info(f"Novo cupom encontrado e salvo: {codigo}")
            return cupom_data
        else:
            logger.warning(f"Erro ao salvar o cupom {codigo}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao processar item do story: {str(e)}")
        return None

def monitor_stories():
    """
    Função principal para monitorar stories e processar cupons
    """
    # Log com horário do Brasil
    now_br = datetime.now(BRAZIL_TZ)
    logger.info(f"Iniciando monitoramento de stories - Horário Brasil: {now_br.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not check_is_monitoring_time():
        logger.info("Fora do horário de monitoramento, pulando verificação")
        return
    
    # Buscar stories recentes
    stories = get_stories()
    
    if not stories:
        logger.warning("Nenhum story encontrado ou erro na API")
        return
    
    logger.info(f"Encontrados {len(stories)} stories para analisar")
    
    # Processar cada story
    for item in stories:
        cupom_data = process_story_item(item)
        
        if cupom_data:
            # Enviar para webhook
            webhook_success = send_to_webhook(cupom_data)
            
            if webhook_success:
                mark_cupom_sent(cupom_data["codigo"])
                logger.info(f"Cupom {cupom_data['codigo']} enviado com sucesso para webhook")
            else:
                logger.error(f"Falha ao enviar cupom {cupom_data['codigo']} para webhook")
    
    logger.info("Monitoramento finalizado")

if __name__ == "__main__":
    monitor_stories() 