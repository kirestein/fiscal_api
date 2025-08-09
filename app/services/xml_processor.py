"""
Processador de XML fiscal para documentos NF-e.

Este módulo implementa o processamento completo de documentos fiscais eletrônicos,
incluindo parsing, validação, extração de dados e geração de XML atualizado.
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
    """Erro específico de processamento de XML fiscal."""
    pass


class XMLValidator:
    """
    Validador de estrutura e conteúdo de XML fiscal.
    
    Implementa validações específicas para documentos NF-e conforme
    especificação técnica da SEFAZ.
    """
    
    @staticmethod
    def validate_nfe_structure(xml_content: str) -> bool:
        """
        Valida estrutura básica de NF-e conforme layout 4.00.
        
        Args:
            xml_content: Conteúdo XML a ser validado
            
        Returns:
            bool: True se estrutura é válida, False caso contrário
        """
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Verificar namespace obrigatório
            if 'portalfiscal.inf.br/nfe' not in str(root.nsmap):
                return False
            
            # Verificar elementos obrigatórios conforme layout
            required_elements = [
                './/nfe:infNFe',      # Informações da NF-e
                './/nfe:ide',         # Identificação
                './/nfe:emit',        # Emitente
                './/nfe:dest',        # Destinatário
                './/nfe:det',         # Detalhamento (pelo menos 1 item)
                './/nfe:total'        # Totais
            ]
            
            namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            for element_path in required_elements:
                if root.find(element_path, namespaces) is None:
                    return False
            
            # Validar versão do layout
            inf_nfe = root.find('.//nfe:infNFe', namespaces)
            if inf_nfe is not None:
                versao = inf_nfe.get('versao')
                if versao not in ['4.00']:
                    return False
            
            return True
            
        except (ParseError, Exception):
            return False
    
    @staticmethod
    def validate_document_key(key: str) -> bool:
        """
        Valida chave de acesso do documento fiscal.
        
        A chave deve ter 44 dígitos numéricos e seguir o padrão:
        UF + AAMM + CNPJ + MOD + SERIE + NUMERO + CODIGO + DV
        
        Args:
            key: Chave de acesso a ser validada
            
        Returns:
            bool: True se chave é válida, False caso contrário
        """
        if not key or len(key) != 44:
            return False
        
        if not key.isdigit():
            return False
        
        # Validar UF (primeiros 2 dígitos)
        uf_code = int(key[:2])
        valid_ufs = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                     31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]
        if uf_code not in valid_ufs:
            return False
        
        # Validar modelo (posições 20-21)
        modelo = key[20:22]
        if modelo not in ['55', '65']:  # NF-e ou NFC-e
            return False
        
        # TODO: Implementar validação completa do dígito verificador
        return True
    
    @staticmethod
    def validate_cnpj(cnpj: str) -> bool:
        """
        Valida CNPJ usando algoritmo oficial.
        
        Args:
            cnpj: CNPJ a ser validado (apenas números)
            
        Returns:
            bool: True se CNPJ é válido, False caso contrário
        """
        if not cnpj or len(cnpj) != 14 or not cnpj.isdigit():
            return False
        
        # Verificar sequências inválidas
        if cnpj == cnpj[0] * 14:
            return False
        
        # Calcular primeiro dígito verificador
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum1 = sum(int(cnpj[i]) * weights1[i] for i in range(12))
        digit1 = 11 - (sum1 % 11)
        if digit1 >= 10:
            digit1 = 0
        
        # Calcular segundo dígito verificador
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum2 = sum(int(cnpj[i]) * weights2[i] for i in range(13))
        digit2 = 11 - (sum2 % 11)
        if digit2 >= 10:
            digit2 = 0
        
        return cnpj[-2:] == f"{digit1}{digit2}"


class XMLParser(LoggerMixin):
    """
    Parser especializado para documentos XML fiscais.
    
    Extrai dados estruturados de XMLs NF-e usando lxml para performance
    otimizada e suporte completo a namespaces.
    """
    
    def __init__(self):
        self.namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def parse_nfe_document(self, xml_content: str) -> NFEDocument:
        """
        Converte XML NF-e em modelo de dados estruturado.
        
        Args:
            xml_content: Conteúdo XML da NF-e
            
        Returns:
            NFEDocument: Documento estruturado com todos os dados extraídos
            
        Raises:
            XMLProcessingError: Se XML é inválido ou dados obrigatórios estão ausentes
        """
        try:
            # Validar estrutura antes do processamento
            if not XMLValidator.validate_nfe_structure(xml_content):
                raise XMLProcessingError("Estrutura XML inválida para NF-e")
            
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Extrair dados principais do infNFe
            inf_nfe = root.find('.//nfe:infNFe', self.namespaces)
            if inf_nfe is None:
                raise XMLProcessingError("Elemento infNFe não encontrado")
            
            # Extrair e validar chave de acesso
            document_key = inf_nfe.get('Id', '').replace('NFe', '')
            if not XMLValidator.validate_document_key(document_key):
                raise XMLProcessingError(f"Chave de documento inválida: {document_key}")
            
            # Extrair dados de identificação
            ide_data = self._extract_identification(root)
            
            # Extrair informações de emitente e destinatário
            emitter = self._extract_company_info(root, './/nfe:emit')
            recipient = self._extract_company_info(root, './/nfe:dest')
            
            # Extrair itens do documento
            items = self._extract_items(root)
            if not items:
                raise XMLProcessingError("Nenhum item encontrado no documento")
            
            # Extrair totais do documento
            totals = self._extract_totals(root)
            
            # Extrair detalhes tributários
            tax_details = self._extract_tax_details(root)
            
            # Criar documento estruturado
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
            
            # Log de sucesso
            log_processing_event(
                "xml_parsed_successfully",
                document_key,
                document_type="nfe",
                items_count=len(items),
                total_value=float(totals['total']),
                emitter_cnpj=emitter.cnpj,
                recipient_cnpj=recipient.cnpj
            )
            
            return document
            
        except Exception as e:
            self.logger.error(
                "xml_parsing_failed",
                error=str(e),
                xml_length=len(xml_content),
                error_type=type(e).__name__
            )
            raise XMLProcessingError(f"Erro ao processar XML: {str(e)}")
    
    def _extract_identification(self, root: _Element) -> Dict:
        """
        Extrai dados de identificação do documento (elemento ide).
        
        Args:
            root: Elemento raiz do XML
            
        Returns:
            Dict: Dados de identificação extraídos
            
        Raises:
            XMLProcessingError: Se dados obrigatórios não forem encontrados
        """
        ide = root.find('.//nfe:ide', self.namespaces)
        if ide is None:
            raise XMLProcessingError("Elemento ide não encontrado")
        
        # Extrair série e número
        serie_elem = ide.find('nfe:serie', self.namespaces)
        numero_elem = ide.find('nfe:nNF', self.namespaces)
        
        if serie_elem is None or numero_elem is None:
            raise XMLProcessingError("Série ou número do documento não encontrados")
        
        # Extrair data de emissão (dhEmi ou dEmi para compatibilidade)
        dh_emi = ide.find('nfe:dhEmi', self.namespaces)
        if dh_emi is not None:
            # Formato com hora (layout 4.00)
            issue_date_str = dh_emi.text
            # Remover timezone se presente para parsing
            if '+' in issue_date_str or 'Z' in issue_date_str:
                issue_date_str = issue_date_str.replace('Z', '+00:00')
                issue_date = datetime.fromisoformat(issue_date_str)
            else:
                issue_date = datetime.fromisoformat(issue_date_str)
        else:
            # Fallback para dEmi (formato antigo)
            d_emi = ide.find('nfe:dEmi', self.namespaces)
            if d_emi is not None:
                issue_date = datetime.strptime(d_emi.text, '%Y-%m-%d')
            else:
                raise XMLProcessingError("Data de emissão não encontrada")
        
        # Extrair dados adicionais
        natureza_op = ide.find('nfe:natOp', self.namespaces)
        modelo = ide.find('nfe:mod', self.namespaces)
        
        return {
            'series': int(serie_elem.text),
            'number': int(numero_elem.text),
            'issue_date': issue_date,
            'natureza_operacao': natureza_op.text if natureza_op is not None else None,
            'modelo': modelo.text if modelo is not None else '55'
        }
    
    def _extract_company_info(self, root: _Element, xpath: str) -> CompanyInfo:
        """
        Extrai informações de empresa (emitente ou destinatário).
        
        Args:
            root: Elemento raiz do XML
            xpath: XPath para localizar elemento da empresa
            
        Returns:
            CompanyInfo: Informações estruturadas da empresa
            
        Raises:
            XMLProcessingError: Se dados obrigatórios não forem encontrados
        """
        company_elem = root.find(xpath, self.namespaces)
        if company_elem is None:
            raise XMLProcessingError(f"Elemento não encontrado: {xpath}")
        
        # Extrair CNPJ/CPF
        cnpj_elem = company_elem.find('nfe:CNPJ', self.namespaces)
        cpf_elem = company_elem.find('nfe:CPF', self.namespaces)
        
        if cnpj_elem is not None:
            documento = cnpj_elem.text
            if not XMLValidator.validate_cnpj(documento):
                self.logger.warning("cnpj_validation_failed", cnpj=documento)
        elif cpf_elem is not None:
            documento = cpf_elem.text
        else:
            raise XMLProcessingError("CNPJ/CPF não encontrado")
        
        # Extrair nome
        nome_elem = company_elem.find('nfe:xNome', self.namespaces)
        if nome_elem is None:
            raise XMLProcessingError("Nome da empresa não encontrado")
        
        # Extrair endereço (diferentes padrões para emit/dest)
        if 'emit' in xpath:
            ender_elem = company_elem.find('nfe:enderEmit', self.namespaces)
        else:
            ender_elem = company_elem.find('nfe:enderDest', self.namespaces)
        
        if ender_elem is None:
            # Fallback para endereco genérico
            ender_elem = company_elem.find('nfe:endereco', self.namespaces)
        
        if ender_elem is None:
            raise XMLProcessingError("Endereço não encontrado")
        
        # Extrair dados do endereço
        logradouro = ender_elem.find('nfe:xLgr', self.namespaces)
        numero = ender_elem.find('nfe:nro', self.namespaces)
        complemento = ender_elem.find('nfe:xCpl', self.namespaces)
        bairro = ender_elem.find('nfe:xBairro', self.namespaces)
        municipio = ender_elem.find('nfe:xMun', self.namespaces)
        uf = ender_elem.find('nfe:UF', self.namespaces)
        cep = ender_elem.find('nfe:CEP', self.namespaces)
        
        # Montar endereço completo
        endereco_parts = []
        if logradouro is not None:
            endereco_parts.append(logradouro.text)
        if numero is not None:
            endereco_parts.append(numero.text)
        if complemento is not None:
            endereco_parts.append(complemento.text)
        if bairro is not None:
            endereco_parts.append(bairro.text)
        
        endereco_completo = ', '.join(filter(None, endereco_parts))
        
        return CompanyInfo(
            cnpj=documento,
            company_name=nome_elem.text,
            trade_name=self._get_optional_text(company_elem, 'nfe:xFant'),
            address=endereco_completo,
            city=municipio.text if municipio is not None else '',
            state=uf.text if uf is not None else '',
            zip_code=cep.text if cep is not None else '',
            phone=self._get_optional_text(ender_elem, 'nfe:fone'),
            email=self._get_optional_text(company_elem, 'nfe:email')
        )
    
    def _extract_items(self, root: _Element) -> List[ProductItem]:
        """
        Extrai itens do documento fiscal.
        
        Args:
            root: Elemento raiz do XML
            
        Returns:
            List[ProductItem]: Lista de itens extraídos
        """
        items = []
        det_elements = root.findall('.//nfe:det', self.namespaces)
        
        for det in det_elements:
            try:
                item_num = int(det.get('nItem'))
                
                prod = det.find('nfe:prod', self.namespaces)
                if prod is None:
                    self.logger.warning("produto_nao_encontrado", item_number=item_num)
                    continue
                
                # Extrair dados obrigatórios do produto
                product_code = self._get_required_text(prod, 'nfe:cProd', f"Código do produto item {item_num}")
                product_name = self._get_required_text(prod, 'nfe:xProd', f"Nome do produto item {item_num}")
                ncm = self._get_required_text(prod, 'nfe:NCM', f"NCM item {item_num}")
                cfop = self._get_required_text(prod, 'nfe:CFOP', f"CFOP item {item_num}")
                unit = self._get_required_text(prod, 'nfe:uCom', f"Unidade item {item_num}")
                
                # Extrair valores numéricos
                quantity_text = self._get_required_text(prod, 'nfe:qCom', f"Quantidade item {item_num}")
                unit_value_text = self._get_required_text(prod, 'nfe:vUnCom', f"Valor unitário item {item_num}")
                total_value_text = self._get_required_text(prod, 'nfe:vProd', f"Valor total item {item_num}")
                
                # Converter para Decimal para precisão fiscal
                quantity = Decimal(quantity_text)
                unit_value = Decimal(unit_value_text)
                total_value = Decimal(total_value_text)
                
                # Extrair tributação do item
                tax_details = self._extract_item_tax_details(det)
                
                # Criar item estruturado
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
                
            except Exception as e:
                self.logger.error(
                    "item_extraction_failed",
                    item_number=item_num if 'item_num' in locals() else 'unknown',
                    error=str(e)
                )
                # Continuar processamento dos outros itens
                continue
        
        return items
    
    def _extract_item_tax_details(self, det_element: _Element) -> TaxDetails:
        """
        Extrai detalhes tributários de um item específico.
        
        Args:
            det_element: Elemento det do item
            
        Returns:
            TaxDetails: Detalhes tributários extraídos
        """
        tax_details = TaxDetails()
        
        imposto = det_element.find('nfe:imposto', self.namespaces)
        if imposto is None:
            return tax_details
        
        # Extrair ICMS
        icms = imposto.find('nfe:ICMS', self.namespaces)
        if icms is not None:
            # Pode ter diferentes tipos: ICMS00, ICMS10, ICMS20, etc.
            for icms_child in icms:
                vbc = icms_child.find('nfe:vBC', self.namespaces)
                picms = icms_child.find('nfe:pICMS', self.namespaces)
                vicms = icms_child.find('nfe:vICMS', self.namespaces)
                
                if vbc is not None:
                    tax_details.icms_base = Decimal(vbc.text)
                if picms is not None:
                    tax_details.icms_rate = Decimal(picms.text)
                if vicms is not None:
                    tax_details.icms_value = Decimal(vicms.text)
                break
        
        # Extrair PIS
        pis = imposto.find('nfe:PIS', self.namespaces)
        if pis is not None:
            for pis_child in pis:
                vbc = pis_child.find('nfe:vBC', self.namespaces)
                ppis = pis_child.find('nfe:pPIS', self.namespaces)
                vpis = pis_child.find('nfe:vPIS', self.namespaces)
                
                if vbc is not None:
                    tax_details.pis_base = Decimal(vbc.text)
                if ppis is not None:
                    tax_details.pis_rate = Decimal(ppis.text)
                if vpis is not None:
                    tax_details.pis_value = Decimal(vpis.text)
                break
        
        # Extrair COFINS
        cofins = imposto.find('nfe:COFINS', self.namespaces)
        if cofins is not None:
            for cofins_child in cofins:
                vbc = cofins_child.find('nfe:vBC', self.namespaces)
                pcofins = cofins_child.find('nfe:pCOFINS', self.namespaces)
                vcofins = cofins_child.find('nfe:vCOFINS', self.namespaces)
                
                if vbc is not None:
                    tax_details.cofins_base = Decimal(vbc.text)
                if pcofins is not None:
                    tax_details.cofins_rate = Decimal(pcofins.text)
                if vcofins is not None:
                    tax_details.cofins_value = Decimal(vcofins.text)
                break
        
        return tax_details
    
    def _extract_totals(self, root: _Element) -> Dict[str, Decimal]:
        """
        Extrai totais do documento.
        
        Args:
            root: Elemento raiz do XML
            
        Returns:
            Dict: Totais extraídos do documento
            
        Raises:
            XMLProcessingError: Se totais obrigatórios não forem encontrados
        """
        total_elem = root.find('.//nfe:total/nfe:ICMSTot', self.namespaces)
        if total_elem is None:
            raise XMLProcessingError("Totais (ICMSTot) não encontrados")
        
        # Extrair valores obrigatórios
        v_prod = total_elem.find('nfe:vProd', self.namespaces)
        v_nf = total_elem.find('nfe:vNF', self.namespaces)
        
        if v_nf is None:
            raise XMLProcessingError("Valor total da NF-e não encontrado")
        
        # Extrair valores opcionais
        v_serv = total_elem.find('nfe:vServ', self.namespaces)
        v_desc = total_elem.find('nfe:vDesc', self.namespaces)
        v_frete = total_elem.find('nfe:vFrete', self.namespaces)
        v_seg = total_elem.find('nfe:vSeg', self.namespaces)
        v_outro = total_elem.find('nfe:vOutro', self.namespaces)
        
        return {
            'products': Decimal(v_prod.text) if v_prod is not None else Decimal('0'),
            'services': Decimal(v_serv.text) if v_serv is not None else Decimal('0'),
            'total': Decimal(v_nf.text),
            'discount': Decimal(v_desc.text) if v_desc is not None else Decimal('0'),
            'freight': Decimal(v_frete.text) if v_frete is not None else Decimal('0'),
            'insurance': Decimal(v_seg.text) if v_seg is not None else Decimal('0'),
            'other': Decimal(v_outro.text) if v_outro is not None else Decimal('0')
        }
    
    def _extract_tax_details(self, root: _Element) -> TaxDetails:
        """
        Extrai detalhes tributários consolidados do documento.
        
        Args:
            root: Elemento raiz do XML
            
        Returns:
            TaxDetails: Detalhes tributários consolidados
        """
        tax_details = TaxDetails()
        
        total_elem = root.find('.//nfe:total/nfe:ICMSTot', self.namespaces)
        if total_elem is None:
            return tax_details
        
        # Extrair totais de tributos
        v_icms = total_elem.find('nfe:vICMS', self.namespaces)
        v_pis = total_elem.find('nfe:vPIS', self.namespaces)
        v_cofins = total_elem.find('nfe:vCOFINS', self.namespaces)
        v_ipi = total_elem.find('nfe:vIPI', self.namespaces)
        
        if v_icms is not None:
            tax_details.icms_value = Decimal(v_icms.text)
        if v_pis is not None:
            tax_details.pis_value = Decimal(v_pis.text)
        if v_cofins is not None:
            tax_details.cofins_value = Decimal(v_cofins.text)
        if v_ipi is not None:
            tax_details.ipi_value = Decimal(v_ipi.text)
        
        # Calcular total de tributos federais
        tax_details.total_federal_taxes = (
            tax_details.pis_value + 
            tax_details.cofins_value + 
            tax_details.ipi_value +
            tax_details.ibs_value +  # Será calculado pela API governamental
            tax_details.cbs_value +  # Será calculado pela API governamental
            tax_details.selective_tax_value  # Será calculado pela API governamental
        )
        
        return tax_details
    
    def _get_required_text(self, parent: _Element, xpath: str, field_name: str) -> str:
        """
        Obtém texto de elemento obrigatório.
        
        Args:
            parent: Elemento pai
            xpath: XPath do elemento
            field_name: Nome do campo para erro
            
        Returns:
            str: Texto do elemento
            
        Raises:
            XMLProcessingError: Se elemento não for encontrado
        """
        elem = parent.find(xpath, self.namespaces)
        if elem is None or not elem.text:
            raise XMLProcessingError(f"{field_name} não encontrado")
        return elem.text.strip()
    
    def _get_optional_text(self, parent: _Element, xpath: str) -> Optional[str]:
        """
        Obtém texto de elemento opcional.
        
        Args:
            parent: Elemento pai
            xpath: XPath do elemento
            
        Returns:
            Optional[str]: Texto do elemento ou None se não encontrado
        """
        elem = parent.find(xpath, self.namespaces)
        return elem.text.strip() if elem is not None and elem.text else None


class XMLGenerator(LoggerMixin):
    """
    Gerador de XML fiscal atualizado com novos valores tributários.
    
    Atualiza XMLs existentes preservando estrutura e assinatura digital,
    modificando apenas os valores tributários calculados.
    """
    
    def __init__(self):
        self.namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
    
    def update_nfe_xml(self, document: NFEDocument) -> str:
        """
        Atualiza XML NF-e com novos valores tributários calculados.
        
        Args:
            document: Documento com valores atualizados
            
        Returns:
            str: XML atualizado
            
        Raises:
            XMLProcessingError: Se atualização falhar
        """
        try:
            # Parse do XML original
            root = etree.fromstring(document.original_xml.encode('utf-8'))
            
            # Atualizar tributos por item
            self._update_items_taxes(root, document.items)
            
            # Atualizar totais do documento
            self._update_document_totals(root, document)
            
            # Gerar XML atualizado com formatação
            updated_xml = etree.tostring(
                root,
                encoding='unicode',
                pretty_print=True,
                xml_declaration=True
            )
            
            log_processing_event(
                "xml_updated_successfully",
                document.document_key,
                original_total=float(document.total_document),
                items_updated=len(document.items)
            )
            
            return updated_xml
            
        except Exception as e:
            self.logger.error(
                "xml_update_failed",
                document_key=document.document_key,
                error=str(e),
                error_type=type(e).__name__
            )
            raise XMLProcessingError(f"Erro ao atualizar XML: {str(e)}")
    
    def _update_items_taxes(self, root: _Element, items: List[ProductItem]) -> None:
        """
        Atualiza tributos dos itens no XML.
        
        Args:
            root: Elemento raiz do XML
            items: Lista de itens com tributos atualizados
        """
        det_elements = root.findall('.//nfe:det', self.namespaces)
        
        for det in det_elements:
            item_num = int(det.get('nItem'))
            
            # Encontrar item correspondente
            item = next((i for i in items if i.item_number == item_num), None)
            if item is None:
                continue
            
            # Atualizar impostos do item
            imposto = det.find('nfe:imposto', self.namespaces)
            if imposto is not None:
                self._update_item_icms(imposto, item.tax_details)
                self._update_item_pis(imposto, item.tax_details)
                self._update_item_cofins(imposto, item.tax_details)
                
                # TODO: Adicionar novos tributos (IBS, CBS, IS)
                self._add_new_taxes_to_item(imposto, item.tax_details)
            
            self.logger.debug(
                "item_taxes_updated",
                item_number=item_num,
                product_code=item.product_code,
                total_taxes=float(item.tax_details.total_federal_taxes)
            )
    
    def _update_item_icms(self, imposto: _Element, tax_details: TaxDetails) -> None:
        """Atualiza ICMS do item."""
        icms = imposto.find('nfe:ICMS', self.namespaces)
        if icms is not None:
            for icms_child in icms:
                self._update_element_value(icms_child, 'nfe:vBC', tax_details.icms_base)
                self._update_element_value(icms_child, 'nfe:pICMS', tax_details.icms_rate)
                self._update_element_value(icms_child, 'nfe:vICMS', tax_details.icms_value)
    
    def _update_item_pis(self, imposto: _Element, tax_details: TaxDetails) -> None:
        """Atualiza PIS do item."""
        pis = imposto.find('nfe:PIS', self.namespaces)
        if pis is not None:
            for pis_child in pis:
                self._update_element_value(pis_child, 'nfe:vBC', tax_details.pis_base)
                self._update_element_value(pis_child, 'nfe:pPIS', tax_details.pis_rate)
                self._update_element_value(pis_child, 'nfe:vPIS', tax_details.pis_value)
    
    def _update_item_cofins(self, imposto: _Element, tax_details: TaxDetails) -> None:
        """Atualiza COFINS do item."""
        cofins = imposto.find('nfe:COFINS', self.namespaces)
        if cofins is not None:
            for cofins_child in cofins:
                self._update_element_value(cofins_child, 'nfe:vBC', tax_details.cofins_base)
                self._update_element_value(cofins_child, 'nfe:pCOFINS', tax_details.cofins_rate)
                self._update_element_value(cofins_child, 'nfe:vCOFINS', tax_details.cofins_value)
    
    def _add_new_taxes_to_item(self, imposto: _Element, tax_details: TaxDetails) -> None:
        """
        Adiciona novos tributos (IBS, CBS, IS) ao item.
        
        Args:
            imposto: Elemento imposto do item
            tax_details: Detalhes tributários com novos valores
        """
        # TODO: Implementar adição de novos tributos conforme layout atualizado
        # Por enquanto, apenas log dos valores calculados
        if tax_details.ibs_value > 0:
            self.logger.debug("ibs_calculated", value=float(tax_details.ibs_value))
        if tax_details.cbs_value > 0:
            self.logger.debug("cbs_calculated", value=float(tax_details.cbs_value))
        if tax_details.selective_tax_value > 0:
            self.logger.debug("selective_tax_calculated", value=float(tax_details.selective_tax_value))
    
    def _update_document_totals(self, root: _Element, document: NFEDocument) -> None:
        """
        Atualiza totais do documento no XML.
        
        Args:
            root: Elemento raiz do XML
            document: Documento com totais atualizados
        """
        total_elem = root.find('.//nfe:total/nfe:ICMSTot', self.namespaces)
        if total_elem is None:
            return
        
        # Atualizar totais de tributos
        self._update_element_value(total_elem, 'nfe:vICMS', document.tax_details.icms_value)
        self._update_element_value(total_elem, 'nfe:vPIS', document.tax_details.pis_value)
        self._update_element_value(total_elem, 'nfe:vCOFINS', document.tax_details.cofins_value)
        self._update_element_value(total_elem, 'nfe:vIPI', document.tax_details.ipi_value)
        
        # TODO: Adicionar novos campos de tributos no total
        # Aguardando definição do layout atualizado
        
        self.logger.debug(
            "document_totals_updated",
            document_key=document.document_key,
            total_value=float(document.total_document),
            total_taxes=float(document.tax_details.total_federal_taxes)
        )
    
    def _update_element_value(self, parent: _Element, xpath: str, value: Decimal) -> None:
        """
        Atualiza valor de um elemento XML.
        
        Args:
            parent: Elemento pai
            xpath: XPath do elemento a atualizar
            value: Novo valor
        """
        if value is None:
            return
            
        elem = parent.find(xpath, self.namespaces)
        if elem is not None:
            elem.text = f"{value:.2f}"


class XMLProcessor(LoggerMixin):
    """
    Processador principal de XML fiscal.
    
    Orquestra o processamento completo de documentos fiscais,
    incluindo parsing, validação, cálculos tributários e geração
    de XML atualizado.
    """
    
    def __init__(self):
        self.parser = XMLParser()
        self.generator = XMLGenerator()
        self.validator = XMLValidator()
    
    def extract_document_summary(self, xml_content: str) -> Dict:
        """
        Extrai resumo rápido do documento sem processamento completo.
        
        Args:
            xml_content: Conteúdo XML
            
        Returns:
            Dict: Resumo com dados básicos do documento
        """
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
            namespaces = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Extrair dados básicos
            inf_nfe = root.find('.//nfe:infNFe', namespaces)
            document_key = inf_nfe.get('Id', '').replace('NFe', '') if inf_nfe is not None else ''
            
            ide = root.find('.//nfe:ide', namespaces)
            serie = ide.find('nfe:serie', namespaces).text if ide is not None and ide.find('nfe:serie', namespaces) is not None else ''
            numero = ide.find('nfe:nNF', namespaces).text if ide is not None and ide.find('nfe:nNF', namespaces) is not None else ''
            
            emit = root.find('.//nfe:emit', namespaces)
            emitente = emit.find('nfe:xNome', namespaces).text if emit is not None and emit.find('nfe:xNome', namespaces) is not None else ''
            
            total = root.find('.//nfe:total/nfe:ICMSTot/nfe:vNF', namespaces)
            valor_total = total.text if total is not None else '0.00'
            
            return {
                'document_key': document_key,
                'series': serie,
                'number': numero,
                'emitter_name': emitente,
                'total_value': valor_total,
                'valid_structure': self.validate_xml_structure(xml_content, DocumentType.NFE)
            }
            
        except Exception as e:
            self.logger.error("summary_extraction_failed", error=str(e))
            return {
                'document_key': '',
                'series': '',
                'number': '',
                'emitter_name': '',
                'total_value': '0.00',
                'valid_structure': False,
                'error': str(e)
            }
    
    def validate_xml_structure(self, xml_content: str, document_type: DocumentType) -> bool:
        """
        Valida estrutura de XML fiscal.
        
        Args:
            xml_content: Conteúdo XML a ser validado
            document_type: Tipo de documento esperado
            
        Returns:
            bool: True se estrutura é válida, False caso contrário
        """
        if document_type == DocumentType.NFE:
            return self.validator.validate_nfe_structure(xml_content)
        
        # TODO: Implementar validação para outros tipos (NFC-e, CT-e, etc.)
        return False
    
    def process_nfe_document(self, xml_content: str) -> NFEDocument:
        """
        Processa documento NF-e completo com atualização tributária.
        
        Args:
            xml_content: Conteúdo XML da NF-e
            
        Returns:
            NFEDocument: Documento processado e atualizado
            
        Raises:
            XMLProcessingError: Se processamento falhar
        """
        start_time = datetime.utcnow()
        
        try:
            # Parse do documento
            document = self.parser.parse_nfe_document(xml_content)
            
            # TODO: Integrar com TaxCalculatorService para atualizar tributos
            # Por enquanto, manter valores originais
            
            # Gerar XML atualizado
            updated_xml = self.generator.update_nfe_xml(document)
            document.updated_xml = updated_xml
            document.updated_at = datetime.utcnow()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_processing_event(
                "document_processed_successfully",
                document.document_key,
                processing_time_ms=processing_time,
                items_count=len(document.items),
                emitter_cnpj=document.emitter.cnpj,
                total_value=float(document.total_document)
            )
            
            return document
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.error(
                "document_processing_failed",
                error=str(e),
                processing_time_ms=processing_time,
                xml_length=len(xml_content),
                error_type=type(e).__name__
            )
            raise
    
    def validate_xml_structure(self, xml_content: str, document_type: DocumentType) -> bool:
        """
        Valida estrutura de XML fiscal.
        
        Args:
            xml_content: Conteúdo XML a validar
            document_type: Tipo de documento fiscal
            
        Returns:
            bool: True se estrutura é válida
        """
        if document_type == DocumentType.NFE:
            return self.validator.validate_nfe_structure(xml_content)
        
        # TODO: Implementar validação para outros tipos (NFC-e, CT-e, etc.)
        return False


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



    
    def validate_xml_structure(self, xml_content: str, document_type: DocumentType) -> bool:
        """Valida estrutura de XML fiscal."""
        if document_type == DocumentType.NFE:
            return self.validator.validate_nfe_structure(xml_content)
        
        # TODO: Implementar validação para outros tipos
        return False

