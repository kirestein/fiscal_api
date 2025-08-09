"""
Configurações centralizadas da aplicação.

Este módulo centraliza todas as configurações da aplicação usando Pydantic Settings,
permitindo carregamento automático de variáveis de ambiente com validação de tipos.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente.
    
    Utiliza Pydantic Settings para validação automática de tipos e carregamento
    de configurações a partir de variáveis de ambiente ou arquivo .env.
    """
    
    # === CONFIGURAÇÕES DA APLICAÇÃO ===
    app_name: str = Field(default="Fiscal XML API", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # === CONFIGURAÇÕES DO SERVIDOR ===
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # === CONFIGURAÇÕES DO BANCO DE DADOS ===
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/fiscal_api",
        alias="DATABASE_URL"
    )
    
    # === CONFIGURAÇÕES DA API GOVERNAMENTAL ===
    government_api_base_url: str = Field(
        default="https://piloto-cbs.tributos.gov.br/servico/calculadora-consumo/api",
        alias="GOVERNMENT_API_BASE_URL"
    )
    government_api_timeout: int = Field(default=30, alias="GOVERNMENT_API_TIMEOUT")
    government_api_retry_attempts: int = Field(default=3, alias="GOVERNMENT_API_RETRY_ATTEMPTS")
    
    # === CONFIGURAÇÕES DE SEGURANÇA ===
    secret_key: str = Field(default="dev-secret-key", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")
    
    # === CONFIGURAÇÕES DE CACHE ===
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    
    # === CONFIGURAÇÕES DE MONITORAMENTO ===
    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    
    # === CONFIGURAÇÕES DE PROCESSAMENTO ===
    max_concurrent_jobs: int = Field(default=10, alias="MAX_CONCURRENT_JOBS")
    batch_size: int = Field(default=100, alias="BATCH_SIZE")
    processing_timeout_minutes: int = Field(default=30, alias="PROCESSING_TIMEOUT_MINUTES")
    
    class Config:
        """Configurações do Pydantic Settings."""
        env_file = ".env"
        case_sensitive = False


# Instância global das configurações - carregada automaticamente na inicialização
settings = Settings()

