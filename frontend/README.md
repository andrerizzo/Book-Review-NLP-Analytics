# 📚 POC - Análise de Livros e Reviews

Frontend em Streamlit para análise de dados de livros e reviews, focado em tomada de decisões de negócio.

## 🎯 Objetivo

Esta POC (Proof of Concept) demonstra análises de dados para:
- Identificar livros problemáticos
- Selecionar usuários para entrevistas
- Calcular ROI por categoria/autor
- Detectar discrepâncias de sentimento

## 🛠️ Configuração Rápida

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Preparar Banco de Dados
```bash
# Opção A: Criação automática (recomendado)
python parquet_to_sqlite.py

# Opção B: Copiar banco existente
# Copie books_database.db para esta pasta
```

### 3. Executar Frontend
```bash
streamlit run streamlit_poc.py
```

Acesse: http://localhost:8501

## 📁 Estrutura de Arquivos

```
frontend/
├── streamlit_poc.py          # Interface principal
├── poc_queries.py            # Consultas SQL
├── parquet_to_sqlite.py      # Criador do banco
├── books_database.db         # Banco SQLite (gerado)
├── requirements.txt          # Dependências
└── README.md                # Este arquivo
```

## 🔧 Funcionalidades

### 🏠 Dashboard Geral
- Métricas principais (livros, reviews, usuários)
- Distribuição de sentimentos
- Insights rápidos

### ⚠️ Livros Problemáticos
- Identifica livros com reviews negativos
- Score de problema baseado em múltiplos fatores
- Categorização por nível de risco

### 👥 Usuários para Entrevista
- Segmentação de usuários por perfil
- Score de diversidade para seleção
- Filtros por segmento e atividade

### 💰 ROI por Categoria/Autor
- Análise de retorno sobre investimento
- Métricas de engajamento e qualidade
- Comparação entre categorias e autores

### 🔍 Discrepâncias de Sentimento
- Detecta erros na classificação automática
- Casos onde sentimento e score divergem
- Priorização por nível de discrepância

## 📊 Dados Necessários

O sistema espera arquivos Parquet com as seguintes tabelas:

### books_data_processed
- `Title_padrao`: Título padronizado
- `authors_padrao`: Autor(es) padronizado
- `categories_padrao`: Categorias padronizadas
- `publishedDate_padrao`: Data de publicação

### books_rating_modified
- `Title`: Título do livro
- `User_id`: ID do usuário
- `text`: Texto do review
- `sentimento`: Classificação (positivo/negativo/neutro)
- `compound`: Score de sentimento (-1 a 1)

## 🚨 Solução de Problemas

### Banco de dados não encontrado
```bash
# Execute o criador do banco
python parquet_to_sqlite.py
```

### Erro ao importar módulos
```bash
# Instale dependências
pip install -r requirements.txt
```

### Arquivos Parquet não encontrados
1. Verifique se os arquivos estão em uma dessas pastas:
   - `./data/processed/`
   - `./data/modified/`
   - `../data/processed/`
   - `../data/modified/`

2. Ou copie os arquivos para a pasta `frontend/`

### Erro de memória
- Use um subconjunto dos dados para teste
- Ajuste o `chunksize` em `parquet_to_sqlite.py`

## 📈 Métricas e KPIs

### Score de Problema (Livros)
```
Score = (% Reviews Negativos × 0.6) + (|Compound Negativo| × 100 × 0.4)
```

### Score de Diversidade (Usuários)
```
Score = (Num Reviews × 0.3) + (Sentimentos Diversos × 10) + (Categorias × 5)
```

### ROI Estimado
```
ROI = (Reviews/Livro) × (Compound + 1) × log(Num Livros) / 10
```

## 🎨 Personalização

### Modificar Consultas
Edite `poc_queries.py` para ajustar:
- Thresholds de classificação
- Fórmulas de score
- Filtros de dados

### Customizar Interface
Edite `streamlit_poc.py` para:
- Alterar layout e cores
- Adicionar/remover gráficos
- Modificar métricas exibidas

### Adicionar Análises
1. Crie novas funções em `poc_queries.py`
2. Adicione páginas em `streamlit_poc.py`
3. Atualize a navegação

## 🔒 Segurança e Performance

### Banco de Dados
- SQLite otimizado com índices
- Queries parametrizadas (SQL injection safe)
- Tratamento de erros robusto

### Interface
- Cache de dados do Streamlit
- Paginação para grandes datasets
- Validação de entrada do usuário

## 📝 Logs e Monitoramento

O sistema registra:
- Erros de conexão com banco
- Performance de consultas
- Estatísticas de uso

Logs aparecem no console onde o Streamlit é executado.

## 🚀 Próximos Passos

Para expandir a POC:

1. **Integração com APIs**
   - Conectar com sistemas reais
   - Atualização automática de dados

2. **ML/IA Avançado**
   - Modelos de recomendação
   - Análise preditiva

3. **Alertas Automáticos**
   - Notificações de problemas
   - Relatórios programados

4. **Dashboard Executivo**
   - Métricas de alto nível
   - Exportação para PDF

## 🤝 Suporte

Para problemas ou dúvidas:
1. Verifique os logs no console
2. Execute `python poc_queries.py` para diagnóstico
3. Confirme se todos os arquivos estão presentes

---

**Versão:** 1.0.0  
**Última atualização:** 2025-06-22