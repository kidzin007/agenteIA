# Bot Financeiro com OpenAI GPT-4o

## Para testar o bot procure no telgram por: @AgenteIA_01_bot

Um bot de Telegram especializado em consultoria financeira, desenvolvido com a API da OpenAI (GPT-4o) para fornecer respostas precisas, personalizadas e humanizadas sobre investimentos, planejamento financeiro e educação financeira.

## Características

- 🤖 Integração com OpenAI GPT-4o para respostas inteligentes e detalhadas
- 💬 Interface amigável via Telegram com menu interativo
- 🧠 Sistema avançado de memória para lembrar interações anteriores com usuários
- 🔍 Capacidade de pesquisa na web para informações atualizadas sobre mercado financeiro
- 🌐 Integração com MongoDB para armazenamento de dados (opcional)
- 🧩 Múltiplas personalidades adaptáveis ao contexto da conversa
- 🗣️ Linguagem natural brasileira com variações regionais
- 😊 Análise de sentimento para respostas empáticas
- ⌨️ Simulação realista de digitação humana

## Requisitos

- Python 3.8+
- Token de Bot do Telegram (obtenha com [@BotFather](https://t.me/BotFather))
- Chave de API da OpenAI
- MongoDB (opcional, para armazenamento avançado)

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd <nome-da-pasta>
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Se você estiver usando spaCy, instale o modelo em português (ou inglês como fallback):
```bash
# Para português
python -m spacy download pt_core_news_sm

# Ou para inglês (fallback)
python -m spacy download en_core_web_sm
```

4. Crie um arquivo `.env` na raiz do projeto com suas credenciais:
```
TELEGRAM_TOKEN=seu_token_aqui
OPENAI_API_KEY=sua_chave_api_aqui
MONGODB_URI=sua_uri_mongodb_aqui (opcional)
```

## Uso

Execute o bot:
```bash
python main.py
```

Inicie uma conversa com seu bot no Telegram e use o comando `/start` para começar.

## Sistema de Personalidades

O bot possui quatro personalidades distintas que são automaticamente selecionadas com base no contexto da conversa:

- **Default**: Consultor financeiro experiente e direto
- **Technical**: Especialista técnico para tópicos complexos
- **Friendly**: Consultor acessível para iniciantes
- **Mentor**: Conselheiro didático para planejamento financeiro

Cada personalidade possui características específicas de linguagem, formalidade e estilo conversacional.

## Armazenamento de Dados

O bot oferece dois modos de armazenamento:

1. **Arquivo Local**: Armazena dados em `user_memory.json` (padrão)
2. **MongoDB**: Para uso em produção, oferece maior escalabilidade e persistência

Para usar o MongoDB, defina a variável de ambiente `MONGODB_URI` no arquivo `.env`.

## Humanização do Bot

O bot implementa diversas técnicas para simular comportamento humano:

- Variações de tempo de resposta baseadas na complexidade da pergunta
- Indicadores de "pensando" e "digitando" realistas
- Uso de expressões regionais brasileiras
- Estilo conversacional adaptativo
- Perguntas de follow-up contextuais
- Detecção de nível de conhecimento do usuário

Para mais detalhes, consulte [HUMANIZACAO.md](HUMANIZACAO.md).

## Implantação

Para instruções detalhadas sobre como implantar o bot em diferentes plataformas (Heroku, PythonAnywhere, VPS, etc.), consulte [DEPLOY.md](DEPLOY.md).

## Integração com MongoDB

Para instruções sobre como configurar e utilizar o MongoDB com o bot, consulte [MONGODB_INTEGRATION.md](MONGODB_INTEGRATION.md).

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE). 