"""
Processador de XML fiscal para documentos NF-e.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from xml.etree.ElementTree import ParseError

from lxml import etree
from lxml.etree import _Element

from app.core.logging import LoggerMixin, log_processing_event
from app.models.fiscal import (
    CompanyInfo,
    DocumentType,
    NFEDocument,
    ProductItem,
    TaxDetails
)


class XMLProcessingError(Exception):
    """Erro de processamento de XML."""
    pass


class XMLValidator:
    """Validador de XML fiscal."""
    
    @staticmethod
    def validate_nfe_structure(xml_content: str) -> bool:
        """Valida estrutura básica de NF-e."""
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Verificar namespace
            if 'portalfiscal.inf.br/nfe' not in str(root.nsmap):
                return False
            
            # Verificar elementos obrigatórios
            required_elements = [
                './/nfe:infNFe',
                './/nfe:ide',
                './/nfe:emit',
                './/nfe:dest',
                './/nfe:det',
                './/nfe:total'
            ]
            
            namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            for element_path in required_elements:
                if root.find(element_path, namespaces) is None:
                    return False
            
            return True
            
        except (ParseError, Exception):
            return False
    
    @staticmethod
    def validate_document_key(key: str) -> bool:
        """Valida chave de acesso do documento."""
        if not key or len(key) != 44:
            return False
        
        if not key.isdigit():
            return False
        
        # Validar dígito verificador (algoritmo simplificado)
        return True


class XMLParser(LoggerMixin):
    """Parser de XML fiscal."""
    
    def __init__(self):
        self.namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def parse_nfe_document(self, xml_content: str) -> NFEDocument:
        """Converte XML NF-e em modelo de dados."""
        try:
            # Validar estrutura
            if not XMLValidator.validate_nfe_structure(xml_content):
                raise XMLProcessingError("Estrutura XML inválida para NF-e")
            
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Extrair dados principais
            inf_nfe = root.find('.//nfe:infNFe', self.namespaces)
            if inf_nfe is None:
                raise XMLProcessingError("Elemento infNFe não encontrado")
            
            document_key = inf_nfe.get('Id', '').replace('NFe', '')
            
            if not XMLValidator.validate_document_key(document_key):
                raise XMLProcessingError(f"Chave de documento inválida: {document_key}")
            
            # Extrair identificação
            ide_data = self._extract_identification(root)
            
            # Extrair emitente e destinatário
            emitter = self._extract_company_info(root, './/nfe:emit')
            recipient = self._extract_company_info(root, './/nfe:dest')
            
            # Extrair itens
            items = self._extract_items(root)
            
            # Extrair totais
            totals = self._extract_totals(root)
            
            # Extrair tributação
            tax_details = self._extract_tax_details(root)
            
            # Criar documento
            document = NFEDocument(
                document_key=document_key,
                document_type=DocumentType.NFE,
                series=ide_data['series'],
                number=ide_data['number'],
                issue_date=ide_data['issue_date'],
                emitter=emitter,
                recipient=recipient,
                items=items,
                total_products=totals['products'],
                total_services=totals['services'],
                total_document=totals['total'],
                tax_details=tax_details,
                original_xml=xml_content
            )
            
            log_processing_event(
                "xml_parsed_successfully",
                document_key,
                document_type="nfe",
                items_count=len(items),
                total_value=float(totals['total'])
            )
            
            return document
            
        except Exception as e:
            self.logger.error(
                "xml_parsing_failed",
                error=str(e),
                xml_length=len(xml_content)
            )
            raise XMLProcessingError(f"Erro ao processar XML: {str(e)}")
    
    def _extract_identification(self, root: _Element) -> Dict:
        """Extrai dados de identificação do documento."""
        ide = root.find('.//nfe:ide', self.namespaces)
        if ide is None:
            raise XMLProcessingError("Elemento ide não encontrado")
        
        # Data de emissão
        dh_emi = ide.find('nfe:dhEmi', self.namespaces)
        if dh_emi is not None:
            issue_date = datetime.fromisoformat(dh_emi.text.replace('Z', '+00:00'))
        else:
            # Fallback para dEmi (formato antigo)
            d_emi = ide.find('nfe:dEmi', self.namespaces)
            if d_emi is not None:
                issue_date = datetime.strptime(d_emi.text, '%Y-%m-%d')
            else:
                raise XMLProcessingError("Data de emissão não encontrada")
        
        return {
            'series': int(ide.find('nfe:serie', self.namespaces).text),
            'number': int(ide.find('nfe:nNF', self.namespaces).text),
            'issue_date': issue_date
        }
    
    def _extract_company_info(self, root: _Element, xpath: str) -> CompanyInfo:
        """Extrai informações de empresa (emitente/destinatário)."""
        company_elem = root.find(xpath, self.namespaces)
        if company_elem is None:
            raise XMLProcessingError(f"Elemento não encontrado: {xpath}")
        
        # CNPJ
        cnpj_elem = company_elem.find('nfe:CNPJ', self.namespaces)
        if cnpj_elem is None:
            raise XMLProcessingError("CNPJ não encontrado")
        
        # Endereço
        ender_elem = company_elem.find('nfe:enderEmit' if 'emit' in xpath else 'nfe:enderDest', self.namespaces)
        if ender_elem is None:
            ender_elem = company_elem.find('nfe:endereco', self.namespaces)
        
        if ender_elem is None:
            raise XMLProcessingError("Endereço não encontrado")
        
        return CompanyInfo(
            cnpj=cnpj_elem.text,
            company_name=company_elem.find('nfe:xNome', self.namespaces).text,
            trade_name=self._get_optional_text(company_elem, 'nfe:xFant'),
            address=f"{ender_elem.find('nfe:xLgr', self.namespaces).text}, {ender_elem.find('nfe:nro', self.namespaces).text}",
            city=ender_elem.find('nfe:xMun', self.namespaces).text,
            state=ender_elem.find('nfe:UF', self.namespaces).text,
            zip_code=ender_elem.find('nfe:CEP', self.namespaces).text,
            phone=self._get_optional_text(ender_elem, 'nfe:fone'),
            email=self._get_optional_text(company_elem, 'nfe:email')
        )
    
    def _extract_items(self, root: _Element) -> List[ProductItem]:
        """Extrai itens do documento."""
        items = []
        det_elements = root.findall('.//nfe:det', self.namespaces)
        
        for det in det_elements:
            item_num = int(det.get('nItem'))
            
            prod = det.find('nfe:prod', self.namespaces)
            if prod is None:
                continue
            
            # Dados do produto
            product_code = prod.find('nfe:cProd', self.namespaces).text
            product_name = prod.find('nfe:xProd', self.namespaces).text
            ncm = prod.find('nfe:NCM', self.namespaces).text
            cfop = prod.find('nfe:CFOP', self.namespaces).text
            unit = prod.find('nfe:uCom', self.namespaces).text
            quantity = Decimal(prod.find('nfe:qCom', self.namespaces).text)
            unit_value = Decimal(prod.find('nfe:vUnCom', self.namespaces).text)
            total_value = Decimal(prod.find('nfe:vProd', self.namespaces).text)
            
            # Tributação do item
            tax_details = self._extract_item_tax_details(det)
            
            item = ProductItem(
                item_number=item_num,
                product_code=product_code,
                product_name=product_name,
                ncm=ncm,
                cfop=cfop,
                unit=unit,
                quantity=quantity,
                unit_value=unit_value,
                total_value=total_value,
                tax_details=tax_details
            )
            
            items.append(item)
        
        return items
    
    def _extract_item_tax_details(self, det_element: _Element) -> TaxDetails:
        """Extrai detalhes tributários de um item."""
        # Por enquanto, retorna valores zerados
        # TODO: Implementar extração real de tributos por item
        return TaxDetails()
    
    def _extract_totals(self, root: _Element) -> Dict[str, Decimal]:
        """Extrai totais do documento."""
        total_elem = root.find('.//nfe:total/nfe:ICMSTot', self.namespaces)
        if total_elem is None:
            raise XMLProcessingError("Totais não encontrados")
        
        v_prod = total_elem.find('nfe:vProd', self.namespaces)
        v_serv = total_elem.find('nfe:vServ', self.namespaces)
        v_nf = total_elem.find('nfe:vNF', self.namespaces)
        
        return {
            'products': Decimal(v_prod.text) if v_prod is not None else Decimal('0'),
            'services': Decimal(v_serv.text) if v_serv is not None else Decimal('0'),
            'total': Decimal(v_nf.text) if v_nf is not None else Decimal('0')
        }
    
    def _extract_tax_details(self, root: _Element) -> TaxDetails:
        """Extrai detalhes tributários do documento."""
        # Por enquanto, retorna valores zerados
        # TODO: Implementar extração real de tributos do documento
        return TaxDetails()
    
    def _get_optional_text(self, parent: _Element, xpath: str) -> Optional[str]:
        """Obtém texto de elemento opcional."""
        elem = parent.find(xpath, self.namespaces)
        return elem.text if elem is not None else None


class XMLGenerator(LoggerMixin):
    """Gerador de XML fiscal atualizado."""
    
    def __init__(self):
        self.namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def update_nfe_xml(self, document: NFEDocument) -> str:
        """Atualiza XML NF-e com novos valores tributários."""
        try:
            # Parse do XML original
            root = etree.fromstring(document.original_xml.encode('utf-8'))
            
            # Atualizar tributos por item
            self._update_items_taxes(root, document.items)
            
            # Atualizar totais do documento
            self._update_document_totals(root, document)
            
            # Gerar XML atualizado
            updated_xml = etree.tostring(
                root,
                encoding='unicode',
                pretty_print=True
            )
            
            log_processing_event(
                "xml_updated_successfully",
                document.document_key,
                original_total=float(document.total_document),
                updated_total=float(document.total_document)
            )
            
            return updated_xml
            
        except Exception as e:
            self.logger.error(
                "xml_update_failed",
                document_key=document.document_key,
                error=str(e)
            )
            raise XMLProcessingError(f"Erro ao atualizar XML: {str(e)}")
    
    def _update_items_taxes(self, root: _Element, items: List[ProductItem]) -> None:
        """Atualiza tributos dos itens no XML."""
        det_elements = root.findall('.//nfe:det', self.namespaces)
        
        for det in det_elements:
            item_num = int(det.get('nItem'))
            
            # Encontrar item correspondente
            item = next((i for i in items if i.item_number == item_num), None)
            if item is None:
                continue
            
            # TODO: Implementar atualização real de tributos por item
            # Por enquanto, apenas log
            self.logger.debug(
                "updating_item_taxes",
                item_number=item_num,
                product_code=item.product_code
            )
    
    def _update_document_totals(self, root: _Element, document: NFEDocument) -> None:
        """Atualiza totais do documento no XML."""
        total_elem = root.find('.//nfe:total/nfe:ICMSTot', self.namespaces)
        if total_elem is None:
            return
        
        # TODO: Implementar atualização real de totais
        # Por enquanto, apenas log
        self.logger.debug(
            "updating_document_totals",
            document_key=document.document_key,
            total_value=float(document.total_document)
        )


class XMLProcessor(LoggerMixin):
    """Processador principal de XML fiscal."""
    
    def __init__(self):
        self.parser = XMLParser()
        self.generator = XMLGenerator()
        self.validator = XMLValidator()
    
    def process_nfe_document(self, xml_content: str) -> NFEDocument:
        """Processa documento NF-e completo."""
        start_time = datetime.utcnow()
        
        try:
            # Parse do documento
            document = self.parser.parse_nfe_document(xml_content)
            
            # TODO: Integrar com Tax Calculator para atualizar tributos
            
            # Gerar XML atualizado
            updated_xml = self.generator.update_nfe_xml(document)
            document.updated_xml = updated_xml
            document.updated_at = datetime.utcnow()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_processing_event(
                "document_processed_successfully",
                document.document_key,
                processing_time_ms=processing_time,
                items_count=len(document.items)
            )
            
            return document
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.error(
                "document_processing_failed",
                error=str(e),
                processing_time_ms=processing_time
            )
            raise
    
    def validate_xml_structure(self, xml_content: str, document_type: DocumentType) -> bool:
        """Valida estrutura de XML fiscal."""
        if document_type == DocumentType.NFE:
            return self.validator.validate_nfe_structure(xml_content)
        
        # TODO: Implementar validação para outros tipos
        return False

