#!/usr/bin/env python3
"""
Script para fazer a autenticação OAuth inicial usando device flow.
Não requer navegador dentro do container.
"""

import os
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# Define os escopos necessários
SCOPES = ['https://www.googleapis.com/auth/generative-language']

def main():
    print("🔐 Iniciando processo de autenticação OAuth para Gemini API...")
    print("⚠️ Este processo não abre um navegador automaticamente.")
    
    try:
        # Carrega credenciais do arquivo de configuração
        with open('credentials.json', 'r') as f:
            client_config = json.load(f)
        
        # Cria um fluxo OAuth com configuração manual para device flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri='http://localhost:8501'  # Indica fluxo manual
        )
        
        # Gera URL de autenticação
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        # Exibe instruções para o usuário
        print("\n" + "="*60)
        print("1) Acesse esta URL no seu navegador:")
        print("\n" + auth_url + "\n")
        print("2) Faça login e autorize o aplicativo")
        print("3) Copie o código de autorização mostrado")
        print("="*60 + "\n")
        
        # Solicita o código de autorização
        code = input("Cole o código de autorização aqui: ").strip()
        
        # Troca o código por token de acesso
        flow.fetch_token(code=code)
        
        # Salva credenciais para uso futuro
        credentials = flow.credentials
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
            
        print("\n✅ Autenticação concluída! Token salvo em 'token.json'")
        print("🚀 Você pode iniciar a aplicação agora.")
        
    except Exception as e:
        print(f"\n❌ Erro na autenticação: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())