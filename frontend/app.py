"""
Frontend Streamlit para POC de Análise de Livros
Interface simples para análises de negócio
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import gdown


#Fazer download da base a partir do GDrive
def download_database():
    """Faz download do banco de dados do Google Drive se não existir localmente."""
    db_path = "books_database.db"
    if not os.path.exists(db_path):
        st.info("Baixando banco de dados do Google Drive...")
        url = "https://drive.google.com/file/d/1xDblPfCXZwKcmHJ1rtJLQSmlGRhYGkeg/view?usp=sharing"  # Link do arquivo no GDrive
        gdown.download(url, db_path, quiet=False)
        st.success("Banco de dados baixado com sucesso!")
    else:
        st.info("Banco de dados já existe, usando arquivo local.")



# Importar funções de consulta
try:
    from poc_queries import (
        get_problematic_books,
        get_users_for_interview,
        get_roi_by_category,
        get_roi_by_author,
        get_sentiment_discrepancies,
        get_summary_stats,
        get_sentiment_distribution,
        # Novas análises
        get_best_worst_books,
        get_best_worst_publishers,
        get_best_worst_themes,
        get_reviews_by_period,
        get_reviews_by_year,
        get_trending_analysis,
        # Funções para IA
        search_books_for_summary,
        get_book_info,
        get_all_reviews_for_book
    )
    QUERIES_AVAILABLE = True
except ImportError as e:
    st.error(f"Erro ao importar funções de consulta: {e}")
    st.info("Verifique se poc_queries.py está na mesma pasta")
    QUERIES_AVAILABLE = False

# Importar funções de resumo IA
try:
    from ai_summary_functions import (
        test_openai_connection,
        search_books_for_summary,
        run_book_summary_analysis
    )
    SUMMARY_AVAILABLE = True
except ImportError:
    SUMMARY_AVAILABLE = False

# Configuração da página
st.set_page_config(
    page_title="POC - Análise de Livros",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para melhor visual
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 5px solid #1f77b4;
    margin-bottom: 1rem;
}
.alert-high { border-left-color: #d62728; }
.alert-medium { border-left-color: #ff7f0e; }
.alert-low { border-left-color: #2ca02c; }

.stApp > header {
    background-color: transparent;
}

.main-header {
    padding: 1rem 0;
    border-bottom: 2px solid #e6e6e6;
    margin-bottom: 2rem;
}

.status-ok {
    color: #2ca02c;
    font-weight: bold;
}

.status-error {
    color: #d62728;
    font-weight: bold;
}

.summary-box {
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 5px solid #1f77b4;
}

.positive-summary {
    background-color: #d4edda;
    border-left-color: #2ca02c;
}

.negative-summary {
    background-color: #f8d7da;
    border-left-color: #d62728;
}

.insights-summary {
    background-color: #d1ecf1;
    border-left-color: #1f77b4;
}
</style>
""", unsafe_allow_html=True)

def check_database_status():
    """Verifica se o banco de dados existe e está acessível."""
    db_path = "books_database.db"
    
    if not os.path.exists(db_path):
        return False, f"Banco de dados não encontrado: {db_path}"
    
    try:
        # Teste simples de conexão
        stats = get_summary_stats(db_path)
        return True, "Banco de dados conectado com sucesso"
    except Exception as e:
        return False, f"Erro ao conectar: {str(e)}"

def show_status_bar():
    """Mostra barra de status do sistema."""
    is_ok, message = check_database_status()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if is_ok:
            st.markdown(f'<span class="status-ok">✅ {message}</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="status-error">❌ {message}</span>', unsafe_allow_html=True)
    
    with col2:
        if st.button("🔄 Atualizar Status"):
            st.rerun()
    
    with col3:
        st.markdown("**Versão:** 1.1.0")

def main():
    """Função principal do app Streamlit."""
    
    # Verificar dependências básicas
    if not QUERIES_AVAILABLE:
        st.error("Módulo de consultas não disponível!")
        st.stop()
    
    # Header principal
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("📚 POC - Análise de Livros e Reviews")
    st.markdown("**Dashboard para tomada de decisões baseada em dados**")
    show_status_bar()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Verificar se banco existe antes de continuar
    is_ok, message = check_database_status()
    if not is_ok:
        st.error("🚨 Sistema não pode inicializar!")
        st.error(message)
        st.info("**Soluções:**")
        st.info("1. Execute: `python parquet_to_sqlite.py`")
        st.info("2. Verifique se os arquivos .parquet estão na pasta correta")
        st.info("3. Verifique se o banco foi criado na pasta frontend")
        
        if st.button("🔧 Tentar criar banco automaticamente"):
            with st.spinner("Criando banco de dados..."):
                try:
                    # Importar e executar criação do banco
                    import parquet_to_sqlite
                    parquet_to_sqlite.main()
                    st.success("Banco criado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar banco: {e}")
        return
    
    # Sidebar com navegação
    st.sidebar.title("🧭 Navegação")
    st.sidebar.markdown("---")
    
    # Lista de páginas dinâmica baseada na disponibilidade
    pages = [
        "🏠 Dashboard Geral",
        "⚠️ Livros Problemáticos", 
        "👥 Usuários para Entrevista",
        "💰 ROI por Categoria/Autor",
        "🔍 Discrepâncias de Sentimento",
        "📈 Análise de Desempenho",
        "📅 Análise Temporal"
    ]
    
    # Adicionar página de IA se disponível
    if SUMMARY_AVAILABLE:
        pages.append("📝 Resumo de Reviews IA")
    else:
        pages.append("📝 Resumo IA (Indisponível)")
    
    page = st.sidebar.selectbox("Escolha a análise:", pages)
    
    # Status dos módulos na sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Status dos Módulos")
    
    if QUERIES_AVAILABLE:
        st.sidebar.success("✅ Consultas SQL")
    else:
        st.sidebar.error("❌ Consultas SQL")
    
    if SUMMARY_AVAILABLE:
        st.sidebar.success("✅ Resumo IA")
    else:
        st.sidebar.warning("⚠️ Resumo IA (instale: openai, python-dotenv)")
    
    # Informações adicionais na sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Sobre a POC")
    st.sidebar.info(
        "Esta POC analisa dados de livros e reviews para "
        "identificar oportunidades de negócio e problemas de qualidade."
    )
    
    # Roteamento das páginas
    if page == "🏠 Dashboard Geral":
        show_dashboard()
    elif page == "⚠️ Livros Problemáticos":
        show_problematic_books()
    elif page == "👥 Usuários para Entrevista":
        show_users_interview()
    elif page == "💰 ROI por Categoria/Autor":
        show_roi_analysis()
    elif page == "🔍 Discrepâncias de Sentimento":
        show_sentiment_discrepancies()
    elif page == "📈 Análise de Desempenho":
        show_performance_analysis()
    elif page == "📅 Análise Temporal":
        show_temporal_analysis()
    elif page == "📝 Resumo de Reviews IA" and SUMMARY_AVAILABLE:
        show_reviews_summary()
    elif "Resumo IA" in page:
        show_summary_unavailable()

def show_summary_unavailable():
    """Página quando o módulo de IA não está disponível."""
    st.header("📝 Resumo de Reviews IA")
    st.error("🚨 Módulo de IA não disponível")
    
    st.markdown("""
    ### 🔧 Para ativar esta funcionalidade:
    
    1. **Instale as dependências:**
    ```bash
    pip install openai python-dotenv
    ```
    
    2. **Crie arquivo `.env` na pasta frontend:**
    ```env
    OPENAI_API_KEY=sua_chave_aqui
    ```
    
    3. **Obtenha sua chave OpenAI:**
    - Acesse: https://platform.openai.com/
    - Crie uma conta e gere uma API key
    - Adicione créditos à sua conta
    
    4. **Reinicie o Streamlit**
    """)
    
    st.info("💡 **Dica:** Esta funcionalidade permite gerar resumos automáticos de reviews positivos e negativos usando IA.")

def show_dashboard():
    """Dashboard geral com estatísticas principais."""
    
    st.header("📊 Dashboard Geral")
    
    # Carregar estatísticas
    with st.spinner("Carregando dados..."):
        try:
            stats = get_summary_stats("books_database.db")
            sentiment_dist = get_sentiment_distribution("books_database.db")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return
    
    # Métricas principais em cards
    st.subheader("📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="📚 Total de Livros",
            value=f"{stats.get('total_books', 0):,}",
            help="Número total de livros na base"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="💬 Total de Reviews",
            value=f"{stats.get('total_reviews', 0):,}",
            help="Número total de reviews analisados"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="👥 Usuários Únicos",
            value=f"{stats.get('total_users', 0):,}",
            help="Número de usuários que fizeram reviews"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        sentiment_val = stats.get('avg_sentiment', 0)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="😊 Sentimento Médio",
            value=f"{sentiment_val:.3f}",
            delta="Positivo" if sentiment_val > 0 else "Negativo",
            help="Score médio de sentimento (-1 a 1)"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos lado a lado
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Distribuição de Sentimentos")
        if not sentiment_dist.empty:
            fig = px.pie(
                sentiment_dist, 
                values='quantidade', 
                names='sentimento',
                color_discrete_map={
                    'positivo': '#2ca02c',
                    'neutro': '#ff7f0e', 
                    'negativo': '#d62728'
                },
                title="Proporção de Sentimentos"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Dados de sentimento não disponíveis")
    
    with col2:
        st.subheader("📊 Resumo Numérico")
        if not sentiment_dist.empty:
            # Tabela formatada
            sentiment_display = sentiment_dist.copy()
            sentiment_display['percentual'] = sentiment_display['percentual'].apply(lambda x: f"{x}%")
            
            st.dataframe(
                sentiment_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "sentimento": "Sentimento",
                    "quantidade": st.column_config.NumberColumn("Quantidade", format="%d"),
                    "percentual": "Percentual"
                }
            )
        
        # Quick insights
        st.subheader("🔍 Insights Rápidos")
        try:
            problematic = get_problematic_books(limit=3, db_path="books_database.db")
            if not problematic.empty:
                st.write("**Top 3 Livros Problemáticos:**")
                for idx, row in problematic.iterrows():
                    st.write(f"• {row['titulo'][:40]}... (Score: {row['problema_score']:.1f})")
            else:
                st.info("✅ Nenhum livro altamente problemático identificado")
        except Exception as e:
            st.warning(f"Erro ao carregar insights: {e}")

def show_problematic_books():
    """Página de análise de livros problemáticos."""
    
    st.header("⚠️ Livros Mais Problemáticos")
    st.markdown("Identificação de livros com alta taxa de reviews negativos e baixo sentimento.")
    
    # Controles em colunas
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        limit = st.slider("Número de livros", min_value=10, max_value=50, value=20)
    with col2:
        show_details = st.checkbox("Mostrar detalhes", value=True)
    
    # Carregar dados
    with st.spinner("Analisando livros problemáticos..."):
        try:
            df = get_problematic_books(limit=limit, db_path="books_database.db")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return
    
    if df.empty:
        st.success("✅ Nenhum livro altamente problemático encontrado!")
        st.balloons()
        return
    
    # Métricas de alerta em cards visuais
    st.subheader("🚨 Níveis de Risco")
    
    high_problem = len(df[df['problema_score'] > 50])
    medium_problem = len(df[(df['problema_score'] > 25) & (df['problema_score'] <= 50)])
    low_problem = len(df[df['problema_score'] <= 25])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card alert-high">', unsafe_allow_html=True)
        st.metric("🚨 Alto Risco", high_problem, help="Score > 50")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card alert-medium">', unsafe_allow_html=True)
        st.metric("⚠️ Médio Risco", medium_problem, help="Score 25-50")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card alert-low">', unsafe_allow_html=True)
        st.metric("⚡ Baixo Risco", low_problem, help="Score < 25")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Visualizações
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras horizontal
        fig = px.bar(
            df.head(15), 
            x='problema_score', 
            y='titulo',
            orientation='h',
            color='problema_score',
            color_continuous_scale='Reds',
            title="Score de Problema por Livro",
            labels={'problema_score': 'Score Problema', 'titulo': 'Livro'}
        )
        fig.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
        fig.update_traces(texttemplate='%{x:.1f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribuição dos scores
        fig = px.histogram(
            df,
            x='problema_score',
            nbins=10,
            title="Distribuição dos Scores de Problema",
            labels={'problema_score': 'Score Problema', 'count': 'Frequência'}
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela detalhada
    if show_details:
        st.subheader("📋 Detalhes dos Livros Problemáticos")
        
        # Adicionar filtro por score
        min_score = st.slider("Score mínimo", 0, 100, 0)
        df_filtered = df[df['problema_score'] >= min_score]
        
        # Formatação da tabela
        df_display = df_filtered.copy()
        df_display['titulo'] = df_display['titulo'].str[:60] + '...'
        df_display['autor'] = df_display['autor'].str[:30] + '...'
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "titulo": "Título",
                "autor": "Autor", 
                "categoria": "Categoria",
                "total_reviews": st.column_config.NumberColumn("Total Reviews", format="%d"),
                "reviews_negativos": st.column_config.NumberColumn("Reviews Negativos", format="%d"),
                "pct_negativo": st.column_config.NumberColumn(
                    "% Negativo",
                    help="Percentual de reviews negativos",
                    format="%.1f%%"
                ),
                "compound_medio": st.column_config.NumberColumn(
                    "Sentimento Médio",
                    help="Score médio de sentimento",
                    format="%.3f"
                ),
                "problema_score": st.column_config.NumberColumn(
                    "Score Problema",
                    help="Quanto maior, mais problemático",
                    format="%.1f"
                )
            }
        )
        
        # Opção de download
        if st.button("📥 Download CSV"):
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                label="⬇️ Baixar dados",
                data=csv,
                file_name="livros_problematicos.csv",
                mime="text/csv"
            )

def show_users_interview():
    """Página de seleção de usuários para entrevista."""
    
    st.header("👥 Usuários para Entrevista")
    st.markdown("Seleção estratégica de usuários segmentados para pesquisa qualitativa.")
    
    # Controles
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.slider("Número de usuários", min_value=20, max_value=100, value=50)
    with col2:
        segment_filter = st.selectbox(
            "Filtrar por segmento",
            ["Todos", "Otimista", "Crítico", "Equilibrado", "Ativo", "Regular"]
        )
    with col3:
        min_reviews = st.number_input("Mínimo de reviews", min_value=1, max_value=50, value=3)
    
    # Carregar dados
    with st.spinner("Selecionando usuários..."):
        try:
            df = get_users_for_interview(limit=limit, db_path="books_database.db")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return
    
    if df.empty:
        st.warning("Nenhum usuário encontrado com os critérios selecionados.")
        return
    
    # Filtrar por segmento e reviews mínimos
    if segment_filter != "Todos":
        df = df[df['segmento'] == segment_filter]
    
    df = df[df['total_reviews'] >= min_reviews]
    
    # Estatísticas dos usuários selecionados
    st.subheader("📊 Perfil dos Usuários Selecionados")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Selecionados", len(df))
    with col2:
        st.metric("📚 Média de Reviews", f"{df['total_reviews'].mean():.1f}")
    with col3:
        st.metric("🎯 Score Médio", f"{df['diversidade_score'].mean():.1f}")
    with col4:
        st.metric("😊 Sentimento Médio", f"{df['compound_medio'].mean():.3f}")
    
    # Visualizações
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Distribuição por Segmento")
        segment_counts = df['segmento'].value_counts()
        fig = px.pie(
            values=segment_counts.values,
            names=segment_counts.index,
            title="Usuários por Segmento"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Score vs Reviews")
        fig = px.scatter(
            df,
            x='total_reviews',
            y='diversidade_score',
            color='segmento',
            size='categorias_diversas',
            hover_data=['User_id', 'compound_medio'],
            title="Relação Score Diversidade x Total Reviews"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela de usuários
    st.subheader("📋 Lista de Usuários Selecionados")
    
    # Opções de exibição
    col1, col2 = st.columns(2)
    with col1:
        show_all_columns = st.checkbox("Mostrar todas as colunas")
    with col2:
        if st.button("📥 Preparar Download"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="usuarios_entrevista.csv",
                mime="text/csv"
            )
    
    # Configurar colunas a exibir
    if show_all_columns:
        columns_to_show = df.columns.tolist()
    else:
        columns_to_show = ['User_id', 'segmento', 'total_reviews', 'diversidade_score', 'compound_medio']
    
    st.dataframe(
        df[columns_to_show],
        use_container_width=True,
        hide_index=True,
        column_config={
            "User_id": "ID Usuário",
            "segmento": "Segmento",
            "total_reviews": st.column_config.NumberColumn("Total Reviews", format="%d"),
            "sentimentos_diversos": st.column_config.NumberColumn("Sentimentos Diversos", format="%d"),
            "categorias_diversas": st.column_config.NumberColumn("Categorias Diversas", format="%d"),
            "diversidade_score": st.column_config.NumberColumn(
                "Score Diversidade",
                help="Quanto maior, mais interessante para entrevista",
                format="%.1f"
            ),
            "compound_medio": st.column_config.NumberColumn(
                "Sentimento Médio",
                help="Score médio de sentimento (-1 a 1)",
                format="%.3f"
            )
        }
    )


def show_roi_analysis():
    """Página de análise de ROI por categoria e autor."""
    
    st.header("💰 Análise de ROI")
    st.markdown("Retorno sobre investimento estimado por categoria e autor.")
    
    # Tabs para categoria e autor
    tab1, tab2 = st.tabs(["📚 Por Categoria", "✍️ Por Autor"])
    
    with tab1:
        st.subheader("💼 ROI por Categoria")
        
        with st.spinner("Calculando ROI por categoria..."):
            try:
                df_cat = get_roi_by_category(db_path="books_database.db")
            except Exception as e:
                st.error(f"Erro ao carregar dados de categoria: {e}")
                return
        
        if not df_cat.empty:
            # Métricas resumo
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏆 Melhor Categoria", df_cat.iloc[0]['categoria'])
            with col2:
                st.metric("💰 Melhor ROI", f"{df_cat.iloc[0]['roi_estimado']:.2f}")
            with col3:
                st.metric("📚 Total Categorias", len(df_cat))
            
            # Visualizações para categorias
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico scatter ROI vs Volume para categorias
                fig = px.scatter(
                    df_cat,
                    x='total_livros',
                    y='roi_estimado',
                    size='total_reviews',
                    hover_data=['categoria', 'sentimento_medio'],
                    title="ROI vs Volume de Livros (Categorias)",
                    labels={'total_livros': 'Total de Livros', 'roi_estimado': 'ROI Estimado'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Top 10 categorias
                fig = px.bar(
                    df_cat.head(10),
                    x='roi_estimado',
                    y='categoria',
                    orientation='h',
                    title="Top 10 Categorias por ROI"
                )
                fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada categorias
            st.subheader("📊 Dados Detalhados - Categorias")
            df_cat_display = df_cat.copy()
            df_cat_display['categoria'] = df_cat_display['categoria'].str[:50] + '...'
            
            st.dataframe(
                df_cat_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "categoria": "Categoria",
                    "total_livros": st.column_config.NumberColumn("Total Livros", format="%d"),
                    "total_reviews": st.column_config.NumberColumn("Total Reviews", format="%d"),
                    "reviews_por_livro": st.column_config.NumberColumn("Reviews/Livro", format="%.2f"),
                    "sentimento_medio": st.column_config.NumberColumn("Sentimento Médio", format="%.3f"),
                    "pct_positivo": st.column_config.NumberColumn("% Positivo", format="%.1f%%"),
                    "roi_estimado": st.column_config.NumberColumn(
                        "ROI Estimado",
                        help="Retorno sobre investimento estimado",
                        format="%.2f"
                    )
                }
            )
        else:
            st.warning("Dados de ROI por categoria não disponíveis")
    
    with tab2:
        st.subheader("✍️ ROI por Autor")
        
        with st.spinner("Calculando ROI por autor..."):
            try:
                df_author = get_roi_by_author(db_path="books_database.db")
            except Exception as e:
                st.error(f"Erro ao carregar dados de autor: {e}")
                return
        
        if not df_author.empty:
            # Métricas resumo
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏆 Melhor Autor", df_author.iloc[0]['autor'][:30] + "...")
            with col2:
                st.metric("💰 Melhor ROI", f"{df_author.iloc[0]['roi_estimado']:.2f}")
            with col3:
                st.metric("✍️ Total Autores", len(df_author))
            
            # Visualizações para autores
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico scatter ROI vs Volume para autores
                fig = px.scatter(
                    df_author,
                    x='total_livros',
                    y='roi_estimado',
                    size='total_reviews',
                    hover_data=['autor', 'sentimento_medio'],
                    title="ROI vs Volume de Livros (Autores)",
                    labels={'total_livros': 'Total de Livros', 'roi_estimado': 'ROI Estimado'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Top 10 autores
                fig = px.bar(
                    df_author.head(10),
                    x='roi_estimado',
                    y='autor',
                    orientation='h',
                    title="Top 10 Autores por ROI"
                )
                fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada autores
            st.subheader("📊 Dados Detalhados - Autores")
            df_author_display = df_author.copy()
            df_author_display['autor'] = df_author_display['autor'].str[:50] + '...'
            
            st.dataframe(
                df_author_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "autor": "Autor",
                    "total_livros": st.column_config.NumberColumn("Total Livros", format="%d"),
                    "total_reviews": st.column_config.NumberColumn("Total Reviews", format="%d"),
                    "reviews_por_livro": st.column_config.NumberColumn("Reviews/Livro", format="%.2f"),
                    "sentimento_medio": st.column_config.NumberColumn("Sentimento Médio", format="%.3f"),
                    "pct_positivo": st.column_config.NumberColumn("% Positivo", format="%.1f%%"),
                    "roi_estimado": st.column_config.NumberColumn(
                        "ROI Estimado",
                        help="Retorno sobre investimento estimado",
                        format="%.2f"
                    )
                }
            )
        else:
            st.warning("Dados de ROI por autor não disponíveis")


def show_sentiment_discrepancies():
    """Página de análise de discrepâncias de sentimento."""
    
    st.header("🔍 Discrepâncias de Sentimento")
    st.markdown("Identificação de casos onde a classificação automática pode estar incorreta.")
    
    # Controles
    col1, col2, col3 = st.columns(3)
    with col1:
        limit = st.slider("Número de casos", min_value=20, max_value=100, value=50)
    with col2:
        level_filter = st.selectbox(
            "Filtrar por nível",
            ["Todos", "Alto", "Médio", "Baixo"]
        )
    with col3:
        show_reviews = st.checkbox("Mostrar reviews", value=False)
    
    # Carregar dados
    with st.spinner("Analisando discrepâncias..."):
        try:
            df = get_sentiment_discrepancies(limit=limit, db_path="books_database.db")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return
    
    if df.empty:
        st.success("✅ Nenhuma discrepância significativa encontrada!")
        st.balloons()
        return
    
    # Filtrar por nível se selecionado
    if level_filter != "Todos":
        df = df[df['nivel_discrepancia'] == level_filter]
    
    if df.empty:
        st.warning(f"Nenhuma discrepância de nível '{level_filter}' encontrada.")
        return
    
    # Métricas de discrepância
    st.subheader("🚨 Análise de Discrepâncias")
    
    high_disc = len(df[df['nivel_discrepancia'] == 'Alto'])
    medium_disc = len(df[df['nivel_discrepancia'] == 'Médio'])
    low_disc = len(df[df['nivel_discrepancia'] == 'Baixo'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card alert-high">', unsafe_allow_html=True)
        st.metric("🚨 Discrepância Alta", high_disc)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card alert-medium">', unsafe_allow_html=True)
        st.metric("⚠️ Discrepância Média", medium_disc)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card alert-low">', unsafe_allow_html=True)
        st.metric("⚡ Discrepância Baixa", low_disc)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.metric("🎯 Total Analisados", len(df))
    
    # Visualizações
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribuição por Nível")
        level_counts = df['nivel_discrepancia'].value_counts()
        fig = px.pie(
            values=level_counts.values,
            names=level_counts.index,
            color_discrete_map={
                'Alto': '#d62728',
                'Médio': '#ff7f0e',
                'Baixo': '#2ca02c'
            },
            title="Discrepâncias por Nível"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Score vs Compound")
        fig = px.scatter(
            df,
            x='compound_score',
            y='score_discrepancia',
            color='nivel_discrepancia',
            hover_data=['sentimento_classificado', 'sentimento_esperado'],
            title="Discrepância vs Compound Score",
            color_discrete_map={
                'Alto': '#d62728',
                'Médio': '#ff7f0e',
                'Baixo': '#2ca02c'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Análise detalhada de casos
    if show_reviews:
        st.subheader("🔍 Análise Detalhada de Casos")
        
        # Mostrar casos mais críticos
        critical_cases = df[df['nivel_discrepancia'] == 'Alto'].head(5)
        
        if not critical_cases.empty:
            st.write("**🚨 Casos mais críticos:**")
            
            for idx, row in critical_cases.iterrows():
                with st.expander(f"📖 {row['titulo'][:50]}... | Score: {row['score_discrepancia']:.3f}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**📝 Texto do Review:**")
                        st.write(f"_{row['review_preview']}_")
                        
                    with col2:
                        st.write("**🧠 Análise Automática:**")
                        st.write(f"**Classificado como:** `{row['sentimento_classificado']}`")
                        st.write(f"**Deveria ser:** `{row['sentimento_esperado']}`")
                        st.write(f"**Compound Score:** `{row['compound_score']}`")
                        st.write(f"**Nível de Discrepância:** `{row['nivel_discrepancia']}`")
                        
                        # Sugestão de ação
                        if row['nivel_discrepancia'] == 'Alto':
                            st.error("🔴 **Ação:** Revisar classificação manualmente")
                        elif row['nivel_discrepancia'] == 'Médio':
                            st.warning("🟡 **Ação:** Validar com mais dados")
                        else:
                            st.info("🟢 **Ação:** Monitorar tendência")
    
    # Tabela resumo
    st.subheader("📋 Resumo das Discrepâncias")
    
    # Opções de visualização
    col1, col2 = st.columns(2)
    with col1:
        show_full_text = st.checkbox("Mostrar texto completo do review")
    with col2:
        if st.button("📥 Download Discrepâncias"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv,
                file_name="discrepancias_sentimento.csv",
                mime="text/csv"
            )
    
    # Preparar dados para exibição
    df_display = df.copy()
    if not show_full_text:
        df_display['review_preview'] = df_display['review_preview'].str[:100] + '...'
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "titulo": "Título do Livro",
            "review_preview": "Texto do Review",
            "sentimento_classificado": "Classificado",
            "sentimento_esperado": "Esperado",
            "compound_score": st.column_config.NumberColumn(
                "Compound Score",
                help="Score de sentimento VADER",
                format="%.3f"
            ),
            "nivel_discrepancia": "Nível",
            "score_discrepancia": st.column_config.NumberColumn(
                "Score Discrepância",
                help="Intensidade da discrepância",
                format="%.3f"
            )
        }
    )
    
    # Insights e recomendações
    st.subheader("💡 Insights e Recomendações")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **🎯 O que fazer com discrepâncias altas:**
        - Revisar manualmente os casos
        - Ajustar thresholds do modelo
        - Treinar com mais dados específicos
        - Considerar contexto do domínio (livros)
        """)
    
    with col2:
        st.success("""
        **✅ Próximos passos:**
        - Criar dataset de validação manual
        - Implementar feedback loop
        - Monitorar performance contínua
        - Documentar casos especiais
        """)


def show_performance_analysis():
    """Página de análise de desempenho (melhores e piores)."""
    
    st.header("📈 Análise de Desempenho")
    st.markdown("Comparação entre melhores e piores livros, editoras e temas.")
    
    # Tabs para diferentes análises
    tab1, tab2, tab3 = st.tabs(["📚 Livros", "🏢 Editoras", "🏷️ Temas"])
    
    with tab1:
        st.subheader("📊 Desempenho de Livros")
        
        # Controles
        col1, col2 = st.columns(2)
        with col1:
            limit_books = st.slider("Número de livros por categoria", min_value=5, max_value=25, value=15)
        with col2:
            show_comparison = st.checkbox("Mostrar comparação lado a lado", value=True)
        
        with st.spinner("Analisando desempenho dos livros..."):
            try:
                books_data = get_best_worst_books(limit=limit_books, db_path="books_database.db")
            except Exception as e:
                st.error(f"Erro ao carregar dados: {e}")
                return
        
        if show_comparison and not books_data['melhores'].empty and not books_data['piores'].empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏆 Melhores Livros")
                st.success(f"Top {len(books_data['melhores'])} livros com melhor desempenho")
                
                # Gráfico dos melhores
                fig = px.bar(
                    books_data['melhores'].head(10),
                    x='performance_score',
                    y='titulo',
                    orientation='h',
                    color='performance_score',
                    color_continuous_scale='Greens',
                    title="Score de Performance"
                )
                fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Top 5 em tabela
                st.dataframe(
                    books_data['melhores'].head(5)[['titulo', 'autor', 'performance_score', 'sentimento_medio']],
                    use_container_width=True,
                    hide_index=True
                )
            
            with col2:
                st.markdown("### ⚠️ Piores Livros")
                st.error(f"Top {len(books_data['piores'])} livros com pior desempenho")
                
                # Gráfico dos piores
                fig = px.bar(
                    books_data['piores'].head(10),
                    x='problema_score',
                    y='titulo',
                    orientation='h',
                    color='problema_score',
                    color_continuous_scale='Reds',
                    title="Score de Problema"
                )
                fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Top 5 em tabela
                st.dataframe(
                    books_data['piores'].head(5)[['titulo', 'autor', 'problema_score', 'sentimento_medio']],
                    use_container_width=True,
                    hide_index=True
                )
        
        else:
            # Mostrar sequencial
            if not books_data['melhores'].empty:
                st.markdown("### 🏆 Melhores Livros")
                st.dataframe(books_data['melhores'], use_container_width=True, hide_index=True)
            
            if not books_data['piores'].empty:
                st.markdown("### ⚠️ Piores Livros")
                st.dataframe(books_data['piores'], use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("🏢 Desempenho de Editoras")
        
        limit_publishers = st.slider("Número de editoras por categoria", min_value=5, max_value=20, value=10)
        
        with st.spinner("Analisando desempenho das editoras..."):
            try:
                publishers_data = get_best_worst_publishers(limit=limit_publishers, db_path="books_database.db")
            except Exception as e:
                st.error(f"Erro ao carregar dados: {e}")
                return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏆 Melhores Editoras")
            if not publishers_data['melhores'].empty:
                # Gráfico
                fig = px.scatter(
                    publishers_data['melhores'],
                    x='total_livros',
                    y='performance_score',
                    size='total_reviews',
                    hover_data=['editora', 'sentimento_medio'],
                    title="Performance vs Volume",
                    color='sentimento_medio',
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela
                st.dataframe(
                    publishers_data['melhores'][['editora', 'total_livros', 'performance_score', 'sentimento_medio']],
                    use_container_width=True,
                    hide_index=True
                )
        
        with col2:
            st.markdown("### ⚠️ Piores Editoras")
            if not publishers_data['piores'].empty:
                # Gráfico
                fig = px.scatter(
                    publishers_data['piores'],
                    x='total_livros',
                    y='problema_score',
                    size='total_reviews',
                    hover_data=['editora', 'sentimento_medio'],
                    title="Problemas vs Volume",
                    color='sentimento_medio',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela
                st.dataframe(
                    publishers_data['piores'][['editora', 'total_livros', 'problema_score', 'sentimento_medio']],
                    use_container_width=True,
                    hide_index=True
                )
    
    with tab3:
        st.subheader("🏷️ Desempenho de Temas")
        
        limit_themes = st.slider("Número de temas por categoria", min_value=5, max_value=20, value=12)
        
        with st.spinner("Analisando desempenho dos temas..."):
            try:
                themes_data = get_best_worst_themes(limit=limit_themes, db_path="books_database.db")
            except Exception as e:
                st.error(f"Erro ao carregar dados: {e}")
                return
        
        # Comparação visual
        if not themes_data['melhores'].empty and not themes_data['piores'].empty:
            # Gráfico comparativo
            st.subheader("📊 Comparação de Performance por Tema")
            
            # Combinar dados para comparação
            best_themes = themes_data['melhores'].head(8).copy()
            best_themes['categoria'] = 'Melhores'
            best_themes['score'] = best_themes['performance_score']
            
            worst_themes = themes_data['piores'].head(8).copy()
            worst_themes['categoria'] = 'Piores'
            worst_themes['score'] = worst_themes['problema_score']
            
            combined = pd.concat([
                best_themes[['tema', 'categoria', 'score', 'sentimento_medio']],
                worst_themes[['tema', 'categoria', 'score', 'sentimento_medio']]
            ])
            
            fig = px.bar(
                combined,
                x='score',
                y='tema',
                color='categoria',
                orientation='h',
                title="Comparação: Melhores vs Piores Temas",
                color_discrete_map={'Melhores': '#2ca02c', 'Piores': '#d62728'}
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabelas detalhadas
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏆 Melhores Temas")
            if not themes_data['melhores'].empty:
                st.dataframe(
                    themes_data['melhores'][['tema', 'total_livros', 'performance_score', 'pct_positivo']],
                    use_container_width=True,
                    hide_index=True
                )
        
        with col2:
            st.markdown("### ⚠️ Piores Temas")
            if not themes_data['piores'].empty:
                st.dataframe(
                    themes_data['piores'][['tema', 'total_livros', 'problema_score', 'pct_negativo']],
                    use_container_width=True,
                    hide_index=True
                )


def show_temporal_analysis():
    """Página de análise temporal."""
    
    st.header("📅 Análise Temporal")
    st.markdown("Evolução dos reviews e sentimentos ao longo do tempo.")
    
    # Análise por períodos
    st.subheader("📊 Análise por Períodos")
    
    with st.spinner("Carregando análise temporal..."):
        try:
            periods_data = get_reviews_by_period(db_path="books_database.db")
            trending_data = get_trending_analysis(db_path="books_database.db")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return
    
    if not periods_data.empty:
        # Métricas de tendência
        if trending_data.get('tendencias'):
            st.subheader("📈 Tendências Gerais")
            
            col1, col2, col3 = st.columns(3)
            
            trends = trending_data['tendencias']
            
            with col1:
                sentiment_trend = trends.get('sentimento_trend', 0)
                st.metric(
                    "Tendência Sentimento",
                    f"{sentiment_trend:+.3f}",
                    delta="Melhorando" if sentiment_trend > 0 else "Piorando" if sentiment_trend < 0 else "Estável"
                )
            
            with col2:
                reviews_trend = trends.get('reviews_trend', 0)
                st.metric(
                    "Tendência Engajamento",
                    f"{reviews_trend:+.1f}",
                    delta="Aumentando" if reviews_trend > 0 else "Diminuindo" if reviews_trend < 0 else "Estável"
                )
            
            with col3:
                positive_trend = trends.get('positivo_trend', 0)
                st.metric(
                    "Tendência % Positivo",
                    f"{positive_trend:+.1f}%",
                    delta="Melhorando" if positive_trend > 0 else "Piorando" if positive_trend < 0 else "Estável"
                )
        
        # Visualizações
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de sentimento por período
            fig = px.bar(
                periods_data,
                x='periodo',
                y='sentimento_medio',
                color='sentimento_medio',
                color_continuous_scale='RdYlGn',
                title="Sentimento Médio por Período"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Gráfico de volume por período
            fig = px.bar(
                periods_data,
                x='periodo',
                y='total_reviews',
                color='reviews_por_livro',
                color_continuous_scale='Blues',
                title="Volume de Reviews por Período"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de evolução
        st.subheader("📈 Evolução Detalhada")
        
        fig = px.line(
            periods_data,
            x='periodo',
            y=['pct_positivo', 'pct_negativo'],
            title="Evolução: % Positivos vs % Negativos",
            labels={'value': 'Percentual', 'variable': 'Tipo'}
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela detalhada
        st.subheader("📋 Dados Detalhados por Período")
        
        st.dataframe(
            periods_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "periodo": "Período",
                "total_livros": st.column_config.NumberColumn("Total Livros", format="%d"),
                "total_reviews": st.column_config.NumberColumn("Total Reviews", format="%d"),
                "reviews_por_livro": st.column_config.NumberColumn("Reviews/Livro", format="%.1f"),
                "sentimento_medio": st.column_config.NumberColumn("Sentimento Médio", format="%.3f"),
                "pct_positivo": st.column_config.NumberColumn("% Positivo", format="%.1f%%"),
                "pct_negativo": st.column_config.NumberColumn("% Negativo", format="%.1f%%")
            }
        )
    
    # Análise por ano específico
    st.subheader("📅 Análise Anual Detalhada")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        start_year = st.number_input(
            "Ano inicial", 
            min_value=1990, 
            max_value=2024, 
            value=2010,
            help="Análise detalhada ano a ano"
        )
    
    with col2:
        if st.button("🔍 Analisar por Anos"):
            with st.spinner("Carregando dados anuais..."):
                try:
                    yearly_data = get_reviews_by_year(start_year=start_year, db_path="books_database.db")
                    
                    if not yearly_data.empty:
                        # Gráfico temporal anual
                        fig = px.line(
                            yearly_data,
                            x='ano',
                            y='sentimento_medio',
                            title=f"Evolução do Sentimento ({start_year}-2024)",
                            markers=True
                        )
                        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutro")
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabela anual
                        st.dataframe(
                            yearly_data.head(15),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.warning(f"Nenhum dado encontrado para o período a partir de {start_year}")
                        
                except Exception as e:
                    st.error(f"Erro na análise anual: {e}")


def show_reviews_summary():
    """Página de resumo de reviews com IA."""
    
    st.header("📝 Resumo de Reviews IA")
    st.markdown("Análise automática de reviews usando Inteligência Artificial.")
    
    # Verificar conexão OpenAI
    from ai_summary_functions import test_openai_connection, get_available_books_for_analysis, run_book_summary_analysis, format_summary_for_display
    
    # Status da conexão
    st.subheader("🔌 Status da Conexão")
    
    with st.spinner("Verificando conexão OpenAI..."):
        is_connected, connection_message = test_openai_connection()
    
    if is_connected:
        st.success(f"✅ {connection_message}")
    else:
        st.error(f"❌ {connection_message}")
        st.stop()
    
    # Interface de busca e seleção
    st.subheader("🔍 Selecionar Livro para Análise")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input(
            "Buscar livro por título ou autor:",
            placeholder="Ex: Harry Potter, Stephen King, etc."
        )
    
    with col2:
        search_limit = st.number_input("Máximo de resultados", min_value=5, max_value=20, value=10)
    
    # Buscar livros disponíveis
    if st.button("🔍 Buscar Livros") or not search_query:
        with st.spinner("Buscando livros disponíveis..."):
            try:
                available_books = get_available_books_for_analysis(
                    query=search_query, 
                    limit=search_limit, 
                    db_path="books_database.db"
                )
                
                if not available_books.empty:
                    st.subheader("📚 Livros Disponíveis")
                    
                    # Exibir livros em formato selecionável
                    for idx, book in available_books.iterrows():
                        with st.expander(
                            f"📖 {book['titulo']} - {book['autor']} "
                            f"({book['total_reviews']} reviews, sentimento: {book['sentimento_medio']:.3f})"
                        ):
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                st.write(f"**Título:** {book['titulo']}")
                                st.write(f"**Autor:** {book['autor']}")
                                st.write(f"**Categoria:** {book.get('categoria', 'N/A')}")
                            
                            with col2:
                                st.metric("Total Reviews", book['total_reviews'])
                                st.metric("Reviews Positivos", book['positivos'])
                            
                            with col3:
                                st.metric("Reviews Negativos", book['negativos'])
                                st.metric("Sentimento Médio", f"{book['sentimento_medio']:.3f}")
                            
                            # Botão para analisar este livro
                            if st.button(f"🤖 Analisar com IA", key=f"analyze_{idx}"):
                                analyze_book_with_ai(book['titulo'])
                else:
                    st.warning("Nenhum livro encontrado com os critérios especificados.")
                    st.info("💡 **Dica:** Tente termos mais genéricos ou deixe em branco para ver os livros mais populares.")
                    
            except Exception as e:
                st.error(f"Erro na busca: {e}")


def analyze_book_with_ai(book_title):
    """Executa análise de IA para um livro específico."""
    
    st.subheader(f"🤖 Análise IA: {book_title}")
    
    with st.spinner("Analisando reviews com IA... (pode levar 30-60 segundos)"):
        try:
            from ai_summary_functions import run_book_summary_analysis, format_summary_for_display
            
            # Executar análise
            analysis_result = run_book_summary_analysis(book_title, "books_database.db")
            
            if not analysis_result:
                st.error("Erro na análise - resultado vazio")
                return
            
            result, message = analysis_result
            
            if not result:
                st.error(f"Erro na análise: {message}")
                return
            
            # Formatar para exibição
            formatted = format_summary_for_display(analysis_result)
            
            if formatted.get('status') == 'success':
                display_analysis_results(formatted)
            else:
                st.error(f"Erro na formatação: {formatted.get('error', 'Erro desconhecido')}")
                
        except Exception as e:
            st.error(f"Erro durante a análise: {e}")
            st.info("💡 Verifique se sua chave OpenAI tem créditos suficientes.")


def display_analysis_results(analysis_data):
    """Exibe os resultados da análise de IA."""
    
    book_info = analysis_data['book_info']
    insights = analysis_data['general_insights']
    summaries = analysis_data['summaries']
    
    # Informações gerais do livro
    st.subheader("📊 Resumo Executivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Reviews", book_info.get('total_reviews', 0))
    with col2:
        st.metric("Reviews Positivos", book_info.get('total_positivos', 0))
    with col3:
        st.metric("Reviews Negativos", book_info.get('total_negativos', 0))
    with col4:
        st.metric("Sentimento Médio", f"{book_info.get('sentimento_medio', 0):.3f}")
    
    # Recomendação de negócio
    st.subheader("💼 Recomendação de Negócio")
    
    recommendation = insights.get('recommendation', '')
    priority = insights.get('business_priority', 'Média')
    
    if '✅' in recommendation:
        st.success(recommendation)
    elif '⚠️' in recommendation:
        st.error(recommendation)
    elif '🔄' in recommendation:
        st.info(recommendation)
    else:
        st.warning(recommendation)
    
    st.write(f"**Prioridade de Negócio:** {priority}")
    
    # Resumos de IA por sentimento
    st.subheader("🤖 Resumos Gerados por IA")
    
    # Tabs para cada tipo de sentimento
    tab1, tab2, tab3 = st.tabs(["😊 Reviews Positivos", "😟 Reviews Negativos", "😐 Reviews Neutros"])
    
    with tab1:
        display_sentiment_summary(summaries.get('positivos', {}), '😊', 'positive')
    
    with tab2:
        display_sentiment_summary(summaries.get('negativos', {}), '😟', 'negative')
    
    with tab3:
        display_sentiment_summary(summaries.get('neutros', {}), '😐', 'neutral')
    
    # Gráfico de distribuição
    st.subheader("📈 Distribuição de Sentimentos")
    
    sentiment_data = {
        'Positivos': book_info.get('total_positivos', 0),
        'Negativos': book_info.get('total_negativos', 0),
        'Neutros': book_info.get('total_neutros', 0)
    }
    
    fig = px.pie(
        values=list(sentiment_data.values()),
        names=list(sentiment_data.keys()),
        color_discrete_map={
            'Positivos': '#2ca02c',
            'Neutros': '#ff7f0e',
            'Negativos': '#d62728'
        },
        title=f"Distribuição de Reviews - {book_info.get('titulo', '')}"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_sentiment_summary(summary_data, emoji, sentiment_class):
    """Exibe resumo de um tipo específico de sentimento."""
    
    if not summary_data.get('has_data'):
        st.warning(f"{emoji} {summary_data.get('message', 'Nenhum resumo disponível')}")
        return
    
    total_reviews = summary_data.get('total_reviews', 0)
    summary_text = summary_data.get('summary', '')
    
    st.success(f"{emoji} **{total_reviews} reviews analisados**")
    
    # Exibir resumo em caixa estilizada
    css_class = f"{sentiment_class}-summary"
    
    st.markdown(f"""
    <div class="summary-box {css_class}">
        <h4>{emoji} Resumo da IA:</h4>
        <p>{summary_text}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão para ver reviews originais
    if st.button(f"📖 Ver Reviews Originais {emoji}", key=f"show_{sentiment_class}"):
        with st.expander(f"Reviews {sentiment_class.title()} Originais"):
            # Aqui você poderia mostrar alguns reviews originais se necessário
            st.info("Esta funcionalidade mostraria alguns reviews originais para validação.")


# Funções auxiliares (mantidas as existentes)


# Funções auxiliares
def format_number(num):
    """Formatar números para exibição."""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return str(num)


def create_alert_box(message, alert_type="info"):
    """Criar caixa de alerta customizada."""
    colors = {
        "info": "#d1ecf1",
        "warning": "#fff3cd", 
        "danger": "#f8d7da",
        "success": "#d4edda"
    }
    
    st.markdown(f"""
    <div style="
        padding: 0.75rem 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid transparent;
        border-radius: 0.25rem;
        background-color: {colors.get(alert_type, colors['info'])};
    ">
    {message}
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    # Verificar se o banco existe
    db_path = "books_database.db"
    if not os.path.exists(db_path):
        st.error("🚨 Banco de dados não encontrado!")
        st.info("**Soluções:**")
        st.info("1. Execute: `python parquet_to_sqlite.py`")
        st.info("2. Certifique-se que os arquivos .parquet estão disponíveis")
        st.info("3. Verifique se está executando da pasta frontend")
        st.stop()
    
    main()