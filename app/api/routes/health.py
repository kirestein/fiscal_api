"""
Endpoints de health check e status da aplicação.
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from app.core import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check básico da aplicação.
    
    Returns:
        Dict com status da aplicação
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "service": settings.app_name
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """
    Readiness check para Kubernetes.
    
    Returns:
        Dict com status de prontidão
    """
    # TODO: Verificar dependências (banco, APIs externas)
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "ok",  # TODO: Implementar check real
            "government_api": "ok"  # TODO: Implementar check real
        }
    }


@router.get("/metrics")
async def metrics() -> Dict[str, float]:
    """
    Métricas básicas da aplicação.
    
    Returns:
        Dict com métricas da aplicação
    """
    # TODO: Implementar métricas reais
    
    return {
        "uptime_seconds": 0,  # TODO: Calcular uptime real
        "requests_total": 0,  # TODO: Contador real
        "active_jobs": 0,  # TODO: Jobs ativos
        "memory_usage_mb": 0,  # TODO: Uso de memória
        "cpu_usage_percent": 0  # TODO: Uso de CPU
    }

