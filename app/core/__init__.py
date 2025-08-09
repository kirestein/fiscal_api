"""
Módulo core da aplicação.

Contém configurações, logging, e utilitários centrais.
"""

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

__all__ = ["settings", "configure_logging", "get_logger"]

