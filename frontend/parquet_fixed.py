"""
Script para carregar dados Parquet diretamente no SQLite
Versão otimizada para frontend
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path
import sys


def create_database_from_parquet(
    parquet_files,
    db_path="books_database.db",
    if_exists="replace"
):
    """
    Carrega arquivos Parquet diretamente no SQLite.
    
    Args:
        parquet_files (dict): {'table_name': 'path/to/file.parquet'}
        db_path (str): Caminho para o banco SQLite
        if_exists (str): 'replace', 'append', ou 'fail'
    
    Returns:
        str: Caminho do banco criado
    """
    
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    
    # Conectar ao SQLite
    conn = sqlite3.connect(db_path)
    
    print(f"Criando banco de dados: {db_path}")
    print("=" * 60)
    
    try:
        total_records = 0
        
        for table_name, parquet_path in parquet_files.items():
            
            if not os.path.exists(parquet_path):
                print(f"Arquivo não encontrado: {parquet_path}")
                continue
            
            print(f"📊 Carregando {table_name}...")
            
            # Carregar Parquet
            try:
                df = pd.read_parquet(parquet_path)
            except Exception as e:
                print(f"Erro ao ler {parquet_path}: {e}")
                continue
            
            # Verificar se DataFrame não está vazio
            if df.empty:
                print(f"{table_name}: DataFrame vazio!")
                continue
            
            # Limpar dados básico
            df = clean_dataframe(df, table_name)
            
            # Salvar no SQLite
            try:
                df.to_sql(
                    name=table_name,
                    con=conn,
                    if_exists=if_exists,
                    index=False,
                    method='multi',  # Inserção otimizada
                    chunksize=1000   # Processar em lotes
                )
                
                print(f"   {table_name}: {len(df):,} registros carregados")
                print(f"   Colunas: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
                print(f"   Tamanho: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
                
                total_records += len(df)
                
            except Exception as e:
                print(f"Erro ao salvar {table_name}: {e}")
                continue
            
            print()
        
        # Criar índices para performance
        print("Criando índices...")
        create_indexes(conn)
        
        # Estatísticas do banco
        print_database_stats(conn)
        
        print(f"Total de registros carregados: {total_records:,}")
        
    except Exception as e:
        print(f"Erro crítico ao criar banco: {e}")
        raise
    
    finally:
        conn.close()
    
    print(f"🎉 Banco criado com sucesso: {db_path}")
    return db_path


def clean_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """
    Limpeza básica do DataFrame antes de salvar.
    
    Args:
        df: DataFrame para limpar
        table_name: Nome da tabela (para logs)
    
    Returns:
        DataFrame limpo
    """
    
    original_size = len(df)
    
    # Remover duplicatas se existirem
    df = df.drop_duplicates()
    
    # Limpar valores nulos excessivos
    # (manter apenas colunas com pelo menos 10% de dados válidos)
    threshold = len(df) * 0.1
    df = df.dropna(axis=1, thresh=int(threshold))
    
    # Converter tipos de dados problemáticos
    for col in df.columns:
        if df[col].dtype == 'object':
            # Limpar strings
            df[col] = df[col].astype(str).str.strip()
            # Converter 'nan' string para None
            df[col] = df[col].replace(['nan', 'None', 'null', ''], None)
    
    cleaned_size = len(df)
    
    if cleaned_size != original_size:
        print(f"   Limpeza: {original_size:,} → {cleaned_size:,} registros")
    
    return df


def create_indexes(conn):
    """
    Cria índices úteis para consultas comuns.
    
    Args:
        conn: Conexão SQLite
    """
    
    indexes = [
        # Índices para books_data
        ("idx_books_title", "books_data_processed", "Title_padrao"),
        ("idx_books_authors", "books_data_processed", "authors_padrao"),
        ("idx_books_categories", "books_data_processed", "categories_padrao"),
        ("idx_books_year", "books_data_processed", "publishedDate_padrao"),
        
        # Índices para books_rating
        ("idx_rating_title", "books_rating_modified", "Title"),
        ("idx_rating_user", "books_rating_modified", "User_id"),
        ("idx_rating_sentiment", "books_rating_modified", "sentimento"),
        ("idx_rating_compound", "books_rating_modified", "compound"),
        
        # Índices compostos úteis
        ("idx_rating_title_sentiment", "books_rating_modified", "Title, sentimento"),
        ("idx_rating_user_sentiment", "books_rating_modified", "User_id, sentimento")
    ]
    
    created_count = 0
    
    for idx_name, table, columns in indexes:
        try:
            # Verificar se tabela existe
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                (table,)
            )
            if not cursor.fetchone():
                continue
            
            # Criar índice
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({columns})"
            conn.execute(sql)
            created_count += 1
            
        except sqlite3.OperationalError as e:
            print(f"   Aviso ao criar índice {idx_name}: {e}")
        except Exception as e:
            print(f"   Erro ao criar índice {idx_name}: {e}")
    
    conn.commit()
    print(f"   {created_count} índices criados")


def print_database_stats(conn):
    """
    Mostra estatísticas do banco criado.
    
    Args:
        conn: Conexão SQLite
    """
    
    print()
    print("ESTATÍSTICAS DO BANCO")
    print("=" * 40)
    
    # Listar tabelas
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    if not tables:
        print("Nenhuma tabela encontrada!")
        return
    
    total_records = 0
    
    for (table_name,) in tables:
        try:
            # Contar registros
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_records += count
            
            # Info das colunas
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print(f" Tabela: {table_name}")
            print(f"   Registros: {count:,}")
            print(f"   Colunas: {len(columns)}")
            
            # Mostrar algumas colunas principais
            key_columns = [col[1] for col in columns[:5]]
            print(f"   Campos: {key_columns}{'...' if len(columns) > 5 else ''}")
            print()
            
        except Exception as e:
            print(f"   Erro ao analisar {table_name}: {e}")
    
    print(f" Total geral: {total_records:,} registros")


def test_database_queries(db_path):
    """
    Testa consultas básicas no banco criado.
    
    Args:
        db_path (str): Caminho do banco SQLite
    """
    
    print()
    print(" TESTANDO CONSULTAS")
    print("=" * 40)
    
    if not os.path.exists(db_path):
        print(f" Banco não encontrado: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    
    test_queries = [
        {
            "name": "📚 Top 5 autores por número de livros",
            "sql": """
                SELECT authors_padrao as autor, COUNT(*) as num_livros
                FROM books_data_processed 
                WHERE authors_padrao IS NOT NULL
                GROUP BY authors_padrao 
                ORDER BY num_livros DESC 
                LIMIT 5
            """
        },
        {
            "name": " Distribuição de sentimentos",
            "sql": """
                SELECT sentimento, COUNT(*) as count
                FROM books_rating_modified 
                WHERE sentimento IS NOT NULL
                GROUP BY sentimento 
                ORDER BY count DESC
            """
        },
        {
            "name": " Livros por década",
            "sql": """
                SELECT 
                    (publishedDate_padrao / 10) * 10 as decada,
                    COUNT(*) as num_livros
                FROM books_data_processed 
                WHERE publishedDate_padrao IS NOT NULL
                AND publishedDate_padrao > 1900
                GROUP BY decada 
                ORDER BY decada DESC
                LIMIT 5
            """
        }
    ]
    
    success_count = 0
    
    for query in test_queries:
        try:
            print(f"{query['name']}:")
            df = pd.read_sql_query(query['sql'], conn)
            
            if not df.empty:
                print(df.to_string(index=False, max_rows=5))
                success_count += 1
            else:
                print("   Consulta retornou vazio")
                
        except Exception as e:
            print(f"   Erro: {e}")
        
        print()
    
    conn.close()
    
    print(f" {success_count}/{len(test_queries)} consultas executadas com sucesso")


def find_data_files():
    """
    Busca arquivos de dados em locais comuns.
    
    Returns:
        dict: Mapeamento de tabelas para arquivos encontrados
    """
    
    # Possíveis localizações dos arquivos
    search_paths = [
        ".",  # Pasta atual (frontend)
        "../data/processed",  # Pasta pai
        "../data/modified",
        "data/processed",     # Subpasta local
        "data/modified",
        "../../data/processed",  # Dois níveis acima
        "../../data/modified"
    ]
    
    # Arquivos que procuramos
    target_files = {
        "books_data_processed": ["books_data_processed.parquet", "books_data_processed.csv"],
        "books_rating_modified": ["books_rating_modified.parquet", "books_rating_modified.csv"],
        "books_data_modified": ["books_data_imputado.parquet", "books_data_imputado.csv"],
        "books_rating_processed": ["books_rating_processed.parquet", "books_rating_processed.csv"]
    }
    
    found_files = {}
    
    print("🔍 Procurando arquivos de dados...")
    
    for table_name, filenames in target_files.items():
        for search_path in search_paths:
            for filename in filenames:
                file_path = os.path.join(search_path, filename)
                
                if os.path.exists(file_path):
                    # Se for CSV, converter para Parquet
                    if filename.endswith('.csv'):
                        parquet_path = file_path.replace('.csv', '.parquet')
                        if not os.path.exists(parquet_path):
                            print(f"   🔄 Convertendo {filename} para Parquet...")
                            try:
                                df = pd.read_csv(file_path)
                                df.to_parquet(parquet_path, index=False)
                                found_files[table_name] = parquet_path
                                print(f"   {filename} → {os.path.basename(parquet_path)}")
                            except Exception as e:
                                print(f"   Erro na conversão: {e}")
                                continue
                        else:
                            found_files[table_name] = parquet_path
                    else:
                        found_files[table_name] = file_path
                    
                    print(f"   Encontrado: {table_name} → {file_path}")
                    break
            
            if table_name in found_files:
                break
    
    return found_files


def main():
    """
    Função principal - configura e executa a criação do banco.
    """
    
    print("🚀 CRIADOR DE BANCO DE DADOS - POC LIVROS")
    print("=" * 60)
    
    # Buscar arquivos automaticamente
    found_files = find_data_files()
    
    if not found_files:
        print(" ERRO: Nenhum arquivo de dados encontrado!")
        print("\n Locais procurados:")
        print("   • ./data/processed/")
        print("   • ./data/modified/")
        print("   • ../data/processed/")
        print("   • ../data/modified/")
        print("\n Arquivos esperados:")
        print("   • books_data_processed.parquet")
        print("   • books_rating_modified.parquet")
        print("   • books_data_imputado.parquet (opcional)")
        print("   • books_rating_processed.parquet (opcional)")
        
        print("\n Soluções:")
        print("   1. Copie os arquivos .parquet para a pasta frontend")
        print("   2. Execute este script da pasta que contém 'data/'")
        print("   3. Verifique se o pipeline de dados foi executado")
        
        return False
    
    print(f"\n Encontrados {len(found_files)} arquivo(s) de dados")
    print()
    
    # Criar banco
    db_path = "books_database.db"
    
    try:
        create_database_from_parquet(
            parquet_files=found_files,
            db_path=db_path
        )
        
        # Testar consultas
        test_database_queries(db_path)
        
        print()
        print(" PROCESSO CONCLUÍDO!")
        print(f" Banco SQLite pronto: {db_path}")
        print(" Frontend pode ser executado com: streamlit run streamlit_poc.py")
        
        return True
        
    except Exception as e:
        print(f" ERRO CRÍTICO: {e}")
        return False


if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n  Processo falhou. Verifique os erros acima.")
        sys.exit(1)
    else:
        print("\n Tudo pronto para usar!")

