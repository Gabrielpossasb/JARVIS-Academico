# Análise de Erros — JARVIS Acadêmico

Documento referente à seção 7 do enunciado (Avaliação e análise de erros). As falhas abaixo foram identificadas durante a execução da avaliação registrada em `avaliacao/resultados.json` e em testes adicionais do sistema.

---

## Falha 1 — Recuperação RAG insuficiente para "árvores de decisão"

- **Referência:** `resultados.json`, item ID 2 (categoria RAG), classificação *parcialmente_correta*
- **Tipo:** Recuperação (RAG)
- **Causa:** Para a pergunta "Quais são as vantagens e desvantagens das árvores de decisão?", o FAISS retornou chunks de `Aula 05 - Árvores Binárias de Busca.pdf`, `Aula 04 - Árvores Binárias.pdf` e `IHC___Aula_02___Fatores_Humanos.pdf`, mas **não** retornou `aula-arvoresDecisao.pdf`, que é o material correto. A similaridade vetorial entre "árvores de decisão" e "árvores binárias" é alta o suficiente para essas estruturas de dados ocuparem as posições de maior score, deslocando o documento correto. A resposta final do LLM ficou correta apenas porque ele recorreu a conhecimento geral, não aos documentos do dataset.
- **Possível solução:** Aumentar `top_k` ou `n_candidatos` na busca, e/ou usar um modelo de embeddings com melhor distinção semântica entre termos próximos (ex.: `all-mpnet-base-v2`). Outra alternativa é fazer *reranking* dos candidatos com base em sobreposição de palavras-chave da pergunta antes de aplicar o corte de diversidade.

---

## Falha 2 — Documento de domínio irrelevante recuperado em pergunta de exercícios

- **Referência:** `resultados.json`, item ID 9 (categoria Exercícios), classificação *correta*
- **Tipo:** Recuperação (RAG)
- **Causa:** Na pergunta "Gere 3 exercícios sobre o algoritmo KNN com gabarito comentado", o RAG retornou `Introducao_a_Sistemas_Digitais.pdf`, um material de outra disciplina (Sistemas Digitais), sem relação com KNN. O sistema funcionou apesar disso porque o LLM ignorou o trecho irrelevante, mas isso mostra que o índice FAISS não está penalizando o suficiente documentos de domínios distintos quando os chunks mais relevantes (`aula-KNN.pdf`, `lista1.pdf`) já preenchem parte do `top_k`.
- **Possível solução:** Definir um limiar mínimo de similaridade (score de corte) para descartar chunks pouco relevantes, em vez de sempre completar o `top_k` com os próximos candidatos disponíveis.

---

## Falha 3 — Resposta de priorização retornava a agenda completa em vez de uma resposta direta

- **Referência:** `resultados.json`, item ID 8 (categoria Planejamento), classificação *correta* (após correção)
- **Tipo:** Geração de resposta final
- **Causa:** Para perguntas do tipo "O que devo priorizar hoje nos meus estudos?", `gerar_resposta_final()` originalmente repassava ao usuário todo o contexto de agenda/tarefas/RAG sem sintetizar uma recomendação — o usuário recebia a grade de aulas do dia inteira em vez de uma orientação objetiva sobre prioridades.
- **Solução aplicada:** Adicionada a função `_is_prioridade()` em `main.py`, que detecta perguntas de priorização e aciona uma instrução específica em `gerar_resposta_final()` para que o LLM responda de forma direta e ordenada (o que fazer primeiro, depois, etc.), sem listar a agenda inteira. Re-testado com sucesso — ver observação do item 8.

---

## Falha 4 — Nomes de arquivos com acentos corrompidos no cache (mojibake)

- **Referência:** `data/cache/chunks.json` (verificado diretamente — não aparece em `resultados.json` pois os nomes já chegam corrompidos desde a indexação)
- **Tipo:** Dados / Indexação
- **Causa:** Ao ler os nomes dos arquivos em `data/docs/` via `os.listdir()` no Windows, nomes com acentuação (ex.: "Árvores Binárias", "Dispersão", "Cópia", "Tópico") são decodificados incorretamente e armazenados com caracteres de substituição (`�`, U+FFFD) em `chunks.json`. Isso é uma corrupção real dos dados (não um artefato de exibição do terminal), confirmada via `repr()` dos valores carregados do JSON. O impacto prático é baixo porque o conteúdo dos chunks (texto) não é afetado, apenas o campo `arquivo` usado para citar a fonte — então a referência exibida ao usuário fica com caracteres ilegíveis.
- **Possível solução:** Normalizar/sanitizar os nomes de arquivo ao indexar (ex.: `arquivo.encode('utf-8', errors='replace').decode('utf-8')` não resolve, pois o dado já está corrompido na origem; a solução correta é reconstruir o cache após renomear os PDFs em `data/docs/` para nomes sem caracteres especiais, ou tratar a leitura com a codificação correta do filesystem do Windows).

---

## Resumo

| # | Tipo | Severidade | Status |
|---|---|---|---|
| 1 | Recuperação (RAG) | Média | Identificada, não corrigida |
| 2 | Recuperação (RAG) | Baixa | Identificada, não corrigida |
| 3 | Geração de resposta | Alta | **Corrigida** |
| 4 | Dados / Indexação | Baixa | Identificada, não corrigida |
