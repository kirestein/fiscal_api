"""
Sistema de logging estruturado para a aplicação.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def configure_logging() -> None:
    """Configura o sistema de logging estruturado."""
    
    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configurar logging padrão
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin para adicionar logging estruturado a classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Retorna logger com contexto da classe."""
        return get_logger(self.__class__.__name__)


def log_processing_event(
    event: str,
    document_id: str,
    **kwargs: Any
) -> None:
    """Log estruturado para eventos de processamento."""
    logger = get_logger("processing")
    logger.info(
        event,
        document_id=document_id,
        **kwargs
    )


def log_integration_event(
    event: str,
    service: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """Log estruturado para eventos de integração."""
    logger = get_logger("integration")
    logger.info(
        event,
        service=service,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_security_event(
    event: str,
    user_id: str,
    action: str,
    resource: str,
    **kwargs: Any
) -> None:
    """Log estruturado para eventos de segurança."""
    logger = get_logger("security")
    logger.info(
        event,
        user_id=user_id,
        action=action,
        resource=resource,
        **kwargs
    )

