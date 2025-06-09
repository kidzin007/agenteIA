import logging
import os
import re
import random
import time
import sys
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from openai import OpenAI
from dotenv import load_dotenv
import traceback
import requests
from googlesearch import search
from bs4 import BeautifulSoup
import json
from datetime import datetime

# Configuração de logging mais detalhada com tratamento para caracteres Unicode
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Substituindo caracteres Unicode problemáticos
            msg = msg.encode('cp1252', errors='replace').decode('cp1252')
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        UnicodeStreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Estados para o ConversationHandler
WAITING_RESPONSE = 0
FOLLOW_UP = 1

class GoogleSearch:
    """Classe para realizar pesquisas no Google e extrair informações relevantes."""
    
    @staticmethod
    async def search_google(query, num_results=5):
        """Realiza uma pesquisa no Google e retorna os resultados."""
        try:
            logger.info(f"Realizando pesquisa no Google para: {query}")
            search_results = []
            
            # Adicionando tratamento de erros mais robusto
            try:
                # Realizando a pesquisa
                search_urls = list(search(query, num_results=num_results, lang="pt", country="br", stop=num_results))
                
                if not search_urls:
                    logger.warning("Nenhum resultado encontrado na pesquisa.")
                    return []
                
                for url in search_urls:
                    try:
                        # Ignorando URLs problemáticas comuns
                        if any(blocked in url.lower() for blocked in ["youtube.com", "facebook.com", "instagram.com", "twitter.com", "tiktok.com"]):
                            continue
                            
                        # Obtendo o conteúdo da página com timeout
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        }
                        response = requests.get(url, headers=headers, timeout=5)
                        
                        if response.status_code == 200:
                            # Parseando o HTML
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Obtendo o título
                            title = soup.title.string if soup.title else "Sem título"
                            
                            # Obtendo um resumo do conteúdo (primeiros parágrafos)
                            paragraphs = soup.find_all('p')
                            content = ""
                            for p in paragraphs[:5]:  # Pegando os 5 primeiros parágrafos
                                if p.text and len(p.text.strip()) > 20:  # Evitando parágrafos vazios ou muito curtos
                                    content += p.text.strip() + " "
                            
                            if content:
                                # Limpando o conteúdo (removendo caracteres especiais e formatação)
                                content = re.sub(r'\s+', ' ', content)  # Substituindo múltiplos espaços por um único
                                content = re.sub(r'[^\w\s.,;:!?()-]', '', content)  # Removendo caracteres especiais
                                
                                # Limitando o tamanho do conteúdo
                                content = content[:500] + "..." if len(content) > 500 else content
                                
                                # Adicionando aos resultados
                                search_results.append({
                                    "title": title,
                                    "url": url,
                                    "content": content
                                })
                        
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Erro ao acessar URL {url}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"Erro ao processar URL {url}: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Erro durante a pesquisa: {str(e)}")
                return []
            
            logger.info(f"Pesquisa concluída. Encontrados {len(search_results)} resultados.")
            return search_results
            
        except Exception as e:
            logger.error(f"Erro na pesquisa Google: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    @staticmethod
    def format_search_results(results):
        """Formata os resultados da pesquisa para uso no prompt."""
        if not results:
            return "Não foi possível encontrar resultados relevantes para esta pesquisa."
        
        formatted_results = "Resultados da pesquisa na web:\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result['title']}\n"
            formatted_results += f"URL: {result['url']}\n"
            formatted_results += f"Resumo: {result['content']}\n\n"
        
        return formatted_results

class UserMemory:
    """Classe para gerenciar a memória de interações com usuários."""
    
    def __init__(self):
        self.user_data = {}
        self.memory_file = "user_memory.json"
        self.load_memory()
    
    def load_memory(self):
        """Carrega a memória de usuários do arquivo."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
                logger.info(f"Memória de usuários carregada: {len(self.user_data)} usuários")
            else:
                logger.info("Arquivo de memória não encontrado. Criando nova memória.")
        except Exception as e:
            logger.error(f"Erro ao carregar memória: {str(e)}")
    
    def save_memory(self):
        """Salva a memória de usuários no arquivo."""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
            logger.info("Memória de usuários salva com sucesso")
        except Exception as e:
            logger.error(f"Erro ao salvar memória: {str(e)}")
    
    def get_user_info(self, user_id):
        """Obtém informações sobre um usuário específico."""
        user_id_str = str(user_id)
        if user_id_str not in self.user_data:
            self.user_data[user_id_str] = {
                "first_interaction": datetime.now().isoformat(),
                "last_interaction": datetime.now().isoformat(),
                "interaction_count": 0,
                "topics": [],
                "preferences": {},
                "conversation_history": []
            }
        return self.user_data[user_id_str]
    
    def update_user_interaction(self, user_id, user_message, bot_response):
        """Atualiza as informações de interação de um usuário."""
        user_id_str = str(user_id)
        user_info = self.get_user_info(user_id)
        
        # Atualizando dados básicos
        user_info["last_interaction"] = datetime.now().isoformat()
        user_info["interaction_count"] += 1
        
        # Adicionando ao histórico de conversas (limitando a 10 interações)
        user_info["conversation_history"].append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response
        })
        
        # Mantendo apenas as 10 últimas interações
        if len(user_info["conversation_history"]) > 10:
            user_info["conversation_history"] = user_info["conversation_history"][-10:]
        
        # Identificando tópicos com base em palavras-chave
        topics_keywords = {
            "investimentos": ["investir", "investimento", "ação", "ações", "bolsa"],
            "renda_fixa": ["renda fixa", "cdb", "tesouro", "lci", "lca"],
            "aposentadoria": ["aposentadoria", "previdência", "inss", "aposentar"],
            "dívidas": ["dívida", "dívidas", "empréstimo", "crédito", "financiamento"],
            "economia": ["economia", "poupar", "economizar", "gastos"],
            "educação_financeira": ["educação financeira", "aprender", "finanças"],
            "impostos": ["imposto", "impostos", "ir", "declaração"],
            "imóveis": ["imóvel", "imóveis", "casa", "apartamento", "financiamento"]
        }
        
        for topic, keywords in topics_keywords.items():
            for keyword in keywords:
                if keyword.lower() in user_message.lower() and topic not in user_info["topics"]:
                    user_info["topics"].append(topic)
        
        # Salvando as alterações
        self.user_data[user_id_str] = user_info
        self.save_memory()
    
    def get_conversation_summary(self, user_id):
        """Obtém um resumo das conversas recentes com o usuário."""
        user_id_str = str(user_id)
        user_info = self.get_user_info(user_id)
        
        if not user_info["conversation_history"]:
            return "Não há histórico de conversas anteriores."
        
        summary = "Resumo das conversas recentes:\n\n"
        
        for i, interaction in enumerate(user_info["conversation_history"][-3:], 1):
            timestamp = datetime.fromisoformat(interaction["timestamp"]).strftime("%d/%m/%Y %H:%M")
            summary += f"Interação {i} ({timestamp}):\n"
            summary += f"Usuário: {interaction['user_message']}\n"
            summary += f"Bot: {interaction['bot_response'][:100]}...\n\n"
        
        summary += f"Tópicos de interesse: {', '.join(user_info['topics']) if user_info['topics'] else 'Nenhum identificado ainda'}\n"
        summary += f"Total de interações: {user_info['interaction_count']}"
        
        return summary

class OpenAIAdvisor:
    def __init__(self):
        logger.info("Iniciando configuração da API OpenAI...")
        try:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente!")
            
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.user_memory = UserMemory()
            logger.info("Cliente OpenAI configurado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao configurar cliente OpenAI: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _get_current_date(self):
        """Retorna a data atual formatada."""
        return datetime.now().strftime("%d/%m/%Y")

    async def generate_response(self, user_input: str, user_id: int, context_data=None, search_web=True):
        try:
            logger.debug(f"Gerando resposta com OpenAI para input: {user_input}")
            
            # Obtendo informações do usuário
            user_info = self.user_memory.get_user_info(user_id)
            
            # Realizando pesquisa na web se necessário
            web_search_results = ""
            if search_web and any(keyword in user_input.lower() for keyword in ["atual", "hoje", "recente", "notícia", "mercado", "taxa", "cotação", "preço", "inflação", "selic", "dólar", "euro", "bolsa"]):
                logger.info("Detectada necessidade de informações atualizadas. Realizando pesquisa web.")
                search_query = f"finanças {user_input} brasil atual"
                results = await GoogleSearch.search_google(search_query)
                if results:
                    web_search_results = GoogleSearch.format_search_results(results)
            
            # Construindo o contexto da conversa (apenas última interação para ser mais conciso)
            conversation_context = ""
            if user_info["interaction_count"] > 0:
                last_interactions = user_info["conversation_history"][-1:] if len(user_info["conversation_history"]) > 0 else []
                if last_interactions:
                    conversation_context = "Última conversa:\n"
                    for interaction in last_interactions:
                        conversation_context += f"Usuário: {interaction['user_message']}\n"
                        conversation_context += f"Você: {interaction['bot_response'][:50]}...\n\n"
            
            # Adicionando dados de contexto específicos se fornecidos
            if context_data:
                conversation_context += f"\nContexto adicional: {context_data}\n\n"
            
            # Sistema de prompt para respostas adaptativas e detalhadas quando necessário
            system_prompt = f"""Você é Paulo, consultor financeiro experiente e qualificado com mais de 15 anos no mercado. Responda como um especialista conversando informalmente.

            REGRAS CRÍTICAS:
            1. ADAPTE A PROFUNDIDADE DA RESPOSTA:
               - Para perguntas gerais ou simples: use 1-3 frases informativas
               - Para perguntas específicas ou técnicas: forneça respostas detalhadas e completas (até 5-8 frases)
               - Quando o usuário pedir detalhes ou explicações: seja abrangente e didático
            
            2. PERSONALIDADE: amigável, direto, com um toque de humor sutil
            
            3. ESTILO BRASILEIRO: use expressões como "olha", "na verdade", "veja bem"
            
            4. LINGUAGEM NATURAL: use "tá", "pra", "vamo" ocasionalmente em respostas curtas
            
            5. RESPOSTAS DETALHADAS QUANDO:
               - O usuário pedir explicitamente mais informações
               - A pergunta contiver termos como "explique", "detalhe", "como funciona"
               - O tópico for complexo e exigir explicação para ser útil
               - Envolver planejamento, estratégias ou conceitos técnicos
            
            6. ESTRUTURA PARA RESPOSTAS DETALHADAS:
               - Comece com uma visão geral concisa
               - Desenvolva com pontos-chave organizados (2-4 pontos)
               - Inclua exemplos práticos ou números quando relevante
               - Termine com uma conclusão acionável
            
            7. DADOS E PRECISÃO: use dados concretos, números e estatísticas relevantes
            
            8. DIDÁTICO: use analogias simples para explicar conceitos complexos
            
            9. ADAPTAÇÃO TÉCNICA: ajuste o nível técnico baseado na sofisticação da pergunta
            
            10. HONESTIDADE: admita quando não tiver informações suficientes
            
            LEMBRE-SE: você é um especialista real com experiência prática, não um chatbot. Responda com a autoridade de quem já ajudou centenas de pessoas com situações semelhantes.
            
            {conversation_context}
            
            {web_search_results}
            
            Dada sua experiência, analise a pergunta e forneça uma resposta adaptada ao nível de detalhe necessário - seja concisa para perguntas simples ou detalhada para questões complexas ou específicas."""
            
            logger.debug("Enviando requisição para a API da OpenAI...")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=800,  # Aumentado para permitir respostas mais detalhadas
                top_p=0.9
            )
            
            formatted_response = response.choices[0].message.content
            logger.debug(f"Resposta da OpenAI: {formatted_response}")
            
            # Formatando para Markdown
            formatted_response = formatted_response.replace('*', '\\*')
            formatted_response = formatted_response.replace('_', '\\_')
            formatted_response = formatted_response.replace('`', '\\`')
            
            # Atualizando a memória do usuário
            self.user_memory.update_user_interaction(user_id, user_input, formatted_response)
            
            return formatted_response

        except Exception as e:
            logger.error(f"Erro na geração de resposta com OpenAI: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "Ops! Tive um problema ao processar sua pergunta. Pode tentar novamente?"

class TelegramBot:
    def __init__(self):
        logger.info("Iniciando TelegramBot...")
        try:
            self.advisor = OpenAIAdvisor()
            self.app = None
            
            # Frases de espera profissionais e naturais
            self.typing_messages = [
                "Analisando sua questão...",
                "Consultando os dados...",
                "Processando isso...",
                "Um momento, por favor...",
                "Elaborando uma resposta...",
                "Verificando as informações...",
                "Pensando na melhor estratégia...",
                "Avaliando as opções...",
            ]
            
            # Frases de follow-up engajadoras
            self.follow_up_questions = [
                "Essa perspectiva faz sentido para você?",
                "Isso esclareceu sua dúvida?",
                "Quer explorar mais algum aspecto desse tema?",
                "Posso detalhar melhor algum ponto específico?",
                "Esse caminho parece adequado para seu objetivo?",
                "Consegui responder completamente sua pergunta?",
                "Há algo mais que gostaria de saber sobre esse assunto?"
            ]
            
            # Frases de espera mais profissionais e naturais
            self.typing_messages = [
                "Analisando sua questão...",
                "Consultando os dados...",
                "Processando isso...",
                "Um momento, por favor...",
                "Elaborando uma resposta...",
                "Verificando as informações...",
                "Pensando na melhor estratégia...",
                "Avaliando as opções...",
            ]
            
            # Frases de follow-up mais engajadoras
            self.follow_up_questions = [
                "Essa perspectiva faz sentido para você?",
                "Isso esclareceu sua dúvida?",
                "Quer explorar mais algum aspecto desse tema?",
                "Posso detalhar melhor algum ponto específico?",
                "Esse caminho parece adequado para seu objetivo?",
                "Consegui responder completamente sua pergunta?",
                "Há algo mais que gostaria de saber sobre esse assunto?"
            ]
            
            logger.info("TelegramBot iniciado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao iniciar TelegramBot: {str(e)}")
            raise

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = update.effective_user
            logger.info(f"Novo usuário iniciou o bot: {user.id}")
            
            # Simulando digitação para parecer mais humano
            await update.message.chat.send_action(action="typing")
            await asyncio.sleep(1.0)  # Pausa mais curta
            
            keyboard = [
                [
                    InlineKeyboardButton("📈 Investimentos", callback_data='investments'),
                    InlineKeyboardButton("💰 Renda Fixa", callback_data='fixed_income'),
                    InlineKeyboardButton("📊 Renda Variável", callback_data='variable_income')
                ],
                [
                    InlineKeyboardButton("🏦 Fundos", callback_data='funds'),
                    InlineKeyboardButton("💲 Cripto", callback_data='crypto'),
                    InlineKeyboardButton("📝 Planejamento", callback_data='planning')
                ],
                [
                    InlineKeyboardButton("📉 Análise de Mercado", callback_data='market_analysis'),
                    InlineKeyboardButton("📰 Notícias", callback_data='news')
                ],
                [
                    InlineKeyboardButton("🔍 Pesquisar na Web", callback_data='web_search'),
                    InlineKeyboardButton("❓ Ajuda", callback_data='help')
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_message = (
                f"Olá, {user.first_name}! 👋\n\n"
                "Sou Paulo, consultor financeiro com mais de 15 anos de experiência no mercado. "
                "Estou aqui para ajudar com suas dúvidas sobre investimentos, planejamento financeiro e economia.\n\n"
                "Como posso auxiliar você hoje? Escolha uma opção abaixo ou me faça uma pergunta direta sobre qualquer tema financeiro."
            )
            
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
            return WAITING_RESPONSE
            
        except Exception as e:
            logger.error(f"Erro no comando start: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await update.message.reply_text(
                "Ops! Tive um problema ao iniciar. Pode tentar novamente?"
            )
            return ConversationHandler.END

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = update.effective_user
            message = update.message.text
            logger.info(f"Mensagem recebida do usuário {user.id}: {message}")

            # Verificando se estamos aguardando uma consulta de pesquisa
            if context.user_data.get('awaiting_search_query'):
                return await self.handle_web_search(update, context)

            # Enviando uma mensagem de "estou pensando" aleatória para parecer mais humano
            # Apenas 50% das vezes para não parecer repetitivo
            if random.random() < 0.5:
                typing_message = random.choice(self.typing_messages)
                thinking_message = await update.message.reply_text(typing_message)
            else:
                thinking_message = None
            
            # Enviando mensagem de "digitando..."
            await update.message.chat.send_action(action="typing")
            
            # Simulando tempo de digitação adaptativo baseado na complexidade da pergunta
            # Perguntas que pedem detalhes merecem mais "tempo de reflexão"
            base_typing_time = 1.0
            
            # Aumenta o tempo de digitação para perguntas complexas ou que pedem detalhes
            if wants_details or any(term in message.lower() for term in ["como", "porquê", "detalhe", "explique", "diferença"]):
                typing_time = random.uniform(2.0, 3.5)  # Mais tempo para perguntas complexas
            elif len(message.split()) > 15:  # Mensagem longa
                typing_time = random.uniform(1.5, 3.0)  # Tempo médio para mensagens longas
            else:
                typing_time = random.uniform(1.0, 2.0)  # Tempo padrão para mensagens simples
                
            await asyncio.sleep(typing_time)
            
            # Removendo a mensagem de "estou pensando" se existir
            if thinking_message:
                await thinking_message.delete()
            
            # Verificando se a mensagem parece ser uma pergunta sobre informações atualizadas ou detalhadas
            search_keywords = ["atual", "hoje", "recente", "notícia", "mercado", "taxa", "cotação", "preço", 
                             "inflação", "selic", "dólar", "euro", "bolsa", "tendência", "projeção", "previsão"]
            
            # Palavras que indicam pedido de detalhamento
            detail_keywords = ["detalhe", "explique", "explica", "como funciona", "passo a passo", 
                              "aprofunde", "mais informações", "específico", "detalhadamente"]
            
            # Verificando se é uma solicitação de busca na web
            search_web = any(keyword in message.lower() for keyword in search_keywords)
            
            # Detectando se é uma solicitação de resposta detalhada
            wants_details = any(keyword in message.lower() for keyword in detail_keywords)
            
            # Ajustando o contexto se o usuário quiser detalhes
            context_data = None
            if wants_details:
                context_data = "O usuário está solicitando uma explicação detalhada e abrangente. Forneça uma resposta completa com exemplos práticos quando possível."
            
            # Gerando resposta com detalhamento quando solicitado
            response = await self.advisor.generate_response(message, user.id, context_data=context_data, search_web=search_web)
            
            # Dividindo respostas longas
            if len(response) > 4096:
                chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(chunk, parse_mode='Markdown')
                    # Se não for o último chunk, simular digitação entre chunks
                    if i < len(chunks) - 1:
                        await update.message.chat.send_action(action="typing")
                        await asyncio.sleep(0.8)
            else:
                await update.message.reply_text(response, parse_mode='Markdown')
            
            # Adicionando uma pergunta de acompanhamento ocasionalmente (apenas 30% das vezes)
            # Maior probabilidade para respostas mais longas
            message_length = len(response)
            follow_up_probability = 0.3
            
            # Aumenta a probabilidade para respostas longas (mais detalhadas)
            if message_length > 300:
                follow_up_probability = 0.5  # 50% de chance para respostas detalhadas
            
            if random.random() < follow_up_probability:
                await asyncio.sleep(1.2)  # Pausa maior após respostas detalhadas
                await update.message.chat.send_action(action="typing")
                await asyncio.sleep(0.7)
                
                # Seleciona follow-up específico para respostas mais detalhadas
                if message_length > 300:
                    detailed_followups = [
                        "Gostaria que eu explorasse algum desses pontos em mais detalhes?",
                        "Tem alguma parte específica que você quer que eu aprofunde?",
                        "Isso atendeu ao nível de detalhe que você precisava?",
                        "Quer que eu dê exemplos práticos de algum desses pontos?"
                    ]
                    follow_up = random.choice(detailed_followups)
                else:
                    follow_up = random.choice(self.follow_up_questions)
                
                await update.message.reply_text(follow_up)
            
            return WAITING_RESPONSE

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await update.message.reply_text(
                "Ops! Tive um problema ao processar sua pergunta. Pode tentar novamente?"
            )
            return WAITING_RESPONSE

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            user = query.from_user
            logger.info(f"Callback recebido do usuário {user.id}: {query.data}")

            await query.answer()
            
            # Tratamento especial para pesquisa na web
            if query.data == 'web_search':
                await query.message.reply_text("Sobre o que você quer pesquisar?")
                context.user_data['awaiting_search_query'] = True
                return WAITING_RESPONSE
            
            await query.message.chat.send_action(action="typing")
            
            # Simulando tempo de digitação mais curto
            typing_time = random.uniform(1.0, 2.0)
            await asyncio.sleep(typing_time)

            prompts = {
                'investments': "Quais são as principais opções de investimento no Brasil hoje, considerando diferentes perfis de risco e objetivos financeiros? O que você recomenda para quem está começando?",
                'fixed_income': "Detalhe as melhores opções de renda fixa disponíveis no Brasil atualmente, com seus rendimentos aproximados, tributação, riscos e para qual perfil de investidor cada uma é mais adequada.",
                'variable_income': "Quais são as melhores estratégias para investir em renda variável no Brasil atualmente? Fale sobre ações, FIIs, ETFs e BDRs, com dicas práticas para diferentes perfis de investidor.",
                'funds': "Explique os principais tipos de fundos de investimento disponíveis no Brasil, suas características, vantagens e desvantagens. Como escolher o fundo mais adequado para cada objetivo?",
                'crypto': "Qual a melhor forma de investir em criptomoedas com segurança no Brasil? Quais são as principais criptomoedas, exchanges confiáveis e estratégias recomendadas para diferentes perfis?",
                'planning': "Como elaborar um planejamento financeiro completo e eficiente? Quais são as etapas essenciais, desde o orçamento pessoal até a aposentadoria?",
                'market_analysis': "Como está o cenário macroeconômico e o mercado financeiro brasileiro atualmente? Quais são as perspectivas para os próximos meses e como isso afeta as decisões de investimento?",
                'news': "Quais são as principais notícias econômicas e financeiras recentes que podem impactar os investimentos no Brasil? Como os investidores devem se posicionar diante desses acontecimentos?",
                'help': "De que maneiras você pode me ajudar com planejamento financeiro, investimentos e educação financeira? Quais são seus diferenciais como consultor?"
            }

            if query.data in prompts:
                # Para análise de mercado e notícias, sempre pesquisar na web
                search_web = query.data in ['market_analysis', 'news']
                
                # Para tópicos específicos, solicitar respostas mais detalhadas
                detailed_topics = ['variable_income', 'funds', 'crypto', 'planning']
                context_data = None
                
                if query.data in detailed_topics:
                    context_data = "Este é um tópico complexo que exige uma explicação detalhada. Forneça uma resposta abrangente com pontos específicos e exemplos práticos."
                
                response = await self.advisor.generate_response(prompts[query.data], user.id, context_data=context_data, search_web=search_web)
                await query.message.reply_text(response, parse_mode='Markdown')
            else:
                logger.warning(f"Callback não reconhecido: {query.data}")
                await query.message.reply_text("Não entendi essa opção. Pode tentar novamente?")
            
            return WAITING_RESPONSE

        except Exception as e:
            logger.error(f"Erro no callback: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await query.message.reply_text(
                "Ops! Tive um problema ao processar sua solicitação. Pode tentar novamente?"
            )
            return WAITING_RESPONSE
    
    async def handle_web_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trata consultas específicas de pesquisa na web."""
        user = update.effective_user
        query = update.message.text
        
        # Verificando se estamos aguardando uma consulta de pesquisa
        if context.user_data.get('awaiting_search_query'):
            # Enviando mensagem de "pesquisando"
            search_message = await update.message.reply_text("Pesquisando...")
            
            # Enviando mensagem de "digitando..."
            await update.message.chat.send_action(action="typing")
            
            # Realizando a pesquisa
            search_query = f"finanças {query} brasil atual"
            results = await GoogleSearch.search_google(search_query)
            
            # Removendo a mensagem de "pesquisando"
            await search_message.delete()
            
            if results:
                # Gerando resposta com base nos resultados da pesquisa
                context_data = GoogleSearch.format_search_results(results)
                response = await self.advisor.generate_response(
                    f"Com base nas informações recentes sobre '{query}'", 
                    user.id, 
                    context_data=context_data,
                    search_web=False  # Já fizemos a pesquisa manualmente
                )
                
                await update.message.reply_text(response, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    "Não encontrei informações sobre isso. Pode tentar outra pergunta?"
                )
            
            # Resetando o estado de espera
            context.user_data['awaiting_search_query'] = False
            
        return WAITING_RESPONSE

    def run(self):
        try:
            logger.info("Iniciando aplicação do bot...")
            self.app = Application.builder().token(TOKEN).build()
            
            # Importando asyncio aqui para evitar problemas de importação circular
            import asyncio
            global asyncio
            
            # Configurando o ConversationHandler
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler("start", self.start)],
                states={
                    WAITING_RESPONSE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
                        CallbackQueryHandler(self.button_callback)
                    ],
                    FOLLOW_UP: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
                        CallbackQueryHandler(self.button_callback)
                    ]
                },
                fallbacks=[CommandHandler("start", self.start)]
            )
            
            # Adicionando handlers
            self.app.add_handler(conv_handler)
            
            logger.info("Bot iniciado com sucesso! Iniciando polling...")
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Erro fatal ao iniciar o bot: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

if __name__ == "__main__":
    try:
        if not TOKEN:
            raise ValueError("Token do Telegram não encontrado no arquivo .env!")
        
        if not OPENAI_API_KEY:
            raise ValueError("API Key da OpenAI não encontrada no arquivo .env!")
        
        logger.info("Iniciando bot...")
        bot = TelegramBot()
        bot.run()
        
    except Exception as e:
        logger.critical(f"Erro crítico: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        sys.exit(1) 