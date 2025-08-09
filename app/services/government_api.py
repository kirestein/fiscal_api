"""
Cliente para integração com APIs governamentais de cálculo tributário.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient, Response

from app.core.config import settings
from app.core.logging import LoggerMixin, log_integration_event
from app.models.fiscal import TaxDetails


class GovernmentAPIError(Exception):
    """Erro de integração com API governamental."""
    pass


class GovernmentAPIClient(LoggerMixin):
    """Cliente para APIs governamentais de cálculo tributário."""
    
    def __init__(self):
        self.base_url = settings.government_api_base_url
        self.timeout = settings.government_api_timeout
        self.retry_attempts = settings.government_api_retry_attempts
        self._client: Optional[AsyncClient] = None
    
    async def __aenter__(self):
        """Context manager entry."""
        self._client = AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "User-Agent": f"{settings.app_name}/{settings.app_version}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def calculate_ibs_cbs(
        self,
        ncm: str,
        cfop: str,
        base_value: Decimal,
        state_origin: str,
        state_destination: str
    ) -> TaxDetails:
        """
        Calcula IBS e CBS para um item específico.
        
        Args:
            ncm: Código NCM do produto
            cfop: Código CFOP da operação
            base_value: Valor base para cálculo
            state_origin: Estado de origem (UF)
            state_destination: Estado de destino (UF)
            
        Returns:
            Detalhes tributários calculados
            
        Raises:
            GovernmentAPIError: Se houver erro na API
        """
        start_time = datetime.utcnow()
        
        try:
            # Preparar payload
            payload = {
                "ncm": ncm,
                "cfop": cfop,
                "valorBase": str(base_value),
                "ufOrigem": state_origin,
                "ufDestino": state_destination,
                "dataOperacao": datetime.utcnow().strftime("%Y-%m-%d")
            }
            
            # Fazer requisição com retry
            response = await self._make_request_with_retry(
                "POST",
                "/calculo/ibs-cbs",
                json=payload
            )
            
            # Processar resposta
            data = response.json()
            
            # Extrair valores calculados
            tax_details = TaxDetails(
                ibs_base=base_value,
                ibs_rate=Decimal(str(data.get("aliquotaIBS", "0"))),
                ibs_value=Decimal(str(data.get("valorIBS", "0"))),
                cbs_base=base_value,
                cbs_rate=Decimal(str(data.get("aliquotaCBS", "0"))),
                cbs_value=Decimal(str(data.get("valorCBS", "0")))
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_integration_event(
                "ibs_cbs_calculated",
                "government_api",
                "/calculo/ibs-cbs",
                response.status_code,
                duration_ms,
                ncm=ncm,
                cfop=cfop,
                ibs_value=float(tax_details.ibs_value),
                cbs_value=float(tax_details.cbs_value)
            )
            
            return tax_details
            
        except httpx.HTTPStatusError as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_integration_event(
                "ibs_cbs_calculation_failed",
                "government_api",
                "/calculo/ibs-cbs",
                e.response.status_code,
                duration_ms,
                error=str(e)
            )
            
            raise GovernmentAPIError(
                f"Erro na API governamental: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.error(
                "ibs_cbs_calculation_error",
                error=str(e),
                duration_ms=duration_ms,
                ncm=ncm,
                cfop=cfop
            )
            
            raise GovernmentAPIError(f"Erro no cálculo IBS/CBS: {str(e)}")
    
    async def calculate_selective_tax(
        self,
        ncm: str,
        base_value: Decimal,
        product_type: str = "default"
    ) -> Decimal:
        """
        Calcula Imposto Seletivo para um produto.
        
        Args:
            ncm: Código NCM do produto
            base_value: Valor base para cálculo
            product_type: Tipo de produto (bebidas, fumo, etc.)
            
        Returns:
            Valor do Imposto Seletivo calculado
        """
        start_time = datetime.utcnow()
        
        try:
            # Preparar payload
            payload = {
                "ncm": ncm,
                "valorBase": str(base_value),
                "tipoProduto": product_type,
                "dataOperacao": datetime.utcnow().strftime("%Y-%m-%d")
            }
            
            # Fazer requisição
            response = await self._make_request_with_retry(
                "POST",
                "/calculo/imposto-seletivo",
                json=payload
            )
            
            data = response.json()
            selective_tax_value = Decimal(str(data.get("valorImpostoSeletivo", "0")))
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_integration_event(
                "selective_tax_calculated",
                "government_api",
                "/calculo/imposto-seletivo",
                response.status_code,
                duration_ms,
                ncm=ncm,
                selective_tax_value=float(selective_tax_value)
            )
            
            return selective_tax_value
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.error(
                "selective_tax_calculation_error",
                error=str(e),
                duration_ms=duration_ms,
                ncm=ncm
            )
            
            # Retornar zero em caso de erro (fallback)
            return Decimal("0")
    
    async def validate_xml_structure(self, xml_content: str) -> Dict[str, any]:
        """
        Valida estrutura XML através da API governamental.
        
        Args:
            xml_content: Conteúdo XML para validação
            
        Returns:
            Resultado da validação
        """
        start_time = datetime.utcnow()
        
        try:
            # Preparar payload
            payload = {
                "xmlContent": xml_content,
                "tipoDocumento": "NFe"
            }
            
            # Fazer requisição
            response = await self._make_request_with_retry(
                "POST",
                "/validacao/xml",
                json=payload
            )
            
            data = response.json()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_integration_event(
                "xml_validation_completed",
                "government_api",
                "/validacao/xml",
                response.status_code,
                duration_ms,
                valid=data.get("valido", False)
            )
            
            return data
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.error(
                "xml_validation_error",
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Retornar resultado de fallback
            return {
                "valido": False,
                "erros": [f"Erro na validação: {str(e)}"],
                "avisos": []
            }
    
    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Response:
        """
        Faz requisição HTTP com retry automático.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API
            **kwargs: Argumentos adicionais para a requisição
            
        Returns:
            Resposta HTTP
            
        Raises:
            GovernmentAPIError: Se todas as tentativas falharem
        """
        if not self._client:
            raise GovernmentAPIError("Cliente HTTP não inicializado")
        
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                response = await self._client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                # Não fazer retry para erros 4xx (exceto 429)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise
                
                last_exception = e
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
            
            # Aguardar antes da próxima tentativa (backoff exponencial)
            if attempt < self.retry_attempts - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                
                self.logger.warning(
                    "api_request_retry",
                    attempt=attempt + 1,
                    max_attempts=self.retry_attempts,
                    wait_time=wait_time,
                    endpoint=endpoint
                )
        
        # Se chegou aqui, todas as tentativas falharam
        raise GovernmentAPIError(
            f"Falha após {self.retry_attempts} tentativas: {str(last_exception)}"
        )


class TaxCalculatorService(LoggerMixin):
    """Serviço de cálculo tributário com integração governamental."""
    
    def __init__(self):
        self.api_client = GovernmentAPIClient()
    
    async def calculate_document_taxes(
        self,
        items: List[Dict],
        emitter_state: str,
        recipient_state: str
    ) -> Tuple[List[TaxDetails], TaxDetails]:
        """
        Calcula tributos para todos os itens de um documento.
        
        Args:
            items: Lista de itens do documento
            emitter_state: Estado do emitente
            recipient_state: Estado do destinatário
            
        Returns:
            Tupla com (tributos por item, tributos totais do documento)
        """
        try:
            async with self.api_client:
                item_taxes = []
                total_taxes = TaxDetails()
                
                for item in items:
                    # Calcular IBS/CBS para o item
                    tax_details = await self.api_client.calculate_ibs_cbs(
                        ncm=item["ncm"],
                        cfop=item["cfop"],
                        base_value=Decimal(str(item["total_value"])),
                        state_origin=emitter_state,
                        state_destination=recipient_state
                    )
                    
                    # Calcular Imposto Seletivo se aplicável
                    selective_tax = await self.api_client.calculate_selective_tax(
                        ncm=item["ncm"],
                        base_value=Decimal(str(item["total_value"]))
                    )
                    
                    tax_details.selective_tax_value = selective_tax
                    
                    item_taxes.append(tax_details)
                    
                    # Somar aos totais
                    total_taxes.ibs_value += tax_details.ibs_value
                    total_taxes.cbs_value += tax_details.cbs_value
                    total_taxes.selective_tax_value += tax_details.selective_tax_value
                
                # Calcular total de tributos federais
                total_taxes.total_federal_taxes = (
                    total_taxes.ibs_value +
                    total_taxes.cbs_value +
                    total_taxes.selective_tax_value
                )
                
                self.logger.info(
                    "document_taxes_calculated",
                    items_count=len(items),
                    total_ibs=float(total_taxes.ibs_value),
                    total_cbs=float(total_taxes.cbs_value),
                    total_selective=float(total_taxes.selective_tax_value),
                    total_federal=float(total_taxes.total_federal_taxes)
                )
                
                return item_taxes, total_taxes
                
        except Exception as e:
            self.logger.error(
                "document_tax_calculation_failed",
                error=str(e),
                items_count=len(items)
            )
            raise

