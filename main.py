import logging
import os
import re
import random
import time
import sys
import io
import json
import asyncio
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from openai import OpenAI
from dotenv import load_dotenv
import traceback
import requests
from googlesearch import search
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
import spacy
import socket

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

# Tentar baixar recursos do NLTK se ainda não foram baixados
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    logger.info("Baixando recursos NLTK necessários...")
    nltk.download('vader_lexicon')

# Tentar carregar modelo spaCy para português
try:
    nlp = spacy.load("pt_core_news_sm")
except OSError:
    logger.warning("Modelo spaCy para português não encontrado. Usando modelo em inglês como fallback.")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.error("Nenhum modelo spaCy encontrado. Funcionalidades de NLP serão limitadas.")
        nlp = None

class PersonalityManager:
    """Gerencia diferentes personalidades e estilos conversacionais para o bot."""
    
    def __init__(self):
        self.personalities = {
            "default": {
                "name": "Paulo",
                "description": "consultor financeiro experiente e direto",
                "tone": "profissional e amigável",
                "formality": "moderada",
                "expertise": "finanças pessoais e investimentos",
                "conversation_style": "consultivo e educativo",
                "speech_patterns": [
                    "Na verdade", "Veja bem", "A questão é", "Na minha experiência", 
                    "O importante aqui é", "Olha só", "Pense nisso"
                ],
                "casual_expressions": [
                    "tá", "pra", "né", "tô", "cara", "beleza", "massa", "tranquilo", 
                    "valeu", "e aí", "então"
                ]
            },
            "technical": {
                "name": "Paulo",
                "description": "especialista técnico em investimentos",
                "tone": "analítico e preciso",
                "formality": "alta",
                "expertise": "análise técnica e mercado financeiro",
                "conversation_style": "detalhado e orientado a dados",
                "speech_patterns": [
                    "Analisando tecnicamente", "Os indicadores mostram", "Do ponto de vista estrutural",
                    "Considerando as variáveis", "Em termos quantitativos", "Estatisticamente falando"
                ],
                "casual_expressions": [
                    "vamos analisar", "observe que", "note bem", "é relevante", "considere"
                ]
            },
            "friendly": {
                "name": "Paulo",
                "description": "consultor financeiro acessível e próximo",
                "tone": "casual e conversacional",
                "formality": "baixa",
                "expertise": "finanças do dia a dia e economia doméstica",
                "conversation_style": "empático e simplificador",
                "speech_patterns": [
                    "Cara", "Então", "Vamos lá", "Tipo assim", "Imagina só", 
                    "Tá ligado?", "Sabe como é", "Ó só"
                ],
                "casual_expressions": [
                    "tá", "pra", "né", "tô", "cara", "beleza", "massa", "tranquilo", 
                    "valeu", "e aí", "vamo", "daora", "firmeza", "mano"
                ]
            },
            "mentor": {
                "name": "Paulo",
                "description": "mentor financeiro sábio e experiente",
                "tone": "paciente e didático",
                "formality": "moderada",
                "expertise": "educação financeira e planejamento de longo prazo",
                "conversation_style": "narrativo e baseado em exemplos",
                "speech_patterns": [
                    "Pense nisso como", "Vamos por partes", "Imagine o seguinte", 
                    "É como se fosse", "O segredo está em", "A chave para entender"
                ],
                "casual_expressions": [
                    "vamos juntos", "passo a passo", "lembre-se", "reflita sobre", "considere"
                ]
            }
        }
        
        # Expressões regionais brasileiras por região
        self.regional_expressions = {
            "sudeste": [
                "uai", "trem bão", "pô", "caracas", "maneiro", "bacanudo", 
                "legal demais", "da hora", "meu", "mano"
            ],
            "nordeste": [
                "oxe", "eita", "arretado", "massa", "vixe", "bichinho", 
                "mainha", "painho", "aperreado", "danado"
            ],
            "sul": [
                "tchê", "bah", "barbaridade", "tri", "pila", "guri", 
                "capaz", "gurias", "bagual", "faceiro"
            ],
            "norte": [
                "égua", "parente", "mana", "mano", "é paia", "diacho", 
                "igarapé", "mangar", "botar boneco", "fofar"
            ],
            "centro_oeste": [
                "trem", "rapa", "ocê", "firme", "mano", "véi", 
                "dar conta", "caçar", "mió", "prosa"
            ]
        }
        
        # Tipos de interações e níveis de formalidade
        self.interaction_types = [
            "consulta", "ensino", "aconselhamento", "suporte", "conversa casual"
        ]
        
        self.formality_levels = ["muito informal", "informal", "neutro", "formal", "muito formal"]
        
        # Conectores conversacionais para humanizar as respostas
        self.conversation_connectors = [
            "então", "daí", "bem", "aliás", "inclusive", "além disso", 
            "por outro lado", "na verdade", "pois é", "agora", "bom",
            "enfim", "por sinal", "veja bem", "olha só", "imagine só",
            "pense bem", "sabe", "entende", "certo", "tá ligado"
        ]
        
        # Recursos para variação de estilo
        self.thinking_indicators = [
            "Hmm", "Bem", "Deixa eu pensar", "Olha", "Veja bem", 
            "Então", "Na verdade", "Considerando isso", "Analisando",
            "Pois é", "Interessante", "Entendo"
        ]
        
        self.fillers = [
            "né", "tipo", "assim", "digamos", "bem", "vamos dizer",
            "por assim dizer", "meio que", "basicamente", "praticamente",
            "essencialmente", "meio", "um pouco", "de certa forma"
        ]
        
        # Sentimentos e respostas emocionais
        self.sentiment_responses = {
            "muito_positivo": [
                "Que ótimo!", "Isso é excelente!", "Maravilha!", 
                "Que demais!", "Fantástico!", "Sensacional!"
            ],
            "positivo": [
                "Legal!", "Bom saber!", "Que bom!", "Bacana!",
                "Massa!", "Que legal!", "Boa!"
            ],
            "neutro": [
                "Entendo.", "Certo.", "Compreendo.", "Ok.",
                "Pois é.", "Vejo.", "Hmm, entendi."
            ],
            "negativo": [
                "Sinto muito por isso.", "Que pena.", "Entendo sua preocupação.",
                "Posso imaginar que isso seja difícil.", "É uma situação complicada."
            ],
            "muito_negativo": [
                "Nossa, lamento muito.", "Puxa, isso é realmente difícil.", 
                "Sinto muito que esteja passando por isso.", 
                "Caramba, é uma situação bem complicada."
            ]
        }
    
    def get_personality(self, personality_type="default"):
        """Retorna uma personalidade específica."""
        return self.personalities.get(personality_type, self.personalities["default"])
    
    def get_regional_expressions(self, region="sudeste"):
        """Retorna expressões regionais de uma região específica."""
        return self.regional_expressions.get(region, self.regional_expressions["sudeste"])
    
    def get_random_connector(self):
        """Retorna um conector conversacional aleatório."""
        return random.choice(self.conversation_connectors)
    
    def get_random_filler(self):
        """Retorna um preenchedor de frase aleatório."""
        return random.choice(self.fillers)
    
    def get_random_thinking_indicator(self):
        """Retorna um indicador de pensamento aleatório."""
        return random.choice(self.thinking_indicators)
    
    def get_sentiment_response(self, sentiment_level):
        """Retorna uma resposta baseada no sentimento."""
        return random.choice(self.sentiment_responses.get(sentiment_level, self.sentiment_responses["neutro"]))
    
    def analyze_text_complexity(self, text):
        """Analisa a complexidade do texto para determinar o nível de resposta."""
        if not text or len(text) < 10:
            return "simples"
        
        # Analisando quantidade de palavras e comprimento médio
        words = text.split()
        word_count = len(words)
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        
        # Analisando presença de termos técnicos ou complexos
        financial_terms = ["investimento", "ações", "rendimento", "tributação", "dividendos", 
                         "volatilidade", "liquidez", "benchmark", "hedge", "alavancagem", 
                         "derivativos", "criptomoedas", "análise", "rentabilidade"]
        
        technical_count = sum(1 for term in financial_terms if term in text.lower())
        
        # Determinando complexidade
        if word_count > 20 and (avg_word_length > 6 or technical_count >= 3):
            return "complexo"
        elif word_count > 10 or technical_count >= 1:
            return "médio"
        else:
            return "simples"
    
    def select_appropriate_personality(self, text, user_data=None):
        """Seleciona a personalidade mais apropriada com base no texto e dados do usuário."""
        
        # Verifica complexidade do texto
        complexity = self.analyze_text_complexity(text)
        
        # Palavras-chave para categorizar o tipo de consulta
        technical_keywords = ["análise", "técnica", "gráfico", "indicadores", "tendência", 
                             "mercado", "economia", "taxa", "rendimento", "comparativo"]
        
        friendly_keywords = ["começando", "iniciante", "básico", "simples", "fácil", 
                            "entender", "ajuda", "dúvida", "conselho"]
        
        mentor_keywords = ["planejar", "futuro", "longo prazo", "aposentadoria", "objetivo", 
                          "meta", "sonho", "realizar", "educar", "aprender"]
        
        # Contagem de palavras-chave no texto
        text_lower = text.lower()
        technical_count = sum(1 for keyword in technical_keywords if keyword in text_lower)
        friendly_count = sum(1 for keyword in friendly_keywords if keyword in text_lower)
        mentor_count = sum(1 for keyword in mentor_keywords if keyword in text_lower)
        
        # Seleciona personalidade baseada na contagem e complexidade
        if complexity == "complexo" or technical_count >= 2:
            return "technical"
        elif friendly_count >= 2 or complexity == "simples":
            return "friendly"
        elif mentor_count >= 2:
            return "mentor"
        else:
            return "default"
    
    def create_human_variation(self, text, personality_type="default", formality_level=2, add_fillers=True):
        """Adiciona variações humanas ao texto para torná-lo mais natural."""
        
        if not text:
            return text
        
        personality = self.get_personality(personality_type)
        
        # Adicionando indicador de pensamento no início ocasionalmente
        if random.random() < 0.3:
            text = f"{self.get_random_thinking_indicator()}, {text[0].lower()}{text[1:]}"
        
        # Substituindo pontuações para adicionar expressões características
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for i in range(len(sentences)):
            # Adiciona expressões características em algumas frases
            if random.random() < 0.25 and len(sentences[i]) > 20:
                speech_pattern = random.choice(personality["speech_patterns"])
                sentences[i] = f"{speech_pattern}, {sentences[i][0].lower()}{sentences[i][1:]}"
            
            # Adiciona expressões casuais em algumas frases dependendo da formalidade
            if formality_level <= 2 and random.random() < 0.3 and len(sentences[i]) > 15:
                casual_expr = random.choice(personality["casual_expressions"])
                # Decide onde colocar a expressão casual
                if random.random() < 0.5:
                    # No início
                    sentences[i] = f"{casual_expr}, {sentences[i][0].lower()}{sentences[i][1:]}"
                else:
                    # No meio da frase
                    words = sentences[i].split()
                    if len(words) > 4:
                        insert_pos = random.randint(2, min(len(words) - 2, 5))
                        words.insert(insert_pos, casual_expr)
                        sentences[i] = " ".join(words)
        
        # Reconstrói o texto com as modificações
        modified_text = " ".join(sentences)
        
        # Adiciona preenchimentos (fillers) ocasionais para parecer mais natural
        if add_fillers and formality_level <= 3:
            words = modified_text.split()
            for _ in range(min(2, len(words) // 20 + 1)):
                if len(words) > 5:
                    insert_pos = random.randint(3, len(words) - 3)
                    filler = self.get_random_filler()
                    words.insert(insert_pos, filler)
            
            modified_text = " ".join(words)
        
        return modified_text

class TextAnalyzer:
    """Analisa texto para detectar sentimentos, tópicos e intenções."""
    
    def __init__(self):
        try:
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            self.nlp = nlp  # Usando o modelo spaCy carregado globalmente
        except Exception as e:
            logger.error(f"Erro ao inicializar TextAnalyzer: {str(e)}")
            self.sentiment_analyzer = None
            self.nlp = None
    
    def analyze_sentiment(self, text):
        """Analisa o sentimento do texto."""
        if not self.sentiment_analyzer or not text:
            return "neutro"
        
        try:
            # Convertendo texto para inglês para análise VADER (temporário)
            # Em um cenário real, usar um modelo de sentimento para português
            sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
            compound = sentiment_scores["compound"]
            
            if compound >= 0.5:
                return "muito_positivo"
            elif compound >= 0.1:
                return "positivo"
            elif compound <= -0.5:
                return "muito_negativo"
            elif compound <= -0.1:
                return "negativo"
            else:
                return "neutro"
        except Exception as e:
            logger.error(f"Erro na análise de sentimento: {str(e)}")
            return "neutro"
    
    def extract_topics(self, text):
        """Extrai tópicos principais do texto."""
        topics = []
        
        if not text:
            return topics
        
        # Lista de tópicos financeiros para detectar
        financial_topics = {
            "investimentos": ["investir", "investimento", "aplicar", "aplicação", "retorno"],
            "renda_fixa": ["renda fixa", "tesouro", "cdb", "lci", "lca", "poupança"],
            "renda_variável": ["ações", "bolsa", "fii", "etf", "bdr", "dividendos"],
            "criptomoedas": ["cripto", "bitcoin", "ethereum", "blockchain", "token", "nft"],
            "planejamento": ["planejar", "planejamento", "orçamento", "meta", "objetivo"],
            "aposentadoria": ["aposentar", "aposentadoria", "previdência", "inss", "velhice"],
            "educação_financeira": ["educação", "aprender", "conhecimento", "curso", "livro"],
            "economia": ["economia", "mercado", "taxa", "juros", "inflação", "pib", "selic"],
            "impostos": ["imposto", "tributo", "ir", "declaração", "restituição", "fisco"],
            "dívidas": ["dívida", "empréstimo", "financiamento", "crédito", "parcelar"],
            "seguros": ["seguro", "proteção", "sinistro", "cobertura", "apólice"]
        }
        
        text_lower = text.lower()
        
        for topic, keywords in financial_topics.items():
            for keyword in keywords:
                if keyword in text_lower:
                    topics.append(topic)
                    break
        
        return topics
    
    def detect_question_complexity(self, text):
        """Detecta a complexidade da pergunta."""
        if not text:
            return "simples"
        
        # Palavras-chave que indicam pedido de explicação detalhada
        detail_keywords = ["explique", "detalhe", "explica", "como funciona", 
                          "aprofunde", "elabore", "descreva", "mais informações"]
        
        # Palavras-chave técnicas
        technical_keywords = ["alocação", "diversificação", "benchmark", "volatilidade", 
                             "correlação", "liquidez", "taxa", "rendimento", "tributação"]
        
        text_lower = text.lower()
        
        # Verificando presença de palavras-chave de detalhamento
        has_detail_request = any(keyword in text_lower for keyword in detail_keywords)
        
        # Verificando presença de termos técnicos
        technical_count = sum(1 for keyword in technical_keywords if keyword in text_lower)
        
        # Verificando comprimento da pergunta
        word_count = len(text.split())
        
        # Determinando complexidade
        if has_detail_request or technical_count >= 2 or word_count > 20:
            return "complexo"
        elif technical_count >= 1 or word_count > 10:
            return "médio"
        else:
            return "simples"
    
    def detect_user_region(self, text):
        """Tenta detectar a região do usuário com base em expressões regionais."""
        if not text:
            return None
        
        # Expressões regionais para detecção
        regional_markers = {
            "sudeste": ["uai", "pô", "mano", "meu", "cara", "da hora", "maneiro"],
            "nordeste": ["oxe", "eita", "vixe", "massa", "arretado", "bichinho"],
            "sul": ["tchê", "bah", "tri", "guri", "pila", "capaz"],
            "norte": ["égua", "mana", "parente", "igarapé"],
            "centro_oeste": ["trem", "ocê", "mió", "véi"]
        }
        
        text_lower = text.lower()
        region_scores = {region: 0 for region in regional_markers}
        
        for region, markers in regional_markers.items():
            for marker in markers:
                if f" {marker} " in f" {text_lower} ":  # Adiciona espaços para evitar falsos positivos
                    region_scores[region] += 1
        
        # Se encontrou marcadores, retorna a região com maior pontuação
        max_score = max(region_scores.values())
        if max_score > 0:
            max_regions = [region for region, score in region_scores.items() if score == max_score]
            return random.choice(max_regions)  # Em caso de empate, escolhe aleatoriamente
        
        return None  # Nenhuma região detectada

class GoogleSearch:
    """Classe para realizar pesquisas no Google e extrair informações relevantes."""
    
    @staticmethod
    async def search_google(query, num_results=5):
        """Realiza uma pesquisa no Google e retorna os resultados."""
        try:
            logger.info(f"Realizando pesquisa no Google para: {query}")
            search_results = []
            
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
        self.text_analyzer = TextAnalyzer()
    
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
            current_time = datetime.now().isoformat()
            self.user_data[user_id_str] = {
                "first_interaction": current_time,
                "last_interaction": current_time,
                "interaction_count": 0,
                "topics": [],
                "detected_region": None,
                "detected_expertise": "iniciante",  # iniciante, intermediário, avançado
                "sentiment_history": [],  # histórico de sentimentos detectados
                "conversation_style": "default",  # estilo de conversa preferido
                "conversation_history": [],
                "personality_compatibility": {  # compatibilidade com cada personalidade
                    "default": 0,
                    "technical": 0,
                    "friendly": 0,
                    "mentor": 0
                },
                "long_term_memory": {  # memória de longo prazo
                    "personal_details": {},
                    "preferences": {},
                    "important_dates": {},
                    "significant_topics": [],
                    "key_questions": []
                },
                "session_data": {  # dados da sessão atual
                    "session_start": current_time,
                    "queries_this_session": 0,
                    "current_topic": None,
                    "topic_continuity": False,
                    "last_sentiment": "neutro"
                }
            }
        return self.user_data[user_id_str]
    
    def update_user_interaction(self, user_id, user_message, bot_response):
        """Atualiza as informações de interação de um usuário de forma mais completa."""
        user_id_str = str(user_id)
        user_info = self.get_user_info(user_id)
        current_time = datetime.now().isoformat()
        
        # Atualizando dados básicos
        user_info["last_interaction"] = current_time
        user_info["interaction_count"] += 1
        
        # Analisando a mensagem do usuário
        sentiment = self.text_analyzer.analyze_sentiment(user_message)
        topics = self.text_analyzer.extract_topics(user_message)
        question_complexity = self.text_analyzer.detect_question_complexity(user_message)
        detected_region = self.text_analyzer.detect_user_region(user_message)
        
        # Atualizando sentimento
        user_info["sentiment_history"].append({
            "timestamp": current_time,
            "sentiment": sentiment
        })
        
        # Mantendo apenas os 20 últimos sentimentos
        if len(user_info["sentiment_history"]) > 20:
            user_info["sentiment_history"] = user_info["sentiment_history"][-20:]
        
        # Atualizando região detectada se encontrada
        if detected_region:
            user_info["detected_region"] = detected_region
        
        # Atualizando dados da sessão
        user_info["session_data"]["queries_this_session"] += 1
        user_info["session_data"]["last_sentiment"] = sentiment
        
        # Determinando continuidade de tópico
        if topics and user_info["session_data"]["current_topic"] in topics:
            user_info["session_data"]["topic_continuity"] = True
        else:
            user_info["session_data"]["topic_continuity"] = False
            if topics:
                user_info["session_data"]["current_topic"] = topics[0]
        
        # Adicionando ao histórico de conversas (limitando a 15 interações)
        user_info["conversation_history"].append({
            "timestamp": current_time,
            "user_message": user_message,
            "bot_response": bot_response,
            "sentiment": sentiment,
            "topics": topics,
            "complexity": question_complexity
        })
        
        # Mantendo apenas as 15 últimas interações
        if len(user_info["conversation_history"]) > 15:
            user_info["conversation_history"] = user_info["conversation_history"][-15:]
        
        # Atualizando tópicos do usuário
        for topic in topics:
            if topic not in user_info["topics"]:
                user_info["topics"].append(topic)
        
        # Atualizando tópicos significativos
        for topic in topics:
            if topic not in user_info["long_term_memory"]["significant_topics"]:
                topic_mentions = sum(1 for interaction in user_info["conversation_history"] 
                                  if topic in interaction.get("topics", []))
                
                # Se o tópico foi mencionado pelo menos 3 vezes, consideramos significativo
                if topic_mentions >= 3:
                    user_info["long_term_memory"]["significant_topics"].append(topic)
        
        # Ajustando nível de expertise com base na complexidade das perguntas
        if question_complexity == "complexo":
            # Aumentando a chance de ser considerado intermediário ou avançado
            if user_info["detected_expertise"] == "iniciante" and random.random() < 0.3:
                user_info["detected_expertise"] = "intermediário"
            elif user_info["detected_expertise"] == "intermediário" and random.random() < 0.2:
                user_info["detected_expertise"] = "avançado"
        
        # Extrair possíveis preferências ou detalhes pessoais de mensagens longas
        if len(user_message.split()) > 15:
            # Procurando por preferências comuns em finanças
            preferences_keywords = {
                "risco": ["conservador", "moderado", "arrojado", "agressivo", "cauteloso"],
                "horizonte": ["curto prazo", "médio prazo", "longo prazo"],
                "objetivo": ["aposentadoria", "casa própria", "viagem", "educação", "independência"]
            }
            
            for category, keywords in preferences_keywords.items():
                for keyword in keywords:
                    if keyword in user_message.lower():
                        user_info["long_term_memory"]["preferences"][category] = keyword
            
            # Procurando por detalhes pessoais
            personal_details_patterns = [
                (r"tenho\s+(\d+)\s+anos", "idade"),
                (r"trabalho\s+(?:como|na|no|em)\s+(\w+\s\w+|\w+)", "profissão"),
                (r"moro\s+(?:em|no|na)\s+(\w+\s\w+|\w+)", "localização"),
                (r"(casado|solteiro|divorciado)", "estado_civil"),
                (r"tenho\s+(\d+)\s+filhos?", "filhos")
            ]
            
            for pattern, detail_type in personal_details_patterns:
                match = re.search(pattern, user_message.lower())
                if match:
                    user_info["long_term_memory"]["personal_details"][detail_type] = match.group(1)
        
        # Atualizando compatibilidade com personalidades
        # Com base nas interações e complexidade das perguntas
        personality_compatibility = user_info["personality_compatibility"]
        
        if question_complexity == "complexo":
            personality_compatibility["technical"] += 1
        elif question_complexity == "simples":
            personality_compatibility["friendly"] += 1
        
        if sentiment in ["positivo", "muito_positivo"]:
            personality_compatibility["friendly"] += 0.5
        
        if any(topic in ["planejamento", "educação_financeira", "aposentadoria"] for topic in topics):
            personality_compatibility["mentor"] += 1
        
        # Determinando a personalidade preferida
        max_compatibility = max(personality_compatibility.values())
        max_personalities = [p for p, score in personality_compatibility.items() if score == max_compatibility]
        
        if max_personalities:
            user_info["conversation_style"] = max_personalities[0]
        
        # Salvando as alterações
        self.user_data[user_id_str] = user_info
        self.save_memory()
        
        return user_info
    
    def get_conversation_summary(self, user_id, detailed=False):
        """Obtém um resumo das conversas recentes com o usuário."""
        user_id_str = str(user_id)
        user_info = self.get_user_info(user_id)
        
        if not user_info["conversation_history"]:
            return "Não há histórico de conversas anteriores."
        
        if detailed:
            summary = "Resumo detalhado do usuário:\n\n"
            
            # Informações básicas
            first_interaction = datetime.fromisoformat(user_info["first_interaction"]).strftime("%d/%m/%Y")
            last_interaction = datetime.fromisoformat(user_info["last_interaction"]).strftime("%d/%m/%Y")
            
            summary += f"🗓️ Primeira interação: {first_interaction}\n"
            summary += f"🗓️ Última interação: {last_interaction}\n"
            summary += f"🔄 Total de interações: {user_info['interaction_count']}\n\n"
            
            # Tópicos e preferências
            summary += f"📊 Tópicos de interesse: {', '.join(user_info['topics']) if user_info['topics'] else 'Nenhum identificado ainda'}\n"
            summary += f"⭐ Tópicos significativos: {', '.join(user_info['long_term_memory']['significant_topics']) if user_info['long_term_memory']['significant_topics'] else 'Nenhum ainda'}\n"
            summary += f"🧠 Nível detectado: {user_info['detected_expertise']}\n"
            
            if user_info["long_term_memory"]["preferences"]:
                summary += "\n🔍 Preferências detectadas:\n"
                for category, value in user_info["long_term_memory"]["preferences"].items():
                    summary += f"- {category}: {value}\n"
            
            # Detalhes pessoais (se existirem)
            if user_info["long_term_memory"]["personal_details"]:
                summary += "\n👤 Detalhes pessoais detectados:\n"
                for detail_type, value in user_info["long_term_memory"]["personal_details"].items():
                    summary += f"- {detail_type}: {value}\n"
            
            # Histórico de conversas recentes
            summary += "\n💬 Conversas recentes:\n\n"
            
            for i, interaction in enumerate(user_info["conversation_history"][-5:], 1):
                timestamp = datetime.fromisoformat(interaction["timestamp"]).strftime("%d/%m/%Y %H:%M")
                summary += f"Interação {i} ({timestamp}):\n"
                summary += f"Usuário: {interaction['user_message']}\n"
                summary += f"Bot: {interaction['bot_response'][:100]}...\n"
                summary += f"Sentimento: {interaction['sentiment']}, Complexidade: {interaction['complexity']}\n\n"
            
            return summary
        else:
            # Versão simplificada
            summary = "Resumo das conversas recentes:\n\n"
            
            for i, interaction in enumerate(user_info["conversation_history"][-3:], 1):
                timestamp = datetime.fromisoformat(interaction["timestamp"]).strftime("%d/%m/%Y %H:%M")
                summary += f"Interação {i} ({timestamp}):\n"
                summary += f"Usuário: {interaction['user_message']}\n"
                summary += f"Bot: {interaction['bot_response'][:100]}...\n\n"
            
            summary += f"Tópicos de interesse: {', '.join(user_info['topics']) if user_info['topics'] else 'Nenhum identificado ainda'}\n"
            summary += f"Total de interações: {user_info['interaction_count']}"
            
            return summary
    
    def get_user_preferences(self, user_id):
        """Obtém as preferências detectadas para um usuário."""
        user_info = self.get_user_info(user_id)
        return user_info["long_term_memory"]["preferences"]
    
    def get_long_term_context(self, user_id):
        """Gera um contexto de longo prazo para uso nos prompts."""
        user_info = self.get_user_info(user_id)
        
        context = "Informações sobre o usuário:\n"
        
        # Adiciona detalhes pessoais se disponíveis
        if user_info["long_term_memory"]["personal_details"]:
            context += "Dados pessoais: "
            details = []
            for detail_type, value in user_info["long_term_memory"]["personal_details"].items():
                details.append(f"{detail_type}: {value}")
            context += ", ".join(details) + "\n"
        
        # Adiciona preferências se disponíveis
        if user_info["long_term_memory"]["preferences"]:
            context += "Preferências financeiras: "
            prefs = []
            for category, value in user_info["long_term_memory"]["preferences"].items():
                prefs.append(f"{category}: {value}")
            context += ", ".join(prefs) + "\n"
        
        # Adiciona tópicos significativos
        if user_info["long_term_memory"]["significant_topics"]:
            context += f"Tópicos recorrentes: {', '.join(user_info['long_term_memory']['significant_topics'])}\n"
        
        # Adiciona nível de expertise
        context += f"Nível de conhecimento: {user_info['detected_expertise']}\n"
        
        # Adiciona região detectada se disponível
        if user_info["detected_region"]:
            context += f"Região detectada: {user_info['detected_region']}\n"
        
        # Adiciona estilo de conversa preferido
        context += f"Estilo de comunicação preferido: {user_info['conversation_style']}\n"
        
        # Adiciona sentimento atual
        context += f"Sentimento atual: {user_info['session_data']['last_sentiment']}\n"
        
        # Adiciona últimas interações muito resumidas (apenas tópicos)
        if user_info["conversation_history"]:
            context += "Contexto recente: "
            recent_topics = []
            for interaction in user_info["conversation_history"][-3:]:
                if interaction.get("topics"):
                    recent_topics.extend(interaction["topics"])
            
            if recent_topics:
                context += f"recentemente falamos sobre {', '.join(set(recent_topics))}\n"
            
            # Adiciona última pergunta do usuário
            context += f"Última pergunta: {user_info['conversation_history'][-1]['user_message']}\n"
        
        return context
    
    def detect_intent_change(self, user_id, current_message):
        """Detecta se houve mudança significativa de intenção ou tópico."""
        user_info = self.get_user_info(user_id)
        
        if not user_info["conversation_history"]:
            return True  # Primeira mensagem sempre é uma nova intenção
        
        # Extraindo tópicos da mensagem atual
        current_topics = self.text_analyzer.extract_topics(current_message)
        
        # Obtendo tópicos da última mensagem
        last_interaction = user_info["conversation_history"][-1]
        last_topics = last_interaction.get("topics", [])
        
        # Verificando sobreposição de tópicos
        common_topics = set(current_topics).intersection(set(last_topics))
        
        # Se não houver tópicos em comum, provável mudança de intenção
        if not common_topics and (current_topics or last_topics):
            return True
        
        # Verificando comprimento da mensagem
        # Mensagens muito curtas após uma longa podem indicar mudança de contexto
        current_length = len(current_message.split())
        last_length = len(last_interaction["user_message"].split())
        
        if current_length <= 3 and last_length > 15:
            return True
        
        # Verificando palavras-chave de transição
        transition_keywords = ["outra", "diferente", "novo", "mudar", "outro assunto", "falando em"]
        if any(keyword in current_message.lower() for keyword in transition_keywords):
            return True
        
        return False

class MongoDBStorage:
    """Classe para gerenciar o armazenamento de dados no MongoDB."""
    
    def __init__(self):
        """Inicializa a conexão com o MongoDB."""
        self.client = None
        self.db = None
        self.users_collection = None
        self.mongodb_uri = os.getenv('MONGODB_URI')
        
        if self.mongodb_uri:
            try:
                logger.info("Conectando ao MongoDB...")
                self.client = MongoClient(self.mongodb_uri)
                self.db = self.client.finance_bot
                self.users_collection = self.db.users
                # Criando índice para melhorar a performance das consultas
                self.users_collection.create_index("user_id")
                logger.info("Conexão com MongoDB estabelecida com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao conectar ao MongoDB: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.client = None
        else:
            logger.info("URI do MongoDB não configurada. Usando armazenamento local.")
    
    def is_connected(self):
        """Verifica se a conexão com o MongoDB está ativa."""
        return self.client is not None
    
    def get_user_info(self, user_id):
        """Obtém informações sobre um usuário específico."""
        user_id_str = str(user_id)
        
        if not self.is_connected():
            logger.warning("MongoDB não está conectado. Não foi possível obter informações do usuário.")
            return None
        
        user_doc = self.users_collection.find_one({"user_id": user_id_str})
        
        if not user_doc:
            # Criando um novo documento para o usuário
            user_doc = {
                "user_id": user_id_str,
                "first_interaction": datetime.now(),
                "last_interaction": datetime.now(),
                "interaction_count": 0,
                "topics": [],
                "preferences": {},
                "conversation_history": []
            }
            self.users_collection.insert_one(user_doc)
            logger.info(f"Novo usuário criado no MongoDB: {user_id_str}")
        
        return user_doc
    
    def update_user_interaction(self, user_id, user_message, bot_response):
        """Atualiza as informações de interação de um usuário."""
        if not self.is_connected():
            logger.warning("MongoDB não está conectado. Não foi possível atualizar interação do usuário.")
            return
        
        user_id_str = str(user_id)
        
        # Obtendo o documento do usuário
        user_doc = self.get_user_info(user_id)
        
        # Atualizando dados básicos
        update_data = {
            "last_interaction": datetime.now(),
            "interaction_count": user_doc["interaction_count"] + 1
        }
        
        # Criando nova interação
        new_interaction = {
            "timestamp": datetime.now(),
            "user_message": user_message,
            "bot_response": bot_response
        }
        
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
        
        new_topics = []
        for topic, keywords in topics_keywords.items():
            for keyword in keywords:
                if keyword.lower() in user_message.lower() and topic not in user_doc["topics"]:
                    new_topics.append(topic)
        
        # Atualizando o documento do usuário no MongoDB
        self.users_collection.update_one(
            {"user_id": user_id_str},
            {
                "$set": update_data,
                "$push": {
                    "conversation_history": {
                        "$each": [new_interaction],
                        "$slice": -10  # Mantém apenas as 10 últimas interações
                    },
                    "topics": {
                        "$each": new_topics
                    }
                }
            }
        )
        
        logger.debug(f"Interação do usuário {user_id_str} atualizada no MongoDB")
    
    def get_conversation_summary(self, user_id):
        """Obtém um resumo das conversas recentes com o usuário."""
        if not self.is_connected():
            logger.warning("MongoDB não está conectado. Não foi possível obter resumo da conversa.")
            return "Não foi possível acessar o histórico de conversas."
        
        user_id_str = str(user_id)
        user_doc = self.get_user_info(user_id)
        
        if not user_doc or not user_doc.get("conversation_history"):
            return "Não há histórico de conversas anteriores."
        
        summary = "Resumo das conversas recentes:\n\n"
        
        # Pegando as 3 últimas interações
        recent_interactions = user_doc["conversation_history"][-3:]
        
        for i, interaction in enumerate(recent_interactions, 1):
            timestamp = interaction["timestamp"].strftime("%d/%m/%Y %H:%M") if isinstance(interaction["timestamp"], datetime) else "Data desconhecida"
            summary += f"Interação {i} ({timestamp}):\n"
            summary += f"Usuário: {interaction['user_message']}\n"
            summary += f"Bot: {interaction['bot_response'][:100]}...\n\n"
        
        summary += f"Tópicos de interesse: {', '.join(user_doc['topics']) if user_doc['topics'] else 'Nenhum identificado ainda'}\n"
        summary += f"Total de interações: {user_doc['interaction_count']}"
        
        return summary

class OpenAIAdvisor:
    def __init__(self):
        logger.info("Iniciando configuração da API OpenAI...")
        try:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente!")
            
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            
            # Verificando se devemos usar MongoDB ou armazenamento local
            mongodb_uri = os.getenv('MONGODB_URI')
            if mongodb_uri:
                logger.info("Usando MongoDB para armazenamento de dados")
                self.storage = MongoDBStorage()
                # Verificando se a conexão foi bem-sucedida
                if not self.storage.is_connected():
                    logger.warning("Falha na conexão com MongoDB. Usando armazenamento local como fallback.")
                    self.storage = UserMemory()
            else:
                logger.info("Usando armazenamento local para dados dos usuários")
                self.storage = UserMemory()
            
            # Inicializando o gerenciador de personalidades e analisador de texto
            self.personality_manager = PersonalityManager()
            self.text_analyzer = TextAnalyzer()
            
            # Inicializando cache para evitar chamadas repetidas
            self.response_cache = {}
            self.cache_expiry = 3600  # Cache válido por 1 hora
                
            logger.info("Cliente OpenAI configurado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao configurar cliente OpenAI: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _get_current_date(self):
        """Retorna a data atual formatada."""
        return datetime.now().strftime("%d/%m/%Y")
    
    def _is_question_in_cache(self, user_id, question):
        """Verifica se uma pergunta semelhante está no cache."""
        if user_id not in self.response_cache:
            return None
        
        for cached_q, response_data in self.response_cache[user_id].items():
            # Verifica similaridade básica
            if cached_q.lower() == question.lower():
                timestamp = response_data["timestamp"]
                # Verifica se o cache ainda é válido
                if (datetime.now() - timestamp).total_seconds() < self.cache_expiry:
                    return response_data["response"]
        
        return None
    
    def _add_to_cache(self, user_id, question, response):
        """Adiciona uma resposta ao cache."""
        if user_id not in self.response_cache:
            self.response_cache[user_id] = {}
        
        self.response_cache[user_id][question] = {
            "response": response,
            "timestamp": datetime.now()
        }
    
    def _clean_expired_cache(self):
        """Limpa entradas expiradas do cache."""
        for user_id in list(self.response_cache.keys()):
            for question in list(self.response_cache[user_id].keys()):
                timestamp = self.response_cache[user_id][question]["timestamp"]
                if (datetime.now() - timestamp).total_seconds() > self.cache_expiry:
                    del self.response_cache[user_id][question]
            
            # Remove usuário do cache se não tiver mais entradas
            if not self.response_cache[user_id]:
                del self.response_cache[user_id]

    async def generate_response(self, user_input: str, user_id: int, context_data=None, search_web=True):
        try:
            logger.debug(f"Gerando resposta para input: {user_input}")
            
            # Limpando cache expirado periodicamente
            self._clean_expired_cache()
            
            # Verificando cache para perguntas semelhantes
            cached_response = self._is_question_in_cache(user_id, user_input)
            if cached_response:
                logger.info("Resposta encontrada no cache")
                return cached_response
            
            # Obtendo informações do usuário
            user_info = self.storage.get_user_info(user_id)
            
            # Analisando características da mensagem
            sentiment = self.text_analyzer.analyze_sentiment(user_input)
            user_region = self.text_analyzer.detect_user_region(user_input) or user_info.get("detected_region")
            question_complexity = self.text_analyzer.detect_question_complexity(user_input)
            
            # Analisando se houve mudança de tópico
            intent_changed = False
            if hasattr(self.storage, 'detect_intent_change'):
                intent_changed = self.storage.detect_intent_change(user_id, user_input)
            
            # Selecionando personalidade apropriada
            personality_type = self.personality_manager.select_appropriate_personality(user_input, user_info)
            personality = self.personality_manager.get_personality(personality_type)
            
            # Ajustando nível de formalidade com base no sentimento e complexidade
            formality_level = 2  # Padrão é moderado
            if sentiment in ["positivo", "muito_positivo"]:
                formality_level = 1  # Mais informal para sentimentos positivos
            elif sentiment in ["negativo", "muito_negativo"]:
                formality_level = 3  # Mais formal para sentimentos negativos
            
            if question_complexity == "complexo":
                formality_level += 1  # Mais formal para perguntas complexas
            elif question_complexity == "simples":
                formality_level -= 1  # Mais informal para perguntas simples
            
            # Ajustando para ficar entre 0 e 4
            formality_level = max(0, min(formality_level, 4))
            
            # Realizando pesquisa na web se necessário
            web_search_results = ""
            if search_web and any(keyword in user_input.lower() for keyword in ["atual", "hoje", "recente", "notícia", "mercado", "taxa", "cotação", "preço", "inflação", "selic", "dólar", "euro", "bolsa"]):
                logger.info("Detectada necessidade de informações atualizadas. Realizando pesquisa web.")
                search_query = f"finanças {user_input} brasil atual"
                results = await GoogleSearch.search_google(search_query)
                if results:
                    web_search_results = GoogleSearch.format_search_results(results)
            
            # Obtendo contexto de memória de longo prazo
            long_term_context = ""
            if hasattr(self.storage, 'get_long_term_context'):
                long_term_context = self.storage.get_long_term_context(user_id)
            
            # Construindo o contexto da conversa (últimas interações para continuidade)
            conversation_context = ""
            if user_info:
                if isinstance(self.storage, MongoDBStorage):
                    # Para MongoDB
                    if user_info.get("interaction_count", 0) > 0 and user_info.get("conversation_history"):
                        last_interactions = user_info["conversation_history"][-2:] if intent_changed else user_info["conversation_history"][-3:]
                        if last_interactions:
                            conversation_context = "Últimas conversas:\n"
                            for interaction in last_interactions:
                                conversation_context += f"Usuário: {interaction['user_message']}\n"
                                conversation_context += f"Você: {interaction['bot_response'][:100]}...\n\n"
            else:
                    # Para UserMemory
                    if user_info.get("interaction_count", 0) > 0 and user_info.get("conversation_history"):
                        last_interactions = user_info["conversation_history"][-2:] if intent_changed else user_info["conversation_history"][-3:]
                        if last_interactions:
                            conversation_context = "Últimas conversas:\n"
                            for interaction in last_interactions:
                                conversation_context += f"Usuário: {interaction['user_message']}\n"
                                conversation_context += f"Você: {interaction['bot_response'][:100]}...\n\n"
            
            # Adicionando dados de contexto específicos se fornecidos
            if context_data:
                conversation_context += f"\nContexto adicional: {context_data}\n\n"
            
            # Sistema de prompt para personalidades diferentes e respostas humanizadas
            system_prompt = f"""Você é {personality['name']}, {personality['description']} com mais de 15 anos no mercado. Responda como um especialista conversando de forma {personality['tone']}.

            CONTEXTO DO USUÁRIO:
            {long_term_context}
            
            REGRAS DE ESTILO:
            1. PERSONALIDADE: {personality['description']}
            2. TOM: {personality['tone']} 
            3. FORMALIDADE: {self.personality_manager.formality_levels[formality_level]}
            4. EXPERTISE: {personality['expertise']}
            5. ESTILO CONVERSACIONAL: {personality['conversation_style']}
            
            REGRAS CRÍTICAS:
            1. ADAPTE A PROFUNDIDADE DA RESPOSTA:
               - Para perguntas simples: use 1-3 frases informativas e diretas
               - Para perguntas técnicas: forneça respostas mais detalhadas (até 5-8 frases)
               - Quando o usuário pedir detalhes: seja abrangente e didático
            
            2. LINGUAGEM NATURAL BRASILEIRA:
               - Use expressões como "{', '.join(personality['speech_patterns'][:3])}" ocasionalmente
               - Quando apropriado, use "{', '.join(personality['casual_expressions'][:3])}"
               - Adapte seu vocabulário ao nível de conhecimento do usuário
            
            3. RESPOSTA AO SENTIMENTO:
               - Sentimento atual detectado: {sentiment}
               - Ajuste seu tom para corresponder adequadamente
            
            4. ESTRUTURA:
               - Comece com um cumprimento breve ou reconhecimento se apropriado
               - Desenvolva a resposta em um fluxo conversacional natural
               - Conclua de forma prática e útil
            
            5. AUTENTICIDADE:
               - Você é um especialista real, não um chatbot
               - Responda com autoridade e experiência prática
               - Admita quando não souber algo
            
            {conversation_context}
            
            {web_search_results}
            
            Dada sua experiência, analise a pergunta e forneça uma resposta humana adaptada ao contexto - seja concisa para perguntas simples ou detalhada para questões complexas ou específicas."""
            
            logger.debug("Enviando requisição para a API da OpenAI...")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=800,
                top_p=0.9
            )
            
            raw_response = response.choices[0].message.content
            logger.debug(f"Resposta bruta da OpenAI: {raw_response}")
            
            # Humanizando a resposta com o estilo da personalidade escolhida
            humanized_response = self.personality_manager.create_human_variation(
                raw_response,
                personality_type=personality_type,
                formality_level=formality_level,
                add_fillers=(formality_level <= 3)  # Adiciona fillers apenas em níveis mais informais
            )
            
            # Adicionando expressões regionais ocasionalmente se uma região foi detectada
            if user_region and random.random() < 0.3:
                regional_expressions = self.personality_manager.get_regional_expressions(user_region)
                if regional_expressions and random.random() < 0.5:  # 50% de chance
                    regional_expr = random.choice(regional_expressions)
                    sentences = humanized_response.split('. ')
                    if len(sentences) > 2:
                        # Inserindo expressão regional em uma frase aleatória (não a primeira nem a última)
                        insert_pos = random.randint(1, len(sentences) - 2)
                        sentences[insert_pos] = f"{sentences[insert_pos][:-1]}, {regional_expr}"
                        humanized_response = '. '.join(sentences)

            # Formatando para Markdown
            formatted_response = humanized_response.replace('*', '\\*')
            formatted_response = formatted_response.replace('_', '\\_')
            formatted_response = formatted_response.replace('`', '\\`')
            
            # Atualizando a memória do usuário
            self.storage.update_user_interaction(user_id, user_input, formatted_response)
            
            # Adicionando ao cache
            self._add_to_cache(user_id, user_input, formatted_response)
            
            return formatted_response

        except Exception as e:
            logger.error(f"Erro na geração de resposta: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "Ops! Tive um problema ao processar sua pergunta. Pode tentar novamente?"

class TelegramBot:
    def __init__(self):
        logger.info("Iniciando TelegramBot...")
        try:
            self.advisor = OpenAIAdvisor()
            self.app = None
            
            # Inicializando componentes de humanização
            self.personality_manager = PersonalityManager()
            self.text_analyzer = TextAnalyzer()
            
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
                "Buscando as informações mais recentes...",
                "Deixa eu pensar aqui...",
                "Estou considerando os detalhes...",
                "Reunindo os dados relevantes...",
                "Fazendo os cálculos...",
                "Analisando o cenário atual...",
                "Organizando as ideias..."
            ]
            
            # Variações de pensamento para diferentes personalidades
            self.thinking_variations = {
                "default": [
                    "Analisando isso...", 
                    "Considerando os fatores...", 
                    "Verificando os dados..."
                ],
                "technical": [
                    "Processando os indicadores...", 
                    "Analisando métricas...", 
                    "Calculando as variáveis..."
                ],
                "friendly": [
                    "Deixa eu ver isso rapidinho...", 
                    "Hmm, pensando aqui...", 
                    "Peraí, vou te responder já..."
                ],
                "mentor": [
                    "Refletindo sobre sua questão...", 
                    "Pensando na melhor abordagem...", 
                    "Buscando um exemplo adequado..."
                ]
            }
            
            # Frases de follow-up engajadoras
            self.follow_up_questions = [
                "Essa perspectiva faz sentido para você?",
                "Isso esclareceu sua dúvida?",
                "Quer explorar mais algum aspecto desse tema?",
                "Posso detalhar melhor algum ponto específico?",
                "Esse caminho parece adequado para seu objetivo?",
                "Consegui responder completamente sua pergunta?",
                "Há algo mais que gostaria de saber sobre esse assunto?",
                "Isso atende ao que você estava procurando?",
                "Faz sentido para sua situação?",
                "Gostaria de exemplos práticos sobre isso?",
                "Quer que eu aborde algum outro aspecto?",
                "Tem alguma dúvida específica sobre o que expliquei?",
                "Isso te ajuda a tomar uma decisão?"
            ]
            
            # Variações de follow-up para diferentes personalidades
            self.follow_up_variations = {
                "default": [
                    "Isso atende sua expectativa?", 
                    "Posso ajudar com algo mais?", 
                    "Ficou claro ou quer que eu detalhe?"
                ],
                "technical": [
                    "Gostaria de mais dados sobre isso?", 
                    "Quer que analise algum outro indicador?", 
                    "Precisa de informações mais específicas?"
                ],
                "friendly": [
                    "E aí, faz sentido pra você?", 
                    "Tá tranquilo ou quer saber mais?", 
                    "Ficou alguma dúvida?"
                ],
                "mentor": [
                    "Como isso se aplica ao seu caso?", 
                    "Consegue visualizar isso no seu contexto?", 
                    "Quer explorar mais esse conceito?"
                ]
            }
            
            # Feedback de recebimento de mensagem
            self.message_acknowledgments = [
                "👍",
                "Entendi",
                "Certo",
                "Vamos lá",
                "Ok",
                "Sim",
                "Claro",
                "Perfeito",
                "Compreendi",
                "Vou ver isso"
            ]
            
            # Padrão de comportamento humano para digitação
            self.human_typing_speeds = {
                "lento": (70, 90),  # caracteres por minuto
                "médio": (120, 180),
                "rápido": (200, 280)
            }
            
            # Configurações para variação de comportamento
            self.variation_settings = {
                "acknowledge_message_chance": 0.15,  # chance de enviar reconhecimento
                "thinking_message_chance": 0.5,     # chance de enviar "pensando"
                "follow_up_chance": 0.3,           # chance de perguntar follow-up
                "typing_indicator_delay_range": (0.3, 1.2),  # atraso antes de mostrar digitando
                "response_delay_range": (0.5, 2.0)  # atraso adicional antes de responder
            }
            
            logger.info("TelegramBot iniciado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao iniciar TelegramBot: {str(e)}")
            raise

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = update.effective_user
            logger.info(f"Novo usuário iniciou o bot: {user.id}")
            
            # Verificando se é um usuário recorrente
            user_info = self.advisor.storage.get_user_info(user.id)
            is_returning_user = user_info.get("interaction_count", 0) > 0
            
            # Enviando "digitando..." com uma pausa natural
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await update.message.chat.send_action(action="typing")
            
            # Calculando um tempo de digitação realista para a mensagem de boas-vindas
            if is_returning_user:
                # Mensagem mais curta para usuários recorrentes
                typing_time = random.uniform(1.5, 2.5)
            else:
                # Mensagem mais longa para novos usuários
                typing_time = random.uniform(2.5, 3.5)
            
            await asyncio.sleep(typing_time)
            
            # Preparando o teclado de opções
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
            
            # Preparando mensagem de boas-vindas personalizada
            if is_returning_user:
                # Calculando o tempo desde a última interação
                last_interaction = datetime.fromisoformat(user_info["last_interaction"])
                now = datetime.now()
                days_since_last = (now - last_interaction).days
                
                # Personalizando saudação com base no tempo passado
                if days_since_last == 0:
                    # Mesmo dia
                    greeting = f"Olá novamente, {user.first_name}! 👋 Que bom te ver de volta tão rápido."
                elif days_since_last == 1:
                    # Dia seguinte
                    greeting = f"Olá, {user.first_name}! 👋 Bom te ver novamente depois de ontem."
                elif days_since_last < 7:
                    # Menos de uma semana
                    greeting = f"Olá, {user.first_name}! 👋 Bom te ver de volta depois de alguns dias."
                elif days_since_last < 30:
                    # Menos de um mês
                    greeting = f"Que bom te ver novamente, {user.first_name}! 👋 Faz algumas semanas desde nossa última conversa."
                else:
                    # Muito tempo
                    greeting = f"Nossa, {user.first_name}! 👋 Quanto tempo! Que bom que você voltou."
                
                # Adicionando referência a tópicos anteriores se existirem
                if user_info.get("topics"):
                    topics = user_info["topics"][:2]  # Pegando até 2 tópicos
                    topics_text = ", ".join(topics)
                    welcome_message = (
                        f"{greeting}\n\n"
                        f"Da última vez conversamos sobre {topics_text}. Como posso te ajudar hoje? "
                        f"Escolha uma das opções abaixo ou me faça uma pergunta direta."
                    )
                else:
                    welcome_message = (
                        f"{greeting}\n\n"
                        f"Como posso te ajudar hoje? Escolha uma das opções abaixo ou me faça uma pergunta direta."
                    )
            else:
                # Novo usuário - mensagem padrão
                welcome_message = (
                    f"Olá, {user.first_name}! 👋\n\n"
                    "Sou Paulo, consultor financeiro com mais de 15 anos de experiência no mercado. "
                    "Estou aqui para ajudar com suas dúvidas sobre investimentos, planejamento financeiro e economia.\n\n"
                    "Como posso auxiliar você hoje? Escolha uma opção abaixo ou me faça uma pergunta direta sobre qualquer tema financeiro."
                )
            if not is_returning_user and random.random() < 0.7:
                await update.message.chat.send_action(action="typing")
                await asyncio.sleep(random.uniform(1.2, 2.0))
                
                follow_up_tips = (
                    "💡 Dica: Você pode me perguntar sobre praticamente qualquer assunto financeiro, como:\n\n"
                    "• \"Qual a melhor forma de começar a investir?\"\n"
                    "• \"Como montar uma reserva de emergência?\"\n"
                    "• \"O que é melhor: Tesouro Direto ou CDB?\"\n"
                    "• \"Como funciona o mercado de ações?\""
                )
                
                await update.message.reply_text(follow_up_tips)
            
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
            
            # Detectando a personalidade apropriada com base na mensagem
            personality_type = self.personality_manager.select_appropriate_personality(message)
            
            # Detectando sentimento da mensagem
            sentiment = self.text_analyzer.analyze_sentiment(message)
            
            # Calculando probabilidade de enviar reconhecimento com base no sentimento
            acknowledge_chance = self.variation_settings["acknowledge_message_chance"]
            if sentiment in ["positivo", "muito_positivo"]:
                acknowledge_chance += 0.1  # Aumenta chances para mensagens positivas
            elif len(message) < 10:
                acknowledge_chance += 0.15  # Aumenta chances para mensagens curtas
            
            # Enviando reconhecimento de recebimento ocasionalmente
            if random.random() < acknowledge_chance:
                # Escolhendo um reconhecimento apropriado com base no sentimento
                if sentiment in ["positivo", "muito_positivo"]:
                    ack_options = ["👍", "Beleza", "Certo", "Sim"] 
                elif sentiment in ["negativo", "muito_negativo"]:
                    ack_options = ["Entendi", "Compreendo", "Ok"]
                else:
                    ack_options = self.message_acknowledgments
                
                await update.message.reply_text(random.choice(ack_options))
                
                # Adicionando uma pausa natural após o reconhecimento
                await asyncio.sleep(random.uniform(0.5, 1.2))
            
            # Pausa breve e realista antes de mostrar o indicador de "digitando"
            await asyncio.sleep(random.uniform(*self.variation_settings["typing_indicator_delay_range"]))
            
            # Enviando mensagem de "pensando" ocasionalmente (apenas 50% das vezes)
            thinking_message = None
            if random.random() < self.variation_settings["thinking_message_chance"]:
                # Usando variações de pensamento baseadas na personalidade
                thinking_messages = self.thinking_variations.get(
                    personality_type, self.thinking_variations["default"]
                )
                thinking_text = random.choice(thinking_messages) if thinking_messages else random.choice(self.typing_messages)
                thinking_message = await update.message.reply_text(thinking_text)

            # Enviando mensagem de "digitando..."
            await update.message.chat.send_action(action="typing")
            
            # Analisando complexidade da pergunta
            question_complexity = self.text_analyzer.detect_question_complexity(message)
            
            # Calculando tempo de digitação realista baseado na complexidade
            # 1. Primeiro, determinamos a "velocidade de digitação" desta personalidade
            if personality_type == "technical":
                typing_speed_range = self.human_typing_speeds["rápido"]  # Especialistas técnicos digitam mais rápido
            elif personality_type == "friendly":
                typing_speed_range = self.human_typing_speeds["médio"]  # Pessoas amigáveis digitam em velocidade média
            else:
                typing_speed_range = random.choice([
                    self.human_typing_speeds["médio"], 
                    self.human_typing_speeds["rápido"]
                ])  # Outras personalidades variam
            
            # 2. Estimando o tamanho da resposta com base na complexidade da pergunta
            if question_complexity == "complexo":
                estimated_response_length = random.randint(1000, 1500)  # Caracteres estimados
            elif question_complexity == "médio":
                estimated_response_length = random.randint(400, 800)
            else:
                estimated_response_length = random.randint(100, 300)
            
            # 3. Calculando tempo de digitação natural em segundos
            typing_speed = random.uniform(*typing_speed_range)  # Caracteres por minuto
            typing_time_minutes = estimated_response_length / typing_speed
            typing_time_seconds = typing_time_minutes * 60
            
            # 4. Adicionando variabilidade e limitando valores extremos
            typing_time_seconds = min(max(typing_time_seconds * random.uniform(0.7, 1.1), 1.5), 6.0)
            
            # Ajustando para perguntas que precisam de "reflexão"
            if "explique" in message.lower() or "detalhe" in message.lower() or "como" in message.lower():
                typing_time_seconds += random.uniform(0.5, 1.5)  # Tempo adicional para "pensar"
            
            # Aplicando o tempo de digitação calculado
            await asyncio.sleep(typing_time_seconds)
            
            # Removendo a mensagem de "estou pensando" se existir
            if thinking_message:
                await thinking_message.delete()
            
            # Verificando se é uma solicitação de busca na web
            search_keywords = ["atual", "hoje", "recente", "notícia", "mercado", "taxa", "cotação", "preço", 
                             "inflação", "selic", "dólar", "euro", "bolsa", "tendência", "projeção", "previsão"]
            
            # Verificando se é uma solicitação de busca na web
            search_web = any(keyword in message.lower() for keyword in search_keywords)
            
            # Ajustando o contexto baseado na complexidade da pergunta
            context_data = None
            if question_complexity == "complexo":
                context_data = "O usuário está solicitando uma explicação detalhada e abrangente. Forneça uma resposta completa com exemplos práticos quando possível."
            
            # Gerando resposta
            response = await self.advisor.generate_response(message, user.id, context_data=context_data, search_web=search_web)
            
            # Pequena pausa adicional para humanizar a resposta
            await asyncio.sleep(random.uniform(*self.variation_settings["response_delay_range"]))
            
            # Dividindo respostas longas para não exceder limites do Telegram
            if len(response) > 4096:
                chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(chunk, parse_mode='Markdown')
                    
                    # Se não for o último chunk, simular digitação entre chunks
                    if i < len(chunks) - 1:
                        await asyncio.sleep(random.uniform(0.5, 1.2))  # Pausa natural entre chunks
                        await update.message.chat.send_action(action="typing")
                        await asyncio.sleep(random.uniform(0.8, 1.5))
            else:
                    await update.message.reply_text(response, parse_mode='Markdown')
            
            # Adicionando follow-up ocasionalmente com probabilidade adaptativa
            message_length = len(response)
            follow_up_chance = self.variation_settings["follow_up_chance"]
            
            # Aumentando a chance para respostas longas ou complexas
            if message_length > 500 or question_complexity == "complexo":
                follow_up_chance += 0.2
            
            # Diminuindo a chance para mensagens que parecem conclusivas
            if any(term in response.lower() for term in ["espero ter ajudado", "mais alguma dúvida", "qualquer dúvida"]):
                follow_up_chance -= 0.15
            
            # Aumentando chance para tópicos que geralmente precisam de acompanhamento
            topics = self.text_analyzer.extract_topics(message)
            if any(topic in ["investimentos", "planejamento", "aposentadoria"] for topic in topics):
                follow_up_chance += 0.1
            
            # Aplicando a probabilidade de follow-up
            if random.random() < follow_up_chance:
                # Pausa mais longa e natural antes do follow-up
                await asyncio.sleep(random.uniform(1.0, 2.0))
                await update.message.chat.send_action(action="typing")
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
                # Selecionando follow-up apropriado para a personalidade e complexidade
                if question_complexity == "complexo":
                    detailed_followups = [
                        "Gostaria que eu explorasse algum desses pontos em mais detalhes?",
                        "Tem alguma parte específica que você quer que eu aprofunde?",
                        "Isso atendeu ao nível de detalhe que você precisava?",
                        "Quer que eu dê exemplos práticos de algum desses pontos?"
                    ]
                    follow_up = random.choice(detailed_followups)
                else:
                    # Usando variações de follow-up baseadas na personalidade
                    follow_up_options = self.follow_up_variations.get(
                        personality_type, self.follow_up_variations["default"]
                    )
                    follow_up = random.choice(follow_up_options if follow_up_options else self.follow_up_questions)
                
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
                # Pausa natural antes de responder
                await asyncio.sleep(random.uniform(0.3, 0.7))
                await query.message.chat.send_action(action="typing")
                await asyncio.sleep(random.uniform(0.7, 1.2))
                
                web_search_prompts = [
                    "Sobre o que você quer pesquisar?",
                    "O que você gostaria de saber?",
                    "Qual assunto financeiro você quer que eu pesquise?",
                    "Pode me dizer o que você quer saber?"
                ]
                
                await query.message.reply_text(random.choice(web_search_prompts))
                context.user_data['awaiting_search_query'] = True
                return WAITING_RESPONSE
            
            # Enviando "digitando..." com uma pausa natural
            await asyncio.sleep(random.uniform(0.2, 0.5))
            await query.message.chat.send_action(action="typing")
            
            # Selecionando uma personalidade apropriada para o tópico
            personality_type = "default"
            if query.data in ['variable_income', 'market_analysis', 'crypto']:
                personality_type = "technical"  # Tópicos mais técnicos
            elif query.data in ['planning', 'help']:
                personality_type = "mentor"     # Tópicos de planejamento/educação
            elif query.data in ['investments']:
                personality_type = "friendly"   # Tópicos para iniciantes
            
            # Obtendo a personalidade
            personality = self.personality_manager.get_personality(personality_type)
            
            # Escolhendo uma mensagem de "pensando" baseada na personalidade
            if random.random() < 0.4:  # 40% de chance
                thinking_messages = self.thinking_variations.get(
                    personality_type, self.thinking_variations["default"]
                )
                thinking_message = await query.message.reply_text(
                    random.choice(thinking_messages) if thinking_messages else random.choice(self.typing_messages)
                )
            else:
                thinking_message = None
            
            # Calculando tempo de digitação baseado no tópico e personalidade
            # Tópicos mais complexos requerem "mais tempo para pensar"
            if query.data in ['variable_income', 'market_analysis', 'crypto', 'funds']:
                # Tópicos complexos
                typing_time = random.uniform(2.5, 4.0)
            elif query.data in ['planning', 'fixed_income']:
                # Tópicos médios
                typing_time = random.uniform(1.8, 3.0)
            else:
                # Tópicos simples
                typing_time = random.uniform(1.2, 2.2)
            
            await asyncio.sleep(typing_time)
            
            # Removendo mensagem de "pensando" se existir
            if thinking_message:
                await thinking_message.delete()

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
                
                # Gerando resposta com a personalidade adequada
                response = await self.advisor.generate_response(
                    prompts[query.data], 
                    user.id, 
                    context_data=context_data, 
                    search_web=search_web
                )
                
                # Se a resposta for muito longa, dividir
                if len(response) > 4096:
                    chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
                    for i, chunk in enumerate(chunks):
                        await query.message.reply_text(chunk, parse_mode='Markdown')
                        # Se não for o último chunk, simular digitação entre chunks
                        if i < len(chunks) - 1:
                            await asyncio.sleep(random.uniform(0.5, 0.8))
                            await query.message.chat.send_action(action="typing")
                            await asyncio.sleep(random.uniform(0.8, 1.2))
                else:
                    await query.message.reply_text(response, parse_mode='Markdown')
                
                # Adicionando follow-up ocasionalmente
                if random.random() < 0.25:  # 25% de chance
                    await asyncio.sleep(random.uniform(1.0, 1.5))
                    await query.message.chat.send_action(action="typing")
                    await asyncio.sleep(random.uniform(0.5, 0.8))
                    
                    follow_up_options = self.follow_up_variations.get(
                        personality_type, self.follow_up_variations["default"]
                    )
                    follow_up = random.choice(follow_up_options if follow_up_options else self.follow_up_questions)
                    
                    await query.message.reply_text(follow_up)
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
            # Variações de mensagens para indicar que estamos pesquisando
            searching_messages = [
                "Pesquisando...",
                "Procurando informações...",
                "Buscando dados atualizados...",
                "Consultando fontes confiáveis...",
                "Coletando informações recentes..."
            ]
            
            # Enviando mensagem de "pesquisando" após uma pequena pausa
            await asyncio.sleep(random.uniform(0.3, 0.7))
            search_message = await update.message.reply_text(random.choice(searching_messages))
            
            # Enviando mensagem de "digitando..."
            await update.message.chat.send_action(action="typing")
            
            # Realizando a pesquisa
            search_query = f"finanças {query} brasil atual"
            results = await GoogleSearch.search_google(search_query)
            
            # Simulando o tempo de pesquisa
            await asyncio.sleep(random.uniform(1.5, 3.0))
            
            # Removendo a mensagem de "pesquisando"
            await search_message.delete()
            
            # Enviando "digitando..." novamente para indicar que estamos processando os resultados
            await update.message.chat.send_action(action="typing")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            if results:
                # Gerando resposta com base nos resultados da pesquisa
                context_data = GoogleSearch.format_search_results(results)
                
                # Usando uma personalidade mais técnica para respostas baseadas em pesquisas
                response = await self.advisor.generate_response(
                    f"Com base nas informações recentes sobre '{query}'", 
                    user.id, 
                    context_data=context_data,
                    search_web=False  # Já fizemos a pesquisa manualmente
                )
                
                # Dividindo respostas longas
                if len(response) > 4096:
                    chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
                    for i, chunk in enumerate(chunks):
                        await update.message.reply_text(chunk, parse_mode='Markdown')
                        # Se não for o último chunk, simular digitação entre chunks
                        if i < len(chunks) - 1:
                            await asyncio.sleep(random.uniform(0.5, 0.8))
                            await update.message.chat.send_action(action="typing")
                            await asyncio.sleep(random.uniform(0.8, 1.2))
                else:
                    await update.message.reply_text(response, parse_mode='Markdown')
                
                # Adicionando ocasionalmente uma pergunta sobre a utilidade da pesquisa
                if random.random() < 0.3:
                    utility_questions = [
                        "Essas informações foram úteis?",
                        "Isso responde à sua pergunta?",
                        "Gostaria de saber mais algum detalhe específico?",
                        "Há algo específico desses dados que você gostaria de entender melhor?"
                    ]
                    
                    await asyncio.sleep(random.uniform(1.0, 1.5))
                    await update.message.chat.send_action(action="typing")
                    await asyncio.sleep(random.uniform(0.5, 0.8))
                    
                    await update.message.reply_text(random.choice(utility_questions))
            else:
                no_results_responses = [
                    "Não encontrei informações específicas sobre isso. Pode tentar reformular sua pergunta?",
                    "Parece que não consegui encontrar dados confiáveis sobre esse tema. Poderia detalhar melhor o que está procurando?",
                    "Não achei informações recentes sobre isso. Talvez possamos abordar o assunto de outra forma?",
                    "Não encontrei resultados satisfatórios. Poderia tentar com outras palavras-chave?"
                ]
                
                await update.message.reply_text(random.choice(no_results_responses))
            
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
        # Verificar se o bot já está em execução
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Tenta vincular a uma porta específica
        try:
            s.bind(('localhost', 12345))
        except socket.error:
            logger.critical("Outra instância do bot já está em execução!")
            sys.exit(1)
            
        if not TOKEN:
            raise ValueError("Token do Telegram não encontrado no arquivo .env!")
        
        if not OPENAI_API_KEY:
            raise ValueError("API Key da OpenAI não encontrada no arquivo .env!")
        
        # Inicializando modelos de NLP necessários
        def init_models():
            """Inicializa e baixa os modelos necessários para NLP"""
            try:
                logger.info("Verificando e baixando recursos NLTK necessários...")
                try:
                    nltk.data.find('vader_lexicon')
                    logger.info("Recursos NLTK já estão disponíveis")
                except LookupError:
                    logger.info("Baixando vader_lexicon para análise de sentimento...")
                    nltk.download('vader_lexicon', quiet=True)
                
                logger.info("Verificando modelo spaCy...")
                try:
                    if not spacy.util.is_package("pt_core_news_sm"):
                        logger.info("Modelo spaCy em português não encontrado. Tentando baixar...")
                        os.system("python -m spacy download pt_core_news_sm")
                    else:
                        logger.info("Modelo spaCy em português já está disponível")
                except Exception as e:
                    logger.warning(f"Não foi possível verificar ou baixar o modelo spaCy: {str(e)}")
                    logger.info("Tentando usar modelo em inglês como fallback")
                    try:
                        if not spacy.util.is_package("en_core_web_sm"):
                            logger.info("Modelo spaCy em inglês não encontrado. Tentando baixar...")
                            os.system("python -m spacy download en_core_web_sm")
                    except Exception as e:
                        logger.error(f"Não foi possível baixar nenhum modelo spaCy: {str(e)}")
                        logger.warning("Algumas funcionalidades de NLP estarão limitadas")
                
                logger.info("Inicialização de modelos NLP concluída")
            except Exception as e:
                logger.error(f"Erro ao inicializar modelos NLP: {str(e)}")
                logger.warning("O bot funcionará com capacidades de NLP limitadas")
        
        # Inicializando modelos NLP
        init_models()
        
        logger.info("Iniciando bot...")
        bot = TelegramBot()
        bot.run()
        
    except Exception as e:
        logger.critical(f"Erro crítico: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        sys.exit(1) 