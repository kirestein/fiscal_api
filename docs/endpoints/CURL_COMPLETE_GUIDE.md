# 📡 Documentação Completa - Comandos cURL API Fiscal XML

## 📋 Visão Geral

Esta documentação fornece comandos cURL completos e prontos para uso com a API Fiscal XML, incluindo todos os endpoints, parâmetros, headers e cenários de uso.

### **Base URL:**
```
Desenvolvimento: http://localhost:8000
Produção: https://api.fiscal-xml.com
```

### **Endpoints Disponíveis:**
- `GET /health` - Health check da API
- `POST /api/v1/xml/validate` - Validação rápida de XML
- `POST /api/v1/xml/summary` - Resumo otimizado de documento
- `POST /api/v1/xml/read` - Leitura completa com processamento

## 🔍 Health Check

### **Endpoint:** `GET /health`
**Descrição:** Verifica se a API está funcionando corretamente

#### **Comando Básico:**
```bash
curl -X GET http://localhost:8000/health
```

#### **Resposta Esperada:**
```json
{
  "status": "healthy",
  "timestamp": 1691596800.123,
  "version": "1.0.0"
}
```

#### **Com Headers Detalhados:**
```bash
curl -X GET \
  -H "Accept: application/json" \
  -H "User-Agent: FiscalAPI-Client/1.0" \
  -v \
  http://localhost:8000/health
```

#### **Verificação de Performance:**
```bash
# Medir tempo de resposta
curl -X GET \
  -w "Time: %{time_total}s\nStatus: %{http_code}\n" \
  -s -o /dev/null \
  http://localhost:8000/health
```

## ✅ Validação de XML

### **Endpoint:** `POST /api/v1/xml/validate`
**Descrição:** Validação rápida da estrutura do XML sem processamento completo

#### **Comando Básico:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/validate
```

#### **Com Headers Completos:**
```bash
curl -X POST \
  -H "Accept: application/json" \
  -H "User-Agent: FiscalAPI-Client/1.0" \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/validate
```

#### **Resposta de Sucesso:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "document_key": "41250115495505000141550010001278001000921722",
  "document_type": "nfe",
  "file_size": 5243,
  "processing_time_ms": 45.2
}
```

#### **Resposta de Erro:**
```json
{
  "valid": false,
  "errors": [
    {
      "code": "INVALID_XML_STRUCTURE",
      "message": "XML mal formado na linha 15",
      "line": 15,
      "column": 23
    }
  ],
  "warnings": [],
  "file_size": 1234,
  "processing_time_ms": 12.5
}
```

#### **Validação com Timeout Customizado:**
```bash
curl -X POST \
  -H "Accept: application/json" \
  -F "xml_file=@documento.xml" \
  --max-time 30 \
  http://localhost:8000/api/v1/xml/validate
```

## 📊 Resumo de Documento

### **Endpoint:** `POST /api/v1/xml/summary`
**Descrição:** Extração rápida de dados essenciais do documento fiscal

#### **Comando Básico:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/summary
```

#### **Com Parâmetros Opcionais:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "include_items=true" \
  -F "validate_cnpj=true" \
  http://localhost:8000/api/v1/xml/summary
```

#### **Resposta de Sucesso:**
```json
{
  "document_key": "41250115495505000141550010001278001000921722",
  "document_type": "nfe",
  "emitter_name": "EMPRESA TESTE LTDA",
  "emitter_cnpj": "15495505000141",
  "recipient_name": "CLIENTE TESTE LTDA",
  "recipient_cnpj": "12345678000195",
  "total_value": "150.00",
  "issue_date": "2025-01-15",
  "items_count": 1,
  "processing_time_ms": 15.3
}
```

#### **Com Output Formatado:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/summary | jq '.'
```

#### **Salvando Resposta em Arquivo:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  -o summary_response.json \
  http://localhost:8000/api/v1/xml/summary
```


## 📄 Leitura Completa de Documento

### **Endpoint:** `POST /api/v1/xml/read`
**Descrição:** Processamento completo do XML com extração de todos os dados e cálculos tributários

#### **Comando Básico:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/read
```

#### **Com Todos os Parâmetros:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=true" \
  -F "validate_cnpj=true" \
  -F "calculate_totals=true" \
  -F "generate_updated_xml=true" \
  http://localhost:8000/api/v1/xml/read
```

#### **Resposta de Sucesso (Resumida):**
```json
{
  "success": true,
  "processing_time_ms": 1.4,
  "errors": [],
  "warnings": [],
  "document": {
    "document_key": "41250115495505000141550010001278001000921722",
    "document_type": "nfe",
    "processing_status": "completed",
    "emitter": {
      "trade_name": "EMPRESA TESTE LTDA",
      "cnpj": "15495505000141",
      "address": "RUA TESTE, 123"
    },
    "recipient": {
      "trade_name": "CLIENTE TESTE LTDA", 
      "cnpj": "12345678000195"
    },
    "total_document": "150.00",
    "items": [
      {
        "product_name": "PRODUTO TESTE",
        "quantity": 1.0,
        "unit_value": "150.00",
        "total_value": "150.00"
      }
    ]
  }
}
```

#### **Com Headers de Autenticação (Produção):**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Accept: application/json" \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=true" \
  https://api.fiscal-xml.com/api/v1/xml/read
```

#### **Processamento com Timeout Estendido:**
```bash
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=true" \
  --max-time 60 \
  --connect-timeout 10 \
  http://localhost:8000/api/v1/xml/read
```

#### **Salvando XML Atualizado:**
```bash
# Extrair XML atualizado da resposta
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "generate_updated_xml=true" \
  http://localhost:8000/api/v1/xml/read | \
  jq -r '.updated_xml' > documento_atualizado.xml
```

## 🔧 Parâmetros Detalhados

### **Parâmetros Comuns:**

#### **xml_file (obrigatório)**
- **Tipo:** File upload
- **Formato:** Multipart form data
- **Tamanhos aceitos:** Até 10MB
- **Formatos:** .xml

```bash
-F "xml_file=@/caminho/para/documento.xml"
```

#### **extract_taxes (opcional)**
- **Tipo:** Boolean
- **Default:** false
- **Descrição:** Calcula tributos IBS/CBS/IS

```bash
-F "extract_taxes=true"
```

#### **validate_cnpj (opcional)**
- **Tipo:** Boolean  
- **Default:** false
- **Descrição:** Valida CNPJs com algoritmo oficial

```bash
-F "validate_cnpj=true"
```

#### **calculate_totals (opcional)**
- **Tipo:** Boolean
- **Default:** true
- **Descrição:** Recalcula totais do documento

```bash
-F "calculate_totals=false"
```

#### **generate_updated_xml (opcional)**
- **Tipo:** Boolean
- **Default:** false
- **Descrição:** Gera XML atualizado com novos cálculos

```bash
-F "generate_updated_xml=true"
```

### **Headers Recomendados:**

#### **Accept**
```bash
-H "Accept: application/json"
```

#### **User-Agent**
```bash
-H "User-Agent: FiscalAPI-Client/1.0"
```

#### **Content-Type (automático com -F)**
```bash
# Não necessário com -F, é definido automaticamente como:
# Content-Type: multipart/form-data; boundary=...
```

## 📊 Códigos de Status HTTP

### **Códigos de Sucesso:**
- **200 OK** - Processamento realizado com sucesso
- **202 Accepted** - Processamento aceito (modo assíncrono)

### **Códigos de Erro do Cliente:**
- **400 Bad Request** - Parâmetros inválidos ou XML mal formado
- **401 Unauthorized** - Token de autenticação inválido
- **403 Forbidden** - Acesso negado ou quota excedida
- **413 Payload Too Large** - Arquivo muito grande (>10MB)
- **415 Unsupported Media Type** - Formato de arquivo não suportado
- **422 Unprocessable Entity** - XML válido mas com dados inconsistentes
- **429 Too Many Requests** - Rate limit excedido

### **Códigos de Erro do Servidor:**
- **500 Internal Server Error** - Erro interno do servidor
- **502 Bad Gateway** - Erro de gateway
- **503 Service Unavailable** - Serviço temporariamente indisponível
- **504 Gateway Timeout** - Timeout de processamento

## 🎯 Exemplos por Cenário

### **Cenário 1: Validação Rápida**
```bash
# Para verificar se um XML está bem formado
curl -X POST \
  -F "xml_file=@documento.xml" \
  -w "Status: %{http_code}\nTime: %{time_total}s\n" \
  http://localhost:8000/api/v1/xml/validate
```

### **Cenário 2: Dashboard de Resumos**
```bash
# Para exibir dados em dashboard
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "include_items=true" \
  http://localhost:8000/api/v1/xml/summary | \
  jq '{
    empresa: .emitter_name,
    valor: .total_value,
    data: .issue_date,
    itens: .items_count
  }'
```

### **Cenário 3: Processamento Completo**
```bash
# Para análise fiscal completa
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=true" \
  -F "validate_cnpj=true" \
  -F "generate_updated_xml=true" \
  http://localhost:8000/api/v1/xml/read | \
  jq '.document | {
    chave: .document_key,
    emitente: .emitter.trade_name,
    total: .total_document,
    status: .processing_status
  }'
```

### **Cenário 4: Batch Processing**
```bash
# Processar múltiplos arquivos
for file in *.xml; do
  echo "Processando: $file"
  curl -X POST \
    -F "xml_file=@$file" \
    -s \
    http://localhost:8000/api/v1/xml/summary | \
    jq -r '"\(.emitter_name): \(.total_value)"'
done
```


## 🚀 Exemplos Avançados

### **Processamento com Diferentes Tipos de XML**

#### **NF-e Simples:**
```bash
# Documento com um item
curl -X POST \
  -F "xml_file=@nfe_simples.xml" \
  -F "extract_taxes=true" \
  http://localhost:8000/api/v1/xml/read | \
  jq '.document.items | length'
```

#### **NF-e com Múltiplos Itens:**
```bash
# Documento com vários produtos
curl -X POST \
  -F "xml_file=@nfe_multiplos_itens.xml" \
  -F "calculate_totals=true" \
  http://localhost:8000/api/v1/xml/read | \
  jq '.document.items[] | {produto: .product_name, valor: .total_value}'
```

#### **NF-e com Serviços:**
```bash
# Documento de prestação de serviços
curl -X POST \
  -F "xml_file=@nfe_servicos.xml" \
  -F "extract_taxes=true" \
  -F "validate_cnpj=true" \
  http://localhost:8000/api/v1/xml/read | \
  jq '.document.tax_details'
```

### **Autenticação e Segurança**

#### **Com JWT Token:**
```bash
# Obter token de autenticação
TOKEN=$(curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' \
  https://api.fiscal-xml.com/auth/login | \
  jq -r '.access_token')

# Usar token na requisição
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -F "xml_file=@documento.xml" \
  https://api.fiscal-xml.com/api/v1/xml/read
```

#### **Com API Key:**
```bash
# Definir API key como variável de ambiente
export API_KEY="your-api-key-here"

# Usar API key na requisição
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -F "xml_file=@documento.xml" \
  https://api.fiscal-xml.com/api/v1/xml/validate
```

#### **Autenticação Combinada:**
```bash
# JWT + API Key para máxima segurança
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Key: $API_KEY" \
  -H "Accept: application/json" \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=true" \
  https://api.fiscal-xml.com/api/v1/xml/read
```

### **Performance e Monitoramento**

#### **Medição de Performance:**
```bash
# Medir tempo detalhado
curl -X POST \
  -F "xml_file=@documento.xml" \
  -w "
DNS Lookup:    %{time_namelookup}s
Connect:       %{time_connect}s
Pre-transfer:  %{time_pretransfer}s
Start-transfer:%{time_starttransfer}s
Total:         %{time_total}s
Size:          %{size_download} bytes
Speed:         %{speed_download} bytes/s
" \
  -o response.json \
  http://localhost:8000/api/v1/xml/read
```

#### **Teste de Carga Simples:**
```bash
# Executar 10 requisições paralelas
seq 1 10 | xargs -n1 -P10 -I{} curl -X POST \
  -F "xml_file=@documento.xml" \
  -s -w "Request {}: %{time_total}s\n" \
  -o /dev/null \
  http://localhost:8000/api/v1/xml/validate
```

#### **Monitoramento Contínuo:**
```bash
# Verificar saúde da API a cada 30 segundos
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
  echo "$(date): API Status $STATUS"
  sleep 30
done
```

### **Processamento em Lote**

#### **Script de Processamento em Lote:**
```bash
#!/bin/bash
# process_batch.sh

INPUT_DIR="./xml_files"
OUTPUT_DIR="./processed"
API_URL="http://localhost:8000/api/v1/xml/summary"

mkdir -p "$OUTPUT_DIR"

for xml_file in "$INPUT_DIR"/*.xml; do
  filename=$(basename "$xml_file" .xml)
  echo "Processando: $filename"
  
  curl -X POST \
    -F "xml_file=@$xml_file" \
    -F "include_items=true" \
    -s \
    "$API_URL" > "$OUTPUT_DIR/${filename}_summary.json"
  
  if [ $? -eq 0 ]; then
    echo "✅ $filename processado com sucesso"
  else
    echo "❌ Erro ao processar $filename"
  fi
done
```

#### **Processamento Paralelo:**
```bash
#!/bin/bash
# parallel_process.sh

find ./xml_files -name "*.xml" | \
xargs -n1 -P5 -I{} bash -c '
  filename=$(basename "{}" .xml)
  curl -X POST \
    -F "xml_file=@{}" \
    -s \
    http://localhost:8000/api/v1/xml/validate > "./results/${filename}_result.json"
  echo "Processado: $filename"
'
```

### **Integração com Pipelines**

#### **Pipeline CI/CD:**
```bash
# .github/workflows/test-api.yml
- name: Test API Endpoints
  run: |
    # Aguardar API estar online
    timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
    
    # Testar validação
    curl -X POST \
      -F "xml_file=@tests/fixtures/valid.xml" \
      --fail \
      http://localhost:8000/api/v1/xml/validate
    
    # Testar processamento
    curl -X POST \
      -F "xml_file=@tests/fixtures/complete.xml" \
      -F "extract_taxes=true" \
      --fail \
      http://localhost:8000/api/v1/xml/read
```

#### **Webhook Integration:**
```bash
# Processar e enviar resultado via webhook
RESULT=$(curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=true" \
  http://localhost:8000/api/v1/xml/read)

# Enviar resultado para webhook
curl -X POST \
  -H "Content-Type: application/json" \
  -d "$RESULT" \
  https://your-webhook-url.com/fiscal-processed
```

### **Casos de Uso Específicos**

#### **Validação de Lote para Contabilidade:**
```bash
#!/bin/bash
# validate_accounting_batch.sh

REPORT_FILE="validation_report_$(date +%Y%m%d_%H%M%S).csv"
echo "Arquivo,Status,Chave,Emitente,Valor,Erros" > "$REPORT_FILE"

for xml_file in ./nfes/*.xml; do
  filename=$(basename "$xml_file")
  
  result=$(curl -X POST \
    -F "xml_file=@$xml_file" \
    -s \
    http://localhost:8000/api/v1/xml/summary)
  
  if echo "$result" | jq -e '.document_key' > /dev/null; then
    key=$(echo "$result" | jq -r '.document_key')
    emitter=$(echo "$result" | jq -r '.emitter_name')
    value=$(echo "$result" | jq -r '.total_value')
    echo "$filename,VÁLIDO,$key,$emitter,$value," >> "$REPORT_FILE"
  else
    errors=$(echo "$result" | jq -r '.errors[]?.message' | tr '\n' ';')
    echo "$filename,INVÁLIDO,,,,$errors" >> "$REPORT_FILE"
  fi
done

echo "Relatório gerado: $REPORT_FILE"
```

#### **Extração de Dados para BI:**
```bash
#!/bin/bash
# extract_for_bi.sh

OUTPUT_FILE="fiscal_data_$(date +%Y%m%d).json"
echo "[]" > "$OUTPUT_FILE"

for xml_file in ./xml_files/*.xml; do
  echo "Extraindo dados de: $(basename "$xml_file")"
  
  data=$(curl -X POST \
    -F "xml_file=@$xml_file" \
    -F "extract_taxes=true" \
    -F "validate_cnpj=true" \
    -s \
    http://localhost:8000/api/v1/xml/read | \
    jq '{
      document_key: .document.document_key,
      emitter_cnpj: .document.emitter.cnpj,
      emitter_name: .document.emitter.trade_name,
      total_value: .document.total_document,
      issue_date: .document.issue_date,
      items_count: (.document.items | length),
      tax_total: .document.tax_details.total_taxes,
      processing_date: now | strftime("%Y-%m-%d %H:%M:%S")
    }')
  
  # Adicionar ao arquivo JSON
  jq ". += [$data]" "$OUTPUT_FILE" > temp.json && mv temp.json "$OUTPUT_FILE"
done

echo "Dados extraídos para: $OUTPUT_FILE"
```

#### **Monitoramento de Compliance:**
```bash
#!/bin/bash
# compliance_check.sh

COMPLIANCE_REPORT="compliance_$(date +%Y%m%d).txt"

{
  echo "=== RELATÓRIO DE COMPLIANCE FISCAL ==="
  echo "Data: $(date)"
  echo "======================================="
  echo
  
  total_files=0
  valid_files=0
  invalid_cnpj=0
  tax_errors=0
  
  for xml_file in ./audit/*.xml; do
    ((total_files++))
    filename=$(basename "$xml_file")
    
    result=$(curl -X POST \
      -F "xml_file=@$xml_file" \
      -F "extract_taxes=true" \
      -F "validate_cnpj=true" \
      -s \
      http://localhost:8000/api/v1/xml/read)
    
    if echo "$result" | jq -e '.success' > /dev/null; then
      ((valid_files++))
      
      # Verificar CNPJ
      cnpj_valid=$(echo "$result" | jq -r '.document.emitter.cnpj_valid // false')
      if [ "$cnpj_valid" = "false" ]; then
        ((invalid_cnpj++))
        echo "⚠️  CNPJ inválido em: $filename"
      fi
      
      # Verificar cálculos tributários
      tax_errors_count=$(echo "$result" | jq -r '.warnings | map(select(.type == "tax_calculation")) | length')
      if [ "$tax_errors_count" -gt 0 ]; then
        ((tax_errors++))
        echo "⚠️  Erro de cálculo tributário em: $filename"
      fi
      
    else
      echo "❌ Arquivo inválido: $filename"
    fi
  done
  
  echo
  echo "=== RESUMO ==="
  echo "Total de arquivos: $total_files"
  echo "Arquivos válidos: $valid_files"
  echo "CNPJs inválidos: $invalid_cnpj"
  echo "Erros tributários: $tax_errors"
  echo "Taxa de conformidade: $(( valid_files * 100 / total_files ))%"
  
} > "$COMPLIANCE_REPORT"

echo "Relatório de compliance gerado: $COMPLIANCE_REPORT"
```


## 🔧 Troubleshooting e Debugging

### **Modo Verbose para Debug**

#### **Debug Completo:**
```bash
# Mostrar todos os detalhes da requisição
curl -X POST \
  -F "xml_file=@documento.xml" \
  -v \
  --trace-ascii debug.log \
  http://localhost:8000/api/v1/xml/validate
```

#### **Headers de Debug:**
```bash
# Incluir headers de debug
curl -X POST \
  -H "X-Debug-Mode: true" \
  -H "X-Request-ID: $(uuidgen)" \
  -F "xml_file=@documento.xml" \
  -v \
  http://localhost:8000/api/v1/xml/read
```

#### **Capturar Headers de Resposta:**
```bash
# Salvar headers em arquivo separado
curl -X POST \
  -F "xml_file=@documento.xml" \
  -D response_headers.txt \
  -o response_body.json \
  http://localhost:8000/api/v1/xml/summary
```

### **Tratamento de Erros Comuns**

#### **Erro 400 - Bad Request:**
```bash
# Verificar formato do arquivo
file documento.xml

# Validar XML localmente
xmllint --noout documento.xml

# Testar com arquivo válido conhecido
curl -X POST \
  -F "xml_file=@valid_sample.xml" \
  http://localhost:8000/api/v1/xml/validate
```

#### **Erro 413 - Payload Too Large:**
```bash
# Verificar tamanho do arquivo
ls -lh documento.xml

# Comprimir XML se necessário
gzip -c documento.xml > documento.xml.gz

# Usar arquivo comprimido (se suportado)
curl -X POST \
  -H "Content-Encoding: gzip" \
  -F "xml_file=@documento.xml.gz" \
  http://localhost:8000/api/v1/xml/validate
```

#### **Erro 429 - Rate Limit:**
```bash
# Implementar retry com backoff
for i in {1..3}; do
  response=$(curl -X POST \
    -F "xml_file=@documento.xml" \
    -w "%{http_code}" \
    -s \
    http://localhost:8000/api/v1/xml/validate)
  
  if [[ "$response" == *"200"* ]]; then
    echo "Sucesso na tentativa $i"
    break
  elif [[ "$response" == *"429"* ]]; then
    echo "Rate limit atingido, aguardando..."
    sleep $((i * 2))
  else
    echo "Erro: $response"
    break
  fi
done
```

#### **Erro 500 - Internal Server Error:**
```bash
# Verificar logs do servidor
curl -X GET \
  -H "X-Request-ID: $(uuidgen)" \
  http://localhost:8000/health

# Tentar endpoint mais simples primeiro
curl -X POST \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/validate

# Se validação funcionar, tentar processamento
curl -X POST \
  -F "xml_file=@documento.xml" \
  -F "extract_taxes=false" \
  http://localhost:8000/api/v1/xml/summary
```

### **Validação de Conectividade**

#### **Teste de Conectividade Básica:**
```bash
# Verificar se o serviço está respondendo
curl -I http://localhost:8000/health

# Teste de latência
ping -c 4 localhost

# Verificar portas abertas
netstat -an | grep 8000
```

#### **Teste de DNS (Produção):**
```bash
# Verificar resolução DNS
nslookup api.fiscal-xml.com

# Teste de conectividade HTTPS
curl -I https://api.fiscal-xml.com/health

# Verificar certificado SSL
openssl s_client -connect api.fiscal-xml.com:443 -servername api.fiscal-xml.com
```

### **Otimizações de Performance**

#### **Reutilização de Conexão:**
```bash
# Usar keep-alive para múltiplas requisições
curl -X POST \
  -H "Connection: keep-alive" \
  -F "xml_file=@documento1.xml" \
  http://localhost:8000/api/v1/xml/validate

curl -X POST \
  -H "Connection: keep-alive" \
  -F "xml_file=@documento2.xml" \
  http://localhost:8000/api/v1/xml/validate
```

#### **Compressão de Resposta:**
```bash
# Solicitar resposta comprimida
curl -X POST \
  -H "Accept-Encoding: gzip, deflate" \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/read
```

#### **Timeout Otimizado:**
```bash
# Configurar timeouts apropriados
curl -X POST \
  --connect-timeout 10 \
  --max-time 60 \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/read
```

### **Monitoramento e Métricas**

#### **Script de Monitoramento:**
```bash
#!/bin/bash
# monitor_api.sh

LOG_FILE="api_monitor_$(date +%Y%m%d).log"

while true; do
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  # Teste de health check
  health_response=$(curl -s -w "%{http_code}:%{time_total}" -o /dev/null http://localhost:8000/health)
  health_code=$(echo $health_response | cut -d: -f1)
  health_time=$(echo $health_response | cut -d: -f2)
  
  # Teste de endpoint funcional
  test_response=$(curl -s -w "%{http_code}:%{time_total}" -o /dev/null \
    -F "xml_file=@test_sample.xml" \
    http://localhost:8000/api/v1/xml/validate)
  test_code=$(echo $test_response | cut -d: -f1)
  test_time=$(echo $test_response | cut -d: -f2)
  
  # Log dos resultados
  echo "$timestamp,health,$health_code,$health_time,validate,$test_code,$test_time" >> $LOG_FILE
  
  # Alertas
  if [ "$health_code" != "200" ] || [ "$test_code" != "200" ]; then
    echo "ALERTA: API com problemas em $timestamp" | mail -s "API Alert" admin@company.com
  fi
  
  sleep 60
done
```

#### **Métricas de Performance:**
```bash
#!/bin/bash
# performance_metrics.sh

echo "=== MÉTRICAS DE PERFORMANCE DA API ==="
echo "Timestamp: $(date)"
echo

# Teste de latência
echo "1. Latência do Health Check:"
for i in {1..10}; do
  time=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8000/health)
  echo "  Tentativa $i: ${time}s"
done

echo
echo "2. Latência de Validação:"
for i in {1..5}; do
  time=$(curl -s -w "%{time_total}" -o /dev/null \
    -F "xml_file=@test_sample.xml" \
    http://localhost:8000/api/v1/xml/validate)
  echo "  Tentativa $i: ${time}s"
done

echo
echo "3. Throughput Test (10 requisições paralelas):"
start_time=$(date +%s)
seq 1 10 | xargs -n1 -P10 -I{} curl -s -o /dev/null \
  -F "xml_file=@test_sample.xml" \
  http://localhost:8000/api/v1/xml/validate
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "  10 requisições em ${duration}s"
echo "  Throughput: $(echo "scale=2; 10 / $duration" | bc) req/s"
```

## 📚 Boas Práticas

### **Segurança**

#### **Nunca Expor Credenciais:**
```bash
# ❌ ERRADO - credenciais no comando
curl -H "Authorization: Bearer abc123" ...

# ✅ CORRETO - usar variáveis de ambiente
export API_TOKEN="abc123"
curl -H "Authorization: Bearer $API_TOKEN" ...

# ✅ CORRETO - ler de arquivo seguro
API_TOKEN=$(cat ~/.api_token)
curl -H "Authorization: Bearer $API_TOKEN" ...
```

#### **Validar Certificados SSL:**
```bash
# ✅ Sempre validar certificados em produção
curl --cacert /path/to/ca-bundle.crt \
  -H "Authorization: Bearer $API_TOKEN" \
  https://api.fiscal-xml.com/api/v1/xml/validate

# ❌ Apenas para desenvolvimento/debug
curl -k https://api.fiscal-xml.com/api/v1/xml/validate
```

### **Eficiência**

#### **Reutilizar Conexões:**
```bash
# ✅ Usar cookie jar para sessões
curl -c cookies.txt -b cookies.txt \
  -F "xml_file=@documento1.xml" \
  http://localhost:8000/api/v1/xml/validate

curl -c cookies.txt -b cookies.txt \
  -F "xml_file=@documento2.xml" \
  http://localhost:8000/api/v1/xml/validate
```

#### **Processamento Inteligente:**
```bash
# ✅ Usar endpoint apropriado para cada caso
# Para validação rápida
curl -F "xml_file=@doc.xml" .../xml/validate

# Para dados de dashboard
curl -F "xml_file=@doc.xml" .../xml/summary

# Para análise completa
curl -F "xml_file=@doc.xml" -F "extract_taxes=true" .../xml/read
```

### **Tratamento de Erros**

#### **Verificação de Status:**
```bash
# ✅ Sempre verificar código de status
response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
  -F "xml_file=@documento.xml" \
  http://localhost:8000/api/v1/xml/validate)

http_code=$(echo $response | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
body=$(echo $response | sed -E 's/HTTPSTATUS:[0-9]*$//')

if [ "$http_code" -eq 200 ]; then
  echo "Sucesso: $body"
else
  echo "Erro $http_code: $body"
  exit 1
fi
```

#### **Retry com Backoff:**
```bash
# ✅ Implementar retry inteligente
retry_request() {
  local max_attempts=3
  local delay=1
  local attempt=1
  
  while [ $attempt -le $max_attempts ]; do
    echo "Tentativa $attempt de $max_attempts"
    
    response=$(curl -s -w "%{http_code}" \
      -F "xml_file=@$1" \
      http://localhost:8000/api/v1/xml/validate)
    
    if [[ "$response" == *"200"* ]]; then
      echo "Sucesso!"
      return 0
    elif [[ "$response" == *"429"* ]] || [[ "$response" == *"5"* ]]; then
      echo "Erro temporário, aguardando ${delay}s..."
      sleep $delay
      delay=$((delay * 2))
      attempt=$((attempt + 1))
    else
      echo "Erro permanente: $response"
      return 1
    fi
  done
  
  echo "Máximo de tentativas excedido"
  return 1
}

# Usar a função
retry_request "documento.xml"
```

### **Logging e Auditoria**

#### **Log Estruturado:**
```bash
# ✅ Criar logs estruturados
log_request() {
  local endpoint="$1"
  local file="$2"
  local timestamp=$(date -Iseconds)
  local request_id=$(uuidgen)
  
  echo "[$timestamp] REQUEST_START: id=$request_id endpoint=$endpoint file=$file" >> api_requests.log
  
  response=$(curl -s -w "%{http_code}:%{time_total}" \
    -H "X-Request-ID: $request_id" \
    -F "xml_file=@$file" \
    "$endpoint")
  
  http_code=$(echo $response | cut -d: -f1)
  time_total=$(echo $response | cut -d: -f2)
  
  echo "[$timestamp] REQUEST_END: id=$request_id status=$http_code time=${time_total}s" >> api_requests.log
}

# Usar a função
log_request "http://localhost:8000/api/v1/xml/validate" "documento.xml"
```

## 📖 Referência Rápida

### **Comandos Essenciais:**

```bash
# Health check
curl http://localhost:8000/health

# Validação rápida
curl -F "xml_file=@doc.xml" localhost:8000/api/v1/xml/validate

# Resumo para dashboard
curl -F "xml_file=@doc.xml" localhost:8000/api/v1/xml/summary

# Processamento completo
curl -F "xml_file=@doc.xml" -F "extract_taxes=true" localhost:8000/api/v1/xml/read

# Com autenticação
curl -H "Authorization: Bearer $TOKEN" -F "xml_file=@doc.xml" api.fiscal-xml.com/api/v1/xml/read

# Debug mode
curl -v -F "xml_file=@doc.xml" localhost:8000/api/v1/xml/validate

# Performance test
curl -w "Time: %{time_total}s\n" -F "xml_file=@doc.xml" localhost:8000/api/v1/xml/validate
```

### **Variáveis de Ambiente Recomendadas:**

```bash
# Configuração base
export FISCAL_API_BASE_URL="http://localhost:8000"
export FISCAL_API_TOKEN="your-jwt-token"
export FISCAL_API_KEY="your-api-key"

# Timeouts
export CURL_CONNECT_TIMEOUT=10
export CURL_MAX_TIME=60

# Debug
export CURL_VERBOSE=false
export LOG_REQUESTS=true
```

### **Aliases Úteis:**

```bash
# Adicionar ao ~/.bashrc ou ~/.zshrc
alias fiscal-health='curl $FISCAL_API_BASE_URL/health'
alias fiscal-validate='curl -F "xml_file=@$1" $FISCAL_API_BASE_URL/api/v1/xml/validate'
alias fiscal-summary='curl -F "xml_file=@$1" $FISCAL_API_BASE_URL/api/v1/xml/summary'
alias fiscal-read='curl -F "xml_file=@$1" -F "extract_taxes=true" $FISCAL_API_BASE_URL/api/v1/xml/read'
```

---

## 🎯 Conclusão

Esta documentação fornece todos os comandos cURL necessários para interagir eficientemente com a API Fiscal XML. Use os exemplos básicos para começar rapidamente e os exemplos avançados para casos de uso específicos em produção.

**Para suporte adicional:**
- 📧 Email: support@fiscal-xml.com
- 📚 Documentação: https://docs.fiscal-xml.com
- 🐛 Issues: https://github.com/fiscal-api/issues

**Última atualização:** $(date +"%Y-%m-%d")

