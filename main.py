"""
Ponto de entrada principal da aplicação FastAPI.

Este módulo configura e inicializa a aplicação FastAPI com todas as suas
dependências, middlewares, rotas e configurações de ciclo de vida.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import configure_logging, settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gerencia o ciclo de vida da aplicação FastAPI.
    
    Configura recursos necessários durante o startup e limpa recursos
    durante o shutdown da aplicação.
    
    Args:
        app: Instância da aplicação FastAPI
        
    Yields:
        None: Controle para execução da aplicação
    """
    # === STARTUP ===
    configure_logging()
    
    yield
    
    # === SHUTDOWN ===
    # TODO: Implementar limpeza de recursos (conexões DB, cache, etc.)
    pass


def create_app() -> FastAPI:
    """
    Cria e configura a aplicação FastAPI.
    
    Configura middlewares, rotas, documentação e todas as dependências
    necessárias para o funcionamento da API.
    
    Returns:
        FastAPI: Instância configurada da aplicação
    """
    
    # === CRIAÇÃO DA APLICAÇÃO ===
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API para processamento automatizado de documentos fiscais eletrônicos",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # === CONFIGURAÇÃO DE CORS ===
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # === REGISTRO DE ROTAS ===
    from app.api.routes import health, documents, jobs
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    
    return app


# === INSTÂNCIA GLOBAL DA APLICAÇÃO ===
app = create_app()


if __name__ == "__main__":
    """Execução direta do servidor para desenvolvimento."""
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

