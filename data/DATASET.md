# Dataset — JARVIS Acadêmico

Documentos utilizados pelo RAG, localizados em `data/docs/`. São **13 documentos** (mínimo exigido: 10).

| Arquivo | Conteúdo |
|---|---|
| `aula-KNN.pdf` | IA — Algoritmo K-Nearest Neighbors |
| `aula-arvoresDecisao.pdf` | IA — Árvores de Decisão |
| `Aula 02 - Tabelas de Dispersão.pdf` | Estruturas de Dados — Tabelas Hash |
| `Aula 04 - Árvores Binárias.pdf` | Estruturas de Dados — Árvores Binárias |
| `Aula 05 - Árvores Binárias de Busca.pdf` | Estruturas de Dados — Árvores Binárias de Busca |
| `Cópia de Tópico 3 - Linguagens de Marcação.pptx (1).pdf` | Prog Web — Linguagens de Marcação |
| `Tópico 2 - Engenharia Web.pdf` | Prog web — Engenharia Web |
| `IHC___Aula_02___Fatores_Humanos.pdf` | Interação Humano-Computador — Fatores Humanos |
| `IHC___Aula_03.pdf` | Interação Humano-Computador — Conceitos de Design de Interação |
| `Introducao_a_Sistemas_Digitais.pdf` | Sistemas Digitais — Introdução |
| `Representacao_de_Dados_e_Sistemas_de_Numeracao.pdf` | Sistemas Digitais — Representação de Dados e Numeração |
| `lista1.pdf` | IA — Lista de exercícios  |
| `calendario_academico.pdf` | Calendário acadêmico  |

**Formatos suportados:** `.pdf`, `.docx` (Word) e `.txt` — basta colocar o arquivo em `data/docs/` para que seja indexado na próxima inicialização do RAG.

## Origem dos dados

Materiais fornecidos pelos professores das disciplinas do semestre (slides de aula, listas de exercícios e calendário acadêmico).

## Tipo de conteúdo

Slides de aula, listas de exercícios, apostilas e um documento administrativo (calendário). Conteúdo majoritariamente textual, com algumas tabelas e diagramas simples embutidos nos PDFs.

## Limitações

- Alguns PDFs apresentam problemas de encoding (caracteres especiais corrompidos), por terem sido gerados a partir de slides exportados sem configuração UTF-8.
- Conteúdo visual (diagramas, imagens) não é extraído — apenas o texto, o que pode reduzir a qualidade de respostas sobre conceitos fortemente dependentes de figuras.
- Cobertura desigual entre disciplinas: algumas matérias têm vários documentos (Estruturas de Dados, Engenharia Web), outras só um (Sistemas Digitais), o que pode enviesar a qualidade das respostas do RAG entre temas.

## Estratégia de chunking

Implementada em `tool/rag.py` com `RecursiveCharacterTextSplitter` (LangChain):

- **Tamanho do chunk:** 800 caracteres
- **Overlap:** 100 caracteres

Na busca (`buscar_material`), são recuperados até `top_k × 5` candidatos (top_k padrão = 5) e selecionados no máximo **2 chunks por arquivo**, garantindo diversidade de fontes na resposta final.

## Impacto no RAG

- Chunks de 800 caracteres equilibram precisão e contexto: são pequenos o suficiente para representar um conceito específico (melhorando a relevância da busca vetorial), mas grandes o suficiente para não fragmentar excessivamente o conteúdo de slides.
- O overlap de 100 caracteres evita que frases ou conceitos sejam cortados exatamente na fronteira entre dois chunks, reduzindo perda de contexto.
- O limite de 2 chunks por arquivo na seleção final evita que o sistema dependa excessivamente de um único documento quando vários são relevantes, aumentando a diversidade de fontes citadas na resposta.
- Por outro lado, chunks menores aumentam o número total de embeddings a indexar (maior custo de inicialização do índice FAISS) e podem, em alguns casos, perder contexto de conceitos que se estendem por parágrafos longos.
