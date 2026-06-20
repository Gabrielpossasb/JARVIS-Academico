# 🤖 JARVIS Acadêmico

Assistente pessoal acadêmico desenvolvido para a disciplina de Inteligência Artificial. O sistema auxilia estudantes a organizar seu desempenho utilizando RAG, Tool Calling e um modelo de linguagem (LLM).

---

## 🎯 Funcionalidades obrigatórias

- **3.1 Consulta a materiais de estudo (RAG):** Responde perguntas com base em PDFs e documentos acadêmicos
- **3.2 Agenda acadêmica:** Consulta aulas, provas e eventos por dia, amanhã, semana ou data específica
- **3.3 Lista de tarefas:** Adiciona, lista e conclui tarefas acadêmicas
- **3.4 Planejamento de estudos:** Combina agenda, tarefas pendentes e materiais (RAG) para montar um plano de estudos ou responder "o que devo priorizar hoje?"

## 🧠 Melhorias de aprendizado

- **Geração de exercícios:** Cria questões (múltipla escolha, dissertativa, V/F) com gabarito comentado a partir dos materiais da matéria
- **Active recall interativo:** O sistema gera uma pergunta sobre a matéria, aguarda a resposta do usuário e avalia com nota, acertos, lacunas e dica de reforço

## 📊 Avaliação e análise de erros

- **Avaliação do sistema:** 10 perguntas cobrindo RAG, agenda, tarefas, planejamento e aprendizado, registradas em `avaliacao/resultados.json` com pergunta, documentos recuperados, resposta e classificação (correta / parcialmente correta / incorreta)
- **Análise de erros:** 4 falhas identificadas (tipo, causa, possível solução) documentadas em `avaliacao/analise_erros.md`

## ✨ Funcionalidades extras

- **Adição de eventos à agenda:** Registra provas, atividades e trabalhos via chat, com preenchimento automático de local, horário e professor com base nas aulas da matéria
- **Remoção de eventos da agenda:** Remove provas, atividades e trabalhos por título, data ou ID — aulas regulares nunca são removidas
- **Interface web:** Chat interativo acessível pelo navegador com atalhos rápidos para as principais funcionalidades
- **Resolução de datas relativas:** Converte automaticamente expressões como "próxima segunda" ou "na quarta" para a data correta no formato aceito pelas ferramentas
- **Histórico de conversa:** Mantém contexto dos últimos 10 turnos, permitindo referências como "conclua a tarefa 3" após listar as tarefas

---

## 🛠️ Ferramentas implementadas (Tool Calling)

| Ferramenta | Descrição |
|---|---|
| `consultar_agenda` | Retorna eventos da agenda por período (`'hoje'`, `'amanha'`, `'semana'`) ou data específica (`'YYYY-MM-DD'`) |
| `verificar_provas` | Lista provas nos próximos N dias |
| `listar_tarefas` | Lista tarefas pendentes |
| `adicionar_tarefa` | Adiciona nova tarefa com matéria e prioridade |
| `concluir_tarefa` | Marca tarefa como concluída por ID (prioritário) ou por título — tolerante a acentos e singular/plural |
| `buscar_material` | Busca conteúdo nos documentos via RAG com diversidade de fontes (máx. 2 chunks por arquivo) |
| `adicionar_evento` | Adiciona prova, atividade ou trabalho à agenda, preenchendo automaticamente local e professor a partir das aulas cadastradas da matéria |
| `remover_evento` | Remove prova, atividade ou trabalho da agenda por título, data ou ID — nunca remove aulas regulares |
| `planejar_estudos` | Combina agenda, provas, tarefas pendentes e material RAG para montar um plano de estudos ou responder o que priorizar |
| `gerar_exercicios` | Gera exercícios com gabarito comentado a partir dos materiais da matéria |
| `iniciar_active_recall` | Inicia uma sessão de active recall: gera uma pergunta sobre a matéria e aguarda a resposta do usuário |
| `avaliar_resposta_recall` | Avalia a resposta do usuário na sessão de active recall ativa, com nota, acertos, lacunas e dica de reforço |

A decisão de qual ferramenta usar é feita pelo próprio modelo Gemma 12B, não por lógica fixa.

---

## 📁 Estrutura do projeto

```
JARVIS/
├── app.py               # Servidor Flask — interface web
├── main.py              # Tool calling, decisão de ferramentas, histórico e geração de resposta
├── llm.py               # Conexão com o Gemma 12B
├── tool/
│   ├── rag.py           # RAG: carrega PDFs, gera embeddings, busca com diversidade (cache FAISS)
│   ├── agenda.py        # Agenda acadêmica — leitura, escrita, adição e remoção de eventos
│   ├── tarefas.py       # Lista de tarefas — leitura/escrita, busca flexível por título
│   ├── planejamento.py  # Planejamento de estudos — combina agenda, tarefas e RAG
│   └── aprendizado.py   # Melhorias de aprendizado — exercícios e active recall
├── templates/
│   └── index.html       # Interface web do chat
├── data/
│   ├── docs/            # Documentos acadêmicos (PDFs)
│   ├── cache/           # Índice FAISS em cache (gerado automaticamente)
│   ├── agenda.json      # Eventos do semestre
│   ├── tarefas.json     # Tarefas do estudante
│   └── recall_state.json # Estado da sessão de active recall ativa
├── avaliacao/
│   ├── avaliar_sistema.py # Roteiro de avaliação com 10 perguntas
│   ├── resultados.json    # Resultados, documentos recuperados e classificações
│   └── analise_erros.md   # Falhas identificadas (tipo, causa, possível solução)
├── logs/
│   └── tool_calls.log   # Registro de todas as chamadas de ferramentas (com fontes RAG)
└── README.md
```

---

## 📦 Instalação

### Pré-requisitos

- Python 3.10+
- pip

### Instalar dependências

```bash
pip install -r requirements.txt
```
ou
```bash
python -m pip install -r requirements.txt
```

### Executar (interface web)

```bash
python app.py
```

Acesse **http://localhost:5000** no navegador.

Na primeira execução, o RAG processa todos os PDFs e salva o índice em cache (`data/cache/`). Nas execuções seguintes o carregamento é imediato.

### Executar (terminal)

```bash
python main.py
```

---

## 💬 Exemplos de uso

```
Você: O que tenho hoje?
Você: Qual minha agenda da próxima segunda-feira?
Você: Qual minha agenda do dia 25/05?
Você: Tenho prova essa semana?
Você: Tenho prova de IA no dia 15/06
Você: Tenho trabalho de Web para entregar no dia 20/06 às 23:59
Você: Remove a prova de IA do dia 15/06
Você: Quais são minhas tarefas pendentes?
Você: Adiciona a tarefa estudar redes neurais na matéria de IA com prioridade alta
Você: Conclui a tarefa de estudar redes neurais
Você: Explique o algoritmo KNN
Você: Monte um plano de estudos para a prova de Inteligência Artificial
Você: O que devo priorizar hoje nos meus estudos?
Você: Gere 3 exercícios sobre o algoritmo KNN com gabarito comentado
Você: Iniciar active recall de Inteligência Artificial
```

---

## 🗄️ Dataset

Os documentos usados pelo RAG estão na pasta `data/docs/`. Detalhes completos sobre origem, tipo de conteúdo, limitações, estratégia de chunking e impacto no RAG estão documentados em [`data/DATASET.md`](data/DATASET.md).

---

## 🏗️ Arquitetura

```
Usuário (navegador ou terminal)
   ↓ pergunta
Resolução de datas relativas ("próxima segunda" → "2026-05-25")
   ↓
Flask / loop de conversa  [histórico: últimos 10 turnos]
   ↓
Gemma 12B (decisão de ferramenta)
   ↓ tool calling
┌──────────────┬───────────────┬──────────────┬──────────────────┐
│     RAG      │    Agenda     │   Tarefas    │   Planejamento /  │
│  (FAISS +    │  (JSON local) │ (JSON local) │   Aprendizado     │
│  embeddings) │  add/remove   │ busca flex.  │ (exercícios,      │
│              │               │              │  active recall)   │
└──────────────┴───────────────┴──────────────┴──────────────────┘
   ↓ contexto recuperado
Gemma 12B (geração da resposta final)
   ↓
Usuário
```

---

## 🤖 IAs utilizadas no desenvolvimento

| Ferramenta | Uso |
|---|---|
| Claude (Anthropic) | Geração e revisão de código, arquitetura do sistema, debugging |
| Gemma 12B (Google / UFMS) | LLM principal do JARVIS — raciocínio, tool calling e geração de respostas |

---

## 📋 Logs

Todas as chamadas de ferramentas são registradas em `logs/tool_calls.log` com:
- Timestamp
- Ferramenta chamada
- Entrada (parâmetros)
- Saída (primeiros 200 caracteres)

Para chamadas à ferramenta `buscar_material`, o log também registra os **arquivos fonte** recuperados pelo RAG (ex.: `[aula-KNN.pdf, aula-arvoresDecisao.pdf]`).

---

## 👥 Autores

Trabalho desenvolvido para a disciplina **Inteligência Artificial** — UFMS  
Professor: Edson Matsubara

| Autor | GitHub |
|---|---|
| Gabriel Abraão Possas Borges | [@gabrielpossasb](https://github.com/gabrielpossasb) |
| Glédson Júnio Viana Rocha | [@Gjunio7](https://github.com/Gjunio7) |
