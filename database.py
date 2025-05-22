import os
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cupons.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Cupom(Base):
    __tablename__ = "cupons"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, index=True)
    horario = Column(String(10), nullable=True)
    imagem_url = Column(String(500), nullable=True)
    processed_image_url = Column(String(500), nullable=True)
    data_criacao = Column(DateTime, default=datetime.now)
    enviado = Column(Boolean, default=False)
    detalhes = Column(Text, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "horario": self.horario,
            "imagem_url": self.imagem_url,
            "processed_image_url": self.processed_image_url,
            "data_criacao": self.data_criacao.isoformat(),
            "enviado": self.enviado,
            "detalhes": self.detalhes
        }

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def cupom_exists(codigo):
    """Verifica se o cupom já existe no banco de dados"""
    db = get_db()
    return db.query(Cupom).filter(Cupom.codigo == codigo).first() is not None

def save_cupom(codigo, horario=None, imagem_url=None, detalhes=None):
    """Salva um novo cupom no banco de dados"""
    if cupom_exists(codigo):
        return False
    
    db = get_db()
    novo_cupom = Cupom(
        codigo=codigo,
        horario=horario,
        imagem_url=imagem_url,
        detalhes=detalhes
    )
    db.add(novo_cupom)
    db.commit()
    db.refresh(novo_cupom)
    return novo_cupom.to_dict()

def mark_cupom_sent(codigo):
    """Marca um cupom como enviado"""
    db = get_db()
    cupom = db.query(Cupom).filter(Cupom.codigo == codigo).first()
    if cupom:
        cupom.enviado = True
        db.commit()
        return True
    return False

def update_processed_image(codigo, processed_image_url):
    """Atualiza a URL da imagem processada"""
    db = get_db()
    cupom = db.query(Cupom).filter(Cupom.codigo == codigo).first()
    if cupom:
        cupom.processed_image_url = processed_image_url
        db.commit()
        return True
    return False

# Inicializar o banco de dados ao importar este módulo
init_db() 