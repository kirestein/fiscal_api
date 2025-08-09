"""
Modelos de dados para documentos fiscais e tributação.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class DocumentType(str, Enum):
    """Tipos de documento fiscal."""
    NFE = "nfe"
    NFCE = "nfce"
    CTE = "cte"


class ProcessingStatus(str, Enum):
    """Status de processamento de documento."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    """Status de job de processamento."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaxDetails(BaseModel):
    """Detalhes tributários de um documento."""
    
    # IBS - Imposto sobre Bens e Serviços
    ibs_base: Decimal = Field(
        default=Decimal('0'),
        description="Base de cálculo do IBS",
        ge=0
    )
    ibs_rate: Decimal = Field(
        default=Decimal('0'),
        description="Alíquota do IBS (%)",
        ge=0,
        le=100
    )
    ibs_value: Decimal = Field(
        default=Decimal('0'),
        description="Valor do IBS calculado",
        ge=0
    )
    
    # CBS - Contribuição sobre Bens e Serviços
    cbs_base: Decimal = Field(
        default=Decimal('0'),
        description="Base de cálculo da CBS",
        ge=0
    )
    cbs_rate: Decimal = Field(
        default=Decimal('0'),
        description="Alíquota da CBS (%)",
        ge=0,
        le=100
    )
    cbs_value: Decimal = Field(
        default=Decimal('0'),
        description="Valor da CBS calculado",
        ge=0
    )
    
    # Imposto Seletivo
    selective_tax_base: Decimal = Field(
        default=Decimal('0'),
        description="Base de cálculo do Imposto Seletivo",
        ge=0
    )
    selective_tax_rate: Decimal = Field(
        default=Decimal('0'),
        description="Alíquota do Imposto Seletivo (%)",
        ge=0,
        le=100
    )
    selective_tax_value: Decimal = Field(
        default=Decimal('0'),
        description="Valor do Imposto Seletivo calculado",
        ge=0
    )
    
    # Totais
    total_federal_taxes: Decimal = Field(
        default=Decimal('0'),
        description="Total de tributos federais",
        ge=0
    )
    
    @validator('ibs_value', 'cbs_value', 'selective_tax_value', always=True)
    def calculate_tax_values(cls, v, values, **kwargs):
        """Calcula valores de tributos baseado na base e alíquota."""
        # Obter nome do campo do info se disponível
        info = kwargs.get('info', None)
        field_name = info.field_name if info and hasattr(info, 'field_name') else ''
        
        # Fallback: tentar identificar pelo contexto dos valores
        if not field_name:
            # Se não conseguir identificar o campo, retornar o valor como está
            return v if v is not None else Decimal('0')
        
        if field_name == 'ibs_value':
            base = values.get('ibs_base', Decimal('0'))
            rate = values.get('ibs_rate', Decimal('0'))
            return base * rate / 100
        elif field_name == 'cbs_value':
            base = values.get('cbs_base', Decimal('0'))
            rate = values.get('cbs_rate', Decimal('0'))
            return base * rate / 100
        elif field_name == 'selective_tax_value':
            base = values.get('selective_tax_base', Decimal('0'))
            rate = values.get('selective_tax_rate', Decimal('0'))
            return base * rate / 100
        
        return v if v is not None else Decimal('0')


class ProductItem(BaseModel):
    """Item de produto em documento fiscal."""
    
    item_number: int = Field(description="Número do item no documento")
    product_code: str = Field(description="Código do produto")
    product_name: str = Field(description="Nome/descrição do produto")
    ncm: str = Field(description="Código NCM", pattern=r'^\d{8}$')
    cfop: str = Field(description="Código CFOP", pattern=r'^\d{4}$')
    unit: str = Field(description="Unidade de medida")
    quantity: Decimal = Field(description="Quantidade", gt=0)
    unit_value: Decimal = Field(description="Valor unitário", ge=0)
    total_value: Decimal = Field(description="Valor total do item", ge=0)
    tax_details: TaxDetails = Field(description="Detalhes tributários do item")


class CompanyInfo(BaseModel):
    """Informações de empresa (emitente/destinatário)."""
    
    cnpj: str = Field(description="CNPJ da empresa", pattern=r'^\d{14}$')
    trade_name: Optional[str] = Field(default=None, description="Nome fantasia")
    address: str = Field(description="Endereço completo")
    city: str = Field(description="Cidade")
    state: str = Field(description="Estado (UF)", pattern=r'^[A-Z]{2}$')
    zip_code: str = Field(description="CEP", pattern=r'^\d{8}$')
    phone: Optional[str] = Field(default=None, description="Telefone")
    email: Optional[str] = Field(default=None, description="Email")


class NFEDocument(BaseModel):
    """Documento NF-e completo."""
    
    id: UUID = Field(default_factory=uuid4, description="ID único do documento")
    document_key: str = Field(
        description="Chave de acesso da NF-e",
        pattern=r'^\d{44}$'
    )
    document_type: DocumentType = Field(default=DocumentType.NFE)
    series: int = Field(description="Série do documento")
    number: int = Field(description="Número do documento")
    issue_date: datetime = Field(description="Data de emissão")
    
    # Empresas
    emitter: CompanyInfo = Field(description="Dados do emitente")
    recipient: CompanyInfo = Field(description="Dados do destinatário")
    
    # Produtos/Serviços
    items: List[ProductItem] = Field(description="Itens do documento")
    
    # Totais
    total_products: Decimal = Field(description="Total de produtos", ge=0)
    total_services: Decimal = Field(description="Total de serviços", ge=0)
    total_document: Decimal = Field(description="Total do documento", ge=0)
    
    # Tributação
    tax_details: TaxDetails = Field(description="Detalhes tributários do documento")
    
    # XML
    original_xml: str = Field(description="XML original do documento")
    updated_xml: Optional[str] = Field(default=None, description="XML atualizado")
    
    # Metadados
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    
    @validator('total_document', always=True)
    def validate_total_document(cls, v, values):
        """Valida se o total do documento está correto."""
        total_products = values.get('total_products', Decimal('0'))
        total_services = values.get('total_services', Decimal('0'))
        expected_total = total_products + total_services
        
        if abs(v - expected_total) > Decimal('0.01'):  # Tolerância de 1 centavo
            raise ValueError(
                f"Total do documento ({v}) não confere com soma de produtos e serviços ({expected_total})"
            )
        
        return v


class ProcessingJob(BaseModel):
    """Job de processamento de documentos."""
    
    id: UUID = Field(default_factory=uuid4, description="ID único do job")
    user_id: Optional[str] = Field(default=None, description="ID do usuário")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Status do job")
    
    # Estatísticas
    total_documents: int = Field(description="Total de documentos", ge=1)
    processed_documents: int = Field(default=0, description="Documentos processados")
    successful_documents: int = Field(default=0, description="Documentos com sucesso")
    failed_documents: int = Field(default=0, description="Documentos com falha")
    
    # Configurações
    batch_size: int = Field(default=100, description="Tamanho do lote")
    timeout_minutes: int = Field(default=30, description="Timeout em minutos")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    estimated_completion: Optional[datetime] = Field(default=None)
    
    # Resultados
    error_message: Optional[str] = Field(default=None, description="Mensagem de erro")
    results_summary: Optional[dict] = Field(default=None, description="Resumo dos resultados")


class DocumentProcessingResult(BaseModel):
    """Resultado do processamento de um documento."""
    
    document_id: UUID = Field(description="ID do documento processado")
    document_key: str = Field(description="Chave de acesso do documento")
    status: ProcessingStatus = Field(description="Status do processamento")
    
    # Dados originais vs atualizados
    original_tax_total: Decimal = Field(description="Total de tributos original")
    updated_tax_total: Decimal = Field(description="Total de tributos atualizado")
    tax_difference: Decimal = Field(description="Diferença nos tributos")
    
    # Detalhes do processamento
    processing_duration_ms: int = Field(description="Duração do processamento em ms")
    government_api_calls: int = Field(description="Número de chamadas à API governamental")
    
    # Erros e avisos
    errors: List[str] = Field(default=[], description="Lista de erros encontrados")
    warnings: List[str] = Field(default=[], description="Lista de avisos")
    
    # Metadados
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processor_version: str = Field(default="0.1.0", description="Versão do processador")


class BatchProcessingRequest(BaseModel):
    """Requisição de processamento em lote."""
    
    documents: List[str] = Field(description="Lista de XMLs para processamento")
    batch_size: int = Field(default=100, description="Tamanho do lote", ge=1, le=1000)
    timeout_minutes: int = Field(default=30, description="Timeout em minutos", ge=1, le=120)
    force_update: bool = Field(default=False, description="Forçar atualização mesmo se não necessária")
    
    @validator('documents')
    def validate_documents_not_empty(cls, v):
        """Valida que a lista de documentos não está vazia."""
        if not v:
            raise ValueError("Lista de documentos não pode estar vazia")
        return v


class BatchProcessingResponse(BaseModel):
    """Resposta de processamento em lote."""
    
    job_id: UUID = Field(description="ID do job criado")
    total_documents: int = Field(description="Total de documentos no lote")
    estimated_duration_minutes: int = Field(description="Duração estimada em minutos")
    status_url: str = Field(description="URL para acompanhar o status")
    message: str = Field(description="Mensagem informativa")

