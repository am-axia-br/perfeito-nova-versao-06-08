#!/usr/bin/env python3
"""
Script para testar a conectividade com o ChromaDB
Execute com: docker-compose exec processo-ocr python test_chroma.py
"""

import os
import sys
import time
import requests
import chromadb
from chromadb.utils import embedding_functions

def test_raw_connection():
    """Testa a conexão HTTP básica com o ChromaDB"""
    host = os.getenv("CHROMA_HOST", "chroma")
    port = os.getenv("CHROMA_PORT", "8000")
    url = f"http://{host}:{port}/api/v1/heartbeat"
    
    print(f"🔍 Testando conexão HTTP com {url}")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"✅ Conexão HTTP bem-sucedida! Resposta: {response.text}")
            return True
        else:
            print(f"❌ Conexão HTTP falhou com código {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exceção na conexão HTTP: {e}")
        return False

def test_chroma_client():
    """Testa o cliente ChromaDB"""
    host = os.getenv("CHROMA_HOST", "chroma")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    
    print(f"🔍 Testando cliente ChromaDB em {host}:{port}")
    try:
        client = chromadb.HttpClient(host=host, port=port)
        heartbeat = client.heartbeat()
        print(f"✅ Cliente ChromaDB conectado! Heartbeat: {heartbeat}")
        
        # Teste de criação de coleção
        try:
            ef = embedding_functions.DefaultEmbeddingFunction()
            collection = client.create_collection(name="test_collection", embedding_function=ef)
            print(f"✅ Coleção de teste criada com sucesso!")
            
            # Teste de inserção
            collection.add(
                documents=["Este é um teste do ChromaDB"],
                metadatas=[{"source": "teste"}],
                ids=["id1"]
            )
            print(f"✅ Documento de teste inserido com sucesso!")
            
            # Teste de consulta
            results = collection.query(query_texts=["teste"], n_results=1)
            print(f"✅ Consulta de teste executada com sucesso! Resultados: {results}")
            
            # Limpeza
            client.delete_collection("test_collection")
            print(f"✅ Coleção de teste removida com sucesso!")
            
            return True
        except Exception as e:
            print(f"❌ Erro nas operações do ChromaDB: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão do cliente ChromaDB: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Iniciando testes de diagnóstico do ChromaDB")
    
    # Espere um pouco para garantir que o ChromaDB está pronto
    time.sleep(3)
    
    # Teste de conexão HTTP
    http_ok = test_raw_connection()
    
    # Teste do cliente ChromaDB
    client_ok = test_chroma_client()
    
    # Resumo
    print("\n📋 RESUMO DOS TESTES:")
    print(f"- Conexão HTTP: {'✅ OK' if http_ok else '❌ FALHOU'}")
    print(f"- Cliente ChromaDB: {'✅ OK' if client_ok else '❌ FALHOU'}")
    
    if http_ok and client_ok:
        print("\n🎉 TODOS OS TESTES PASSARAM! O ChromaDB está funcionando corretamente.")
        sys.exit(0)
    else:
        print("\n❌ ALGUNS TESTES FALHARAM. Verifique as mensagens de erro acima.")
        sys.exit(1)