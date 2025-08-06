import os
import google.generativeai as genai
from google.oauth2 import service_account

def configure_gemini_auth():
    """
    Configura a autenticação global do Gemini.
    Usa Service Account se o arquivo existir, senão tenta API Key.
    """
    cred_path = os.path.join(os.path.dirname(__file__), "chaves-google.json")
    api_key = os.getenv("GEMINI_API_KEY")

    if os.path.exists(cred_path):
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        genai.configure(credentials=credentials)
        print("✅ Gemini: Conta de serviço configurada globalmente!")
        return "service_account"
    elif api_key:
        genai.configure(api_key=api_key)
        print("✅ Gemini: API Key configurada globalmente!")
        return "api_key"
    else:
        raise RuntimeError("❌ Nenhum método de autenticação Gemini disponível (nem Service Account nem API Key).")