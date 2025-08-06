#!/usr/bin/env python3
"""
Script para fazer a autenticação OAuth inicial.
Execute este script uma vez para criar o token.json.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# Define os escopos necessários
SCOPES = ['https://www.googleapis.com/auth/generative-language']

def main():
    print("🔐 Iniciando processo de autenticação OAuth para Gemini API...")
    
    try:
        # Carrega credenciais do arquivo de configuração OAuth
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        
        # Faz autenticação via servidor local
        # Isto abrirá um navegador para autenticação
        creds = flow.run_local_server(port=8080)
        
        # Salva credenciais para uso futuro
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        print("✅ Autenticação concluída! Token salvo em 'token.json'")
        print("🚀 Você pode iniciar a aplicação agora.")
        
    except Exception as e:
        print(f"❌ Erro na autenticação: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())