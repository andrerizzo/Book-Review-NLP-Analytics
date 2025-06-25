"""
Módulo para limpeza e normalização de dados - VERSÃO CORRIGIDA
"""

import pandas as pd
import re
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def remover_linhas_duplicadas(df):
    """
    Remove registros duplicados de um DataFrame.
    
    Args:
        df (DataFrame): DataFrame para limpeza
        
    Returns:
        DataFrame sem duplicatas
    """
    initial_count = len(df)
    df_clean = df.drop_duplicates()
    duplicates_removed = initial_count - len(df_clean)
    
    print(f"Duplicatas removidas: {duplicates_removed}")
    
    return df_clean


def normalizar_variavel(variavel):
    """
    Normaliza uma variável textual para padronização e comparação.
    
    Args:
        variavel: Texto ou valor a ser tratado
        
    Returns:
        Texto padronizado ou None para entradas inválidas
    """
    if pd.isna(variavel) or not isinstance(variavel, str) or variavel.strip() == "":
        return None  # MUDANÇA: Retorna None em vez de ""
    
    variavel = variavel.lower()
    variavel = re.sub(r'[^a-z0-9 ]', '', variavel)
    variavel = re.sub(r'\s+', ' ', variavel).strip()
    
    return variavel if variavel else None  # MUDANÇA: Retorna None se string vazia após limpeza


def extrair_autores(autor):
    """
    Normaliza e extrai nomes de autores de uma string contendo lista literal.
    
    Args:
        autor: Representação textual de uma lista de autores ou nome único
        
    Returns:
        String com nomes de autores separados por vírgula, em minúsculas e ordenados, ou None se inválido
    """
    try:
        if pd.isna(autor) or not isinstance(autor, str) or autor.strip() == '':
            return None  # MUDANÇA: Retorna None em vez de ""
        
        autores = ast.literal_eval(autor)
        if isinstance(autores, list):
            autores_limpos = [a.lower().strip() for a in autores if a.strip()]
            if autores_limpos:  # MUDANÇA: Verifica se há autores válidos
                return ', '.join(sorted(set(autores_limpos)))
            return None
        
        autor_limpo = autor.lower().strip()
        return autor_limpo if autor_limpo else None  # MUDANÇA: Retorna None se vazio
        
    except:
        return None  # MUDANÇA: Retorna None em vez de ""


def extrair_categoria(cat_str):
    """
    Normaliza e extrai categorias de uma string contendo lista literal.
    
    Args:
        cat_str: Representação textual de uma lista de categorias
        
    Returns:
        String com categorias separadas por vírgula, em minúsculas e ordenadas, ou None se inválido
    """
    try:
        if pd.isna(cat_str) or not isinstance(cat_str, str) or cat_str.strip() == '':
            return None  # MUDANÇA: Retorna None em vez de ""
        
        categorias = ast.literal_eval(cat_str)
        if isinstance(categorias, list):
            categorias_limpas = [c.lower().strip() for c in categorias if c.strip()]
            if categorias_limpas:  # MUDANÇA: Verifica se há categorias válidas
                return ', '.join(sorted(set(categorias_limpas)))
            return None
        
        categoria_limpa = cat_str.lower().strip()
        return categoria_limpa if categoria_limpa else None  # MUDANÇA: Retorna None se vazio
        
    except:
        return None  # MUDANÇA: Retorna None em vez de ""


def detectar_duplicatas_tfidf(series, threshold=0.85, max_features=1000):
    """
    Detecta duplicatas usando similaridade TF-IDF.
    
    Args:
        series (pd.Series): Série com textos para comparar
        threshold (float): Limiar de similaridade (0.0 a 1.0)
        max_features (int): Número máximo de features TF-IDF
        
    Returns:
        dict: Dicionário mapeando índices duplicados para o índice principal
    """
    # Filtrar valores nulos e vazios
    series_clean = series.dropna()
    series_clean = series_clean[series_clean.str.strip() != '']
    
    if len(series_clean) < 2:
        return {}
    
    # Criar vetorização TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words='english',
        ngram_range=(1, 2),
        lowercase=True
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(series_clean.astype(str))
    except:
        return {}
    
    # Calcular similaridade entre todos os pares
    similarity_matrix = cosine_similarity(tfidf_matrix)
    
    # Encontrar duplicatas
    duplicatas_map = {}
    indices_processados = set()
    
    for i, idx_i in enumerate(series_clean.index):
        if idx_i in indices_processados:
            continue
            
        # Encontrar textos similares
        similares = np.where(similarity_matrix[i] >= threshold)[0]
        
        if len(similares) > 1:  # Mais de um similar (incluindo ele mesmo)
            # O primeiro será o principal, os outros são duplicatas
            principal = series_clean.index[similares[0]]
            
            for j in similares[1:]:
                duplicata_idx = series_clean.index[j]
                if duplicata_idx not in indices_processados:
                    duplicatas_map[duplicata_idx] = principal
                    indices_processados.add(duplicata_idx)
            
            indices_processados.add(principal)
    
    return duplicatas_map


def gerar_mapeamento_padrao(df, coluna_normalizada, coluna_original):
    """
    Gera um dicionário que mapeia cada valor da coluna normalizada para
    o valor mais frequente da coluna original correspondente.
    
    Args:
        df (DataFrame): DataFrame base
        coluna_normalizada (str): Nome da coluna com os valores limpos
        coluna_original (str): Nome da coluna original
        
    Returns:
        dict: Dicionário de mapeamento
    """
    # MUDANÇA: Filtrar valores nulos da coluna normalizada antes do agrupamento
    df_validos = df[df[coluna_normalizada].notna()]
    
    if len(df_validos) == 0:
        return {}
    
    return (
        df_validos
        .groupby(coluna_normalizada)[coluna_original]
        .agg(lambda x: x.value_counts().idxmax() if not x.isnull().all() else None)
        .dropna()
        .to_dict()
    )


def remover_duplicatas_tfidf(df, coluna, threshold=0.85, max_features=1000):
    """
    Remove duplicatas de uma coluna usando TF-IDF.
    Mantém o registro mais completo entre os duplicados.
    
    Args:
        df (DataFrame): DataFrame original
        coluna (str): Nome da coluna para detectar duplicatas
        threshold (float): Limiar de similaridade TF-IDF
        max_features (int): Número máximo de features TF-IDF
        
    Returns:
        DataFrame sem duplicatas baseadas em similaridade TF-IDF
    """
    print(f"Detectando duplicatas em '{coluna}' usando TF-IDF (threshold={threshold})...")
    
    # Detectar duplicatas
    duplicatas_map = detectar_duplicatas_tfidf(
        df[coluna], 
        threshold=threshold, 
        max_features=max_features
    )
    
    if not duplicatas_map:
        print("Nenhuma duplicata detectada.")
        return df
    
    print(f"Detectadas {len(duplicatas_map)} duplicatas potenciais.")
    
    # Preparar DataFrame temporário
    df_temp = df.copy()
    df_temp['n_nulos'] = df_temp.isnull().sum(axis=1)
    
    # Para cada grupo de duplicatas, manter apenas o mais completo
    indices_para_remover = set()
    
    for duplicata_idx, principal_idx in duplicatas_map.items():
        # Comparar completude dos registros
        nulos_duplicata = df_temp.loc[duplicata_idx, 'n_nulos']
        nulos_principal = df_temp.loc[principal_idx, 'n_nulos']
        
        # Se a duplicata tem menos nulos, trocar os papéis
        if nulos_duplicata < nulos_principal:
            indices_para_remover.add(principal_idx)
        else:
            indices_para_remover.add(duplicata_idx)
    
    # Remover duplicatas
    df_final = df_temp.drop(index=indices_para_remover).drop(columns=['n_nulos'])
    
    print(f"Removidos {len(indices_para_remover)} registros duplicados.")
    return df_final


def remover_duplicatas_por_campos_chave(df, colunas_chave, caminho_log='log_duplicatas_excluidas.csv'):
    """
    Remove duplicatas por campos-chave mantendo os registros mais completos.
    Gera um log dos registros que serão excluídos.
    
    Args:
        df (DataFrame): DataFrame original
        colunas_chave (list): Lista de colunas que definem duplicação
        caminho_log (str): Caminho do CSV com os registros excluídos
        
    Returns:
        DataFrame sem duplicatas e com os registros mais completos mantidos
    """
    df_temp = df.copy()
    
    # Conta valores ausentes em cada linha
    df_temp['n_nulos'] = df_temp.isnull().sum(axis=1)
    
    # Ordena por menor número de nulos para priorizar registros mais completos
    df_temp = df_temp.sort_values(by='n_nulos')
    
    # Marca duplicatas (mantendo o mais completo)
    duplicados_mask = df_temp.duplicated(subset=colunas_chave, keep='first')
    
    # Gera log dos que serão removidos
    log_excluidos = df_temp[duplicados_mask].drop(columns='n_nulos')
    log_excluidos.to_csv(caminho_log, index=False)
    print(f"AVISO: {len(log_excluidos)} duplicatas registradas em: {caminho_log}")
    
    # Remove os duplicados e a coluna auxiliar
    df_final = df_temp[~duplicados_mask].drop(columns='n_nulos')
    
    return df_final


def limpar_e_normalizar_books_data(books_data):
    """
    Aplica todo o pipeline de limpeza e normalização no dataset books_data.
    
    Args:
        books_data (DataFrame): DataFrame original do dataset de livros
        
    Returns:
        DataFrame limpo e normalizado
    """
    df = books_data.copy()
    
    print("Iniciando limpeza e normalização do dataset books_data...")
    
    # 1. Remover linhas duplicadas básicas
    df = remover_linhas_duplicadas(df)
    
    # 2. Normalizar e padronizar títulos
    print("Normalizando títulos...")
    df['title_norm'] = df['Title'].apply(normalizar_variavel)
    mapa_titulo_padrao = gerar_mapeamento_padrao(df, 'title_norm', 'Title')
    # MUDANÇA: Usar .map() mas preservar NaN quando não há mapeamento
    df['Title_padrao'] = df['title_norm'].map(mapa_titulo_padrao)
    # Se title_norm é None, Title_padrao deve ser None também
    df.loc[df['title_norm'].isna(), 'Title_padrao'] = None
    df.drop(columns='title_norm', inplace=True)
    
    # 3. Normalizar e padronizar autores  
    print("Normalizando autores...")
    df['authors_norm'] = df['authors'].apply(extrair_autores)
    mapa_autor_padrao = gerar_mapeamento_padrao(df, 'authors_norm', 'authors_norm')
    # MUDANÇA: Preservar None quando authors_norm é None
    df['authors_padrao'] = df['authors_norm'].map(mapa_autor_padrao)
    df.loc[df['authors_norm'].isna(), 'authors_padrao'] = None
    df.drop(columns='authors_norm', inplace=True)
    
    # 4. Normalizar e padronizar editoras
    print("Normalizando editoras...")
    df['publisher_norm'] = df['publisher'].apply(normalizar_variavel)
    mapa_editora_padrao = gerar_mapeamento_padrao(df, 'publisher_norm', 'publisher_norm')
    # MUDANÇA: Preservar None quando publisher_norm é None
    df['publisher_padrao'] = df['publisher_norm'].map(mapa_editora_padrao)
    df.loc[df['publisher_norm'].isna(), 'publisher_padrao'] = None
    df.drop(columns='publisher_norm', inplace=True)
    
    # 5. Normalizar e padronizar categorias
    print("Normalizando categorias...")
    df['categories_norm'] = df['categories'].apply(extrair_categoria)
    mapa_categoria_padrao = gerar_mapeamento_padrao(df, 'categories_norm', 'categories_norm')
    # MUDANÇA: Preservar None quando categories_norm é None  
    df['categories_padrao'] = df['categories_norm'].map(mapa_categoria_padrao)
    df.loc[df['categories_norm'].isna(), 'categories_padrao'] = None
    df.drop(columns='categories_norm', inplace=True)
    
    # 6. Padronizar datas de publicação
    print("Padronizando datas...")
    df['publishedDate'] = pd.to_datetime(df['publishedDate'], errors='coerce')
    df['publishedDate_padrao'] = df['publishedDate'].dt.year
    
    # 7. Remover duplicatas usando TF-IDF em títulos (só se houver títulos válidos)
    if df['Title_padrao'].notna().sum() > 0:
        print("Removendo duplicatas por similaridade TF-IDF em títulos...")
        df = remover_duplicatas_tfidf(df, 'Title_padrao', threshold=0.90)
    
    # 8. Remover duplicatas usando TF-IDF em autores (só se houver autores válidos)
    if df['authors_padrao'].notna().sum() > 0:
        print("Removendo duplicatas por similaridade TF-IDF em autores...")
        df = remover_duplicatas_tfidf(df, 'authors_padrao', threshold=0.95)
    
    # 9. Remover duplicatas tradicionais por título+autor como backup
    print("Removendo duplicatas exatas por título+autor...")
    df['titulo_autor_key'] = (
        df['Title_padrao'].fillna('').astype(str) + "_" + 
        df['authors_padrao'].fillna('').astype(str)
    )
    
    df = remover_duplicatas_por_campos_chave(
        df, 
        colunas_chave=['titulo_autor_key'],
        caminho_log='../data/logs/duplicatas_books_data.csv'
    )
    
    # Remover coluna auxiliar
    df.drop(columns=['titulo_autor_key'], inplace=True)
    
    print("Limpeza e normalização concluída!")
    
    # ADIÇÃO: Relatório final de dados faltantes
    print("\nRelatório final de dados faltantes:")
    campos_verificar = ['Title_padrao', 'authors_padrao', 'publisher_padrao', 'categories_padrao', 'publishedDate_padrao']
    for campo in campos_verificar:
        if campo in df.columns:
            faltantes = df[campo].isna().sum()
            total = len(df)
            percentual = (faltantes / total) * 100
            print(f"   {campo}: {faltantes:,} ({percentual:.1f}%) faltantes")
    
    return df


def limpar_books_rating(books_rating):
    """
    Aplica limpeza básica no dataset books_rating.
    
    Args:
        books_rating (DataFrame): DataFrame original do dataset de avaliações
        
    Returns:
        DataFrame limpo
    """
    df = books_rating.copy()
    
    print("Iniciando limpeza do dataset books_rating...")
    
    # Remover linhas duplicadas
    df = remover_linhas_duplicadas(df)
    
    # Normalizar títulos para matching com books_data
    df['title_norm'] = df['Title'].apply(normalizar_variavel)
    
    print("Limpeza do books_rating concluída!")
    return df


def agrega_pos_normalizacao(df, coluna_chave, funcao_normalizacao=None):
    """
    Agrega duplicados após normalização para qualquer dataset.
    
    Args:
        df (DataFrame): DataFrame original
        coluna_chave (str): Coluna para identificar duplicatas
        funcao_normalizacao (function): Função de normalização a aplicar (opcional)
        
    Returns:
        DataFrame: DataFrame final limpo e sem duplicados
    """
    print("=== AGREGAÇÃO PÓS NORMALIZAÇÃO ===")
    
    # 1. Aplicar normalização se fornecida
    if funcao_normalizacao:
        df_normalizado = funcao_normalizacao(df)
        print(f"Após normalização: {len(df_normalizado)} registros")
    else:
        df_normalizado = df.copy()
        print(f"Dataset original: {len(df_normalizado)} registros")
    
    # 2. Agregação simples dos duplicados restantes
    print(f"Agregando duplicados baseado em '{coluna_chave}'...")
    
    # Contar nulos por linha para escolher o mais completo
    df_temp = df_normalizado.copy()
    df_temp['n_nulos'] = df_temp.isnull().sum(axis=1)
    
    # Para cada grupo duplicado, manter apenas o com menos nulos
    # Em caso de empate, manter o primeiro
    df_final = (df_temp
                .sort_values('n_nulos')  # Menos nulos primeiro
                .drop_duplicates(subset=[coluna_chave], keep='first')
                .drop(columns='n_nulos'))
    
    duplicados_removidos = len(df_normalizado) - len(df_final)
    print(f"Removidos {duplicados_removidos} duplicados finais.")
    print(f"Após agregação: {len(df_final)} registros")
    print(f"Total removido: {len(df) - len(df_final)} registros")
    
    return df_final