"""
avaliacao/avaliar_sistema.py — Avaliação do sistema JARVIS
Executa 10 perguntas de teste, registra respostas e permite classificação manual.
Salva os resultados em avaliacao/resultados.json para documentação do trabalho.

Uso:
    python avaliacao/avaliar_sistema.py
"""
import sys
import json
import os
from datetime import datetime

# Adiciona o diretório raiz ao path para importar os módulos do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import processar_pergunta
from tool.rag import inicializar_rag, get_ultimos_documentos, resetar_ultimos_documentos

# ──────────────────────────────────────────────
# 10 perguntas de teste cobrindo todas as funcionalidades
# ──────────────────────────────────────────────
PERGUNTAS_TESTE = [
    # Categoria: RAG — consulta de conteúdo acadêmico
    {
        "id": 1,
        "categoria": "RAG",
        "pergunta": "Explique como funciona o algoritmo KNN e como ele classifica novos exemplos",
    },
    {
        "id": 2,
        "categoria": "RAG",
        "pergunta": "Quais são as vantagens e desvantagens das árvores de decisão?",
    },
    {
        "id": 3,
        "categoria": "RAG",
        "pergunta": "O que é uma tabela hash e como são tratadas as colisões?",
    },

    # Categoria: Agenda — consultas temporais
    {
        "id": 4,
        "categoria": "Agenda",
        "pergunta": "O que tenho hoje?",
    },
    {
        "id": 5,
        "categoria": "Agenda",
        "pergunta": "Tenho alguma prova nos próximos 30 dias?",
    },

    # Categoria: Tarefas
    {
        "id": 6,
        "categoria": "Tarefas",
        "pergunta": "Quais são minhas tarefas pendentes?",
    },

    # Categoria: Planejamento (Funcionalidade 3.4)
    {
        "id": 7,
        "categoria": "Planejamento",
        "pergunta": "Monte um plano de estudos para a prova de Inteligência Artificial",
    },
    {
        "id": 8,
        "categoria": "Planejamento",
        "pergunta": "O que devo priorizar hoje nos meus estudos?",
    },

    # Categoria: Aprendizado — exercícios
    {
        "id": 9,
        "categoria": "Exercicios",
        "pergunta": "Gere 3 exercícios sobre o algoritmo KNN com gabarito comentado",
    },

    # Categoria: Aprendizado — active recall
    {
        "id": 10,
        "categoria": "Active Recall",
        "pergunta": "Iniciar active recall de Inteligência Artificial",
    },
]


def _classificar(resposta: str) -> tuple[str, str]:
    """Solicita classificação e observação ao avaliador."""
    print("\nClassificação:")
    print("  1 — Correta")
    print("  2 — Parcialmente correta")
    print("  3 — Incorreta")
    opcao = input("Sua classificação (1/2/3): ").strip()
    mapa  = {"1": "correta", "2": "parcialmente_correta", "3": "incorreta"}
    classificacao = mapa.get(opcao, "nao_classificada")
    observacao    = input("Observação (opcional, Enter para pular): ").strip()
    return classificacao, observacao


def executar_avaliacao():
    print("=" * 65)
    print("  AVALIAÇÃO DO SISTEMA JARVIS — T2")
    print("=" * 65)
    print("Inicializando RAG (pode demorar na primeira vez)...")
    inicializar_rag()
    print("RAG pronto.\n")

    resultados = []
    historico   = []  # mantém contexto entre perguntas

    for teste in PERGUNTAS_TESTE:
        print(f"\n{'─' * 65}")
        print(f"  [{teste['id']:02d}/10] Categoria: {teste['categoria']}")
        print(f"  P: {teste['pergunta']}")
        print("─" * 65)

        resetar_ultimos_documentos()
        try:
            resposta = processar_pergunta(teste["pergunta"], historico)
            # Atualiza histórico
            historico.append({"role": "user",      "content": teste["pergunta"]})
            historico.append({"role": "assistant",  "content": resposta})
            if len(historico) > 20:  # mantém os últimos 10 turnos
                historico = historico[-20:]
        except Exception as exc:
            resposta = f"ERRO: {exc}"

        documentos_recuperados = get_ultimos_documentos()

        # Exibe resposta truncada para não poluir o terminal
        preview = resposta[:600] + ("..." if len(resposta) > 600 else "")
        print(f"\n  R: {preview}\n")

        classificacao, observacao = _classificar(resposta)

        resultados.append({
            "id":                    teste["id"],
            "categoria":             teste["categoria"],
            "pergunta":              teste["pergunta"],
            "documentos_recuperados": documentos_recuperados,
            "resposta":              resposta,
            "classificacao":         classificacao,
            "observacao":            observacao,
            "timestamp":     datetime.now().isoformat(),
        })

    # ── Salva resultados ──────────────────────────────────────
    os.makedirs("avaliacao", exist_ok=True)
    output_path = "avaliacao/resultados.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # ── Resumo final ──────────────────────────────────────────
    total     = len(resultados)
    corretas  = sum(1 for r in resultados if r["classificacao"] == "correta")
    parciais  = sum(1 for r in resultados if r["classificacao"] == "parcialmente_correta")
    erradas   = sum(1 for r in resultados if r["classificacao"] == "incorreta")

    print(f"\n{'=' * 65}")
    print("  RESUMO DA AVALIAÇÃO")
    print(f"{'=' * 65}")
    print(f"  Total de perguntas : {total}")
    print(f"  Corretas           : {corretas:2d} ({corretas/total*100:.0f}%)")
    print(f"  Parcialmente corr. : {parciais:2d} ({parciais/total*100:.0f}%)")
    print(f"  Incorretas         : {erradas:2d}  ({erradas/total*100:.0f}%)")
    print(f"\n  Resultados salvos em: {output_path}")
    print("=" * 65)

    return resultados


if __name__ == "__main__":
    executar_avaliacao()