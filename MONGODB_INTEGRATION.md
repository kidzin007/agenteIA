# Integração com MongoDB

Este documento explica como configurar e usar o MongoDB com o Bot de Consultoria Financeira para armazenamento de dados de usuários.

## Visão Geral

O bot foi atualizado para suportar dois métodos de armazenamento de dados:

1. **Armazenamento Local**: Usa o arquivo JSON local (`user_memory.json`) para armazenar dados dos usuários (padrão)
2. **MongoDB**: Usa um banco de dados MongoDB para armazenamento de dados (recomendado para produção)

O sistema detecta automaticamente qual método usar com base na presença da variável de ambiente `MONGODB_URI`. Se a variável estiver configurada, o bot tentará se conectar ao MongoDB; caso contrário, usará o armazenamento local.

## Configuração do MongoDB

### 1. Crie uma conta no MongoDB Atlas (Recomendado)

1. Acesse [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) e crie uma conta gratuita
2. Crie um novo cluster (o plano gratuito é suficiente para a maioria dos casos)
3. Configure o acesso ao banco de dados:
   - Crie um usuário e senha para o banco de dados
   - Configure o acesso à rede (IP Whitelist) - você pode permitir acesso de qualquer lugar (0.0.0.0/0) para testes

### 2. Obtenha a String de Conexão

1. No MongoDB Atlas, clique em "Connect" no seu cluster
2. Escolha "Connect your application"
3. Selecione "Python" como driver e a versão apropriada
4. Copie a string de conexão fornecida, que será semelhante a:
   ```
   mongodb+srv://<username>:<password>@cluster0.mongodb.net/myFirstDatabase?retryWrites=true&w=majority
   ```
5. Substitua `<username>` e `<password>` pelos valores que você configurou

### 3. Configure a Variável de Ambiente

Adicione a string de conexão como uma variável de ambiente:

```
MONGODB_URI=mongodb+srv://seu_usuario:sua_senha@cluster0.mongodb.net/finance_bot?retryWrites=true&w=majority
```

Você pode fazer isso de várias maneiras:

- Adicionando ao arquivo `.env` no diretório do projeto
- Configurando na plataforma de hospedagem (Railway, Heroku, etc.)
- Exportando diretamente no terminal antes de iniciar o bot

## Estrutura de Dados

O MongoDB armazenará os dados de usuários na seguinte estrutura:

- **Database**: `finance_bot`
- **Collection**: `users`
- **Documento de Usuário**:
  ```json
  {
    "user_id": "123456789",
    "first_interaction": ISODate("2023-06-08T23:06:59.417Z"),
    "last_interaction": ISODate("2023-06-08T23:25:47.630Z"),
    "interaction_count": 9,
    "topics": ["investimentos", "impostos", "educação_financeira"],
    "preferences": {},
    "conversation_history": [
      {
        "timestamp": ISODate("2023-06-08T23:07:07.767Z"),
        "user_message": "Me fale sobre investimentos",
        "bot_response": "Olha, existem várias opções..."
      }
      // Limitado às 10 últimas interações
    ]
  }
  ```

## Vantagens do MongoDB

1. **Escalabilidade**: Suporta um grande número de usuários sem problemas de desempenho
2. **Persistência**: Os dados são armazenados com segurança na nuvem
3. **Disponibilidade**: Alta disponibilidade com backups automáticos
4. **Consultas Avançadas**: Possibilidade de realizar análises e consultas complexas sobre os dados
5. **Integração com Serviços**: Facilita a integração com outros serviços e ferramentas

## Fallback para Armazenamento Local

Se a conexão com o MongoDB falhar por qualquer motivo, o bot automaticamente voltará a usar o armazenamento local em arquivo JSON. Isso garante que o bot continue funcionando mesmo em caso de problemas com o banco de dados.

## Monitoramento e Manutenção

Para monitorar o uso do MongoDB:

1. Acesse o painel do MongoDB Atlas
2. Verifique as métricas de uso, consultas e operações
3. Configure alertas para ser notificado sobre problemas

Para manutenção:

1. Faça backups regulares dos dados (o Atlas faz isso automaticamente)
2. Monitore o crescimento da coleção de usuários
3. Considere criar índices adicionais se o número de usuários crescer significativamente

## Solução de Problemas

- **Erro de Conexão**: Verifique se a string de conexão está correta e se o IP está na whitelist
- **Erros de Autenticação**: Confirme se o usuário e senha estão corretos
- **Problemas de Desempenho**: Verifique se há índices adequados e considere otimizar consultas frequentes 