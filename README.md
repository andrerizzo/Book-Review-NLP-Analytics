# Book Review NLP Analytics

Um sistema inteligente de análise de avaliações literárias utilizando Processamento de Linguagem Natural (NLP) e Large Language Models (LLMs) para extrair insights acionáveis do comportamento dos leitores.

## 📋 Sobre o Projeto

Este projeto demonstra a aplicação de técnicas avançadas de NLP para automatizar a análise de avaliações de livros, transformando dados textuais não estruturados em insights estratégicos para editoras e profissionais do mercado literário.

### 🎯 Problema de Negócio

A editora dependia de análises manuais para:
- Avaliar performance de autores e gêneros
- Identificar tendências de mercado
- Encontrar usuários influentes para entrevistas
- Compreender sentimento dos leitores

**Desafio**: Processo manual que consome 15 dias-pessoa por análise, gerando custos elevados e delays na tomada de decisão.

**Solução**: Sistema automatizado que reduz o tempo de análise de semanas para minutos, mantendo qualidade e profundidade dos insights.

| Componente         | Tecnologias Utilizadas                                                             |
| ------------------ | ---------------------------------------------------------------------------------- |
| **NLP**      | VADER (classificação de sentimentos)<br />TF-IDF (normalização de sentenças)) |
| **LLM**      | OpenAI GPT-4o-mini (resumos executivos)                                            |
| **Frontend** | Streamlit (dashboard interativo)                                                   |
| **Dados**    | SQLite + enriquecimento com OpenLibrary API                                        |

---

### ⚙️ Funcionalidades Implementadas

- ⚡ **Dashboard executivo** com métricas e gráficos interativos
- ⚠️ **Identificação automatizada de livros críticos** por sentimento
- 👥 **Seleção inteligente de usuários** para entrevistas
- 📈 **Ranking de performance** por autor, categoria e editora
- 🤖 **Geração de resumos executivos com LLM** para decisões estratégicas

---

## 📊 Impacto Gerado

| Métrica    | Antes                     | Depois           | Redução           |
| ----------- | ------------------------- | ---------------- | ------------------- |
| Tempo       | 3 dias                    | 5 minutos        | **−99,9%**   |
| Custo       | R$ 15.000   | ~R$ 0 (*) | **−100%** |                     |
| Frequência | Mensal                    | Diária          | **30× mais** |

> (*) Custo apenas com infraestrutura e API

---

## 📁 Estrutura do Projeto

```
📦 projeto/
├── data/         → Bases enriquecidas + SQLite
├── frontend/     → App interativo com Streamlit
├── notebooks/    → Análises exploratórias, análise de sentimentos, processo de imputação de dadts
├── scripts/      → Pipelines e extrações
└── src/          → Lógica principal (NLP, IA)
```

---

## 💼 Principais Módulos

### 🎯 Dashboard Executivo

- KPIs de sentimento e engajamento
- Alertas sobre livros fora da média

### 🧠 Análise Estratégica

- Score de problema baseado em % negativos
- Seleção automatizada de leitores representativos

### 🤖 Resumos com IA (LLMs)

- Geração de insights por polaridade de sentimento
- Recomendação executiva para ações editoriais

---

## 👨‍💻 Desenvolvedor

**André Rizzo**
📧 andrerizzo@gmail.com
🔗 [LinkedIn](https://linkedin.com/in/andrerizzo) | [GitHub](https://github.com/andrerizzo)
