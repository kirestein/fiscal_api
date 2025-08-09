"""
Endpoints especializados para leitura e análise de XML fiscal.

Este módulo implementa endpoints focados na leitura, validação e extração
de dados de documentos XML fiscais, com suporte a diferentes formatos e
validações robustas.
"""

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.models.fiscal import DocumentType, NFEDocument
from app.services.xml_processor import XMLProcessor, XMLProcessingError

router = APIRouter(prefix="/xml", tags=["xml-reader"])
logger = get_logger("xml_reader_api")


class XMLValidationResponse(BaseModel):
    """Resposta de validação de XML."""
    
    valid: bool = Field(description="Se o XML é válido")
    document_type: Optional[str] = Field(default=None, description="Tipo de documento identificado")
    errors: List[str] = Field(default_factory=list, description="Lista de erros encontrados")
    warnings: List[str] = Field(default_factory=list, description="Lista de avisos")
    summary: Optional[Dict] = Field(default=None, description="Resumo básico do documento")


class XMLReadResponse(BaseModel):
    """Resposta de leitura completa de XML."""
    
    success: bool = Field(description="Se a leitura foi bem-sucedida")
    document: Optional[NFEDocument] = Field(default=None, description="Documento estruturado")
    processing_time_ms: float = Field(description="Tempo de processamento em milissegundos")
    errors: List[str] = Field(default_factory=list, description="Lista de erros")
    warnings: List[str] = Field(default_factory=list, description="Lista de avisos")


class XMLSummaryResponse(BaseModel):
    """Resposta de resumo rápido de XML."""
    
    document_key: str = Field(description="Chave de acesso do documento")
    document_type: str = Field(description="Tipo de documento")
    series: str = Field(description="Série do documento")
    number: str = Field(description="Número do documento")
    issue_date: Optional[str] = Field(default=None, description="Data de emissão")
    emitter_name: str = Field(description="Nome do emitente")
    emitter_cnpj: str = Field(description="CNPJ do emitente")
    recipient_name: str = Field(description="Nome do destinatário")
    recipient_cnpj: str = Field(description="CNPJ do destinatário")
    total_value: str = Field(description="Valor total do documento")
    items_count: int = Field(description="Quantidade de itens")
    valid_structure: bool = Field(description="Se a estrutura XML é válida")


@router.post("/validate", response_model=XMLValidationResponse)
async def validate_xml_structure(
    xml_file: UploadFile = File(..., description="Arquivo XML para validação"),
    document_type: str = Form(default="nfe", description="Tipo de documento esperado")
) -> XMLValidationResponse:
    """
    Valida estrutura de XML fiscal sem processamento completo.
    
    Este endpoint realiza validação rápida da estrutura XML,
    verificando elementos obrigatórios e conformidade com layout.
    
    Args:
        xml_file: Arquivo XML a ser validado
        document_type: Tipo de documento esperado (nfe, nfce, cte, etc.)
        
    Returns:
        XMLValidationResponse: Resultado da validação com detalhes
    """
    try:
        # Validar tipo de arquivo
        if not xml_file.filename.lower().endswith('.xml'):
            raise HTTPException(
                status_code=400,
                detail="Arquivo deve ter extensão .xml"
            )
        
        # Ler conteúdo do arquivo
        xml_content = await xml_file.read()
        xml_text = xml_content.decode('utf-8')
        
        # Inicializar processor
        processor = XMLProcessor()
        
        # Determinar tipo de documento
        doc_type = DocumentType.NFE if document_type.lower() == "nfe" else DocumentType.NFE
        
        # Validar estrutura
        is_valid = processor.validate_xml_structure(xml_text, doc_type)
        
        errors = []
        warnings = []
        summary = None
        
        if is_valid:
            try:
                # Extrair resumo se estrutura é válida
                summary = processor.extract_document_summary(xml_text)
                
                # Verificar avisos
                if summary.get('emitter_name', '') == '':
                    warnings.append("Nome do emitente não encontrado")
                
                if float(summary.get('total_value', '0')) == 0:
                    warnings.append("Valor total do documento é zero")
                
            except Exception as e:
                warnings.append(f"Erro ao extrair resumo: {str(e)}")
        else:
            errors.append("Estrutura XML não conforme com layout NF-e")
            
            # Tentar identificar problemas específicos
            try:
                from lxml import etree
                root = etree.fromstring(xml_content)
                
                if 'portalfiscal.inf.br/nfe' not in str(root.nsmap):
                    errors.append("Namespace NF-e não encontrado")
                
                namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                
                if root.find('.//nfe:infNFe', namespaces) is None:
                    errors.append("Elemento infNFe não encontrado")
                if root.find('.//nfe:ide', namespaces) is None:
                    errors.append("Elemento ide (identificação) não encontrado")
                if root.find('.//nfe:emit', namespaces) is None:
                    errors.append("Elemento emit (emitente) não encontrado")
                if root.find('.//nfe:dest', namespaces) is None:
                    errors.append("Elemento dest (destinatário) não encontrado")
                if root.find('.//nfe:det', namespaces) is None:
                    errors.append("Nenhum item (det) encontrado")
                if root.find('.//nfe:total', namespaces) is None:
                    errors.append("Elemento total não encontrado")
                    
            except Exception as parse_error:
                errors.append(f"Erro de parsing XML: {str(parse_error)}")
        
        logger.info(
            "xml_validation_completed",
            filename=xml_file.filename,
            valid=is_valid,
            errors_count=len(errors),
            warnings_count=len(warnings),
            file_size=len(xml_content)
        )
        
        return XMLValidationResponse(
            valid=is_valid,
            document_type=document_type if is_valid else None,
            errors=errors,
            warnings=warnings,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "xml_validation_error",
            filename=xml_file.filename if xml_file else "unknown",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno na validação: {str(e)}"
        )


@router.post("/read", response_model=XMLReadResponse)
async def read_xml_document(
    xml_file: UploadFile = File(..., description="Arquivo XML para leitura completa"),
    extract_taxes: bool = Form(default=True, description="Se deve extrair detalhes tributários"),
    validate_cnpj: bool = Form(default=True, description="Se deve validar CNPJs")
) -> XMLReadResponse:
    """
    Realiza leitura completa de XML fiscal com extração de todos os dados.
    
    Este endpoint processa completamente o XML, extraindo todos os dados
    estruturados incluindo itens, tributos, empresas e totais.
    
    Args:
        xml_file: Arquivo XML para processamento
        extract_taxes: Se deve extrair detalhes tributários
        validate_cnpj: Se deve validar CNPJs das empresas
        
    Returns:
        XMLReadResponse: Documento estruturado completo
    """
    from datetime import datetime
    
    start_time = datetime.utcnow()
    
    try:
        # Validar arquivo
        if not xml_file.filename.lower().endswith('.xml'):
            raise HTTPException(
                status_code=400,
                detail="Arquivo deve ter extensão .xml"
            )
        
        # Validar tamanho do arquivo (máximo 10MB)
        xml_content = await xml_file.read()
        if len(xml_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=413,
                detail="Arquivo muito grande. Máximo permitido: 10MB"
            )
        
        xml_text = xml_content.decode('utf-8')
        
        # Inicializar processor
        processor = XMLProcessor()
        
        errors = []
        warnings = []
        document = None
        
        try:
            # Processar documento completo
            document = processor.process_nfe_document(xml_text)
            
            # Validações adicionais se solicitadas
            if validate_cnpj:
                from app.services.xml_processor import XMLValidator
                
                if not XMLValidator.validate_cnpj(document.emitter.cnpj):
                    warnings.append(f"CNPJ do emitente inválido: {document.emitter.cnpj}")
                
                if not XMLValidator.validate_cnpj(document.recipient.cnpj):
                    warnings.append(f"CNPJ do destinatário inválido: {document.recipient.cnpj}")
            
            # Verificar consistência de dados
            if document.total_document <= 0:
                warnings.append("Valor total do documento é zero ou negativo")
            
            if len(document.items) == 0:
                warnings.append("Documento não possui itens")
            
            # Verificar soma dos itens vs total
            soma_itens = sum(item.total_value for item in document.items)
            if abs(soma_itens - document.total_products) > 0.01:
                warnings.append(
                    f"Divergência entre soma dos itens ({soma_itens}) e total de produtos ({document.total_products})"
                )
            
        except XMLProcessingError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Erro no processamento: {str(e)}")
        
        # Calcular tempo de processamento
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        success = document is not None and len(errors) == 0
        
        logger.info(
            "xml_read_completed",
            filename=xml_file.filename,
            success=success,
            processing_time_ms=processing_time,
            errors_count=len(errors),
            warnings_count=len(warnings),
            items_count=len(document.items) if document else 0,
            total_value=float(document.total_document) if document else 0
        )
        
        return XMLReadResponse(
            success=success,
            document=document,
            processing_time_ms=processing_time,
            errors=errors,
            warnings=warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.error(
            "xml_read_error",
            filename=xml_file.filename if xml_file else "unknown",
            error=str(e),
            error_type=type(e).__name__,
            processing_time_ms=processing_time
        )
        
        return XMLReadResponse(
            success=False,
            document=None,
            processing_time_ms=processing_time,
            errors=[f"Erro interno: {str(e)}"],
            warnings=[]
        )


@router.post("/summary", response_model=XMLSummaryResponse)
async def get_xml_summary(
    xml_file: UploadFile = File(..., description="Arquivo XML para resumo rápido")
) -> XMLSummaryResponse:
    """
    Extrai resumo rápido de XML fiscal sem processamento completo.
    
    Este endpoint é otimizado para extrair apenas informações básicas
    do documento de forma rápida, ideal para listagens e previews.
    
    Args:
        xml_file: Arquivo XML para extração de resumo
        
    Returns:
        XMLSummaryResponse: Resumo com dados básicos do documento
    """
    try:
        # Validar arquivo
        if not xml_file.filename.lower().endswith('.xml'):
            raise HTTPException(
                status_code=400,
                detail="Arquivo deve ter extensão .xml"
            )
        
        # Ler conteúdo
        xml_content = await xml_file.read()
        xml_text = xml_content.decode('utf-8')
        
        # Extrair resumo - Implementação direta para contornar problema de importação
        try:
            from lxml import etree
            root = etree.fromstring(xml_content)
            namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Extrair dados básicos diretamente
            inf_nfe = root.find('.//nfe:infNFe', namespaces)
            document_key = inf_nfe.get('Id', '').replace('NFe', '') if inf_nfe is not None else ''
            
            ide = root.find('.//nfe:ide', namespaces)
            serie = ide.find('nfe:serie', namespaces).text if ide is not None and ide.find('nfe:serie', namespaces) is not None else ''
            numero = ide.find('nfe:nNF', namespaces).text if ide is not None and ide.find('nfe:nNF', namespaces) is not None else ''
            
            emit = root.find('.//nfe:emit', namespaces)
            emitente = emit.find('nfe:xNome', namespaces).text if emit is not None and emit.find('nfe:xNome', namespaces) is not None else ''
            
            total = root.find('.//nfe:total/nfe:ICMSTot/nfe:vNF', namespaces)
            valor_total = total.text if total is not None else '0.00'
            
            # Validar estrutura
            processor = XMLProcessor()
            valid_structure = processor.validate_xml_structure(xml_text, DocumentType.NFE)
            
            summary = {
                'document_key': document_key,
                'series': serie,
                'number': numero,
                'emitter_name': emitente,
                'total_value': valor_total,
                'valid_structure': valid_structure
            }
            
        except Exception as e:
            logger.error("direct_summary_extraction_failed", error=str(e))
            raise HTTPException(
                status_code=400,
                detail=f"Erro ao extrair resumo: {str(e)}"
            )
        
        # Extrair dados adicionais para resposta completa
        try:
            from lxml import etree
            root = etree.fromstring(xml_content)
            namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Data de emissão
            ide = root.find('.//nfe:ide', namespaces)
            issue_date = None
            if ide is not None:
                dh_emi = ide.find('nfe:dhEmi', namespaces)
                if dh_emi is not None:
                    issue_date = dh_emi.text
                else:
                    d_emi = ide.find('nfe:dEmi', namespaces)
                    if d_emi is not None:
                        issue_date = d_emi.text
            
            # Dados do destinatário
            dest = root.find('.//nfe:dest', namespaces)
            recipient_name = ""
            recipient_cnpj = ""
            if dest is not None:
                nome_elem = dest.find('nfe:xNome', namespaces)
                cnpj_elem = dest.find('nfe:CNPJ', namespaces)
                cpf_elem = dest.find('nfe:CPF', namespaces)
                
                if nome_elem is not None:
                    recipient_name = nome_elem.text
                if cnpj_elem is not None:
                    recipient_cnpj = cnpj_elem.text
                elif cpf_elem is not None:
                    recipient_cnpj = cpf_elem.text
            
            # Contar itens
            items = root.findall('.//nfe:det', namespaces)
            items_count = len(items)
            
            # CNPJ do emitente
            emit = root.find('.//nfe:emit', namespaces)
            emitter_cnpj = ""
            if emit is not None:
                cnpj_elem = emit.find('nfe:CNPJ', namespaces)
                if cnpj_elem is not None:
                    emitter_cnpj = cnpj_elem.text
            
        except Exception as e:
            logger.warning("summary_extraction_partial_failure", error=str(e))
            issue_date = None
            recipient_name = ""
            recipient_cnpj = ""
            items_count = 0
            emitter_cnpj = ""
        
        logger.info(
            "xml_summary_extracted",
            filename=xml_file.filename,
            document_key=summary.get('document_key', ''),
            emitter_name=summary.get('emitter_name', ''),
            total_value=summary.get('total_value', '0.00'),
            items_count=items_count
        )
        
        return XMLSummaryResponse(
            document_key=summary.get('document_key', ''),
            document_type="NF-e",
            series=summary.get('series', ''),
            number=summary.get('number', ''),
            issue_date=issue_date,
            emitter_name=summary.get('emitter_name', ''),
            emitter_cnpj=emitter_cnpj,
            recipient_name=recipient_name,
            recipient_cnpj=recipient_cnpj,
            total_value=summary.get('total_value', '0.00'),
            items_count=items_count,
            valid_structure=summary.get('valid_structure', False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "xml_summary_error",
            filename=xml_file.filename if xml_file else "unknown",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao extrair resumo: {str(e)}"
        )


@router.post("/batch-summary")
async def get_batch_xml_summary(
    xml_files: List[UploadFile] = File(..., description="Lista de arquivos XML para resumo")
) -> JSONResponse:
    """
    Extrai resumo de múltiplos arquivos XML de forma otimizada.
    
    Este endpoint processa múltiplos XMLs em paralelo para extrair
    resumos básicos, ideal para upload em lote.
    
    Args:
        xml_files: Lista de arquivos XML
        
    Returns:
        JSONResponse: Lista de resumos com status de cada arquivo
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    if len(xml_files) > 50:
        raise HTTPException(
            status_code=400,
            detail="Máximo de 50 arquivos por lote"
        )
    
    results = []
    processor = XMLProcessor()
    
    def process_single_file(file_content: bytes, filename: str) -> Dict:
        """Processa um único arquivo XML."""
        try:
            xml_text = file_content.decode('utf-8')
            summary = processor.extract_document_summary(xml_text)
            
            return {
                'filename': filename,
                'success': True,
                'summary': summary,
                'error': None
            }
        except Exception as e:
            return {
                'filename': filename,
                'success': False,
                'summary': None,
                'error': str(e)
            }
    
    try:
        # Ler todos os arquivos
        file_contents = []
        for xml_file in xml_files:
            if not xml_file.filename.lower().endswith('.xml'):
                results.append({
                    'filename': xml_file.filename,
                    'success': False,
                    'summary': None,
                    'error': 'Arquivo deve ter extensão .xml'
                })
                continue
            
            content = await xml_file.read()
            if len(content) > 5 * 1024 * 1024:  # 5MB por arquivo em lote
                results.append({
                    'filename': xml_file.filename,
                    'success': False,
                    'summary': None,
                    'error': 'Arquivo muito grande para processamento em lote (máx 5MB)'
                })
                continue
            
            file_contents.append((content, xml_file.filename))
        
        # Processar em paralelo
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_single_file, content, filename)
                for content, filename in file_contents
            ]
            
            for future in futures:
                results.append(future.result())
        
        # Estatísticas
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        logger.info(
            "batch_summary_completed",
            total_files=len(xml_files),
            successful=successful,
            failed=failed
        )
        
        return JSONResponse(content={
            'total_files': len(xml_files),
            'successful': successful,
            'failed': failed,
            'results': results
        })
        
    except Exception as e:
        logger.error(
            "batch_summary_error",
            total_files=len(xml_files),
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro no processamento em lote: {str(e)}"
        )


@router.get("/health")
async def xml_reader_health() -> JSONResponse:
    """
    Health check específico do módulo de leitura XML.
    
    Returns:
        JSONResponse: Status de saúde do módulo
    """
    from datetime import datetime
    
    try:
        # Testar inicialização do processor
        processor = XMLProcessor()
        
        # Testar validação com XML mínimo
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
            <NFe>
                <infNFe Id="NFe12345678901234567890123456789012345678901234" versao="4.00">
                    <ide><serie>1</serie><nNF>1</nNF></ide>
                    <emit><CNPJ>12345678000195</CNPJ><xNome>Teste</xNome></emit>
                    <dest><CNPJ>98765432000198</CNPJ><xNome>Teste</xNome></dest>
                    <det nItem="1"><prod><cProd>1</cProd><xProd>Teste</xProd></prod></det>
                    <total><ICMSTot><vNF>100.00</vNF></ICMSTot></total>
                </infNFe>
            </NFe>
        </nfeProc>'''
        
        is_valid = processor.validate_xml_structure(test_xml, DocumentType.NFE)
        
        return JSONResponse(content={
            'status': 'healthy',
            'module': 'xml_reader',
            'processor_initialized': True,
            'validation_working': is_valid,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error("xml_reader_health_check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'module': 'xml_reader',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        )

