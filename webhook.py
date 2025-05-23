import os
import json
import requests
import logging
from dotenv import load_dotenv

# Configurar logging básico caso não esteja configurado
logger = logging.getLogger("shopee_monitor")

# Tentar carregar o arquivo .env, mas não falhar se não existir
try:
    load_dotenv()
    logger.info("Arquivo .env carregado com sucesso em webhook.py")
except Exception as e:
    logger.warning(f"Aviso: Não foi possível carregar o arquivo .env em webhook.py: {str(e)}")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://webhook.zapgrana.online/webhook/82616fd6-e936-45fd-a2e3-ab7c5ef60629")

def send_to_webhook(cupom_data):
    """
    Envia os dados do cupom para o webhook do n8n
    
    Args:
        cupom_data: Dicionário com dados do cupom
        
    Returns:
        bool: True se o envio foi bem-sucedido, False caso contrário
    """
    try:
        # Preparar dados para o webhook
        # Enviar apenas o código do cupom e horário se disponível
        payload = {
            "codigo": cupom_data["codigo"],
            "horario": cupom_data.get("horario", ""),
            "imagem_url": cupom_data.get("imagem_url", "")
        }
        
        # Log dos dados que serão enviados
        logger.info(f"Enviando para webhook: {json.dumps(payload)}")
        
        # Fazer requisição POST para o webhook
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Verificar se houve sucesso (2xx)
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Webhook enviado com sucesso: {response.status_code}")
            return True
        else:
            logger.error(f"Erro no webhook: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exceção ao enviar webhook: {str(e)}")
        return False 
