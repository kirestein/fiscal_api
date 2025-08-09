# 🔧 Comandos cURL - XML Reader API

## 🎯 Comandos Prontos para Teste

### **1. Health Check**
```bash
curl -s http://localhost:8000/api/v1/health
```

### **2. Endpoint Raiz (Informações da API)**
```bash
curl -s http://localhost:8000/
```

---

## 📋 Endpoint: /xml/validate

### **Validação Básica**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/validate
```

### **Validação com Tipo Específico**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  -F "document_type=nfe" \
  http://localhost:8000/api/v1/xml/validate
```

### **Validação com Formatação JSON**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/validate | \
  python -m json.tool
```

---

## 📊 Endpoint: /xml/summary

### **Resumo Básico**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/summary
```

### **Extrair Apenas Dados Específicos**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/summary | \
  jq '{emitter: .emitter_name, value: .total_value, items: .items_count}'
```

### **Resumo com Timestamp**
```bash
echo "Timestamp: $(date)" && \
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/summary
```

---

## 🔍 Endpoint: /xml/read

### **Leitura Completa (Padrão)**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/read
```

### **Leitura Sem Validação de CNPJ**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  -F "extract_taxes=true" \
  -F "validate_cnpj=false" \
  http://localhost:8000/api/v1/xml/read
```

### **Leitura Sem Extração de Tributos**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  -F "extract_taxes=false" \
  -F "validate_cnpj=true" \
  http://localhost:8000/api/v1/xml/read
```

### **Leitura Mínima (Sem Validações)**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  -F "extract_taxes=false" \
  -F "validate_cnpj=false" \
  http://localhost:8000/api/v1/xml/read
```

---

## ⚡ Testes de Performance

### **Teste de Tempo de Resposta**
```bash
time curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/summary > /dev/null
```

### **Teste de Múltiplos Arquivos**
```bash
for file in *.xml; do
  echo "Processando: $file"
  curl -s -X POST \
    -F "xml_file=@$file" \
    http://localhost:8000/api/v1/xml/summary | \
    jq '.emitter_name, .total_value'
  echo "---"
done
```

### **Benchmark de Performance**
```bash
echo "=== BENCHMARK XML READER ==="
echo "1. Validação:"
time curl -s -X POST -F "xml_file=@test_xml_sample.xml" http://localhost:8000/api/v1/xml/validate > /dev/null

echo "2. Resumo:"
time curl -s -X POST -F "xml_file=@test_xml_sample.xml" http://localhost:8000/api/v1/xml/summary > /dev/null

echo "3. Leitura completa:"
time curl -s -X POST -F "xml_file=@test_xml_sample.xml" -F "extract_taxes=false" -F "validate_cnpj=false" http://localhost:8000/api/v1/xml/read > /dev/null
```

---

## 🚨 Testes de Erro

### **Arquivo Inválido (Não XML)**
```bash
echo "teste" > arquivo_invalido.txt
curl -s -X POST \
  -F "xml_file=@arquivo_invalido.txt" \
  http://localhost:8000/api/v1/xml/validate
rm arquivo_invalido.txt
```

### **Arquivo Muito Grande (Simulação)**
```bash
# Criar arquivo grande (>10MB)
dd if=/dev/zero of=arquivo_grande.xml bs=1M count=11 2>/dev/null
curl -s -X POST \
  -F "xml_file=@arquivo_grande.xml" \
  http://localhost:8000/api/v1/xml/validate
rm arquivo_grande.xml
```

### **XML Malformado**
```bash
echo "<xml>malformado" > xml_malformado.xml
curl -s -X POST \
  -F "xml_file=@xml_malformado.xml" \
  http://localhost:8000/api/v1/xml/validate
rm xml_malformado.xml
```

---

## 📈 Monitoramento e Debug

### **Verificar Status da API**
```bash
curl -s http://localhost:8000/api/v1/health | jq '.status'
```

### **Extrair Métricas de Performance**
```bash
curl -s -X POST \
  -F "xml_file=@test_xml_sample.xml" \
  http://localhost:8000/api/v1/xml/read | \
  jq '.processing_time_ms, .success, .errors | length'
```

### **Monitoramento Contínuo**
```bash
while true; do
  echo "$(date): $(curl -s http://localhost:8000/api/v1/health | jq -r '.status')"
  sleep 30
done
```

---

## 🔄 Scripts de Automação

### **Validação em Lote**
```bash
#!/bin/bash
# validate_batch.sh
for xml_file in *.xml; do
  echo "Validando: $xml_file"
  result=$(curl -s -X POST -F "xml_file=@$xml_file" http://localhost:8000/api/v1/xml/validate)
  valid=$(echo $result | jq -r '.valid')
  if [ "$valid" = "true" ]; then
    echo "✅ $xml_file: VÁLIDO"
  else
    echo "❌ $xml_file: INVÁLIDO"
    echo $result | jq '.errors'
  fi
  echo "---"
done
```

### **Extração de Dados para CSV**
```bash
#!/bin/bash
# extract_to_csv.sh
echo "arquivo,emitente,cnpj,valor,itens" > resultados.csv
for xml_file in *.xml; do
  result=$(curl -s -X POST -F "xml_file=@$xml_file" http://localhost:8000/api/v1/xml/summary)
  emitente=$(echo $result | jq -r '.emitter_name')
  cnpj=$(echo $result | jq -r '.emitter_cnpj')
  valor=$(echo $result | jq -r '.total_value')
  itens=$(echo $result | jq -r '.items_count')
  echo "$xml_file,$emitente,$cnpj,$valor,$itens" >> resultados.csv
done
echo "Dados extraídos para: resultados.csv"
```

---

**Nota:** Substitua `test_xml_sample.xml` pelo caminho do seu arquivo XML real.  
**Servidor deve estar rodando em:** http://localhost:8000

