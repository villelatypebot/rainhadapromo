import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
from database import save_cupom, cupom_exists

# Configurar logging
logger = logging.getLogger("shopee_scraper")

# Fuso horário de Brasília
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

def parse_validade(texto):
    """
    Analisa textos como "há 1 dia" ou "há 3 dias" para determinar validade
    """
    try:
        if not texto or "há" not in texto:
            # Se não conseguir determinar, define validade de 1 dia
            return datetime.now(BRAZIL_TZ) + timedelta(days=1)
            
        match = re.search(r'há\s+(\d+)\s+(dia|dias)', texto)
        if match:
            dias = int(match.group(1))
            # Consideramos válido por 7 dias após postagem
            data_postagem = datetime.now(BRAZIL_TZ) - timedelta(days=dias)
            data_validade = data_postagem + timedelta(days=7)
            return data_validade
            
        return datetime.now(BRAZIL_TZ) + timedelta(days=1)
    except Exception as e:
        logger.error(f"Erro ao analisar validade: {str(e)}")
        return datetime.now(BRAZIL_TZ) + timedelta(days=1)

def scrape_promos_geniais():
    """
    Raspa cupons do site PromoGeniais
    """
    try:
        logger.info("Iniciando scraping do PromoGeniais")
        cupons_encontrados = []
        
        # Fazer requisição para a página de cupons da Shopee
        response = requests.get("https://promosgeniaisdaju.com.br/lojas/shopee?tab=coupons", 
                               headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Procurar por elementos de cupom
        cupom_divs = soup.select('.sc-ebcb22be-2')
        
        for div in cupom_divs:
            try:
                # Extrair informações do cupom
                titulo_elemento = div.select_one('h3')
                descricao_elemento = div.select_one('h3 + div')
                
                titulo = titulo_elemento.text.strip() if titulo_elemento else "Cupom Shopee"
                descricao = descricao_elemento.text.strip() if descricao_elemento else None
                
                # Valor desconto e codigo
                desconto_match = re.search(r'R\$\s*(\d+[,.]\d+|\d+)\s+de\s+desconto', div.text)
                codigo_button = div.find('button', string=re.compile('Pegar cupom', re.IGNORECASE))
                
                validade_text = div.find(string=re.compile('há\s+\d+\s+dia', re.IGNORECASE))
                validade = parse_validade(validade_text)
                
                valor_desconto = desconto_match.group(0) if desconto_match else None
                codigo = None
                
                # Obter código do cupom
                if codigo_button:
                    codigo_texto = codigo_button.find_next('div')
                    if codigo_texto:
                        codigo = codigo_texto.text.strip()
                
                # Se não conseguiu extrair código, tenta usar classes específicas ou outros padrões
                if not codigo:
                    # Buscar por padrões de código de cupom (geralmente alfanuméricos)
                    codigo_match = re.search(r'[A-Z0-9]{5,}', div.text)
                    if codigo_match:
                        codigo = codigo_match.group(0)
                
                # Se encontrou um código de cupom, salva no banco
                if codigo and not cupom_exists(codigo):
                    cupom_data = save_cupom(
                        codigo=codigo,
                        descricao=descricao,
                        valor_desconto=valor_desconto,
                        valido_ate=validade,
                        origem="site_promos"
                    )
                    if cupom_data:
                        logger.info(f"Cupom encontrado e salvo: {codigo}")
                        cupons_encontrados.append(cupom_data)
                        
            except Exception as e:
                logger.error(f"Erro ao processar item de cupom: {str(e)}")
                continue
                
        return cupons_encontrados
        
    except Exception as e:
        logger.error(f"Erro ao fazer scraping: {str(e)}")
        return []

def run_all_scrapers():
    """
    Executa todos os scrapers disponíveis
    """
    all_results = []
    
    # PromoGeniais
    promos_results = scrape_promos_geniais()
    if promos_results:
        all_results.extend(promos_results)
        
    # Aqui você pode adicionar mais scrapers no futuro
    
    logger.info(f"Scraping finalizado. Total de cupons encontrados: {len(all_results)}")
    return all_results

if __name__ == "__main__":
    # Configuração de logging para execução independente
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    run_all_scrapers() 