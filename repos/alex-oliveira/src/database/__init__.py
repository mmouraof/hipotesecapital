
from sqlalchemy import create_engine, Column, String, Integer, Date, Numeric, ForeignKey, Text, inspect
from sqlalchemy.orm import DeclarativeBase, Session
from dotenv import load_dotenv
import os


load_dotenv()


DB_CONFIG = {
    "username": os.getenv("USERNAME"),
    "password": os.getenv("PASSWORD"),
    "host": "localhost",
    "port": 3306,         
    "database": "HipoteseCapital",
    "owner": os.getenv("OWNER"), 
}

DRIVER = "mysql+pymysql"

DATABASE_URL = (
    f"{DRIVER}://{DB_CONFIG['username']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

engine = create_engine(DATABASE_URL, echo=False)




class Base(DeclarativeBase):
    pass


class Ativo(Base):
    __tablename__ = "Ativos"

    Ticker                  = Column(String(255),  primary_key=True)
    EmpresaAtivo            = Column(String(20),   nullable=False)
    SetorAtuacaoEmpresa     = Column(String(255),  nullable=False)
    SegmentoAtuacaoEmpresa  = Column(String(255),  nullable=False)
    ResumoEmpresa           = Column(String(2000), nullable=False)


class DadosCotacao(Base):
    __tablename__ = "DadosCotacao"

    IDConsulta          = Column(Integer,       primary_key=True, autoincrement=True)
    DataConsulta        = Column(Date,          nullable=False)
    Ticker              = Column(String(20),    ForeignKey("Ativos.Ticker"), nullable=False)
    Cotacao             = Column(Numeric(10, 2))
    DataUltimaCotacao   = Column(Date,          nullable=False)
    Min52semanas        = Column(Numeric(10, 2))
    Max52semanas        = Column(Numeric(10, 2))
    VolumeMedio2Meses   = Column(Numeric(20, 2))
    ValorMercado        = Column(Numeric(30, 2))
    NumeroAcoes         = Column(Numeric(35, 2))
    DataUltimoBalanco   = Column(Date,          nullable=False)


class IndicadoresFundamentalistas(Base):
    __tablename__ = "IndicadoresFundamentalistas"

    IDConsulta          = Column(Integer,       primary_key=True, autoincrement=True)
    DataConsulta        = Column(Date,          nullable=False)
    Ticker              = Column(String(20),    ForeignKey("Ativos.Ticker"), nullable=False)
    P_L                 = Column(Numeric(10, 2))
    ROE                 = Column(Numeric(10, 2))
    DividaLiquidaEBITDA = Column("DividaLiquida_EBITDA", Numeric(10, 2))
    MargemLiquida       = Column(Numeric(10, 2))
    DividendYield       = Column(Numeric(10, 2))


class Noticias(Base):
    __tablename__ = "Noticias"

    IDConsulta   = Column(Integer,    primary_key=True, autoincrement=True)
    DataConsulta = Column(Date,       primary_key=True, nullable=False)
    Ticker       = Column(String(20), ForeignKey("Ativos.Ticker"), nullable=False)
    URLNoticia   = Column(String(40), nullable=False)
    Resumo       = Column(String(500), nullable=False)
    Classificador= Column(String(10), nullable=False)
    Escala       = Column(Numeric(5, 2))