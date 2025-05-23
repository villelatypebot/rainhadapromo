import os
import time
import pytz
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import uvicorn
import logging

# Configurar logging antes de importar outros módulos
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shopee_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("shopee_app")

# Tentar carregar o arquivo .env, mas não falhar se não existir
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Arquivo .env carregado com sucesso")
except Exception as e:
    logger.warning(f"Aviso: Não foi possível carregar o arquivo .env: {str(e)}")

from monitor import monitor_stories, process_story_item
from database import get_db, Cupom, get_latest_cupons, save_cupom
from scrapers import run_all_scrapers
from coupon_extractor import extract_with_vision

app = FastAPI(
    title="Shopee Cupom Monitor",
    description="Sistema para monitorar e extrair cupons de stories do Instagram da Shopee",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fuso horário de Brasília
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

# Criar o scheduler com fuso horário do Brasil
scheduler = BackgroundScheduler(timezone=BRAZIL_TZ)

# Configurar tarefas agendadas
# Monitora 10min antes e 10min depois de cada hora entre 9h e 0h
for hour in range(9, 24):
    # 10 minutos antes de cada hora
    scheduler.add_job(
        monitor_stories,
        CronTrigger(hour=hour, minute=50, timezone=BRAZIL_TZ),
        id=f"monitor_pre_{hour}"
    )
    
    # Na hora exata
    scheduler.add_job(
        monitor_stories,
        CronTrigger(hour=hour, minute=0, timezone=BRAZIL_TZ),
        id=f"monitor_exact_{hour}"
    )
    
    # 10 minutos depois de cada hora
    scheduler.add_job(
        monitor_stories,
        CronTrigger(hour=hour, minute=10, timezone=BRAZIL_TZ),
        id=f"monitor_post_{hour}"
    )

# Adicionar meia-noite
scheduler.add_job(
    monitor_stories,
    CronTrigger(hour=0, minute=0, timezone=BRAZIL_TZ),
    id="monitor_midnight"
)

scheduler.add_job(
    monitor_stories,
    CronTrigger(hour=0, minute=10, timezone=BRAZIL_TZ),
    id="monitor_post_midnight"
)

# Adicionar job para scraping de sites
# Roda a cada 1 hora durante o dia
for hour in range(9, 24):
    scheduler.add_job(
        run_all_scrapers,
        CronTrigger(hour=hour, minute=30, timezone=BRAZIL_TZ),
        id=f"scraper_{hour}"
    )

# Rodar scrapers na inicialização
scheduler.add_job(
    run_all_scrapers,
    id="initial_scraping",
    trigger="date",
    run_date=datetime.now(BRAZIL_TZ) + timedelta(seconds=30)
)

# Iniciar o scheduler quando o app iniciar
@app.on_event("startup")
def startup_event():
    scheduler.start()
    logger.info(f"Aplicação iniciada e scheduler configurado - Horário Brasil: {datetime.now(BRAZIL_TZ).strftime('%Y-%m-%d %H:%M:%S')}")

# Parar o scheduler quando o app for encerrado
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    logger.info("Aplicação encerrada e scheduler desligado")

# Endpoints da API
@app.get("/")
def read_root():
    return {
        "app": "Shopee Cupom Monitor",
        "status": "online",
        "time": datetime.now(BRAZIL_TZ).isoformat(),
        "timezone": "America/Sao_Paulo (GMT-3)"
    }

@app.get("/cupons", response_class=HTMLResponse)
def view_cupons():
    """Página HTML para visualizar cupons"""
    # Retornar o arquivo HTML diretamente
    return FileResponse("cupons.html")

@app.post("/monitor")
def trigger_monitor(background_tasks: BackgroundTasks):
    """Endpoint para iniciar o monitoramento manualmente"""
    background_tasks.add_task(monitor_stories)
    return {"status": "monitoramento iniciado"}

@app.post("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    """Endpoint para iniciar o scraping manualmente"""
    background_tasks.add_task(run_all_scrapers)
    return {"status": "scraping iniciado"}

@app.post("/test-image-direct")
def test_image_direct(image_url: str = Form(...)):
    """
    Testa a extração de um cupom de uma URL de imagem diretamente,
    simulando um item de story do Instagram
    """
    try:
        # Criar um objeto de story mockado com o mínimo necessário
        mock_story = {
            "id": "test_story",
            "media_type": 1,  # Tipo de mídia para imagem
            "image_versions": {
                "items": [
                    {"url": image_url}
                ]
            },
            "taken_at": int(time.time())
        }
        
        # Usar a função process_story_item do monitor.py
        logger.info(f"Testando extração direta com imagem: {image_url}")
        cupom_data = process_story_item(mock_story)
        
        if cupom_data:
            logger.info(f"Cupom encontrado com sucesso: {cupom_data}")
            return {
                "status": "success", 
                "message": "Cupom extraído e salvo com sucesso", 
                "cupom": cupom_data
            }
        else:
            return {
                "status": "error", 
                "message": "Nenhum cupom encontrado na imagem ou erro na extração"
            }
    except Exception as e:
        logger.error(f"Erro ao testar imagem diretamente: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/add-cupom")
def add_cupom_manual(
    codigo: str = Form(...), 
    descricao: str = Form(None), 
    valor_desconto: str = Form(None),
    valido_ate: str = Form(None),
    db=Depends(get_db)
):
    """Endpoint para adicionar um cupom manualmente"""
    try:
        # Usar a função save_cupom para garantir consistência
        cupom_data = save_cupom(
            codigo=codigo,
            descricao=descricao,
            valor_desconto=valor_desconto,
            valido_ate=valido_ate,
            origem="manual"
        )
        
        if cupom_data:
            logger.info(f"Cupom adicionado manualmente: {codigo}")
            return {"status": "success", "cupom": cupom_data}
        else:
            return {"status": "error", "message": "Erro ao salvar cupom"}
    except Exception as e:
        logger.error(f"Erro ao adicionar cupom manual: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/test-vision")
def test_vision_api(image_url: str = Form(...)):
    """Testa a extração de cupom usando a API Vision"""
    try:
        # Usar a função de extração com Vision
        result = extract_with_vision(image_url)
        
        if result.get("success"):
            # Se encontrou um cupom, tentar salvá-lo
            codigo = result.get("codigo")
            if codigo:
                save_cupom(
                    codigo=codigo,
                    descricao=result.get("descricao"),
                    valor_desconto=result.get("valor_desconto"),
                    valido_ate=result.get("horario"),
                    imagem_url=image_url,
                    origem="instagram"
                )
                logger.info(f"Cupom extraído e salvo via teste: {codigo}")
                
            return {"status": "success", "result": result}
        else:
            return {"status": "error", "message": result.get("error") or "Nenhum cupom encontrado"}
    except Exception as e:
        logger.error(f"Erro ao testar extração via Vision: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/cupons")
def get_cupons(db=Depends(get_db), origem: str = None, limit: int = 50):
    """Retorna todos os cupons encontrados como JSON"""
    query = db.query(Cupom).order_by(Cupom.data_criacao.desc())
    
    if origem:
        query = query.filter(Cupom.origem == origem)
        
    cupons = query.limit(limit).all()
    return [cupom.to_dict() for cupom in cupons]

@app.post("/webhook/send-cupom")
def send_cupom_webhook(codigo: str = Form(...)):
    """Envia um cupom específico para o webhook"""
    try:
        db = get_db()
        cupom = db.query(Cupom).filter(Cupom.codigo == codigo).first()
        
        if not cupom:
            return {"status": "error", "message": "Cupom não encontrado"}
        
        # Preparar dados para o webhook
        cupom_data = {
            "codigo": cupom.codigo,
            "horario": cupom.horario,
            "imagem_url": cupom.imagem_url
        }
        
        # Enviar para o webhook
        webhook_success = send_to_webhook(cupom_data)
        
        if webhook_success:
            # Marcar como enviado no banco de dados
            mark_cupom_sent(cupom.codigo)
            return {"status": "success", "message": f"Cupom {cupom.codigo} enviado com sucesso para o webhook"}
        else:
            return {"status": "error", "message": "Erro ao enviar para webhook"}
    
    except Exception as e:
        logger.error(f"Erro ao enviar cupom para webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/webhook/send-all")
def send_all_cupons_webhook():
    """Envia todos os cupons não enviados para o webhook"""
    try:
        db = get_db()
        cupons = db.query(Cupom).filter(Cupom.enviado == False).all()
        
        if not cupons:
            return {"status": "info", "message": "Não há cupons pendentes para enviar"}
        
        total = len(cupons)
        success = 0
        
        for cupom in cupons:
            # Preparar dados para o webhook
            cupom_data = {
                "codigo": cupom.codigo,
                "horario": cupom.horario,
                "imagem_url": cupom.imagem_url
            }
            
            # Enviar para o webhook
            webhook_success = send_to_webhook(cupom_data)
            
            if webhook_success:
                # Marcar como enviado no banco de dados
                mark_cupom_sent(cupom.codigo)
                success += 1
                logger.info(f"Cupom {cupom.codigo} enviado com sucesso para o webhook")
            else:
                logger.error(f"Erro ao enviar cupom {cupom.codigo} para webhook")
        
        return {
            "status": "success", 
            "message": f"{success} de {total} cupons enviados com sucesso para o webhook"
        }
    
    except Exception as e:
        logger.error(f"Erro ao enviar cupons para webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/webhook/status")
def webhook_status():
    """Retorna o status de envio dos cupons para o webhook"""
    try:
        db = get_db()
        total_cupons = db.query(Cupom).count()
        enviados = db.query(Cupom).filter(Cupom.enviado == True).count()
        pendentes = db.query(Cupom).filter(Cupom.enviado == False).count()
        
        # Listar os últimos 5 cupons enviados
        ultimos_enviados = db.query(Cupom).filter(Cupom.enviado == True).order_by(Cupom.data_criacao.desc()).limit(5).all()
        
        # Listar os cupons pendentes de envio
        cupons_pendentes = db.query(Cupom).filter(Cupom.enviado == False).order_by(Cupom.data_criacao.desc()).all()
        
        return {
            "status": "success",
            "total_cupons": total_cupons,
            "enviados": enviados,
            "pendentes": pendentes,
            "ultimos_enviados": [c.to_dict() for c in ultimos_enviados],
            "cupons_pendentes": [c.to_dict() for c in cupons_pendentes]
        }
    
    except Exception as e:
        logger.error(f"Erro ao obter status do webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/status")
def get_status():
    """Retorna o status do serviço"""
    jobs = scheduler.get_jobs()
    
    # Formatar informações das tarefas agendadas
    jobs_info = []
    for job in jobs:
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs_info.append({
            "id": job.id,
            "next_run": next_run
        })
        
    return {
        "status": "online",
        "scheduler_running": scheduler.running,
        "jobs_count": len(jobs),
        "next_jobs": jobs_info[:5],  # Mostra apenas os próximos 5 jobs
        "current_time": datetime.now(BRAZIL_TZ).isoformat(),
        "timezone": "America/Sao_Paulo (GMT-3)"
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 