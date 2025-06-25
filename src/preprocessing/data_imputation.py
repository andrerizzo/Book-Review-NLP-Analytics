"""
Módulo aprimorado para imputação de dados com múltiplas estratégias de busca
"""

import pandas as pd
import numpy as np
import requests
import time
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
import random
from difflib import SequenceMatcher

# Configurações de API
BASE_URL_SEARCH = "https://openlibrary.org/search.json"
BASE_URL_WORKS = "https://openlibrary.org/works"
REQUEST_DELAY = 0.1  # Reduzido para testar se rate limit era o problema
MAX_RETRIES = 2
TIMEOUT = 10


def normalizar_titulo_para_busca(titulo):
    """
    Normaliza título para maximizar chances de match na API.
    
    Args:
        titulo (str): Título original
        
    Returns:
        str: Título normalizado para busca
    """
    if pd.isna(titulo) or not isinstance(titulo, str):
        return ""
    
    # Remover caracteres especiais e normalizar
    titulo_limpo = re.sub(r'[^\w\s]', '', titulo.lower().strip())
    titulo_limpo = re.sub(r'\s+', ' ', titulo_limpo)
    
    # Remover palavras comuns que podem atrapalhar a busca
    stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    palavras = titulo_limpo.split()
    palavras_filtradas = [p for p in palavras if p not in stop_words and len(p) > 2]
    
    return ' '.join(palavras_filtradas[:5])  # Limitar a 5 palavras principais


def normalizar_autor_para_busca(autor):
    """
    Normaliza nome do autor para busca.
    
    Args:
        autor (str): Nome do autor
        
    Returns:
        str: Autor normalizado
    """
    if pd.isna(autor) or not isinstance(autor, str) or autor.strip() == '':
        return None
    
    # Pegar apenas o primeiro autor se houver múltiplos
    primeiro_autor = autor.split(',')[0].strip()
    
    # Remover caracteres especiais
    autor_limpo = re.sub(r'[^\w\s]', '', primeiro_autor.lower())
    autor_limpo = re.sub(r'\s+', ' ', autor_limpo).strip()
    
    return autor_limpo if len(autor_limpo) > 2 else None


def calcular_similaridade(str1, str2):
    """
    Calcula similaridade entre duas strings.
    
    Args:
        str1, str2 (str): Strings para comparar
        
    Returns:
        float: Similaridade entre 0 e 1
    """
    if not str1 or not str2:
        return 0.0
    
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def buscar_metadados_openlibrary(idx, titulo, autor=None, estrategias_multiplas=True):
    """
    Busca metadados com múltiplas estratégias e melhor matching.
    
    Args:
        idx (int): Índice do registro
        titulo (str): Título do livro
        autor (str): Autor do livro (opcional)
        estrategias_multiplas (bool): Usar múltiplas estratégias de busca
        
    Returns:
        dict: Metadados encontrados
    """
    resultado_base = {
        'index': idx,
        'authors_padrao': None,
        'publisher_padrao': None,
        'categories_padrao': None,
        'publishedDate_padrao': None,
        'estrategia_usada': None,
        'similaridade_titulo': 0.0,
        'total_encontrados': 0
    }
    
    titulo_normalizado = normalizar_titulo_para_busca(titulo)
    autor_normalizado = normalizar_autor_para_busca(autor)
    
    if not titulo_normalizado:
        return resultado_base
    
    estrategias = []
    
    if estrategias_multiplas:
        # Estratégia 1: Título + Autor
        if autor_normalizado:
            estrategias.append(('titulo_autor', f"title:{titulo_normalizado} author:{autor_normalizado}"))
        
        # Estratégia 2: Apenas título completo
        estrategias.append(('titulo_completo', f"title:{titulo_normalizado}"))
        
        # Estratégia 3: Busca geral com título
        estrategias.append(('busca_geral', titulo_normalizado))
        
        # Estratégia 4: Palavras-chave principais (primeiras 3 palavras)
        palavras_principais = ' '.join(titulo_normalizado.split()[:3])
        if len(palavras_principais) > 5:
            estrategias.append(('palavras_chave', palavras_principais))
    else:
        # Estratégia padrão
        estrategias.append(('padrao', titulo_normalizado))
    
    melhor_resultado = resultado_base.copy()
    melhor_similaridade = 0.0
    
    for estrategia_nome, query in estrategias:
        try:
            # Fazer requisição
            params = {
                'q': query,
                'limit': 20,  # Aumentar limite para ter mais opções
                'fields': 'key,title,author_name,publisher,publish_date,subject,first_publish_year'
            }
            
            time.sleep(REQUEST_DELAY)
            response = requests.get(BASE_URL_SEARCH, params=params, timeout=TIMEOUT)
            
            if response.status_code != 200:
                continue
                
            data = response.json()
            docs = data.get('docs', [])
            
            if not docs:
                continue
            
            # Avaliar cada resultado para encontrar o melhor match
            for doc in docs:
                titulo_api = doc.get('title', '')
                
                # Calcular similaridade do título
                similaridade = calcular_similaridade(titulo.lower(), titulo_api.lower())
                
                # Bonus se autor também bate
                if autor_normalizado and 'author_name' in doc:
                    autores_api = [a.lower() for a in doc['author_name']]
                    for autor_api in autores_api:
                        if calcular_similaridade(autor_normalizado, autor_api) > 0.7:
                            similaridade += 0.2  # Bonus por match de autor
                            break
                
                # Se encontrou um resultado melhor
                if similaridade > melhor_similaridade and similaridade > 0.6:  # Threshold mínimo
                    melhor_similaridade = similaridade
                    
                    resultado = {
                        'index': idx,
                        'authors_padrao': None,
                        'publisher_padrao': None,
                        'categories_padrao': None,
                        'publishedDate_padrao': None,
                        'estrategia_usada': estrategia_nome,
                        'similaridade_titulo': similaridade,
                        'total_encontrados': len(docs)
                    }
                    
                    # Extrair metadados
                    if 'author_name' in doc and doc['author_name']:
                        resultado['authors_padrao'] = ', '.join(doc['author_name'][:3])  # Máximo 3 autores
                    
                    if 'publisher' in doc and doc['publisher']:
                        # Pegar o primeiro publisher
                        publisher = doc['publisher'][0] if isinstance(doc['publisher'], list) else doc['publisher']
                        resultado['publisher_padrao'] = str(publisher)
                    
                    if 'subject' in doc and doc['subject']:
                        # Pegar até 5 categorias mais relevantes
                        categories = doc['subject'][:5]
                        resultado['categories_padrao'] = ', '.join(categories)
                    
                    # Data de publicação
                    if 'first_publish_year' in doc and doc['first_publish_year']:
                        resultado['publishedDate_padrao'] = float(doc['first_publish_year'])
                    elif 'publish_date' in doc and doc['publish_date']:
                        dates = doc['publish_date']
                        if isinstance(dates, list) and dates:
                            # Tentar extrair ano da primeira data
                            date_str = str(dates[0])
                            year_match = re.search(r'(\d{4})', date_str)
                            if year_match:
                                resultado['publishedDate_padrao'] = float(year_match.group(1))
                    
                    melhor_resultado = resultado
                    
                    # Se similaridade é muito alta, pode parar de procurar
                    if similaridade > 0.9:
                        return melhor_resultado
            
            # Se já encontrou um resultado razoável, pode parar
            if melhor_similaridade > 0.8:
                break
                
        except Exception as e:
            print(f"Erro na estratégia {estrategia_nome} para índice {idx}: {e}")
            continue
    
    return melhor_resultado


def diagnosticar_problemas_busca(books_data, n_amostras=100):
    """
    Diagnostica problemas na busca analisando uma amostra.
    
    Args:
        books_data (pd.DataFrame): Dataset de livros
        n_amostras (int): Número de amostras para analisar
        
    Returns:
        dict: Relatório de diagnóstico
    """
    print(f"Diagnosticando problemas de busca com {n_amostras} amostras...")
    
    # Selecionar amostra aleatória
    amostra = books_data.sample(n=min(n_amostras, len(books_data)), random_state=42)
    
    relatorio = {
        'total_amostras': len(amostra),
        'titulos_muito_curtos': 0,
        'titulos_muito_longos': 0,
        'sem_autor': 0,
        'caracteres_especiais': 0,
        'resultados_por_estrategia': {},
        'distribuicao_similaridade': [],
        'exemplos_sucesso': [],
        'exemplos_falha': []
    }
    
    print("Testando buscas...")
    for idx, row in amostra.iterrows():
        titulo = row.get('Title_padrao', row.get('Title', ''))
        autor = row.get('authors_padrao', '')
        
        # Análise dos títulos
        if len(str(titulo)) < 5:
            relatorio['titulos_muito_curtos'] += 1
        if len(str(titulo)) > 100:
            relatorio['titulos_muito_longos'] += 1
        if pd.isna(autor) or str(autor).strip() == '' or str(autor) == 'nan':
            relatorio['sem_autor'] += 1
        if re.search(r'[^\w\s]', str(titulo)):
            relatorio['caracteres_especiais'] += 1
        
        # Testar busca
        resultado = buscar_metadados_openlibrary_melhorado(idx, titulo, autor)
        
        estrategia = resultado.get('estrategia_usada', 'falhou')
        if estrategia not in relatorio['resultados_por_estrategia']:
            relatorio['resultados_por_estrategia'][estrategia] = 0
        relatorio['resultados_por_estrategia'][estrategia] += 1
        
        similaridade = resultado.get('similaridade_titulo', 0.0)
        relatorio['distribuicao_similaridade'].append(similaridade)
        
        # Coletar exemplos
        if similaridade > 0.8 and len(relatorio['exemplos_sucesso']) < 5:
            relatorio['exemplos_sucesso'].append({
                'titulo_original': titulo,
                'autor_original': autor,
                'similaridade': similaridade,
                'estrategia': estrategia,
                'encontrado': bool(resultado.get('authors_padrao'))
            })
        elif similaridade < 0.3 and len(relatorio['exemplos_falha']) < 5:
            relatorio['exemplos_falha'].append({
                'titulo_original': titulo,
                'autor_original': autor,
                'similaridade': similaridade,
                'estrategia': estrategia
            })
    
    return relatorio


def imprimir_relatorio_diagnostico(relatorio):
    """
    Imprime relatório de diagnóstico formatado.
    
    Args:
        relatorio (dict): Relatório do diagnóstico
    """
    print("\nRELATÓRIO DE DIAGNÓSTICO")
    print("=" * 50)
    
    total = relatorio['total_amostras']
    print(f"Total de amostras analisadas: {total}")
    print(f"Títulos muito curtos (<5 chars): {relatorio['titulos_muito_curtos']} ({relatorio['titulos_muito_curtos']/total*100:.1f}%)")
    print(f"Títulos muito longos (>100 chars): {relatorio['titulos_muito_longos']} ({relatorio['titulos_muito_longos']/total*100:.1f}%)")
    print(f"Sem autor: {relatorio['sem_autor']} ({relatorio['sem_autor']/total*100:.1f}%)")
    print(f"Com caracteres especiais: {relatorio['caracteres_especiais']} ({relatorio['caracteres_especiais']/total*100:.1f}%)")
    
    print(f"\nResultados por estratégia:")
    for estrategia, count in relatorio['resultados_por_estrategia'].items():
        print(f"   {estrategia}: {count} ({count/total*100:.1f}%)")
    
    similaridades = relatorio['distribuicao_similaridade']
    if similaridades:
        print(f"\nDistribuição de similaridade:")
        print(f"   Média: {np.mean(similaridades):.3f}")
        print(f"   Mediana: {np.median(similaridades):.3f}")
        print(f"   >0.8 (alta): {sum(1 for s in similaridades if s > 0.8)} ({sum(1 for s in similaridades if s > 0.8)/len(similaridades)*100:.1f}%)")
        print(f"   0.6-0.8 (média): {sum(1 for s in similaridades if 0.6 <= s <= 0.8)} ({sum(1 for s in similaridades if 0.6 <= s <= 0.8)/len(similaridades)*100:.1f}%)")
        print(f"   <0.6 (baixa): {sum(1 for s in similaridades if s < 0.6)} ({sum(1 for s in similaridades if s < 0.6)/len(similaridades)*100:.1f}%)")
    
    print(f"\nExemplos de sucesso:")
    for exemplo in relatorio['exemplos_sucesso']:
        print(f"   '{exemplo['titulo_original']}' -> Similaridade: {exemplo['similaridade']:.3f} | Estratégia: {exemplo['estrategia']}")
    
    print(f"\nExemplos de falha:")
    for exemplo in relatorio['exemplos_falha']:
        print(f"   '{exemplo['titulo_original']}' -> Similaridade: {exemplo['similaridade']:.3f} | Estratégia: {exemplo['estrategia']}")


def executa_imputacao_melhorada(
    titulos_para_buscar, 
    books_data, 
    output_dir="../data/modified/",
    max_workers=20,
    checkpoint_interval=500,
    limite=None,
    usar_diagnostico=True
):
    """
    Executa imputação com melhorias e diagnóstico.
    
    Args:
        titulos_para_buscar (list): Lista de (índice, título) para buscar
        books_data (pd.DataFrame): DataFrame original
        output_dir (str): Diretório de saída
        max_workers (int): Número de threads
        checkpoint_interval (int): Intervalo para checkpoint
        limite (int): Limite de registros a processar
        usar_diagnostico (bool): Executar diagnóstico primeiro
        
    Returns:
        list: Lista de dicionários com metadados imputados
    """
    
    # Diagnóstico opcional
    if usar_diagnostico:
        print("Executando diagnóstico preliminar...")
        relatorio = diagnosticar_problemas_busca(books_data, n_amostras=50)
        imprimir_relatorio_diagnostico(relatorio)
        print("\nContinuando com imputação melhorada...\n")
    
    # Aplicar limite se especificado
    if limite:
        titulos_para_buscar = titulos_para_buscar[:limite]
    
    print(f"Iniciando imputação melhorada de {len(titulos_para_buscar)} registros...")
    
    # Criar wrapper para execução paralela
    def processar_item(item):
        idx, titulo = item
        autor = books_data.at[idx, 'authors_padrao'] if 'authors_padrao' in books_data.columns else None
        
        # Tratar strings vazias como None
        if isinstance(autor, str) and autor.strip() == '':
            autor = None
            
        return buscar_metadados_openlibrary_melhorado(idx, titulo, autor, estrategias_multiplas=True)
    
    # Executar em paralelo
    resultados = []
    os.makedirs(output_dir, exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        future_to_item = {
            executor.submit(processar_item, item): item 
            for item in titulos_para_buscar
        }
        
        contador = 0
        sucessos = 0
        
        for future in as_completed(future_to_item):
            try:
                resultado = future.result()
                resultados.append(resultado)
                contador += 1
                
                # Contar sucessos (pelo menos um campo imputado)
                if any(resultado.get(campo) for campo in ['authors_padrao', 'publisher_padrao', 'categories_padrao', 'publishedDate_padrao']):
                    sucessos += 1
                
                # Checkpoint
                if contador % checkpoint_interval == 0:
                    taxa_sucesso = (sucessos / contador) * 100
                    print(f"Processados {contador}/{len(titulos_para_buscar)} | Taxa de sucesso: {taxa_sucesso:.1f}%")
                    
                    # Salvar checkpoint
                    checkpoint_path = os.path.join(output_dir, f'checkpoint_melhorado_{contador}.json')
                    with open(checkpoint_path, 'w', encoding='utf-8') as f:
                        json.dump(resultados, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                print(f"Erro processando item: {e}")
                continue
    
    # Relatório final
    taxa_sucesso_final = (sucessos / len(resultados)) * 100 if resultados else 0
    print(f"\nImputação melhorada concluída!")
    print(f"   Registros processados: {len(resultados)}")
    print(f"   Sucessos: {sucessos}")
    print(f"   Taxa de sucesso: {taxa_sucesso_final:.1f}%")
    
    # Salvar resultado final
    output_path = os.path.join(output_dir, 'dados_imputados_melhorado.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    print(f"   Dados salvos em: {output_path}")
    
    return resultados


# Manter funções originais para compatibilidade
def identificar_registros_faltantes(books_data):
    """Versão original mantida para compatibilidade"""
    df_temp = books_data.copy()
    
    campos_padrao = ['publisher_padrao', 'authors_padrao', 'categories_padrao', 'publishedDate_padrao']
    for campo in campos_padrao:
        if campo in df_temp.columns:
            df_temp[campo] = df_temp[campo].replace('', np.nan)
    
    missing_any = df_temp[
        df_temp['publisher_padrao'].isna() |
        df_temp['authors_padrao'].isna() |
        df_temp['categories_padrao'].isna() |
        df_temp['publishedDate_padrao'].isna()
    ].copy()

    return list(zip(missing_any.index, missing_any['Title_padrao']))


def aplicar_imputacoes(books_data, dados_imputados):
    """Versão original mantida para compatibilidade"""
    df_final = books_data.copy()
    
    for item in dados_imputados:
        idx = item['index']
        
        if idx not in df_final.index:
            continue
        
        for campo in ['authors_padrao', 'publisher_padrao', 'categories_padrao', 'publishedDate_padrao']:
            if item.get(campo) is not None:
                df_final.at[idx, campo] = item[campo]
    
    return df_final
