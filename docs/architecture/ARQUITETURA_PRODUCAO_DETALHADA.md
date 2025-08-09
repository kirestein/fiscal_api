# 🏗️ Arquitetura de Produção Detalhada - MVP API Fiscal XML

## 📋 Visão Geral

A arquitetura de produção foi projetada para atender aos requisitos de **alta disponibilidade**, **escalabilidade horizontal**, **segurança robusta** e **performance otimizada** necessários para uma API fiscal crítica.

### **Princípios Arquiteturais:**
- **Microservices**: Componentes independentes e especializados
- **API-First**: Design centrado na experiência do desenvolvedor
- **Cloud-Native**: Aproveitamento máximo de recursos cloud
- **Security by Design**: Segurança em todas as camadas
- **Observability**: Visibilidade completa do sistema
- **Fault Tolerance**: Resistência a falhas e auto-recuperação

### **Características Técnicas:**
- **Latência**: <100ms p95 para processamento de documentos
- **Throughput**: >10,000 documentos/hora por instância
- **Disponibilidade**: 99.9% uptime (8.76h downtime/ano)
- **Escalabilidade**: Auto-scaling baseado em métricas
- **Segurança**: Zero-trust architecture com múltiplas camadas

## 🏛️ Arquitetura Geral

### **Diagrama de Alto Nível:**

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    EDGE LAYER                               │
├─────────────────────────────────────────────────────────────┤
│  CloudFlare CDN  │  WAF  │  DDoS Protection  │  SSL/TLS    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                 LOAD BALANCER LAYER                        │
├─────────────────────────────────────────────────────────────┤
│     Nginx/HAProxy     │    Health Checks    │   SSL Term   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  API GATEWAY LAYER                         │
├─────────────────────────────────────────────────────────────┤
│  Kong/Traefik  │  Rate Limiting  │  Auth  │  Routing  │ CORS│
└─────────────────────────────────────────────────────────────┘
    │
    ├─────────────┬─────────────┬─────────────┬─────────────┐
    ▼             ▼             ▼             ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│API Core │ │Auth Svc │ │Webhook  │ │Admin    │ │Metrics  │
│(FastAPI)│ │(FastAPI)│ │Service  │ │Portal   │ │Service  │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
    │             │             │             │             │
    └─────────────┼─────────────┼─────────────┼─────────────┘
                  │             │             │
    ┌─────────────▼─────────────▼─────────────▼─────────────┐
    │                MESSAGE QUEUE LAYER                   │
    ├─────────────────────────────────────────────────────────┤
    │     Redis Cluster     │    Celery Workers    │  Beat   │
    └─────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────▼─────────────────────────────┐
    │                   DATA LAYER                         │
    ├─────────────────────────────────────────────────────────┤
    │  PostgreSQL Cluster  │  Redis Cache  │  File Storage   │
    │  (Primary + Replica) │   (Sessions)  │   (S3/MinIO)    │
    └─────────────────────────────────────────────────────────┘
```

### **Fluxo de Dados Principal:**

```
1. Cliente → CloudFlare → Load Balancer → API Gateway
2. API Gateway → Autenticação → Rate Limiting → Roteamento
3. API Core → Validação → Cache Check → Processamento
4. Processamento → Queue (async) → Workers → Database
5. Response → Cache → API Gateway → Cliente
6. Webhook → Queue → Delivery → Cliente (opcional)
```


## 🔧 Componentes Principais

### **1. Edge Layer (CloudFlare)**

#### **Funcionalidades:**
- **CDN Global**: Cache de assets estáticos e responses
- **WAF (Web Application Firewall)**: Proteção contra ataques
- **DDoS Protection**: Mitigação automática de ataques
- **SSL/TLS Termination**: Certificados gerenciados automaticamente
- **Bot Management**: Detecção e bloqueio de bots maliciosos

#### **Configuração:**
```yaml
cloudflare:
  zones:
    - api.fiscal-xml.com
    - docs.fiscal-xml.com
    - status.fiscal-xml.com
  
  security:
    waf: enabled
    ddos_protection: enabled
    bot_fight_mode: enabled
    ssl_mode: "Full (strict)"
    min_tls_version: "1.2"
  
  caching:
    browser_ttl: 3600  # 1 hour
    edge_ttl: 86400    # 24 hours
    cache_level: "aggressive"
  
  page_rules:
    - pattern: "api.fiscal-xml.com/docs/*"
      cache_level: "cache_everything"
      edge_ttl: 86400
    - pattern: "api.fiscal-xml.com/api/*"
      cache_level: "bypass"
```

### **2. Load Balancer Layer (Nginx)**

#### **Funcionalidades:**
- **Load Balancing**: Distribuição inteligente de carga
- **Health Checks**: Monitoramento contínuo de backends
- **SSL Termination**: Offload de processamento SSL
- **Request Routing**: Roteamento baseado em path/headers
- **Rate Limiting**: Controle de tráfego por IP

#### **Configuração Nginx:**
```nginx
upstream api_backend {
    least_conn;
    server api-1.internal:8000 max_fails=3 fail_timeout=30s;
    server api-2.internal:8000 max_fails=3 fail_timeout=30s;
    server api-3.internal:8000 max_fails=3 fail_timeout=30s;
    
    # Health check
    health_check interval=10s fails=3 passes=2;
}

upstream auth_backend {
    server auth-1.internal:8001 max_fails=2 fail_timeout=30s;
    server auth-2.internal:8001 max_fails=2 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.fiscal-xml.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/api.fiscal-xml.com.crt;
    ssl_certificate_key /etc/ssl/private/api.fiscal-xml.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req zone=api burst=20 nodelay;
    
    # API Routes
    location /api/v1/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Auth Routes
    location /auth/ {
        proxy_pass http://auth_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health Check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### **3. API Gateway Layer (Kong)**

#### **Funcionalidades:**
- **Authentication**: JWT, API Key, OAuth2
- **Rate Limiting**: Por usuário, IP, endpoint
- **Request/Response Transformation**: Modificação de dados
- **Analytics**: Coleta de métricas de uso
- **Plugin Ecosystem**: Extensibilidade via plugins

#### **Configuração Kong:**
```yaml
# kong.yml
_format_version: "3.0"

services:
  - name: fiscal-api-core
    url: http://api-core:8000
    plugins:
      - name: jwt
        config:
          secret_is_base64: false
      - name: rate-limiting
        config:
          minute: 1000
          hour: 10000
          policy: redis
          redis_host: redis-cluster
      - name: prometheus
        config:
          per_consumer: true
      - name: cors
        config:
          origins:
            - "https://app.fiscal-xml.com"
            - "https://docs.fiscal-xml.com"
          methods:
            - GET
            - POST
            - PUT
            - DELETE
            - OPTIONS
          headers:
            - Accept
            - Authorization
            - Content-Type
            - X-API-Key
          credentials: true

  - name: auth-service
    url: http://auth-service:8001
    
  - name: webhook-service
    url: http://webhook-service:8002

routes:
  - name: api-routes
    service: fiscal-api-core
    paths:
      - /api/v1
    strip_path: false
    
  - name: auth-routes
    service: auth-service
    paths:
      - /auth
    strip_path: false
    
  - name: webhook-routes
    service: webhook-service
    paths:
      - /webhooks
    strip_path: false

consumers:
  - username: free-tier
    custom_id: free-tier
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000
          
  - username: premium-tier
    custom_id: premium-tier
    plugins:
      - name: rate-limiting
        config:
          minute: 1000
          hour: 100000
```

### **4. API Core Service (FastAPI)**

#### **Arquitetura Interna:**
```
api-core/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── xml.py          # XML processing endpoints
│   │   │   │   ├── documents.py    # Document management
│   │   │   │   ├── health.py       # Health checks
│   │   │   │   └── admin.py        # Admin endpoints
│   │   │   └── api.py              # API router
│   │   └── deps.py                 # Dependencies
│   ├── core/
│   │   ├── config.py               # Configuration
│   │   ├── security.py             # Security utilities
│   │   ├── logging.py              # Logging setup
│   │   └── database.py             # Database connection
│   ├── models/
│   │   ├── domain/                 # Domain models
│   │   ├── database/               # SQLAlchemy models
│   │   └── api/                    # Pydantic models
│   ├── services/
│   │   ├── xml_processor.py        # Core XML processing
│   │   ├── tax_calculator.py       # Tax calculations
│   │   ├── document_service.py     # Document operations
│   │   └── cache_service.py        # Cache operations
│   ├── workers/
│   │   ├── xml_worker.py           # Async XML processing
│   │   ├── webhook_worker.py       # Webhook delivery
│   │   └── cleanup_worker.py       # Maintenance tasks
│   └── utils/
│       ├── validators.py           # Input validation
│       ├── formatters.py           # Output formatting
│       └── exceptions.py           # Custom exceptions
├── tests/
├── migrations/
└── docker/
```

#### **Configuração FastAPI:**
```python
# app/main.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import time
import structlog

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="Fiscal XML API",
    description="API para processamento de documentos fiscais XML",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# Security Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request/Response Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host,
    )
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(
        "request_completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time,
    )
    
    return response

# Include routers
app.include_router(api_router, prefix="/api/v1")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("application_startup", version="1.0.0")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutdown")
```


## ☁️ Infraestrutura e Especificações Técnicas

### **Cloud Provider: AWS**

#### **Justificativa da Escolha:**
- **Maturidade**: Serviços estáveis e bem documentados
- **Compliance**: Certificações SOC, ISO, PCI necessárias
- **Presença no Brasil**: Data centers em São Paulo
- **Ecossistema**: Ampla gama de serviços integrados
- **Suporte**: Suporte enterprise 24/7 em português

### **Arquitetura de Rede**

#### **VPC (Virtual Private Cloud):**
```yaml
VPC Configuration:
  CIDR: 10.0.0.0/16
  
  Subnets:
    Public Subnets:
      - public-subnet-1a: 10.0.1.0/24 (us-east-1a)
      - public-subnet-1b: 10.0.2.0/24 (us-east-1b)
      - public-subnet-1c: 10.0.3.0/24 (us-east-1c)
    
    Private Subnets:
      - private-subnet-1a: 10.0.11.0/24 (us-east-1a)
      - private-subnet-1b: 10.0.12.0/24 (us-east-1b)
      - private-subnet-1c: 10.0.13.0/24 (us-east-1c)
    
    Database Subnets:
      - db-subnet-1a: 10.0.21.0/24 (us-east-1a)
      - db-subnet-1b: 10.0.22.0/24 (us-east-1b)
      - db-subnet-1c: 10.0.23.0/24 (us-east-1c)

  Internet Gateway: igw-fiscal-api
  NAT Gateways:
    - nat-1a (public-subnet-1a)
    - nat-1b (public-subnet-1b)
    - nat-1c (public-subnet-1c)
```

#### **Security Groups:**
```yaml
Security Groups:
  alb-sg:
    description: "Application Load Balancer Security Group"
    ingress:
      - port: 80
        protocol: tcp
        source: 0.0.0.0/0
      - port: 443
        protocol: tcp
        source: 0.0.0.0/0
    egress:
      - port: 8000
        protocol: tcp
        target: api-sg
  
  api-sg:
    description: "API Services Security Group"
    ingress:
      - port: 8000
        protocol: tcp
        source: alb-sg
      - port: 8001
        protocol: tcp
        source: alb-sg
      - port: 22
        protocol: tcp
        source: bastion-sg
    egress:
      - port: 5432
        protocol: tcp
        target: db-sg
      - port: 6379
        protocol: tcp
        target: redis-sg
      - port: 443
        protocol: tcp
        destination: 0.0.0.0/0
  
  db-sg:
    description: "Database Security Group"
    ingress:
      - port: 5432
        protocol: tcp
        source: api-sg
    egress: []
  
  redis-sg:
    description: "Redis Security Group"
    ingress:
      - port: 6379
        protocol: tcp
        source: api-sg
    egress: []
```

### **Compute Resources**

#### **Application Load Balancer (ALB):**
```yaml
ALB Configuration:
  Type: Application Load Balancer
  Scheme: internet-facing
  Subnets:
    - public-subnet-1a
    - public-subnet-1b
    - public-subnet-1c
  
  Listeners:
    HTTP (Port 80):
      action: redirect to HTTPS
    HTTPS (Port 443):
      ssl_policy: ELBSecurityPolicy-TLS-1-2-2017-01
      certificate: arn:aws:acm:us-east-1:account:certificate/cert-id
      
  Target Groups:
    api-core-tg:
      protocol: HTTP
      port: 8000
      health_check:
        path: /health
        interval: 30s
        timeout: 5s
        healthy_threshold: 2
        unhealthy_threshold: 3
    
    auth-service-tg:
      protocol: HTTP
      port: 8001
      health_check:
        path: /health
        interval: 30s
        timeout: 5s
        healthy_threshold: 2
        unhealthy_threshold: 3
```

#### **Auto Scaling Groups:**
```yaml
API Core ASG:
  launch_template: api-core-lt
  min_size: 2
  max_size: 10
  desired_capacity: 3
  target_group_arns:
    - api-core-tg
  subnets:
    - private-subnet-1a
    - private-subnet-1b
    - private-subnet-1c
  
  scaling_policies:
    scale_up:
      metric: CPUUtilization
      threshold: 70
      adjustment: +2 instances
      cooldown: 300s
    
    scale_down:
      metric: CPUUtilization
      threshold: 30
      adjustment: -1 instance
      cooldown: 300s

Auth Service ASG:
  launch_template: auth-service-lt
  min_size: 2
  max_size: 6
  desired_capacity: 2
  target_group_arns:
    - auth-service-tg
  subnets:
    - private-subnet-1a
    - private-subnet-1b
```

#### **Launch Templates:**
```yaml
API Core Launch Template:
  image_id: ami-0abcdef1234567890  # Custom AMI with app
  instance_type: c5.large
  key_name: fiscal-api-key
  security_groups:
    - api-sg
  
  user_data: |
    #!/bin/bash
    cd /opt/fiscal-api
    docker-compose up -d
    
  iam_instance_profile: fiscal-api-instance-profile
  
  monitoring:
    enabled: true
  
  block_device_mappings:
    - device_name: /dev/xvda
      ebs:
        volume_type: gp3
        volume_size: 20
        encrypted: true
        delete_on_termination: true

Auth Service Launch Template:
  image_id: ami-0abcdef1234567890
  instance_type: t3.medium
  key_name: fiscal-api-key
  security_groups:
    - api-sg
  
  user_data: |
    #!/bin/bash
    cd /opt/auth-service
    docker-compose up -d
```

### **Database Layer**

#### **PostgreSQL (RDS):**
```yaml
RDS Configuration:
  engine: postgres
  engine_version: "15.4"
  instance_class: db.r5.xlarge
  allocated_storage: 100
  storage_type: gp3
  storage_encrypted: true
  
  multi_az: true
  backup_retention_period: 7
  backup_window: "03:00-04:00"
  maintenance_window: "sun:04:00-sun:05:00"
  
  db_subnet_group: fiscal-api-db-subnet-group
  vpc_security_groups:
    - db-sg
  
  parameter_group: fiscal-api-postgres-params
  
  monitoring:
    monitoring_interval: 60
    monitoring_role_arn: arn:aws:iam::account:role/rds-monitoring-role
  
  performance_insights:
    enabled: true
    retention_period: 7

Read Replica:
  source_db: fiscal-api-primary
  instance_class: db.r5.large
  multi_az: false
  publicly_accessible: false
```

#### **Redis (ElastiCache):**
```yaml
ElastiCache Configuration:
  engine: redis
  engine_version: "7.0"
  node_type: cache.r6g.large
  num_cache_nodes: 3
  
  replication_group:
    description: "Fiscal API Redis Cluster"
    num_node_groups: 3
    replicas_per_node_group: 1
    
  subnet_group: fiscal-api-redis-subnet-group
  security_groups:
    - redis-sg
  
  parameter_group: fiscal-api-redis-params
  
  backup:
    snapshot_retention_limit: 5
    snapshot_window: "03:00-05:00"
  
  maintenance_window: "sun:05:00-sun:06:00"
  
  encryption:
    at_rest: true
    in_transit: true
```

### **Storage**

#### **S3 Buckets:**
```yaml
S3 Buckets:
  fiscal-api-documents:
    purpose: "Store processed XML documents"
    versioning: enabled
    encryption: AES256
    lifecycle_policy:
      - transition_to_ia: 30 days
      - transition_to_glacier: 90 days
      - expiration: 2555 days  # 7 years (legal requirement)
    
    cors_configuration:
      allowed_origins:
        - "https://api.fiscal-xml.com"
      allowed_methods:
        - GET
        - PUT
        - POST
      allowed_headers:
        - "*"
  
  fiscal-api-backups:
    purpose: "Database and application backups"
    versioning: enabled
    encryption: AES256
    lifecycle_policy:
      - transition_to_glacier: 30 days
      - expiration: 2555 days
  
  fiscal-api-logs:
    purpose: "Application and access logs"
    versioning: disabled
    encryption: AES256
    lifecycle_policy:
      - transition_to_ia: 30 days
      - transition_to_glacier: 90 days
      - expiration: 365 days
```

### **Container Orchestration**

#### **ECS (Elastic Container Service):**
```yaml
ECS Cluster:
  name: fiscal-api-cluster
  capacity_providers:
    - EC2
    - FARGATE
  
  services:
    api-core:
      task_definition: fiscal-api-core:latest
      desired_count: 3
      launch_type: EC2
      network_configuration:
        subnets:
          - private-subnet-1a
          - private-subnet-1b
          - private-subnet-1c
        security_groups:
          - api-sg
      
      load_balancers:
        - target_group_arn: api-core-tg
          container_name: api-core
          container_port: 8000
      
      auto_scaling:
        min_capacity: 2
        max_capacity: 10
        target_cpu: 70
        target_memory: 80
    
    auth-service:
      task_definition: fiscal-auth-service:latest
      desired_count: 2
      launch_type: FARGATE
      network_configuration:
        subnets:
          - private-subnet-1a
          - private-subnet-1b
        security_groups:
          - api-sg
      
      load_balancers:
        - target_group_arn: auth-service-tg
          container_name: auth-service
          container_port: 8001
    
    webhook-service:
      task_definition: fiscal-webhook-service:latest
      desired_count: 2
      launch_type: FARGATE
      network_configuration:
        subnets:
          - private-subnet-1a
          - private-subnet-1b
        security_groups:
          - api-sg
    
    celery-workers:
      task_definition: fiscal-celery-worker:latest
      desired_count: 4
      launch_type: EC2
      network_configuration:
        subnets:
          - private-subnet-1a
          - private-subnet-1b
          - private-subnet-1c
        security_groups:
          - api-sg
      
      auto_scaling:
        min_capacity: 2
        max_capacity: 20
        target_metric: queue_length
        target_value: 100
```

#### **Task Definitions:**
```yaml
API Core Task Definition:
  family: fiscal-api-core
  network_mode: awsvpc
  requires_compatibilities:
    - EC2
  cpu: 1024
  memory: 2048
  
  execution_role_arn: arn:aws:iam::account:role/ecsTaskExecutionRole
  task_role_arn: arn:aws:iam::account:role/fiscal-api-task-role
  
  container_definitions:
    - name: api-core
      image: fiscal-api/core:latest
      port_mappings:
        - container_port: 8000
          protocol: tcp
      
      environment:
        - name: ENVIRONMENT
          value: production
        - name: DATABASE_URL
          value: postgresql://user:pass@rds-endpoint:5432/fiscal_api
        - name: REDIS_URL
          value: redis://elasticache-endpoint:6379/0
      
      secrets:
        - name: JWT_SECRET
          value_from: arn:aws:secretsmanager:us-east-1:account:secret:jwt-secret
        - name: DATABASE_PASSWORD
          value_from: arn:aws:secretsmanager:us-east-1:account:secret:db-password
      
      log_configuration:
        log_driver: awslogs
        options:
          awslogs-group: /ecs/fiscal-api-core
          awslogs-region: us-east-1
          awslogs-stream-prefix: ecs
      
      health_check:
        command:
          - CMD-SHELL
          - "curl -f http://localhost:8000/health || exit 1"
        interval: 30
        timeout: 5
        retries: 3
        start_period: 60
```


## 🔒 Segurança e Compliance

### **Modelo de Segurança Zero-Trust**

#### **Princípios Fundamentais:**
- **Never Trust, Always Verify**: Verificação contínua de identidade
- **Least Privilege Access**: Acesso mínimo necessário
- **Assume Breach**: Preparação para comprometimento
- **Verify Explicitly**: Autenticação e autorização explícitas

### **Camadas de Segurança**

#### **1. Network Security**
```yaml
Network Security Controls:
  WAF (Web Application Firewall):
    provider: AWS WAF v2
    rules:
      - SQL Injection Protection
      - XSS Protection
      - Rate Limiting (1000 req/5min per IP)
      - Geo-blocking (allow only Brazil + US)
      - Known Bad IPs blocking
      - OWASP Top 10 protection
  
  VPC Security:
    private_subnets: true
    nat_gateways: true
    flow_logs: enabled
    network_acls: restrictive
  
  DDoS Protection:
    aws_shield: standard
    cloudflare: enabled
    rate_limiting: multi-layer
```

#### **2. Application Security**
```yaml
Application Security:
  Authentication:
    method: JWT + API Keys
    token_expiry: 1 hour
    refresh_token_expiry: 30 days
    multi_factor: optional (premium)
    
  Authorization:
    model: RBAC (Role-Based Access Control)
    roles:
      - free_user: [xml:validate, xml:summary]
      - paid_user: [xml:*, webhook:read]
      - admin: [*]
    
  Input Validation:
    xml_size_limit: 10MB
    request_timeout: 30s
    content_type_validation: strict
    schema_validation: enabled
    
  Output Security:
    data_sanitization: enabled
    pii_masking: enabled
    error_message_sanitization: enabled
```

#### **3. Data Security**
```yaml
Data Security:
  Encryption:
    at_rest:
      database: AES-256
      s3_buckets: AES-256
      ebs_volumes: AES-256
    in_transit:
      tls_version: 1.3
      cipher_suites: ECDHE-RSA-AES256-GCM-SHA384
      certificate_authority: Let's Encrypt
    
  Data Classification:
    public: API documentation, status pages
    internal: Application logs, metrics
    confidential: Customer data, XML documents
    restricted: Authentication tokens, secrets
    
  Data Retention:
    xml_documents: 7 years (legal requirement)
    access_logs: 1 year
    application_logs: 90 days
    metrics: 1 year
    
  Backup Security:
    encryption: AES-256
    access_control: IAM roles only
    retention: 7 years
    testing: monthly restore tests
```

#### **4. Identity and Access Management (IAM)**
```yaml
IAM Configuration:
  Service Accounts:
    api-core-service:
      policies:
        - s3:GetObject (documents bucket)
        - s3:PutObject (documents bucket)
        - rds:Connect (fiscal_api database)
        - elasticache:Connect (redis cluster)
        - secretsmanager:GetSecretValue
    
    auth-service:
      policies:
        - rds:Connect (auth database)
        - secretsmanager:GetSecretValue
        - ses:SendEmail
    
    webhook-service:
      policies:
        - sqs:ReceiveMessage
        - sqs:DeleteMessage
        - s3:GetObject (documents bucket)
  
  Human Users:
    developers:
      policies:
        - ReadOnlyAccess to production
        - FullAccess to development/staging
        - CloudWatch logs access
    
    operations:
      policies:
        - EC2 management
        - RDS management
        - CloudWatch full access
        - Systems Manager access
    
    security:
      policies:
        - SecurityAudit
        - IAM management
        - Config management
        - GuardDuty access
```

### **Compliance e Auditoria**

#### **Frameworks de Compliance:**
- **LGPD (Lei Geral de Proteção de Dados)**: Proteção de dados pessoais
- **SOC 2 Type II**: Controles de segurança e disponibilidade
- **ISO 27001**: Sistema de gestão de segurança da informação
- **PCI DSS**: Segurança de dados de cartão (se aplicável)

#### **Controles de Auditoria:**
```yaml
Audit Controls:
  CloudTrail:
    enabled: true
    s3_bucket: fiscal-api-audit-logs
    log_file_validation: true
    include_global_services: true
    multi_region: true
    
  Config:
    enabled: true
    rules:
      - s3-bucket-public-access-prohibited
      - rds-storage-encrypted
      - ec2-security-group-attached-to-eni
      - iam-password-policy
      - cloudtrail-enabled
    
  GuardDuty:
    enabled: true
    finding_publishing_frequency: FIFTEEN_MINUTES
    malware_protection: enabled
    
  Security Hub:
    enabled: true
    standards:
      - AWS Foundational Security Standard
      - CIS AWS Foundations Benchmark
      - PCI DSS
```

## 📊 Monitoramento e Observabilidade

### **Stack de Monitoramento**

#### **Métricas (Prometheus + Grafana)**
```yaml
Prometheus Configuration:
  global:
    scrape_interval: 15s
    evaluation_interval: 15s
  
  scrape_configs:
    - job_name: 'api-core'
      static_configs:
        - targets: ['api-core:8000']
      metrics_path: /metrics
      scrape_interval: 10s
    
    - job_name: 'auth-service'
      static_configs:
        - targets: ['auth-service:8001']
      metrics_path: /metrics
      scrape_interval: 15s
    
    - job_name: 'webhook-service'
      static_configs:
        - targets: ['webhook-service:8002']
      metrics_path: /metrics
      scrape_interval: 15s
    
    - job_name: 'redis'
      static_configs:
        - targets: ['redis-exporter:9121']
    
    - job_name: 'postgres'
      static_configs:
        - targets: ['postgres-exporter:9187']
    
    - job_name: 'node'
      static_configs:
        - targets: ['node-exporter:9100']

Grafana Dashboards:
  business_metrics:
    panels:
      - API requests per minute
      - Documents processed per hour
      - Revenue per day
      - Active users
      - Error rate by endpoint
      - Response time percentiles
  
  technical_metrics:
    panels:
      - CPU utilization
      - Memory usage
      - Database connections
      - Queue length
      - Cache hit ratio
      - Disk I/O
  
  infrastructure_metrics:
    panels:
      - EC2 instance health
      - RDS performance
      - ElastiCache performance
      - Load balancer metrics
      - Auto-scaling events
```

#### **Logging (ELK Stack)**
```yaml
Elasticsearch Configuration:
  cluster:
    name: fiscal-api-logs
    nodes: 3
    node_type: data
    instance_type: r5.large
  
  indices:
    application_logs:
      shards: 3
      replicas: 1
      retention: 90 days
    
    access_logs:
      shards: 5
      replicas: 1
      retention: 365 days
    
    audit_logs:
      shards: 2
      replicas: 2
      retention: 7 years

Logstash Configuration:
  input:
    beats:
      port: 5044
    
  filter:
    if [fields][log_type] == "application" {
      json {
        source => "message"
      }
      date {
        match => [ "timestamp", "ISO8601" ]
      }
    }
    
    if [fields][log_type] == "access" {
      grok {
        match => { "message" => "%{COMBINEDAPACHELOG}" }
      }
    }
  
  output:
    elasticsearch:
      hosts => ["elasticsearch:9200"]
      index => "%{[fields][log_type]}-logs-%{+YYYY.MM.dd}"

Kibana Configuration:
  dashboards:
    application_overview:
      visualizations:
        - Request volume over time
        - Error rate by service
        - Response time distribution
        - Top error messages
    
    security_monitoring:
      visualizations:
        - Failed authentication attempts
        - Suspicious IP addresses
        - Rate limiting triggers
        - Security events timeline
```

#### **Distributed Tracing (Jaeger)**
```yaml
Jaeger Configuration:
  collector:
    replicas: 2
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi
  
  query:
    replicas: 2
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi
  
  storage:
    type: elasticsearch
    elasticsearch:
      server_urls: http://elasticsearch:9200
      index_prefix: jaeger
      
Application Instrumentation:
  python_services:
    library: opentelemetry-python
    exporters:
      - jaeger
      - prometheus
    
    traced_operations:
      - HTTP requests
      - Database queries
      - Redis operations
      - External API calls
      - XML processing
```

### **Alerting e SLA**

#### **Alerting Rules:**
```yaml
Prometheus Alerting Rules:
  groups:
    - name: api_health
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "High error rate detected"
            description: "Error rate is {{ $value }} for the last 5 minutes"
        
        - alert: HighLatency
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High latency detected"
            description: "95th percentile latency is {{ $value }}s"
        
        - alert: DatabaseConnectionHigh
          expr: pg_stat_activity_count > 80
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "High database connection count"
            description: "Database has {{ $value }} active connections"
    
    - name: infrastructure
      rules:
        - alert: HighCPUUsage
          expr: cpu_usage_percent > 80
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High CPU usage"
            description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"
        
        - alert: HighMemoryUsage
          expr: memory_usage_percent > 85
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "High memory usage"
            description: "Memory usage is {{ $value }}% on {{ $labels.instance }}"
        
        - alert: DiskSpaceLow
          expr: disk_free_percent < 20
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "Low disk space"
            description: "Disk space is {{ $value }}% full on {{ $labels.instance }}"

Notification Channels:
  slack:
    webhook_url: https://hooks.slack.com/services/xxx
    channel: "#alerts"
    title_template: "{{ .GroupLabels.alertname }}"
    text_template: "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
  
  pagerduty:
    service_key: xxx
    severity_mapping:
      critical: critical
      warning: warning
      info: info
  
  email:
    smtp_server: smtp.gmail.com:587
    from: alerts@fiscal-xml.com
    to:
      - ops-team@fiscal-xml.com
      - on-call@fiscal-xml.com
```

#### **SLA Definitions:**
```yaml
Service Level Agreements:
  availability:
    target: 99.9%
    measurement_window: monthly
    exclusions:
      - planned_maintenance
      - force_majeure
    
  performance:
    api_response_time:
      p95: < 100ms
      p99: < 500ms
    
    document_processing_time:
      p95: < 2s
      p99: < 5s
    
  error_rate:
    target: < 0.1%
    measurement_window: monthly
    
  support_response:
    critical: 1 hour
    high: 4 hours
    medium: 24 hours
    low: 72 hours
```


## 🚀 Deploy e Operações

### **Estratégia de Deployment**

#### **Blue-Green Deployment**
```yaml
Blue-Green Strategy:
  environments:
    blue:
      status: production
      traffic: 100%
      instances: 3
      
    green:
      status: staging
      traffic: 0%
      instances: 3
  
  deployment_process:
    1. Deploy to green environment
    2. Run automated tests
    3. Perform smoke tests
    4. Switch 10% traffic to green
    5. Monitor for 15 minutes
    6. Switch 50% traffic to green
    7. Monitor for 15 minutes
    8. Switch 100% traffic to green
    9. Keep blue as rollback option for 24h
    10. Terminate blue environment
  
  rollback_strategy:
    trigger_conditions:
      - error_rate > 1%
      - latency_p95 > 200ms
      - health_check_failures > 5%
    
    rollback_time: < 2 minutes
    automatic_rollback: enabled
```

#### **CI/CD Pipeline**
```yaml
GitHub Actions Workflow:
  name: Deploy to Production
  
  on:
    push:
      branches: [main]
      tags: ['v*']
  
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - name: Setup Python
          uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        
        - name: Install dependencies
          run: |
            pip install -r requirements.txt
            pip install -r requirements-dev.txt
        
        - name: Run tests
          run: |
            pytest tests/ --cov=app --cov-report=xml
            
        - name: Security scan
          run: |
            bandit -r app/
            safety check
        
        - name: Code quality
          run: |
            flake8 app/
            mypy app/
    
    build:
      needs: test
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        
        - name: Configure AWS credentials
          uses: aws-actions/configure-aws-credentials@v2
          with:
            aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
            aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
            aws-region: us-east-1
        
        - name: Login to Amazon ECR
          uses: aws-actions/amazon-ecr-login@v1
        
        - name: Build and push Docker image
          run: |
            docker build -t fiscal-api/core:${{ github.sha }} .
            docker tag fiscal-api/core:${{ github.sha }} \
              $ECR_REGISTRY/fiscal-api/core:${{ github.sha }}
            docker tag fiscal-api/core:${{ github.sha }} \
              $ECR_REGISTRY/fiscal-api/core:latest
            docker push $ECR_REGISTRY/fiscal-api/core:${{ github.sha }}
            docker push $ECR_REGISTRY/fiscal-api/core:latest
    
    deploy:
      needs: build
      runs-on: ubuntu-latest
      environment: production
      steps:
        - name: Deploy to ECS
          run: |
            aws ecs update-service \
              --cluster fiscal-api-cluster \
              --service api-core \
              --task-definition fiscal-api-core:${{ github.run_number }} \
              --force-new-deployment
        
        - name: Wait for deployment
          run: |
            aws ecs wait services-stable \
              --cluster fiscal-api-cluster \
              --services api-core
        
        - name: Run smoke tests
          run: |
            curl -f https://api.fiscal-xml.com/health
            python scripts/smoke_tests.py
        
        - name: Notify deployment
          uses: 8398a7/action-slack@v3
          with:
            status: ${{ job.status }}
            channel: '#deployments'
            webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### **Disaster Recovery**

#### **Backup Strategy**
```yaml
Backup Configuration:
  database:
    automated_backups:
      retention_period: 7 days
      backup_window: "03:00-04:00 UTC"
      copy_tags_to_snapshot: true
    
    manual_snapshots:
      frequency: weekly
      retention: 30 days
      cross_region_copy: true
      destination_region: us-west-2
    
    point_in_time_recovery:
      enabled: true
      retention_period: 7 days
  
  application_data:
    s3_cross_region_replication:
      source_bucket: fiscal-api-documents
      destination_bucket: fiscal-api-documents-backup
      destination_region: us-west-2
      storage_class: STANDARD_IA
    
    versioning: enabled
    lifecycle_policy:
      - transition_to_ia: 30 days
      - transition_to_glacier: 90 days
  
  configuration:
    infrastructure_as_code:
      repository: github.com/fiscal-api/infrastructure
      backup_frequency: daily
      retention: 90 days
    
    secrets_backup:
      aws_secrets_manager: enabled
      cross_region_replication: true
      retention: 30 days

Recovery Procedures:
  rto: 4 hours  # Recovery Time Objective
  rpo: 1 hour   # Recovery Point Objective
  
  scenarios:
    single_az_failure:
      impact: minimal
      recovery_time: automatic (< 5 minutes)
      procedure: auto-scaling + multi-az deployment
    
    region_failure:
      impact: moderate
      recovery_time: 2-4 hours
      procedure: manual failover to backup region
    
    complete_data_loss:
      impact: high
      recovery_time: 4-8 hours
      procedure: restore from backups + rebuild
```

#### **Multi-Region Setup**
```yaml
Primary Region (us-east-1):
  services:
    - API Gateway
    - Application Load Balancer
    - ECS Cluster
    - RDS Primary
    - ElastiCache Primary
    - S3 Primary
  
  traffic: 100%
  status: active

Secondary Region (us-west-2):
  services:
    - API Gateway (standby)
    - Application Load Balancer (standby)
    - ECS Cluster (minimal)
    - RDS Read Replica
    - ElastiCache (standby)
    - S3 Replica
  
  traffic: 0%
  status: standby
  
  failover_triggers:
    - primary_region_health_check_failure
    - rds_primary_failure
    - application_error_rate > 10%
  
  failover_time: < 15 minutes
  failback_strategy: manual (after issue resolution)
```

### **Operações Diárias**

#### **Runbooks Operacionais**

##### **Incident Response**
```yaml
Incident Response Playbook:
  severity_levels:
    P0 (Critical):
      description: "Complete service outage"
      response_time: 15 minutes
      escalation: immediate
      communication: status page + slack + email
      
    P1 (High):
      description: "Significant service degradation"
      response_time: 1 hour
      escalation: 2 hours
      communication: slack + email
      
    P2 (Medium):
      description: "Minor service issues"
      response_time: 4 hours
      escalation: 24 hours
      communication: slack
      
    P3 (Low):
      description: "Non-urgent issues"
      response_time: 24 hours
      escalation: 72 hours
      communication: ticket system
  
  response_procedures:
    1. Acknowledge incident
    2. Assess severity and impact
    3. Form incident response team
    4. Implement immediate mitigation
    5. Communicate with stakeholders
    6. Investigate root cause
    7. Implement permanent fix
    8. Conduct post-incident review
    9. Update documentation
    10. Implement preventive measures
```

##### **Maintenance Procedures**
```yaml
Maintenance Windows:
  scheduled_maintenance:
    frequency: monthly
    duration: 2 hours
    window: "Sunday 02:00-04:00 UTC"
    notification: 7 days advance
    
  emergency_maintenance:
    approval: CTO + Operations Lead
    notification: 2 hours advance (minimum)
    duration: 4 hours maximum
    
  maintenance_checklist:
    pre_maintenance:
      - [ ] Backup all critical data
      - [ ] Verify rollback procedures
      - [ ] Notify stakeholders
      - [ ] Prepare monitoring
      - [ ] Test in staging environment
    
    during_maintenance:
      - [ ] Execute changes step by step
      - [ ] Monitor system health
      - [ ] Document any issues
      - [ ] Verify functionality
      - [ ] Update status page
    
    post_maintenance:
      - [ ] Verify all services operational
      - [ ] Monitor for 2 hours
      - [ ] Update documentation
      - [ ] Notify completion
      - [ ] Schedule follow-up review
```

##### **Performance Optimization**
```yaml
Performance Monitoring:
  daily_checks:
    - API response times
    - Database query performance
    - Cache hit ratios
    - Error rates
    - Resource utilization
  
  weekly_reviews:
    - Capacity planning
    - Cost optimization
    - Security updates
    - Performance trends
    - Customer feedback
  
  monthly_optimizations:
    - Database maintenance
    - Index optimization
    - Cache tuning
    - Auto-scaling adjustments
    - Cost analysis

Optimization Procedures:
  database_optimization:
    frequency: weekly
    tasks:
      - VACUUM and ANALYZE
      - Index usage analysis
      - Query performance review
      - Connection pool tuning
      - Slow query identification
  
  cache_optimization:
    frequency: daily
    tasks:
      - Hit ratio monitoring
      - Memory usage analysis
      - Eviction rate review
      - TTL optimization
      - Key pattern analysis
  
  application_optimization:
    frequency: monthly
    tasks:
      - Code profiling
      - Memory leak detection
      - CPU usage analysis
      - I/O optimization
      - Dependency updates
```

### **Custos Operacionais**

#### **Estimativa de Custos Mensais (Produção)**
```yaml
AWS Costs (Monthly):
  compute:
    ec2_instances: $800
    ecs_fargate: $400
    load_balancer: $25
    
  storage:
    rds_storage: $150
    s3_storage: $100
    ebs_volumes: $200
    
  database:
    rds_instances: $600
    elasticache: $300
    
  networking:
    data_transfer: $200
    cloudfront: $50
    
  monitoring:
    cloudwatch: $100
    
  security:
    waf: $50
    secrets_manager: $20
    
  backup:
    snapshots: $100
    cross_region: $50
  
  total_aws: $3,145

Third-party Services:
  cloudflare: $200
  datadog: $300
  pagerduty: $100
  github_actions: $50
  
  total_third_party: $650

Total Monthly Cost: $3,795

Cost Optimization Strategies:
  reserved_instances: -20% ($630 savings)
  spot_instances: -30% ($240 savings)
  s3_lifecycle: -15% ($15 savings)
  
  optimized_monthly_cost: $2,910
```

#### **Scaling Cost Projections**
```yaml
Cost Scaling (by user volume):
  1,000 users:
    monthly_cost: $2,910
    cost_per_user: $2.91
    
  10,000 users:
    monthly_cost: $8,500
    cost_per_user: $0.85
    
  100,000 users:
    monthly_cost: $25,000
    cost_per_user: $0.25
    
  1,000,000 users:
    monthly_cost: $75,000
    cost_per_user: $0.075

Cost Optimization Targets:
  year_1: 15% reduction through optimization
  year_2: 25% reduction through reserved instances
  year_3: 35% reduction through custom solutions
```

## 📋 Resumo da Arquitetura

### **Características Principais:**
- **Alta Disponibilidade**: 99.9% uptime com multi-AZ deployment
- **Escalabilidade**: Auto-scaling baseado em métricas
- **Segurança**: Zero-trust architecture com múltiplas camadas
- **Performance**: <100ms latência p95, >10k docs/hora
- **Observabilidade**: Monitoramento completo com alertas
- **Disaster Recovery**: RTO 4h, RPO 1h

### **Tecnologias Core:**
- **Cloud**: AWS (multi-region)
- **Containers**: ECS + Fargate
- **Database**: PostgreSQL + Redis
- **Monitoring**: Prometheus + Grafana + ELK
- **Security**: WAF + IAM + Encryption
- **CI/CD**: GitHub Actions + Blue-Green

### **Custos Operacionais:**
- **Inicial**: $3,795/mês
- **Otimizado**: $2,910/mês
- **Escalabilidade**: Linear com volume

**Esta arquitetura garante uma base sólida, segura e escalável para o MVP da API Fiscal XML, preparada para crescimento e operação em produção.**

