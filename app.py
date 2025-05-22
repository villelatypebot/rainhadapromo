import os
import time
import pytz
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import uvicorn
import logging

from monitor import monitor_stories
from database import get_db, Cupom, get_latest_cupons
from scrapers import run_all_scrapers

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shopee_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("shopee_app")

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

@app.get("/api/cupons")
def get_cupons(db=Depends(get_db), origem: str = None, limit: int = 50):
    """Retorna todos os cupons encontrados como JSON"""
    query = db.query(Cupom).order_by(Cupom.data_criacao.desc())
    
    if origem:
        query = query.filter(Cupom.origem == origem)
        
    cupons = query.limit(limit).all()
    return [cupom.to_dict() for cupom in cupons]

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