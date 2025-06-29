"""
Consultas SQL específicas para a POC
Análises de negócio para tomada de decisão
Adicionado: Funções para busca de livros e reviews para resumo IA
"""

import sqlite3
import pandas as pd
import os
from pathlib import Path


def execute_query(query: str, db_path: str = "books_database.db", params: tuple = ()) -> pd.DataFrame:
    """
    Executa consulta e retorna DataFrame.
    
    Args:
        query (str): Consulta SQL
        db_path (str): Caminho para o banco de dados
        params (tuple): Parâmetros da consulta
    
    Returns:
        pd.DataFrame: Resultado da consulta
    """
    # Verificar se banco existe
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Banco de dados não encontrado: {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        print(f"Erro na consulta: {e}")
        print(f"Query: {query[:200]}...")
        raise


# =================
# 1. LIVROS MAIS PROBLEMÁTICOS
# =================

def get_problematic_books(limit: int = 20, db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Identifica livros mais problemáticos baseado em:
    - Alto percentual de reviews negativos
    - Discrepância entre rating e sentimento
    - Baixo compound score médio
    """
    query = """
    WITH book_metrics AS (
        SELECT 
            b.Title_padrao as titulo,
            b.authors_padrao as autor,
            b.categories_padrao as categoria,
            COUNT(r.sentimento) as total_reviews,
            
            -- Métricas de sentimento
            SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) as reviews_negativos,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) as reviews_positivos,
            AVG(r.compound) as compound_medio,
            
            -- Percentuais
            ROUND((SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)), 1) as pct_negativo,
            
            -- Score de problema (quanto maior, mais problemático)
            (
                (SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.6 +  
                (CASE WHEN AVG(r.compound) < 0 THEN ABS(AVG(r.compound)) * 100 ELSE 0 END) * 0.4  
            ) as problema_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        GROUP BY b.Title_padrao, b.authors_padrao, b.categories_padrao
        HAVING total_reviews >= 5  -- Mínimo 5 reviews para ser considerado
    )
    
    SELECT 
        titulo,
        autor,
        categoria,
        total_reviews,
        reviews_negativos,
        pct_negativo,
        ROUND(compound_medio, 3) as compound_medio,
        ROUND(problema_score, 1) as problema_score
    FROM book_metrics
    ORDER BY problema_score DESC
    LIMIT ?
    """
    
    return execute_query(query, db_path, (limit,))


# =================
# 2. USUÁRIOS PARA ENTREVISTA
# =================

def get_users_for_interview(limit: int = 50, db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Lista usuários segmentados para entrevista baseado em:
    - Volume de reviews
    - Diversidade de sentimentos
    - Atividade em categorias diferentes
    """
    query = """
    WITH user_metrics AS (
        SELECT 
            User_id,
            COUNT(*) as total_reviews,
            COUNT(DISTINCT sentimento) as sentimentos_diversos,
            COUNT(DISTINCT 
                CASE WHEN b.categories_padrao IS NOT NULL AND b.categories_padrao != ''
                THEN substr(b.categories_padrao, 1, 
                    CASE WHEN instr(b.categories_padrao, ',') > 0 
                    THEN instr(b.categories_padrao, ',') - 1
                    ELSE length(b.categories_padrao)
                    END)
                END
            ) as categorias_diversas,
            
            -- Distribuição de sentimentos
            SUM(CASE WHEN sentimento = 'positivo' THEN 1 ELSE 0 END) as reviews_positivos,
            SUM(CASE WHEN sentimento = 'negativo' THEN 1 ELSE 0 END) as reviews_negativos,
            SUM(CASE WHEN sentimento = 'neutro' THEN 1 ELSE 0 END) as reviews_neutros,
            
            AVG(compound) as compound_medio,
            
            -- Score de diversidade (usuário interessante para entrevista)
            (
                (COUNT(*) * 0.3) +  -- Volume de reviews
                (COUNT(DISTINCT sentimento) * 10) +  -- Diversidade de sentimentos
                (COUNT(DISTINCT 
                    CASE WHEN b.categories_padrao IS NOT NULL AND b.categories_padrao != ''
                    THEN substr(b.categories_padrao, 1, 
                        CASE WHEN instr(b.categories_padrao, ',') > 0 
                        THEN instr(b.categories_padrao, ',') - 1
                        ELSE length(b.categories_padrao)
                        END)
                    END) * 5)  -- Diversidade de categorias
            ) as diversidade_score,
            
            -- Segmento do usuário
            CASE 
                WHEN AVG(compound) > 0.3 THEN 'Otimista'
                WHEN AVG(compound) < -0.1 THEN 'Crítico'
                WHEN COUNT(DISTINCT sentimento) >= 3 THEN 'Equilibrado'
                WHEN COUNT(*) > 20 THEN 'Ativo'
                ELSE 'Regular'
            END as segmento
            
        FROM books_rating_modified r
        LEFT JOIN books_data_processed b ON r.Title = b.Title_padrao
        WHERE User_id IS NOT NULL AND sentimento IS NOT NULL
        GROUP BY User_id
        HAVING total_reviews >= 3  -- Mínimo 3 reviews
    )
    
    SELECT 
        User_id,
        segmento,
        total_reviews,
        sentimentos_diversos,
        categorias_diversas,
        reviews_positivos,
        reviews_negativos,
        reviews_neutros,
        ROUND(compound_medio, 3) as compound_medio,
        ROUND(diversidade_score, 1) as diversidade_score
    FROM user_metrics
    ORDER BY diversidade_score DESC, total_reviews DESC
    LIMIT ?
    """
    
    return execute_query(query, db_path, (limit,))


# =================
# 3. ROI POR CATEGORIA/AUTOR
# =================

def get_roi_by_category(db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Calcula ROI estimado por categoria baseado em:
    - Volume de livros
    - Sentimento médio dos reviews
    - Engajamento (número de reviews)
    """
    query = """
    WITH category_metrics AS (
        SELECT 
            TRIM(substr(b.categories_padrao, 1, 
                CASE WHEN instr(b.categories_padrao, ',') > 0 
                THEN instr(b.categories_padrao, ',') - 1
                ELSE length(b.categories_padrao)
                END)) as categoria_principal,
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            
            -- Engajamento médio por livro
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 2) as reviews_por_livro,
            
            -- Score de qualidade (sentimento positivo)
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            
            -- ROI estimado (fórmula hipotética)
            -- ROI = (Engajamento * Qualidade * Volume) / 100
            ROUND(
                (COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao)) *  -- Engajamento
                (AVG(r.compound) + 1) *  -- Qualidade normalizada (0-2)
                LOG(COUNT(DISTINCT b.Title_padrao) + 1) /  -- Volume (log para suavizar)
                10, 2
            ) as roi_estimado
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE b.categories_padrao IS NOT NULL 
        AND b.categories_padrao != ''
        AND r.sentimento IS NOT NULL
        GROUP BY categoria_principal
        HAVING total_livros >= 5  -- Mínimo 5 livros na categoria
        AND categoria_principal IS NOT NULL
        AND categoria_principal != ''
    )
    
    SELECT 
        categoria_principal as categoria,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_positivo, 1) as pct_positivo,
        roi_estimado
    FROM category_metrics
    ORDER BY roi_estimado DESC
    LIMIT 20
    """
    
    return execute_query(query, db_path)


def get_roi_by_author(limit: int = 20, db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Calcula ROI estimado por autor baseado em métricas similares.
    """
    query = """
    WITH author_metrics AS (
        SELECT 
            b.authors_padrao as autor,
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            
            -- Engajamento médio por livro
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 2) as reviews_por_livro,
            
            -- Score de qualidade
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            
            -- ROI estimado
            ROUND(
                (COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao)) *  
                (AVG(r.compound) + 1) *  
                LOG(COUNT(DISTINCT b.Title_padrao) + 1) /  
                10, 2
            ) as roi_estimado
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE b.authors_padrao IS NOT NULL 
        AND b.authors_padrao != ''
        AND r.sentimento IS NOT NULL
        GROUP BY b.authors_padrao
        HAVING total_livros >= 2  -- Mínimo 2 livros do autor
    )
    
    SELECT 
        autor,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_positivo, 1) as pct_positivo,
        roi_estimado
    FROM author_metrics
    ORDER BY roi_estimado DESC
    LIMIT ?
    """
    
    return execute_query(query, db_path, (limit,))


# =================
# 4. DISCREPÂNCIAS SCORE VS SENTIMENTO
# =================

def get_sentiment_discrepancies(limit: int = 50, db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Detecta discrepâncias entre score compound e classificação de sentimento.
    Casos onde a classificação automática pode estar errada.
    """
    query = """
    WITH discrepancies AS (
        SELECT 
            Title as titulo,
            text as review_texto,
            sentimento as sentimento_classificado,
            ROUND(compound, 3) as compound_score,
            
            -- Sentimento esperado baseado no compound
            CASE 
                WHEN compound >= 0.05 THEN 'positivo'
                WHEN compound <= -0.05 THEN 'negativo'
                ELSE 'neutro'
            END as sentimento_esperado,
            
            -- Nível de discrepância
            CASE 
                -- Casos mais graves
                WHEN (compound >= 0.3 AND sentimento = 'negativo') OR 
                     (compound <= -0.3 AND sentimento = 'positivo') THEN 'Alto'
                -- Casos moderados
                WHEN (compound >= 0.1 AND sentimento = 'negativo') OR 
                     (compound <= -0.1 AND sentimento = 'positivo') OR
                     (ABS(compound) >= 0.3 AND sentimento = 'neutro') THEN 'Médio'
                -- Casos leves
                WHEN (compound >= 0.05 AND sentimento = 'neutro') OR 
                     (compound <= -0.05 AND sentimento = 'neutro') THEN 'Baixo'
                ELSE 'Sem discrepância'
            END as nivel_discrepancia,
            
            ABS(
                CASE sentimento
                    WHEN 'positivo' THEN compound - 0.5
                    WHEN 'negativo' THEN compound + 0.5  
                    WHEN 'neutro' THEN compound
                    ELSE 0
                END
            ) as score_discrepancia
            
        FROM books_rating_modified
        WHERE sentimento IS NOT NULL 
        AND compound IS NOT NULL
        AND text IS NOT NULL
        AND LENGTH(text) > 10  -- Reviews com texto mínimo
    )
    
    SELECT 
        titulo,
        substr(review_texto, 1, 200) as review_preview,
        sentimento_classificado,
        sentimento_esperado,
        compound_score,
        nivel_discrepancia,
        ROUND(score_discrepancia, 3) as score_discrepancia
    FROM discrepancies
    WHERE nivel_discrepancia != 'Sem discrepância'
    ORDER BY 
        CASE nivel_discrepancia
            WHEN 'Alto' THEN 1
            WHEN 'Médio' THEN 2
            WHEN 'Baixo' THEN 3
        END,
        score_discrepancia DESC
    LIMIT ?
    """
    
    return execute_query(query, db_path, (limit,))


# =================
# 6. ANÁLISE DE DESEMPENHO DE LIVROS
# =================

def get_best_worst_books(limit: int = 20, db_path: str = "books_database.db") -> dict:
   """
    Identifica livros com melhor e pior desempenho - SQLite compatible
    """
    
    # Query para melhores livros
    best_query = """
    WITH book_performance AS (
        SELECT 
            b.Title_padrao as titulo,
            b.authors_padrao as autor,
            b.categories_padrao as categoria,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            
            -- Score de performance (sem LOG)
            (
                (AVG(r.compound) + 1) * 50 +  -- Sentimento normalizado (0-100)
                (SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.3 +  -- % positivo
                (CASE 
                    WHEN COUNT(r.sentimento) <= 10 THEN 5
                    WHEN COUNT(r.sentimento) <= 50 THEN 15
                    WHEN COUNT(r.sentimento) <= 100 THEN 25
                    ELSE 35
                END)  -- Volume escalonado
            ) as performance_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        GROUP BY b.Title_padrao, b.authors_padrao, b.categories_padrao
        HAVING total_reviews >= 10  -- Mínimo 10 reviews
    )
    
    SELECT 
        titulo,
        autor,
        categoria,
        total_reviews,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_positivo, 1) as pct_positivo,
        ROUND(performance_score, 1) as performance_score
    FROM book_performance
    ORDER BY performance_score DESC
    LIMIT ?
    """
    
    # Query para piores livros
    worst_query = """
    WITH book_performance AS (
        SELECT 
            b.Title_padrao as titulo,
            b.authors_padrao as autor,
            b.categories_padrao as categoria,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_negativo,
            
            -- Score de problema (sem LOG)
            (
                (1 - AVG(r.compound)) * 50 +  -- Sentimento ruim normalizado
                (SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.5 +  -- % negativo
                (CASE 
                    WHEN COUNT(r.sentimento) <= 10 THEN 2
                    WHEN COUNT(r.sentimento) <= 50 THEN 6
                    WHEN COUNT(r.sentimento) <= 100 THEN 10
                    ELSE 14
                END)  -- Volume
            ) as problema_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        GROUP BY b.Title_padrao, b.authors_padrao, b.categories_padrao
        HAVING total_reviews >= 10
    )
    
    SELECT 
        titulo,
        autor,
        categoria,
        total_reviews,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_negativo, 1) as pct_negativo,
        ROUND(problema_score, 1) as problema_score
    FROM book_performance
    ORDER BY problema_score DESC
    LIMIT ?
    """
    
    best_books = execute_query(best_query, db_path, (limit,))
    worst_books = execute_query(worst_query, db_path, (limit,))
    
    return {
        'melhores': best_books,
        'piores': worst_books
    }



# =================
# 7. ANÁLISE DE DESEMPENHO DE EDITORAS
# =================

def get_best_worst_publishers(limit: int = 15, db_path: str = "books_database.db") -> dict:
    """
    Identifica editoras com melhor e pior desempenho - SQLite compatible
    """
    
    # Query para melhores editoras
    best_query = """
    WITH publisher_performance AS (
        SELECT 
            b.publisher_padrao as editora,
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro,
            
            -- Score de performance da editora (sem LOG)
            (
                (AVG(r.compound) + 1) * 40 +  -- Qualidade do sentimento
                (SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.4 +  -- % positivo
                (CASE 
                    WHEN COUNT(DISTINCT b.Title_padrao) <= 3 THEN 10
                    WHEN COUNT(DISTINCT b.Title_padrao) <= 10 THEN 20
                    WHEN COUNT(DISTINCT b.Title_padrao) <= 20 THEN 30
                    ELSE 40
                END) +  -- Volume de livros
                (CASE 
                    WHEN COUNT(r.sentimento) <= 20 THEN 5
                    WHEN COUNT(r.sentimento) <= 100 THEN 15
                    WHEN COUNT(r.sentimento) <= 500 THEN 25
                    ELSE 35
                END)  -- Engajamento
            ) as performance_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        AND b.publisher_padrao IS NOT NULL
        AND b.publisher_padrao != ''
        GROUP BY b.publisher_padrao
        HAVING total_livros >= 3  -- Mínimo 3 livros
        AND total_reviews >= 20   -- Mínimo 20 reviews
    )
    
    SELECT 
        editora,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_positivo, 1) as pct_positivo,
        ROUND(performance_score, 1) as performance_score
    FROM publisher_performance
    ORDER BY performance_score DESC
    LIMIT ?
    """
    
    # Query para piores editoras
    worst_query = """
    WITH publisher_performance AS (
        SELECT 
            b.publisher_padrao as editora,
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_negativo,
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro,
            
            -- Score de problema da editora (sem LOG)
            (
                (1 - AVG(r.compound)) * 40 +  -- Sentimento ruim
                (SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.6 +  -- % negativo
                (CASE 
                    WHEN COUNT(DISTINCT b.Title_padrao) <= 3 THEN 5
                    WHEN COUNT(DISTINCT b.Title_padrao) <= 10 THEN 10
                    WHEN COUNT(DISTINCT b.Title_padrao) <= 20 THEN 15
                    ELSE 20
                END)  -- Volume
            ) as problema_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        AND b.publisher_padrao IS NOT NULL
        AND b.publisher_padrao != ''
        GROUP BY b.publisher_padrao
        HAVING total_livros >= 3
        AND total_reviews >= 20
    )
    
    SELECT 
        editora,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_negativo, 1) as pct_negativo,
        ROUND(problema_score, 1) as problema_score
    FROM publisher_performance
    ORDER BY problema_score DESC
    LIMIT ?
    """
    
    best_publishers = execute_query(best_query, db_path, (limit,))
    worst_publishers = execute_query(worst_query, db_path, (limit,))
    
    return {
        'melhores': best_publishers,
        'piores': worst_publishers
    }


# =================
# 8. ANÁLISE DE DESEMPENHO POR TEMAS/CATEGORIAS
# =================

def get_best_worst_themes(limit: int = 15, db_path: str = "books_database.db") -> dict:
    """
    Identifica temas/categorias com melhor e pior desempenho.
    """
    
    # Query para melhores temas
    best_query = """
    WITH theme_performance AS (
        SELECT 
            TRIM(substr(b.categories_padrao, 1, 
                CASE WHEN instr(b.categories_padrao, ',') > 0 
                THEN instr(b.categories_padrao, ',') - 1
                ELSE length(b.categories_padrao)
                END)) as tema,
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro,
            
            -- Score de performance do tema
            (
                (AVG(r.compound) + 1) * 45 +  -- Qualidade
                (SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.3 +  -- % positivo
                LOG(COUNT(DISTINCT b.Title_padrao) + 1) * 8 +  -- Volume
                (COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao)) * 2  -- Engajamento
            ) as performance_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        AND b.categories_padrao IS NOT NULL
        AND b.categories_padrao != ''
        GROUP BY tema
        HAVING total_livros >= 5  -- Mínimo 5 livros
        AND total_reviews >= 30   -- Mínimo 30 reviews
        AND tema IS NOT NULL
        AND tema != ''
    )
    
    SELECT 
        tema,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_positivo, 1) as pct_positivo,
        ROUND(performance_score, 1) as performance_score
    FROM theme_performance
    ORDER BY performance_score DESC
    LIMIT ?
    """
    
    # Query para piores temas
    worst_query = """
    WITH theme_performance AS (
        SELECT 
            TRIM(substr(b.categories_padrao, 1, 
                CASE WHEN instr(b.categories_padrao, ',') > 0 
                THEN instr(b.categories_padrao, ',') - 1
                ELSE length(b.categories_padrao)
                END)) as tema,
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_negativo,
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro,
            
            -- Score de problema do tema
            (
                (1 - AVG(r.compound)) * 45 +  -- Sentimento ruim
                (SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento)) * 0.5 +  -- % negativo
                LOG(COUNT(DISTINCT b.Title_padrao) + 1) * 5  -- Volume
            ) as problema_score
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        AND b.categories_padrao IS NOT NULL
        AND b.categories_padrao != ''
        GROUP BY tema
        HAVING total_livros >= 5
        AND total_reviews >= 30
        AND tema IS NOT NULL
        AND tema != ''
    )
    
    SELECT 
        tema,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_negativo, 1) as pct_negativo,
        ROUND(problema_score, 1) as problema_score
    FROM theme_performance
    ORDER BY problema_score DESC
    LIMIT ?
    """
    
    best_themes = execute_query(best_query, db_path, (limit,))
    worst_themes = execute_query(worst_query, db_path, (limit,))
    
    return {
        'melhores': best_themes,
        'piores': worst_themes
    }


# =================
# 9. ANÁLISE TEMPORAL DE REVIEWS
# =================

def get_reviews_by_period(db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Analisa distribuição de reviews ao longo do tempo.
    """
    query = """
    WITH period_analysis AS (
        SELECT 
            b.publishedDate_padrao as ano_publicacao,
            
            -- Classificar em períodos
            CASE 
                WHEN b.publishedDate_padrao >= 2020 THEN '2020+'
                WHEN b.publishedDate_padrao >= 2015 THEN '2015-2019'
                WHEN b.publishedDate_padrao >= 2010 THEN '2010-2014'
                WHEN b.publishedDate_padrao >= 2005 THEN '2005-2009'
                WHEN b.publishedDate_padrao >= 2000 THEN '2000-2004'
                WHEN b.publishedDate_padrao >= 1990 THEN '1990-1999'
                ELSE 'Antes de 1990'
            END as periodo,
            
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_negativo,
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        AND b.publishedDate_padrao IS NOT NULL
        AND b.publishedDate_padrao > 1950  -- Filtrar anos muito antigos/inválidos
        GROUP BY periodo
        HAVING total_livros >= 10  -- Mínimo de livros por período
    )
    
    SELECT 
        periodo,
        total_livros,
        total_reviews,
        reviews_por_livro,
        ROUND(sentimento_medio, 3) as sentimento_medio,
        ROUND(pct_positivo, 1) as pct_positivo,
        ROUND(pct_negativo, 1) as pct_negativo
    FROM period_analysis
    ORDER BY 
        CASE periodo
            WHEN 'Antes de 1990' THEN 1
            WHEN '1990-1999' THEN 2
            WHEN '2000-2004' THEN 3
            WHEN '2005-2009' THEN 4
            WHEN '2010-2014' THEN 5
            WHEN '2015-2019' THEN 6
            WHEN '2020+' THEN 7
        END
    """
    
    return execute_query(query, db_path)


def get_reviews_by_year(start_year: int = 2000, db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Análise detalhada de reviews por ano específico.
    """
    query = """
    SELECT 
        b.publishedDate_padrao as ano,
        COUNT(DISTINCT b.Title_padrao) as total_livros,
        COUNT(r.sentimento) as total_reviews,
        AVG(r.compound) as sentimento_medio,
        SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) as reviews_positivos,
        SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) as reviews_negativos,
        SUM(CASE WHEN r.sentimento = 'neutro' THEN 1 ELSE 0 END) as reviews_neutros,
        ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro
        
    FROM books_data_processed b
    LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
    WHERE r.sentimento IS NOT NULL
    AND b.publishedDate_padrao >= ?
    AND b.publishedDate_padrao <= 2024  -- Até ano atual
    GROUP BY b.publishedDate_padrao
    HAVING total_livros >= 5  -- Mínimo de livros por ano
    ORDER BY ano DESC
    """
    
    return execute_query(query, db_path, (start_year,))


def get_trending_analysis(db_path: str = "books_database.db") -> dict:
    """
    Análise de tendências: compara períodos recentes vs antigos.
    """
    query = """
    WITH period_comparison AS (
        SELECT 
            CASE 
                WHEN b.publishedDate_padrao >= 2015 THEN 'Recente (2015+)'
                WHEN b.publishedDate_padrao >= 2000 THEN 'Médio (2000-2014)'
                ELSE 'Antigo (antes 2000)'
            END as categoria_periodo,
            
            COUNT(DISTINCT b.Title_padrao) as total_livros,
            COUNT(r.sentimento) as total_reviews,
            AVG(r.compound) as sentimento_medio,
            SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(r.sentimento) as pct_positivo,
            ROUND(COUNT(r.sentimento) * 1.0 / COUNT(DISTINCT b.Title_padrao), 1) as reviews_por_livro
            
        FROM books_data_processed b
        LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
        WHERE r.sentimento IS NOT NULL
        AND b.publishedDate_padrao IS NOT NULL
        AND b.publishedDate_padrao > 1980
        GROUP BY categoria_periodo
    )
    
    SELECT * FROM period_comparison
    ORDER BY 
        CASE categoria_periodo
            WHEN 'Antigo (antes 2000)' THEN 1
            WHEN 'Médio (2000-2014)' THEN 2
            WHEN 'Recente (2015+)' THEN 3
        END
    """
    
    result = execute_query(query, db_path)
    
    # Calcular tendências
    if len(result) >= 2:
        recente = result[result['categoria_periodo'] == 'Recente (2015+)'].iloc[0] if not result[result['categoria_periodo'] == 'Recente (2015+)'].empty else None
        antigo = result[result['categoria_periodo'] == 'Antigo (antes 2000)'].iloc[0] if not result[result['categoria_periodo'] == 'Antigo (antes 2000)'].empty else None
        
        trends = {}
        if recente is not None and antigo is not None:
            trends = {
                'sentimento_trend': recente['sentimento_medio'] - antigo['sentimento_medio'],
                'reviews_trend': recente['reviews_por_livro'] - antigo['reviews_por_livro'],
                'positivo_trend': recente['pct_positivo'] - antigo['pct_positivo']
            }
        
        return {
            'dados': result,
            'tendencias': trends
        }
    
    return {'dados': result, 'tendencias': {}}

def search_books_for_summary(query_text: str, limit: int = 10, db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Busca livros por título ou autor para análise de resumo.
    """
    query = """
    SELECT DISTINCT
        b.Title_padrao as titulo,
        b.authors_padrao as autor,
        b.categories_padrao as categoria,
        b.publishedDate_padrao as ano,
        COUNT(r.sentimento) as total_reviews,
        SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) as positivos,
        SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) as negativos,
        SUM(CASE WHEN r.sentimento = 'neutro' THEN 1 ELSE 0 END) as neutros,
        ROUND(AVG(r.compound), 3) as sentimento_medio
    FROM books_data_processed b
    LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
    WHERE (
        LOWER(b.Title_padrao) LIKE LOWER(?) OR 
        LOWER(b.authors_padrao) LIKE LOWER(?)
    )
    AND r.sentimento IS NOT NULL
    GROUP BY b.Title_padrao, b.authors_padrao, b.categories_padrao, b.publishedDate_padrao
    HAVING total_reviews >= 5  -- Mínimo 5 reviews para análise
    ORDER BY total_reviews DESC
    LIMIT ?
    """
    
    search_term = f"%{query_text}%"
    return execute_query(query, db_path, (search_term, search_term, limit))


def get_book_info(book_title: str, db_path: str = "books_database.db") -> dict:
    """
    Obtém informações detalhadas de um livro específico.
    """
    query = """
    SELECT DISTINCT
        b.Title_padrao as titulo,
        b.authors_padrao as autor,
        b.categories_padrao as categoria,
        b.publishedDate_padrao as ano_publicacao,
        COUNT(r.sentimento) as total_reviews,
        SUM(CASE WHEN r.sentimento = 'positivo' THEN 1 ELSE 0 END) as total_positivos,
        SUM(CASE WHEN r.sentimento = 'negativo' THEN 1 ELSE 0 END) as total_negativos,
        SUM(CASE WHEN r.sentimento = 'neutro' THEN 1 ELSE 0 END) as total_neutros,
        ROUND(AVG(r.compound), 3) as sentimento_medio
    FROM books_data_processed b
    LEFT JOIN books_rating_modified r ON b.Title_padrao = r.Title
    WHERE b.Title_padrao = ?
    AND r.sentimento IS NOT NULL
    GROUP BY b.Title_padrao, b.authors_padrao, b.categories_padrao, b.publishedDate_padrao
    """
    
    result = execute_query(query, db_path, (book_title,))
    
    if not result.empty:
        return result.iloc[0].to_dict()
    else:
        return {}


def get_reviews_by_sentiment(book_title: str, sentiment: str, limit: int = 10, db_path: str = "books_database.db") -> list:
    """
    Obtém reviews de um livro filtrados por sentimento.
    
    Args:
        book_title: Título do livro
        sentiment: 'positivo', 'negativo' ou 'neutro'
        limit: Número máximo de reviews
        db_path: Caminho do banco
    
    Returns:
        Lista de reviews
    """
    query = """
    SELECT 
        text as review_text,
        compound,
        sentimento
    FROM books_rating_modified
    WHERE Title = ?
    AND sentimento = ?
    AND text IS NOT NULL
    AND LENGTH(TRIM(text)) > 20  -- Reviews com conteúdo mínimo
    ORDER BY ABS(compound) DESC  -- Reviews mais "extremos" primeiro
    LIMIT ?
    """
    
    result = execute_query(query, db_path, (book_title, sentiment, limit))
    
    if not result.empty:
        return result['review_text'].tolist()
    else:
        return []


def get_all_reviews_for_book(book_title: str, db_path: str = "books_database.db") -> dict:
    """
    Obtém todos os reviews de um livro organizados por sentimento.
    
    Returns:
        Dict com listas de reviews por sentimento
    """
    reviews_data = {
        'positivos': get_reviews_by_sentiment(book_title, 'positivo', 10, db_path),
        'negativos': get_reviews_by_sentiment(book_title, 'negativo', 10, db_path),
        'neutros': get_reviews_by_sentiment(book_title, 'neutro', 5, db_path)
    }
    
    return reviews_data


# =================
# FUNÇÕES AUXILIARES PARA DASHBOARD
# =================

def get_summary_stats(db_path: str = "books_database.db") -> dict:
    """
    Estatísticas gerais para o dashboard.
    """
    queries = {
        'total_books': "SELECT COUNT(*) as count FROM books_data_processed",
        'total_reviews': "SELECT COUNT(*) as count FROM books_rating_modified WHERE sentimento IS NOT NULL",
        'total_users': "SELECT COUNT(DISTINCT User_id) as count FROM books_rating_modified WHERE User_id IS NOT NULL",
        'avg_sentiment': "SELECT ROUND(AVG(compound), 3) as avg FROM books_rating_modified WHERE compound IS NOT NULL"
    }
    
    stats = {}
    for key, query in queries.items():
        try:
            result = execute_query(query, db_path)
            stats[key] = result.iloc[0].values[0] if not result.empty else 0
        except Exception as e:
            print(f"Erro ao calcular {key}: {e}")
            stats[key] = 0
    
    return stats


def get_sentiment_distribution(db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Distribuição geral de sentimentos para gráficos.
    """
    query = """
    SELECT 
        sentimento,
        COUNT(*) as quantidade,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM books_rating_modified WHERE sentimento IS NOT NULL), 1) as percentual
    FROM books_rating_modified 
    WHERE sentimento IS NOT NULL
    GROUP BY sentimento
    ORDER BY quantidade DESC
    """
    
    return execute_query(query, db_path)


# =================
# FUNÇÕES DE DIAGNÓSTICO
# =================

def check_database_health(db_path: str = "books_database.db") -> dict:
    """
    Verifica a saúde do banco de dados e retorna diagnóstico.
    """
    health_check = {
        'database_exists': False,
        'tables_exist': False,
        'data_available': False,
        'tables_info': {},
        'errors': []
    }
    
    try:
        # Verificar se banco existe
        if not os.path.exists(db_path):
            health_check['errors'].append(f"Banco de dados não encontrado: {db_path}")
            return health_check
        
        health_check['database_exists'] = True
        
        # Verificar tabelas
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['books_data_processed', 'books_rating_modified']
            missing_tables = [t for t in expected_tables if t not in tables]
            
            if missing_tables:
                health_check['errors'].append(f"Tabelas faltando: {missing_tables}")
            else:
                health_check['tables_exist'] = True
            
            # Verificar dados em cada tabela
            for table in tables:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    health_check['tables_info'][table] = count
                    
                    if count > 0:
                        health_check['data_available'] = True
                except Exception as e:
                    health_check['errors'].append(f"Erro ao verificar tabela {table}: {e}")
    
    except Exception as e:
        health_check['errors'].append(f"Erro geral: {e}")
    
    return health_check


def get_table_info(db_path: str = "books_database.db") -> pd.DataFrame:
    """
    Retorna informações sobre as tabelas do banco.
    """
    query = """
    SELECT 
        name as tabela,
        sql as estrutura
    FROM sqlite_master 
    WHERE type='table'
    ORDER BY name
    """
    
    return execute_query(query, db_path)


if __name__ == "__main__":
    # Teste das funções
    db_path = "books_database.db"
    
    print("=== DIAGNÓSTICO DO BANCO ===")
    health = check_database_health(db_path)
    
    print(f"Banco existe: {health['database_exists']}")
    print(f"Tabelas OK: {health['tables_exist']}")
    print(f"Dados disponíveis: {health['data_available']}")
    
    if health['errors']:
        print("Erros encontrados:")
        for error in health['errors']:
            print(f"  - {error}")
    
    if health['tables_info']:
        print("\nTabelas e registros:")
        for table, count in health['tables_info'].items():
            print(f"  {table}: {count:,} registros")
    
    # Teste de consultas se banco estiver OK
    if health['database_exists'] and health['tables_exist']:
        print("\n=== TESTE DE CONSULTAS ===")
        
        try:
            stats = get_summary_stats(db_path)
            print("Estatísticas gerais:", stats)
            
            problematic = get_problematic_books(limit=5, db_path=db_path)
            print(f"Livros problemáticos encontrados: {len(problematic)}")
            
            users = get_users_for_interview(limit=5, db_path=db_path)
            print(f"Usuários para entrevista: {len(users)}")
            
            # Teste das novas funções
            books = search_books_for_summary("Harry Potter", limit=3, db_path=db_path)
            print(f"Livros encontrados na busca: {len(books)}")
            
            if not books.empty:
                first_book = books.iloc[0]['titulo']
                book_info = get_book_info(first_book, db_path)
                print(f"Info do livro '{first_book}': {book_info.get('total_reviews', 0)} reviews")
                
                reviews = get_all_reviews_for_book(first_book, db_path)
                print(f"Reviews - Positivos: {len(reviews['positivos'])}, Negativos: {len(reviews['negativos'])}")
            
            # Teste das análises de desempenho
            print("\n=== TESTE DAS NOVAS ANÁLISES ===")
            
            best_worst_books = get_best_worst_books(limit=3, db_path=db_path)
            print(f"Melhores livros: {len(best_worst_books['melhores'])}")
            print(f"Piores livros: {len(best_worst_books['piores'])}")
            
            best_worst_publishers = get_best_worst_publishers(limit=3, db_path=db_path)
            print(f"Melhores editoras: {len(best_worst_publishers['melhores'])}")
            print(f"Piores editoras: {len(best_worst_publishers['piores'])}")
            
            best_worst_themes = get_best_worst_themes(limit=3, db_path=db_path)
            print(f"Melhores temas: {len(best_worst_themes['melhores'])}")
            print(f"Piores temas: {len(best_worst_themes['piores'])}")
            
            reviews_period = get_reviews_by_period(db_path)
            print(f"Análise temporal: {len(reviews_period)} períodos")
            
            trending = get_trending_analysis(db_path)
            print(f"Análise de tendências: {len(trending['dados'])} categorias")
            
            print("\n✅ Todas as consultas funcionando!")
            
        except Exception as e:
            print(f"❌ Erro nas consultas: {e}")
    
    else:
        print("\n❌ Banco de dados não está pronto para uso")