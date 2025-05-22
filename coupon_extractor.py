import os
import re
import json
import requests
import openai
from dotenv import load_dotenv

load_dotenv()

# Configurar a API key
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        # Criar client do OpenAI (nova forma de usar a API)
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
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
        
        # Extrair a resposta (nova estrutura de resposta)
        content = response.choices[0].message.content
        
        # Registrar a resposta completa para debug
        print(f"Resposta da API Vision: {content}")
        
        # Tentar encontrar e analisar o JSON na resposta
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            # Tentar extrair o JSON de outra forma
            try:
                result = json.loads(content)
            except:
                # Análise manual com regex melhorado
                codigo_match = re.search(r'codigo["\'s:\s]+([A-Z0-9]+)', content, re.IGNORECASE)
                horario_match = re.search(r'horario["\'s:\s]+([0-9]+H)', content, re.IGNORECASE)
                
                # Fallback para caso o regex não encontre mas o texto contenha o código
                if not codigo_match:
                    # Procurar por sequências que pareçam códigos de cupom (caracteres maiúsculos e números)
                    fallback_codigo = re.search(r'([A-Z0-9]{7,12})', content)
                    if fallback_codigo:
                        codigo_value = fallback_codigo.group(1)
                    else:
                        codigo_value = None
                else:
                    codigo_value = codigo_match.group(1)
                
                result = {
                    "codigo": codigo_value,
                    "horario": horario_match.group(1) if horario_match else None
                }
        
        # Adicionar mais informações extraídas se disponíveis
        descricao_match = re.search(r'(cupom exclusivo|por tempo limitado|frete gr[áa]tis)', content, re.IGNORECASE)
        valor_match = re.search(r'(R\$\s*\d+|\d+%\s*OFF|\d+\s*REAIS)', content, re.IGNORECASE)
        
        result["descricao"] = descricao_match.group(0) if descricao_match else None
        result["valor_desconto"] = valor_match.group(0) if valor_match else None
        
        if result.get("codigo"):
            return {
                "codigo": result.get("codigo"),
                "horario": result.get("horario"),
                "descricao": result.get("descricao"),
                "valor_desconto": result.get("valor_desconto"),
                "success": True
            }
        else:
            return {"success": False, "error": "Código não encontrado na imagem"}
            
    except Exception as e:
        print(f"Erro na extração com Vision API: {str(e)}")
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