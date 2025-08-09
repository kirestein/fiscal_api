# 🚀 **GUIA DE DEPLOYMENT - FISCAL XML API**

## 📋 **Pré-requisitos**

### **Sistema**
- Python 3.11+
- PostgreSQL 13+
- Redis 6+ (opcional, para cache)
- Git

### **Dependências**
```bash
pip install -r requirements.txt
```

## 🔧 **Configuração**

### **1. Variáveis de Ambiente**
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar configurações
nano .env
```

### **2. Configurações Essenciais**
```bash
# Aplicação
APP_NAME="Fiscal XML API"
DEBUG=false
LOG_LEVEL=INFO

# Servidor
HOST=0.0.0.0
PORT=8000

# Banco de Dados
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fiscal_api

# API Governamental
GOVERNMENT_API_BASE_URL=https://piloto-cbs.tributos.gov.br/servico/calculadora-consumo/api
GOVERNMENT_API_TIMEOUT=30

# Segurança
SECRET_KEY=your-super-secret-key-here
JWT_ALGORITHM=HS256

# Cache (opcional)
REDIS_URL=redis://localhost:6379/0
```

## 🐳 **Docker Deployment**

### **1. Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **2. Docker Compose**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/fiscal_api
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: fiscal_api
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## ☁️ **Cloud Deployment**

### **Heroku**
```bash
# Instalar Heroku CLI
# Criar app
heroku create fiscal-xml-api

# Configurar variáveis
heroku config:set DATABASE_URL=your-postgres-url
heroku config:set SECRET_KEY=your-secret-key

# Deploy
git push heroku main
```

### **AWS ECS**
```bash
# Build e push da imagem
docker build -t fiscal-xml-api .
docker tag fiscal-xml-api:latest your-ecr-repo/fiscal-xml-api:latest
docker push your-ecr-repo/fiscal-xml-api:latest

# Deploy via ECS Task Definition
```

### **Google Cloud Run**
```bash
# Build e deploy
gcloud run deploy fiscal-xml-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🔍 **Monitoramento**

### **Health Checks**
```bash
# Verificar saúde da aplicação
curl http://localhost:8000/api/v1/health

# Verificar métricas
curl http://localhost:8000/api/v1/metrics
```

### **Logs**
```bash
# Logs estruturados em JSON
tail -f logs/app.log | jq .

# Filtrar por nível
tail -f logs/app.log | jq 'select(.level == "ERROR")'
```

## 🛡️ **Segurança**

### **HTTPS**
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### **Rate Limiting**
```python
# Adicionar ao main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## 📊 **Performance**

### **Gunicorn**
```bash
# Produção com Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### **Nginx**
```nginx
upstream fiscal_api {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://fiscal_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔄 **CI/CD**

### **GitHub Actions**
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest
    
    - name: Deploy to production
      run: |
        # Seu script de deploy aqui
```

## 🚨 **Troubleshooting**

### **Problemas Comuns**

#### **1. Erro de Conexão com Banco**
```bash
# Verificar conectividade
pg_isready -h localhost -p 5432

# Testar conexão
psql -h localhost -U postgres -d fiscal_api
```

#### **2. Erro de Memória**
```bash
# Monitorar uso de memória
htop

# Ajustar workers do Gunicorn
gunicorn main:app -w 2 --max-requests 1000
```

#### **3. Timeout na API Governamental**
```bash
# Verificar conectividade
curl -I https://piloto-cbs.tributos.gov.br/servico/calculadora-consumo/api

# Ajustar timeout
export GOVERNMENT_API_TIMEOUT=60
```

## 📈 **Escalabilidade**

### **Horizontal Scaling**
- Load balancer (Nginx/HAProxy)
- Múltiplas instâncias da aplicação
- Cache distribuído (Redis Cluster)
- Banco de dados com read replicas

### **Vertical Scaling**
- Aumentar CPU/RAM do servidor
- Otimizar queries do banco
- Implementar cache em memória
- Usar connection pooling

## 🔐 **Backup**

### **Banco de Dados**
```bash
# Backup diário
pg_dump -h localhost -U postgres fiscal_api > backup_$(date +%Y%m%d).sql

# Restore
psql -h localhost -U postgres fiscal_api < backup_20250809.sql
```

### **Logs**
```bash
# Rotação de logs
logrotate /etc/logrotate.d/fiscal-api
```

---

**Preparado por**: Manus AI  
**Data**: 09 de Agosto de 2025  
**Versão**: 1.0

