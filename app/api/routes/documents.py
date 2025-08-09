"""
Endpoints para processamento de documentos fiscais.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, log_processing_event
from app.models.fiscal import (
    NFEDocument,
    BatchProcessingRequest,
    BatchProcessingResponse,
    DocumentProcessingResult,
    ProcessingJob,
    JobStatus
)
from app.services.xml_processor import XMLProcessor, XMLProcessingError

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger("documents_api")


@router.post("/process", response_model=NFEDocument)
async def process_single_document(
    xml_file: UploadFile = File(..., description="Arquivo XML da NF-e")
) -> NFEDocument:
    """
    Processa um único documento NF-e.
    
    Args:
        xml_file: Arquivo XML da NF-e para processamento
        
    Returns:
        Documento processado com tributos atualizados
        
    Raises:
        HTTPException: Se houver erro no processamento
    """
    try:
        # Validar tipo de arquivo
        if not xml_file.filename.lower().endswith('.xml'):
            raise HTTPException(
                status_code=400,
                detail="Arquivo deve ser um XML válido"
            )
        
        # Ler conteúdo do arquivo
        xml_content = await xml_file.read()
        xml_string = xml_content.decode('utf-8')
        
        # Processar documento
        processor = XMLProcessor()
        document = processor.process_nfe_document(xml_string)
        
        log_processing_event(
            "single_document_processed",
            document.document_key,
            filename=xml_file.filename,
            file_size=len(xml_content)
        )
        
        return document
        
    except XMLProcessingError as e:
        logger.error(
            "xml_processing_error",
            filename=xml_file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=422,
            detail=f"Erro no processamento do XML: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "unexpected_error",
            filename=xml_file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
        )


@router.post("/batch", response_model=BatchProcessingResponse)
async def process_batch_documents(
    request: BatchProcessingRequest
) -> BatchProcessingResponse:
    """
    Inicia processamento em lote de documentos NF-e.
    
    Args:
        request: Requisição com lista de XMLs para processamento
        
    Returns:
        Informações do job criado para processamento
    """
    try:
        # Validar documentos
        if not request.documents:
            raise HTTPException(
                status_code=400,
                detail="Lista de documentos não pode estar vazia"
            )
        
        # Criar job de processamento
        job = ProcessingJob(
            total_documents=len(request.documents),
            batch_size=request.batch_size,
            timeout_minutes=request.timeout_minutes
        )
        
        # TODO: Implementar processamento assíncrono real
        # Por enquanto, apenas simular
        
        # Estimar duração (2 segundos por documento)
        estimated_duration = len(request.documents) * 2 // 60  # em minutos
        
        response = BatchProcessingResponse(
            job_id=job.id,
            total_documents=job.total_documents,
            estimated_duration_minutes=max(1, estimated_duration),
            status_url=f"/api/v1/jobs/{job.id}/status",
            message=f"Job criado com sucesso. {job.total_documents} documentos serão processados."
        )
        
        log_processing_event(
            "batch_job_created",
            str(job.id),
            total_documents=job.total_documents,
            batch_size=request.batch_size
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "batch_creation_error",
            error=str(e),
            documents_count=len(request.documents) if request.documents else 0
        )
        raise HTTPException(
            status_code=500,
            detail="Erro ao criar job de processamento"
        )


@router.get("/validate")
async def validate_xml_structure(
    xml_file: UploadFile = File(..., description="Arquivo XML para validação")
) -> JSONResponse:
    """
    Valida estrutura de um arquivo XML fiscal.
    
    Args:
        xml_file: Arquivo XML para validação
        
    Returns:
        Resultado da validação
    """
    try:
        # Ler conteúdo
        xml_content = await xml_file.read()
        xml_string = xml_content.decode('utf-8')
        
        # Validar estrutura
        processor = XMLProcessor()
        from app.models.fiscal import DocumentType
        is_valid = processor.validate_xml_structure(xml_string, DocumentType.NFE)
        
        result = {
            "valid": is_valid,
            "filename": xml_file.filename,
            "file_size": len(xml_content),
            "message": "XML válido" if is_valid else "XML inválido ou estrutura incorreta"
        }
        
        logger.info(
            "xml_validation_completed",
            filename=xml_file.filename,
            valid=is_valid,
            file_size=len(xml_content)
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(
            "validation_error",
            filename=xml_file.filename,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail="Erro na validação do XML"
        )


@router.get("/{document_id}/result", response_model=DocumentProcessingResult)
async def get_document_result(document_id: UUID) -> DocumentProcessingResult:
    """
    Obtém resultado do processamento de um documento específico.
    
    Args:
        document_id: ID do documento processado
        
    Returns:
        Resultado detalhado do processamento
    """
    # TODO: Implementar busca real no banco de dados
    # Por enquanto, retornar dados simulados
    
    from decimal import Decimal
    from datetime import datetime
    
    result = DocumentProcessingResult(
        document_id=document_id,
        document_key="41250115495505000141550010001278001000921722",
        status="completed",
        original_tax_total=Decimal("150.75"),
        updated_tax_total=Decimal("165.20"),
        tax_difference=Decimal("14.45"),
        processing_duration_ms=1250,
        government_api_calls=3,
        errors=[],
        warnings=["Alíquota IBS atualizada conforme nova regulamentação"],
        processed_at=datetime.utcnow()
    )
    
    logger.info(
        "document_result_retrieved",
        document_id=str(document_id),
        status=result.status
    )
    
    return result

