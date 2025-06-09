# Consultor Financeiro Bot

Bot de Telegram que atua como um consultor financeiro humano e realista, utilizando a API da OpenAI (GPT-4o) para gerar respostas naturais, concisas e diretas para perguntas sobre finanças e investimentos, com capacidade de pesquisar informações atualizadas na web.

## Funcionalidades

- Responde perguntas sobre investimentos, renda fixa, análise de mercado e notícias financeiras
- Fornece respostas extremamente concisas e naturais, semelhantes a um humano real
- Pesquisa informações atualizadas na web para fornecer dados recentes
- Interface amigável com botões para tópicos comuns
- Memória de conversas para manter contexto entre interações
- Suporte a armazenamento de dados em MongoDB para maior escalabilidade

## Características Humanizadas

- Respostas curtas e diretas (1-3 frases)
- Linguagem casual e conversacional
- Uso de expressões brasileiras e contrações
- Tempos de resposta naturais e variáveis
- Mensagens intermediárias ocasionais
- Perguntas de acompanhamento ocasionais
- Foco apenas no que foi perguntado, sem informações desnecessárias

## Requisitos

- Python 3.8+
- Biblioteca python-telegram-bot
- API Key da OpenAI
- Acesso à internet para pesquisas web
- MongoDB (opcional, para armazenamento escalável)

## Instalação

1. Clone o repositório
2. Instale as dependências:
```
pip install -r requirements.txt
```
3. Crie um arquivo `.env` baseado no `.env.example`:
```
cp .env.example .env
```
4. Edite o arquivo `.env` e adicione seu token do Telegram e sua API Key da OpenAI:
```
TELEGRAM_TOKEN=seu_token_do_telegram_aqui
OPENAI_API_KEY=sua_chave_api_da_openai_aqui
# Opcional: adicione a URI do MongoDB para armazenamento escalável
MONGODB_URI=sua_string_de_conexao_mongodb
```

## Uso

Execute o bot com:
```
python main.py
```

## Modelo Utilizado

### OpenAI (GPT-4o)
- Configurado para respostas concisas e naturais
- Conhecimento abrangente sobre finanças e investimentos
- Requer API Key da OpenAI

## Pesquisa na Web

O bot pode pesquisar informações atualizadas na internet para responder perguntas sobre:
- Cotações atuais
- Taxas de juros
- Notícias recentes do mercado
- Tendências econômicas
- Outros dados financeiros atualizados

## Armazenamento de Dados

O bot suporta dois métodos de armazenamento de dados:

### Armazenamento Local (Padrão)
- Usa arquivo JSON local para armazenar dados dos usuários
- Adequado para testes e uso com poucos usuários
- Não requer configuração adicional

### MongoDB (Recomendado para Produção)
- Armazenamento escalável em banco de dados MongoDB
- Suporta grande número de usuários simultaneamente
- Persistência de dados confiável
- Requer configuração da variável de ambiente `MONGODB_URI`
- Para mais detalhes, consulte [MONGODB_INTEGRATION.md](MONGODB_INTEGRATION.md)

## Logs

Os logs detalhados são salvos em `bot_debug.log` para facilitar a depuração.

## Implantação

Para informações sobre como implantar o bot em servidores de produção, consulte [DEPLOY.md](DEPLOY.md). 