#!/usr/bin/env python3
"""
Script de teste para a API de processamento XML fiscal.
"""

import asyncio
import json
from pathlib import Path

import httpx


async def test_health_endpoint():
    """Testa endpoint de health check."""
    print("🔍 Testando endpoint de health...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/v1/health")
            print(f"✅ Status: {response.status_code}")
            print(f"📄 Resposta: {json.dumps(response.json(), indent=2)}")
            return True
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False


async def test_xml_validation():
    """Testa validação de XML."""
    print("\n🔍 Testando validação de XML...")
    
    xml_file = Path("test_xml_sample.xml")
    if not xml_file.exists():
        print("❌ Arquivo XML de teste não encontrado")
        return False
    
    async with httpx.AsyncClient() as client:
        try:
            with open(xml_file, "rb") as f:
                files = {"xml_file": ("test.xml", f, "application/xml")}
                response = await client.post(
                    "http://localhost:8000/api/v1/documents/validate",
                    files=files
                )
            
            print(f"✅ Status: {response.status_code}")
            print(f"📄 Resposta: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False


async def test_document_processing():
    """Testa processamento de documento."""
    print("\n🔍 Testando processamento de documento...")
    
    xml_file = Path("test_xml_sample.xml")
    if not xml_file.exists():
        print("❌ Arquivo XML de teste não encontrado")
        return False
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            with open(xml_file, "rb") as f:
                files = {"xml_file": ("test.xml", f, "application/xml")}
                response = await client.post(
                    "http://localhost:8000/api/v1/documents/process",
                    files=files
                )
            
            print(f"✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📄 Documento processado:")
                print(f"   - Chave: {data.get('document_key', 'N/A')}")
                print(f"   - Série: {data.get('series', 'N/A')}")
                print(f"   - Número: {data.get('number', 'N/A')}")
                print(f"   - Total: R$ {data.get('total_document', 'N/A')}")
                print(f"   - Itens: {len(data.get('items', []))}")
            else:
                print(f"📄 Erro: {response.text}")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False


async def test_batch_processing():
    """Testa processamento em lote."""
    print("\n🔍 Testando processamento em lote...")
    
    xml_file = Path("test_xml_sample.xml")
    if not xml_file.exists():
        print("❌ Arquivo XML de teste não encontrado")
        return False
    
    # Ler XML de teste
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_content = f.read()
    
    # Criar requisição de lote
    batch_request = {
        "documents": [xml_content, xml_content],  # 2 documentos iguais para teste
        "batch_size": 10,
        "timeout_minutes": 30,
        "force_update": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/documents/batch",
                json=batch_request
            )
            
            print(f"✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📄 Job criado:")
                print(f"   - Job ID: {data.get('job_id', 'N/A')}")
                print(f"   - Total documentos: {data.get('total_documents', 'N/A')}")
                print(f"   - Duração estimada: {data.get('estimated_duration_minutes', 'N/A')} min")
                print(f"   - Status URL: {data.get('status_url', 'N/A')}")
                return data.get('job_id')
            else:
                print(f"📄 Erro: {response.text}")
                return None
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None


async def test_job_status(job_id: str):
    """Testa consulta de status de job."""
    print(f"\n🔍 Testando status do job {job_id}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://localhost:8000/api/v1/jobs/{job_id}/status"
            )
            
            print(f"✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📄 Status do job:")
                print(f"   - Status: {data.get('status', 'N/A')}")
                print(f"   - Progresso: {data.get('processed_documents', 0)}/{data.get('total_documents', 0)}")
                print(f"   - Sucessos: {data.get('successful_documents', 0)}")
                print(f"   - Falhas: {data.get('failed_documents', 0)}")
            else:
                print(f"📄 Erro: {response.text}")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False


async def test_jobs_list():
    """Testa listagem de jobs."""
    print("\n🔍 Testando listagem de jobs...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/v1/jobs/")
            
            print(f"✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📄 Jobs encontrados: {len(data)}")
                for i, job in enumerate(data[:3]):  # Mostrar apenas os 3 primeiros
                    print(f"   {i+1}. Status: {job.get('status', 'N/A')} | "
                          f"Documentos: {job.get('total_documents', 0)} | "
                          f"Criado: {job.get('created_at', 'N/A')[:19]}")
            else:
                print(f"📄 Erro: {response.text}")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False


async def main():
    """Executa todos os testes."""
    print("🚀 Iniciando testes da API de processamento XML fiscal\n")
    
    results = []
    
    # Teste 1: Health check
    results.append(await test_health_endpoint())
    
    # Teste 2: Validação de XML
    results.append(await test_xml_validation())
    
    # Teste 3: Processamento de documento
    results.append(await test_document_processing())
    
    # Teste 4: Processamento em lote
    job_id = await test_batch_processing()
    results.append(job_id is not None)
    
    # Teste 5: Status de job (se job foi criado)
    if job_id:
        results.append(await test_job_status(job_id))
    else:
        results.append(False)
    
    # Teste 6: Listagem de jobs
    results.append(await test_jobs_list())
    
    # Resumo dos resultados
    print(f"\n📊 RESUMO DOS TESTES:")
    print(f"✅ Sucessos: {sum(results)}")
    print(f"❌ Falhas: {len(results) - sum(results)}")
    print(f"📈 Taxa de sucesso: {sum(results)/len(results)*100:.1f}%")
    
    if all(results):
        print("\n🎉 Todos os testes passaram! API funcionando corretamente.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs acima.")


if __name__ == "__main__":
    asyncio.run(main())

