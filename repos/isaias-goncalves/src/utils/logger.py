import logging
import sys
import os
from pathlib import Path

def setup_logger(name: str = "case_finance") -> logging.Logger:
    """
    Configura um logger centralizado para o projeto com saída para console e arquivo.
    """
    logger = logging.getLogger(name)
    
    # Nível do logger vindo do ENV ou padrão INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level))
        
        # Formato da mensagem
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para Console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler para Arquivo
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "app.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# Instância padrão para uso rápido
logger = setup_logger()
