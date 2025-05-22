import os
import re
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_with_vision(image_url):
    """
    Extrair código de cupom de uma imagem usando OpenAI Vision
    
    Args:
        image_url: URL da imagem a ser analisada
        
    Returns:
        dict: {
            'codigo': string com o código do cupom,
            'horario': string com o horário do cupom (se encontrado),
            'success': boolean indicando se a extração foi bem-sucedida
        }
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em extrair informações de cupons da Shopee. "
                               "Extraia apenas o código do cupom e, se visível, o horário."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analise esta imagem de um cupom da Shopee e extraia: 1) O código do cupom (geralmente em destaque e em caracteres alfanuméricos); 2) O horário de validade do cupom, se estiver visível (ex: '19H'). Responda APENAS com um objeto JSON contendo 'codigo' e 'horario' (pode ser null se não estiver visível)."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            max_tokens=300
        )
        
        # Extrair a resposta
        content = response.choices[0].message.content
        
        # Tentar encontrar e analisar o JSON na resposta
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            # Tentar extrair o JSON de outra forma
            try:
                result = json.loads(content)
            except:
                # Análise manual
                codigo_match = re.search(r'codigo["\s:]+([A-Z0-9]+)', content, re.IGNORECASE)
                horario_match = re.search(r'horario["\s:]+([0-9]+H)', content, re.IGNORECASE)
                
                result = {
                    "codigo": codigo_match.group(1) if codigo_match else None,
                    "horario": horario_match.group(1) if horario_match else None
                }
        
        if result.get("codigo"):
            return {
                "codigo": result.get("codigo"),
                "horario": result.get("horario"),
                "success": True
            }
        else:
            return {"success": False, "error": "Código não encontrado na imagem"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def download_image(url):
    """Baixa uma imagem de uma URL e retorna o caminho para o arquivo local"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Criar diretório para imagens se não existir
        os.makedirs("images", exist_ok=True)
        
        # Criar um nome de arquivo baseado na URL
        filename = f"images/img_{hash(url)}.jpg"
        
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                
        return filename
    except Exception as e:
        print(f"Erro ao baixar imagem: {str(e)}")
        return None 