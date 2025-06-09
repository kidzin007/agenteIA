# Instruções de Implantação do Bot de Consultoria Financeira

Este documento contém instruções para implantar o bot de Telegram em diferentes plataformas de hospedagem.

## Pré-requisitos Gerais

1. Conta no Telegram e token de bot (via BotFather)
2. Conta na OpenAI e chave de API
3. Repositório Git com o código do bot

## Variáveis de Ambiente Necessárias

Configure estas variáveis de ambiente em qualquer plataforma que escolher:

- `TELEGRAM_TOKEN`: Token do seu bot do Telegram
- `OPENAI_API_KEY`: Chave de API da OpenAI
- `MONGODB_URI` (opcional): URI de conexão do MongoDB, se estiver usando

## Opções de Implantação

### 1. Railway

Railway é uma plataforma moderna e fácil de usar com um generoso plano gratuito.

1. Crie uma conta em [Railway](https://railway.app/)
2. Conecte seu repositório GitHub
3. Crie um novo projeto a partir do repositório
4. Configure as variáveis de ambiente necessárias
5. O deployment será automático quando você fizer push para o repositório

**Bônus:** Railway também oferece MongoDB como serviço adicional, que você pode adicionar ao seu projeto.

### 2. PythonAnywhere

PythonAnywhere é uma plataforma especializada em Python com plano gratuito.

1. Crie uma conta em [PythonAnywhere](https://www.pythonanywhere.com/)
2. Vá para a seção "Consoles" e inicie um novo console Bash
3. Clone seu repositório: `git clone [URL_DO_SEU_REPO]`
4. Configure um ambiente virtual:
   ```bash
   cd [NOME_DO_REPO]
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Vá para a seção "Tasks" e adicione uma nova tarefa para executar seu bot:
   ```bash
   cd [CAMINHO_PARA_SEU_REPO] && source venv/bin/activate && python main.py
   ```
6. Configure as variáveis de ambiente no arquivo `.env`

### 3. Render

Render oferece hospedagem gratuita para serviços web com algumas limitações.

1. Crie uma conta em [Render](https://render.com/)
2. Conecte seu repositório GitHub
3. Crie um novo serviço web
4. Configure o comando de inicialização como `python main.py`
5. Configure as variáveis de ambiente necessárias
6. Implante o serviço

### 4. Fly.io

Fly.io oferece um plano gratuito generoso para aplicações pequenas.

1. Instale a CLI do Fly: [Instruções de instalação](https://fly.io/docs/hands-on/install-flyctl/)
2. Faça login: `flyctl auth login`
3. Inicialize a aplicação: `flyctl launch`
4. Configure as variáveis de ambiente: `flyctl secrets set TELEGRAM_TOKEN=seu_token OPENAI_API_KEY=sua_chave`
5. Implante: `flyctl deploy`

### 5. VPS (Servidor Virtual Privado)

Para usuários avançados que desejam controle total.

1. Configure um servidor Linux (Ubuntu recomendado)
2. Instale Python e pip
3. Clone seu repositório
4. Configure um ambiente virtual e instale as dependências
5. Configure as variáveis de ambiente
6. Use o `systemd` ou `supervisor` para manter o bot em execução:

   **Exemplo com systemd:**
   ```
   [Unit]
   Description=Bot de Consultoria Financeira
   After=network.target

   [Service]
   User=seu_usuario
   WorkingDirectory=/caminho/para/seu/repo
   ExecStart=/caminho/para/seu/repo/venv/bin/python main.py
   Restart=always
   Environment=TELEGRAM_TOKEN=seu_token
   Environment=OPENAI_API_KEY=sua_chave

   [Install]
   WantedBy=multi-user.target
   ```

## Usando MongoDB para Armazenamento

O bot agora suporta nativamente o MongoDB para armazenamento de dados dos usuários, oferecendo maior escalabilidade e confiabilidade. Para configurar:

1. Crie uma conta no [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (plano gratuito disponível)
2. Configure um cluster e obtenha a string de conexão
3. Adicione a string de conexão como variável de ambiente `MONGODB_URI`
4. O bot detectará automaticamente e usará o MongoDB se a variável estiver configurada

### Vantagens do MongoDB para Produção

- **Alta Disponibilidade**: Dados sempre acessíveis, mesmo com grande volume de usuários
- **Escalabilidade**: Suporta crescimento do número de usuários sem degradação de desempenho
- **Segurança**: Backups automáticos e proteção de dados
- **Análise de Dados**: Possibilidade de realizar consultas complexas e análises sobre o comportamento dos usuários
- **Monitoramento**: Ferramentas integradas para monitorar o desempenho e uso do banco de dados

Para mais detalhes sobre a integração com MongoDB, consulte o arquivo [MONGODB_INTEGRATION.md](MONGODB_INTEGRATION.md).

## Solução de Problemas

- **Erro de Webhook**: Se estiver usando webhook em vez de polling, certifique-se de que sua URL seja acessível publicamente e tenha HTTPS.
- **Timeouts**: Algumas plataformas têm limites de tempo de execução para tarefas gratuitas. Configure seu bot para reiniciar periodicamente.
- **Erros de Memória**: Se encontrar erros de memória, considere otimizar o armazenamento de histórico de conversas ou usar um banco de dados externo.
- **Erros de Codificação**: Para problemas com caracteres Unicode, verifique se todos os arquivos estão salvos em UTF-8. 