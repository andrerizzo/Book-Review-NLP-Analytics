"""
Módulo para carregamento de datasets
"""

import pandas as pd
import gdown
import os
from sklearn.model_selection import train_test_split


def download_datasets_from_drive():
    """
    Baixa datasets do Google Drive usando gdown.
    Mantém a estrutura original do código.
    """
    # IDs originais do Google Drive
    id_google_drive_file = ['1kttnEbR44oN6zOEm9WDwFZctxcerimNi',
                            '1iYLD6qRipmIPDK-hguiiSw3lwnlCM-0e']
    
    target_files = ['books_data.csv',
                    'Books_rating.csv']

    for i in range(2):
        gdown.download(id=id_google_drive_file[i],
                       output=target_files[i],
                       quiet=False)


def load_datasets_colab():
    """
    Carrega datasets no Google Colab.
    
    Returns:
        books_data (DataFrame): Dataset de livros
        books_rating (DataFrame): Dataset de avaliações
    """
    download_datasets_from_drive()
    
    # Carregar datasets
    books_data = pd.read_csv("books_data.csv")
    books_rating = pd.read_csv("Books_rating.csv")
    
    return books_data, books_rating


def load_datasets_local():
    """
    Carrega datasets de arquivos locais.
    
    Returns:
        books_data (DataFrame): Dataset de livros
        books_rating (DataFrame): Dataset de avaliações
    """
    # Caminhos dos arquivos
    books_data = pd.read_csv("../data/raw/books_data.csv")
    books_rating = pd.read_csv("../data/raw/Books_rating.csv")
    
    return books_data, books_rating


def load_processed_datasets():
    """
    Carrega datasets já processados.
    Para uso no notebook de missing values.
    
    Returns:
        books_data (DataFrame): Dataset de livros processado
        books_rating (DataFrame): Dataset de avaliações processado
    """
    books_data = pd.read_csv(r'..\data\processed\books_data_processed.csv')
    books_rating = pd.read_csv(r'..\data\processed\books_rating_processed.csv')
    
    return books_data, books_rating


def check_duplicates(books_data, books_rating):
    """
    Verifica registros duplicados.
    
    Args:
        books_data (DataFrame): Dataset de livros
        books_rating (DataFrame): Dataset de avaliações
    """
    print(f'BOOKS_DATA: {books_data.duplicated().sum()} registros duplicados')
    print(f'BOOKS_RATING: {books_rating.duplicated().sum()} registros duplicados')


def check_empty_records(books_data, books_rating):
    """
    Verifica registros totalmente vazios.
    
    Args:
        books_data (DataFrame): Dataset de livros
        books_rating (DataFrame): Dataset de avaliações
    """
    print(f'BOOKS_DATA: {books_data.isna().all().sum()} linhas (registros) em branco')
    print(f'BOOKS_RATING: {books_rating.isna().all().sum()} linhas (registros) em branco')


def criar_amostra_estratificada(df, tamanho_amostra=10000, coluna_estratificacao='categories', random_state=42):
    """
    Cria uma amostra estratificada do DataFrame para desenvolvimento e testes.
    
    Args:
        df (DataFrame): DataFrame original
        tamanho_amostra (int): Número de registros na amostra (default: 10.000)
        coluna_estratificacao (str): Coluna para estratificação (default: 'categories')
        random_state (int): Seed para reprodutibilidade
        
    Returns:
        DataFrame com amostra estratificada
        
    Raises:
        ValueError: Se o tamanho da amostra for maior que o dataset original
    """
    if tamanho_amostra >= len(df):
        print(f"AVISO: Tamanho da amostra ({tamanho_amostra}) >= dataset original ({len(df)})")
        print("Retornando dataset completo...")
        return df.copy()
    
    print(f"Criando amostra estratificada de {tamanho_amostra:,} registros...")
    print(f"Dataset original: {len(df):,} registros")
    
    # Calcular fração da amostra
    sample_fraction = tamanho_amostra / len(df)
    
    # Verificar se coluna existe
    if coluna_estratificacao not in df.columns:
        print(f"AVISO: Coluna '{coluna_estratificacao}' não encontrada.")
        print("Fazendo amostragem aleatória simples...")
        return df.sample(n=tamanho_amostra, random_state=random_state)
    
    # Tratamento de valores nulos na coluna de estratificação
    df_temp = df.copy()
    df_temp[coluna_estratificacao] = df_temp[coluna_estratificacao].fillna('missing')
    
    try:
        # Amostragem estratificada usando train_test_split
        amostra, _ = train_test_split(
            df_temp,
            train_size=sample_fraction,
            stratify=df_temp[coluna_estratificacao],
            random_state=random_state
        )
        
        print(f"Amostra criada: {len(amostra):,} registros ({sample_fraction:.1%} do original)")
        
        # Mostrar distribuição por categoria (top 10)
        print("\nDistribuição das principais categorias na amostra:")
        dist_amostra = amostra[coluna_estratificacao].value_counts().head(10)
        for categoria, count in dist_amostra.items():
            pct = (count / len(amostra)) * 100
            print(f"  {categoria}: {count:,} ({pct:.1f}%)")
        
        return amostra
        
    except ValueError as e:
        print(f"Erro na estratificação: {e}")
        print("Fazendo amostragem aleatória simples...")
        return df.sample(n=tamanho_amostra, random_state=random_state)


def criar_amostra_rapida(df, percentual=5, random_state=42):
    """
    Cria uma amostra rápida percentual do DataFrame para testes iniciais.
    
    Args:
        df (DataFrame): DataFrame original
        percentual (int): Percentual da amostra (1-100)
        random_state (int): Seed para reprodutibilidade
        
    Returns:
        DataFrame com amostra percentual
    """
    if not 1 <= percentual <= 100:
        raise ValueError("Percentual deve estar entre 1 e 100")
    
    sample_fraction = percentual / 100
    tamanho_amostra = int(len(df) * sample_fraction)
    
    print(f"Criando amostra rápida de {percentual}% ({tamanho_amostra:,} registros)")
    
    amostra = df.sample(frac=sample_fraction, random_state=random_state)
    
    print(f"Amostra criada: {len(amostra):,} registros")
    return amostra


def salvar_amostra(df_amostra, nome_arquivo='amostra_books_data.csv', caminho='../data/samples/'):
    """
    Salva a amostra em um arquivo CSV.
    
    Args:
        df_amostra (DataFrame): DataFrame da amostra
        nome_arquivo (str): Nome do arquivo
        caminho (str): Diretório para salvar
        
    Returns:
        str: Caminho completo do arquivo salvo
    """
    # Criar diretório se não existir
    os.makedirs(caminho, exist_ok=True)
    
    caminho_completo = os.path.join(caminho, nome_arquivo)
    
    df_amostra.to_csv(caminho_completo, index=False)
    print(f"Amostra salva em: {caminho_completo}")
    
    return caminho_completo


def load_datasets_with_sample(use_sample=True, sample_size=10000, stratify_column='categories'):
    """
    Função unificada para carregar datasets com opção de amostragem.
    Ideal para desenvolvimento e produção.
    
    Args:
        use_sample (bool): Se True, cria amostra estratificada
        sample_size (int): Tamanho da amostra se use_sample=True
        stratify_column (str): Coluna para estratificação
        
    Returns:
        tuple: (books_data, books_rating) - DataFrames originais ou amostrados
    """
    print("=== CARREGAMENTO DE DATASETS ===")
    
    # Carregar datasets completos
    books_data, books_rating = load_datasets_local()
    
    if use_sample and len(books_data) > sample_size:
        print("\n=== MODO DESENVOLVIMENTO: CRIANDO AMOSTRA ===")
        
        # Criar amostra estratificada de books_data
        books_data = criar_amostra_estratificada(
            books_data, 
            tamanho_amostra=sample_size,
            coluna_estratificacao=stratify_column
        )
        
        # Para books_rating, pegar apenas avaliações dos livros da amostra
        if 'Title' in books_rating.columns:
            print("\nFiltrando books_rating para títulos da amostra...")
            titulos_amostra = set(books_data['Title'].unique())
            books_rating = books_rating[books_rating['Title'].isin(titulos_amostra)]
            print(f"books_rating filtrado: {len(books_rating):,} registros")
    
    else:
        print(f"\n=== MODO PRODUÇÃO: DATASET COMPLETO ===")
    
    return books_data, books_rating


def configurar_amostragem(use_sample=True, mode='percentage', **kwargs):
    """
    Função principal para configurar amostragem de forma flexível.
    
    Args:
        use_sample (bool): Se aplicar amostragem
        mode (str): 'fixed' (tamanho fixo) ou 'percentage' (percentuais independentes)
        **kwargs: Argumentos específicos do modo
        
    Returns:
        tuple: (books_data, books_rating)
        
    Exemplos:
        # Produção - dataset completo
        books_data, books_rating = configurar_amostragem(use_sample=False)
        
        # Dev com percentuais independentes
        books_data, books_rating = configurar_amostragem(
            mode='percentage',
            books_data_percentage=5,
            books_rating_percentage=2
        )
        
        # Dev com tamanho fixo estratificado
        books_data, books_rating = configurar_amostragem(
            mode='fixed',
            sample_size=10000
        )
    """
    print("=== CARREGAMENTO DE DATASETS ===")
    
    # Carregar datasets completos primeiro
    books_data, books_rating = load_datasets_local()
    
    if not use_sample:
        print("=== MODO PRODUÇÃO: DATASET COMPLETO ===")
        print(f"books_data: {len(books_data):,} registros")
        print(f"books_rating: {len(books_rating):,} registros")
        return books_data, books_rating
    
    print("=== MODO DESENVOLVIMENTO: APLICANDO AMOSTRAGEM ===")
    
    if mode == 'percentage':
        # Amostragem percentual independente para cada base
        books_data_percentage = kwargs.get('books_data_percentage', 5)
        books_rating_percentage = kwargs.get('books_rating_percentage', 2)
        
        print(f"Configuração: {books_data_percentage}% books_data + {books_rating_percentage}% books_rating")
        
        # Criar amostras independentes
        books_data_sample = criar_amostra_rapida(
            books_data, 
            percentual=books_data_percentage,
            random_state=kwargs.get('random_state', 42)
        )
        
        books_rating_sample = criar_amostra_rapida(
            books_rating, 
            percentual=books_rating_percentage,
            random_state=kwargs.get('random_state', 42)
        )
        
        print(f"\nResultado final:")
        print(f"books_data: {len(books_data_sample):,} registros ({books_data_percentage}% de {len(books_data):,})")
        print(f"books_rating: {len(books_rating_sample):,} registros ({books_rating_percentage}% de {len(books_rating):,})")
        
        return books_data_sample, books_rating_sample
    
    elif mode == 'fixed':
        # Amostragem com tamanho fixo estratificado (modo original)
        sample_size = kwargs.get('sample_size', 10000)
        stratify_column = kwargs.get('stratify_column', 'categories')
        
        print(f"Configuração: {sample_size:,} registros com estratificação por '{stratify_column}'")
        
        if len(books_data) > sample_size:
            # Amostra estratificada de books_data
            books_data_sample = criar_amostra_estratificada(
                books_data, 
                tamanho_amostra=sample_size,
                coluna_estratificacao=stratify_column,
                random_state=kwargs.get('random_state', 42)
            )
            
            # Filtrar books_rating para os livros da amostra
            if 'Title' in books_rating.columns:
                print(f"\nFiltrando books_rating para títulos da amostra...")
                titulos_amostra = set(books_data_sample['Title'].unique())
                books_rating_sample = books_rating[books_rating['Title'].isin(titulos_amostra)]
                print(f"books_rating filtrado: {len(books_rating_sample):,} registros")
            else:
                books_rating_sample = books_rating
            
            return books_data_sample, books_rating_sample
        else:
            print(f"Dataset menor que tamanho solicitado. Retornando completo.")
            return books_data, books_rating
    
    else:
        raise ValueError(f"mode deve ser 'fixed' ou 'percentage', recebido: '{mode}'")