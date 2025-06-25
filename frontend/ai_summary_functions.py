"""
Funções para resumo de reviews usando OpenAI
Código simples para POC - sem orientação a objetos
Autor: André Rizzo
"""

import os

# Importar funções de consulta
from poc_queries import (
    search_books_for_summary,
    get_book_info,
    get_all_reviews_for_book
)

# Tentar importar OpenAI
try:
    from openai import OpenAI
    from dotenv import load_dotenv
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def setup_openai():
    """Configura cliente OpenAI."""
    if not OPENAI_AVAILABLE:
        return None, "OpenAI não instalado. Execute: pip install openai python-dotenv"
    
    try:
        load_dotenv(override=True)
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return None, "OPENAI_API_KEY não encontrada. Crie arquivo .env com sua chave"
        
        client = OpenAI(api_key=api_key)
        return client, "OpenAI configurado com sucesso"
        
    except Exception as e:
        return None, f"Erro ao configurar OpenAI: {e}"


def test_openai_connection():
    """Testa conexão com OpenAI."""
    client, message = setup_openai()
    
    if not client:
        return False, message
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Responda apenas 'OK'"}],
            max_tokens=5,
            temperature=0
        )
        
        if "OK" in response.choices[0].message.content:
            return True, "Conexão OpenAI funcionando"
        else:
            return False, "Resposta inesperada da OpenAI"
            
    except Exception as e:
        return False, f"Erro na conexão: {e}"


def create_summary_prompt(reviews, sentiment_type):
    """Cria prompt para resumir reviews."""
    
    if not reviews:
        return None
    
    # Limitar a 8 reviews e 200 caracteres cada para não sobrecarregar a API
    reviews_sample = reviews[:8]
    reviews_text = "\n\n".join([f"- {review[:200]}..." for review in reviews_sample])
    
    if sentiment_type == "positivo":
        prompt = f"""
Analise os seguintes reviews POSITIVOS de um livro e crie um resumo executivo:

{reviews_text}

Por favor, forneça:
1. Um resumo de 2-3 frases dos principais pontos positivos mencionados
2. Os 3 aspectos mais elogiados pelos leitores
3. Uma recomendação de 1 frase sobre o público-alvo ideal

Mantenha o resumo conciso e focado nos pontos de negócio mais relevantes.
"""
    
    elif sentiment_type == "negativo":
        prompt = f"""
Analise os seguintes reviews NEGATIVOS de um livro e crie um resumo executivo:

{reviews_text}

Por favor, forneça:
1. Um resumo de 2-3 frases dos principais problemas mencionados
2. Os 3 aspectos mais criticados pelos leitores
3. Uma recomendação de 1 frase sobre melhorias necessárias

Mantenha o resumo conciso e focado nos pontos de negócio mais relevantes.
"""
    
    else:  # neutro
        prompt = f"""
Analise os seguintes reviews NEUTROS de um livro e crie um resumo executivo:

{reviews_text}

Por favor, forneça:
1. Um resumo de 2-3 frases das opiniões equilibradas mencionadas
2. Os 3 aspectos mais comentados (nem muito positivos nem negativos)
3. Uma observação de 1 frase sobre o perfil destes leitores

Mantenha o resumo conciso e focado nos pontos de negócio mais relevantes.
"""
    
    return prompt


def generate_summary_with_openai(reviews, sentiment_type):
    """Gera resumo usando OpenAI."""
    
    client, message = setup_openai()
    if not client:
        return None, message
    
    prompt = create_summary_prompt(reviews, sentiment_type)
    if not prompt:
        return None, f"Nenhum review {sentiment_type} disponível para análise"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um analista de negócios especializado em análise de reviews de livros. Seja conciso e focado em insights acionáveis."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        return summary, "Resumo gerado com sucesso"
        
    except Exception as e:
        return None, f"Erro ao gerar resumo: {e}"


def run_book_summary_analysis(book_title, db_path="books_database.db"):
    """
    Executa análise completa de um livro com resumos de IA.
    
    Returns:
        dict: Contém info do livro, reviews e resumos
    """
    
    # Obter informações do livro
    book_info = get_book_info(book_title, db_path)
    if not book_info:
        return None, f"Livro '{book_title}' não encontrado"
    
    # Obter reviews organizados
    reviews_data = get_all_reviews_for_book(book_title, db_path)
    
    # Gerar resumos com IA
    summaries = {}
    
    for sentiment_type, reviews in reviews_data.items():
        if reviews:  # Se há reviews deste tipo
            summary, message = generate_summary_with_openai(reviews, sentiment_type.rstrip('s'))  # Remove 's' do plural
            summaries[sentiment_type] = {
                'summary': summary,
                'status': 'success' if summary else 'error',
                'message': message,
                'total_reviews': len(reviews)
            }
        else:
            summaries[sentiment_type] = {
                'summary': None,
                'status': 'no_data',
                'message': f'Nenhum review {sentiment_type} encontrado',
                'total_reviews': 0
            }
    
    # Gerar insights gerais
    general_insights = generate_general_insights(book_info, summaries)
    
    result = {
        'book_info': book_info,
        'reviews_data': reviews_data,
        'summaries': summaries,
        'general_insights': general_insights,
        'analysis_status': 'completed'
    }
    
    return result, "Análise concluída com sucesso"


def generate_general_insights(book_info, summaries):
    """Gera insights gerais baseados nos resumos."""
    
    insights = {
        'total_reviews': book_info.get('total_reviews', 0),
        'sentiment_score': book_info.get('sentimento_medio', 0),
        'positive_rate': (book_info.get('total_positivos', 0) / book_info.get('total_reviews', 1)) * 100,
        'negative_rate': (book_info.get('total_negativos', 0) / book_info.get('total_reviews', 1)) * 100,
        'recommendation': '',
        'business_priority': ''
    }
    
    # Determinar recomendação de negócio
    sentiment_score = insights['sentiment_score']
    positive_rate = insights['positive_rate']
    total_reviews = insights['total_reviews']
    
    if sentiment_score > 0.3 and positive_rate > 70:
        insights['recommendation'] = "✅ PROMOVER - Livro com excelente recepção"
        insights['business_priority'] = "Alta"
    elif sentiment_score > 0.1 and positive_rate > 60:
        insights['recommendation'] = "🔄 MANTER - Desempenho satisfatório"
        insights['business_priority'] = "Média"
    elif sentiment_score < -0.1 or positive_rate < 40:
        insights['recommendation'] = "⚠️ REVISAR - Problemas de qualidade identificados"
        insights['business_priority'] = "Alta"
    else:
        insights['recommendation'] = "📊 MONITORAR - Desempenho neutro"
        insights['business_priority'] = "Baixa"
    
    # Adicionar contexto de volume
    if total_reviews < 10:
        insights['recommendation'] += " (Poucos reviews - dados limitados)"
    elif total_reviews > 100:
        insights['recommendation'] += " (Alto volume - dados confiáveis)"
    
    return insights


def format_summary_for_display(summary_result):
    """Formata resultado do resumo para exibição no Streamlit."""
    
    if not summary_result:
        return None
    
    result, message = summary_result
    if not result:
        return {"error": message}
    
    # Formatar para exibição
    formatted = {
        'book_info': result['book_info'],
        'general_insights': result['general_insights'],
        'summaries': {},
        'status': 'success'
    }
    
    # Formatar cada tipo de resumo
    for sentiment_type, data in result['summaries'].items():
        formatted['summaries'][sentiment_type] = {
            'has_data': data['status'] == 'success',
            'summary': data['summary'],
            'total_reviews': data['total_reviews'],
            'message': data['message']
        }
    
    return formatted


def get_available_books_for_analysis(query="", limit=20, db_path="books_database.db"):
    """
    Busca livros disponíveis para análise de IA.
    
    Args:
        query: Termo de busca (título ou autor)
        limit: Número máximo de resultados
        db_path: Caminho do banco
    
    Returns:
        Lista de livros disponíveis
    """
    
    if query.strip():
        # Busca específica
        books = search_books_for_summary(query, limit, db_path)
    else:
        # Busca geral - livros com mais reviews
        from poc_queries import execute_query
        
        query_sql = """
        SELECT DISTINCT
            b.Title_padrao as titulo,
            b.authors_padrao as autor,
            b.categories_padrao as categoria,
            COUNT(r.sentimento) as total_reviews,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) as positivos,
            SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) as negativos,
            ROUND(AVG(r.compound), 3) as sentimento_medio
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        GROUP BY b.Title_padrao, b.authors_padrao, b.categories_padrao
        HAVING total_reviews >= 10  -- Mínimo para análise de IA
        ORDER BY total_reviews DESC
        LIMIT ?
        """
        
        books = execute_query(query_sql, db_path, (limit,))
    
    return books


# Função de teste para verificar se tudo está funcionando
def test_ai_functions():
    """Testa as funções de IA."""
    
    print("=== TESTE DAS FUNÇÕES DE IA ===")
    
    # Teste 1: Conexão OpenAI
    print("1. Testando conexão OpenAI...")
    is_connected, message = test_openai_connection()
    print(f"   Resultado: {message}")
    
    if not is_connected:
        print("   ❌ Não é possível testar resumos sem OpenAI")
        return False
    
    # Teste 2: Busca de livros
    print("\n2. Testando busca de livros...")
    try:
        books = get_available_books_for_analysis("Harry Potter", 3)
        print(f"   Encontrados: {len(books)} livros")
        
        if not books.empty:
            first_book = books.iloc[0]['titulo']
            print(f"   Primeiro livro: {first_book}")
            
            # Teste 3: Análise completa
            print(f"\n3. Testando análise do livro: {first_book}")
            result, msg = run_book_summary_analysis(first_book)
            
            if result:
                print("   ✅ Análise concluída com sucesso!")
                print(f"   Total de reviews: {result['book_info'].get('total_reviews', 0)}")
                print(f"   Sentimento médio: {result['book_info'].get('sentimento_medio', 0):.3f}")
                
                for sentiment, data in result['summaries'].items():
                    print(f"   {sentiment.capitalize()}: {data['status']} ({data['total_reviews']} reviews)")
                
                return True
            else:
                print(f"   ❌ Erro na análise: {msg}")
                return False
        else:
            print("   ⚠️ Nenhum livro encontrado para teste")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro no teste: {e}")
        return False


if __name__ == "__main__":
    # Executar teste das funções
    test_ai_functions()
