import requests
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    print("Erro: Token do Telegram não encontrado no arquivo .env!")
    exit(1)

def reset_webhook():
    # URL para deletar o webhook
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true"
    
    # Fazer a requisição
    response = requests.get(url)
    
    # Verificar resultado
    if response.status_code == 200 and response.json().get("ok"):
        print("Webhook removido com sucesso!")
        print("Agora você pode iniciar seu bot sem conflitos.")
    else:
        print(f"Erro ao remover webhook: {response.text}")

if __name__ == "__main__":
    print("Resetando webhook do Telegram...")
    reset_webhook() 