"""
tool/aprendizado.py — Melhorias de aprendizado (Trabalho 2)

Funcionalidades:
1. gerar_exercicios   — gera questões práticas com gabarito comentado (não-interativo)
2. iniciar_active_recall  — gera pergunta e salva estado em disco (interativo)
3. avaliar_resposta_recall — avalia a resposta do aluno e dá feedback detalhado
4. get_recall_ativo   — utilitário: verifica se há sessão ativa (usado em main.py)
"""
import json
import os
from tool.rag import buscar_material
from llm import perguntar

_RECALL_STATE_PATH = 'data/recall_state.json'


# ──────────────────────────────────────────────
# Utilitários de estado do active recall
# ──────────────────────────────────────────────

def _salvar_estado(estado: dict) -> None:
    os.makedirs('data', exist_ok=True)
    with open(_RECALL_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def _limpar_estado() -> None:
    if os.path.exists(_RECALL_STATE_PATH):
        os.remove(_RECALL_STATE_PATH)


def get_recall_ativo() -> dict | None:
    """
    Retorna o estado atual do active recall, ou None se não houver sessão ativa.
    Usado em main.py para injetar aviso no prompt do LLM.
    """
    if not os.path.exists(_RECALL_STATE_PATH):
        return None
    try:
        with open(_RECALL_STATE_PATH, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        return estado if estado.get('ativa') else None
    except (json.JSONDecodeError, IOError):
        return None


# ──────────────────────────────────────────────
# Melhoria 1: Geração de exercícios (não-interativo)
# ──────────────────────────────────────────────

def gerar_exercicios(materia: str, quantidade: int = 3) -> str:
    """
    Gera exercícios práticos com gabarito comentado baseados nos materiais da matéria.

    Params:
        materia:    nome da matéria ou tópico (ex: 'KNN', 'Estruturas de Dados')
        quantidade: número de exercícios a gerar (padrão: 3)

    Returns:
        Texto formatado com exercícios e gabarito.
    """
    material = buscar_material(materia)

    prompt = f"""Você é um professor universitário criando uma lista de exercícios.

Com base no material abaixo sobre "{materia}", crie {quantidade} exercício(s) variado(s):
- Se quantidade >= 2: inclua pelo menos 1 de múltipla escolha (4 alternativas, indique a correta)
- Se quantidade >= 2: inclua pelo menos 1 dissertativo
- Se quantidade >= 3: inclua 1 verdadeiro ou falso

Para cada exercício, forneça o gabarito comentado ao final (explique o raciocínio).

MATERIAL DE REFERÊNCIA:
{material}

Formato esperado:
EXERCÍCIO 1 — [tipo]
[enunciado]
[alternativas, se couber]

...

GABARITO COMENTADO
1. [resposta + explicação do raciocínio]
...

Responda em português."""

    mensagens = [
        {'role': 'system', 'content': (
            'Você é um professor universitário. '
            'Gere exercícios acadêmicos de qualidade baseados estritamente no material fornecido.'
        )},
        {'role': 'user', 'content': prompt},
    ]

    return perguntar(mensagens)


# ──────────────────────────────────────────────
# Melhoria 2: Active recall interativo
# ──────────────────────────────────────────────

def iniciar_active_recall(materia: str) -> str:
    """
    Inicia uma sessão de active recall:
    1. Busca material relevante via RAG
    2. Pede ao LLM que gere uma pergunta + resposta esperada (JSON)
    3. Salva o estado em data/recall_state.json
    4. Retorna a pergunta para exibir ao usuário

    Params:
        materia: nome da matéria ou tópico

    Returns:
        Texto com a pergunta de active recall para o usuário responder.
    """
    material = buscar_material(materia)

    prompt = f"""Com base no material abaixo sobre "{materia}", formule UMA pergunta de active recall.

REGRAS OBRIGATÓRIAS:
- "pergunta": frase interrogativa CURTA, termina com "?" — NÃO coloque explicações aqui
- "resposta_esperada": resposta completa e detalhada
- "topico": tópico específico abordado

EXEMPLO de JSON correto:
{{
  "pergunta": "Como o valor de k afeta o viés e a variância no KNN?",
  "resposta_esperada": "K pequeno = alta variância, baixo viés (overfitting). K grande = baixa variância, alto viés (underfitting). O ideal é usar validação cruzada para encontrar o k ótimo.",
  "topico": "Valor de k"
}}

MATERIAL:
{material}

Responda SOMENTE com JSON válido, sem markdown, sem texto extra.
{{
  "pergunta": "frase interrogativa curta?",
  "resposta_esperada": "resposta detalhada aqui",
  "topico": "tópico abordado"
}}"""

    mensagens = [
        {'role': 'system', 'content': 'Você é um professor. Retorne apenas JSON válido, sem markdown, sem texto extra.'},
        {'role': 'user',   'content': prompt},
    ]

    raw = perguntar(mensagens).strip()

    # Limpa markdown caso o modelo envie ```json ... ```
    if '```' in raw:
        for parte in raw.split('```'):
            if '{' in parte:
                raw = parte.strip().lstrip('json').strip()
                break

    try:
        estado = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback genérico se o LLM não retornar JSON válido
        estado = {
            'pergunta': (
                f'Explique os conceitos principais de {materia} '
                f'com suas próprias palavras, como se ensinasse a um colega.'
            ),
            'resposta_esperada': (
                f'O aluno deve demonstrar compreensão dos conceitos centrais de '
                f'{materia} conforme os materiais da disciplina.'
            ),
            'topico': materia,
        }

    estado['ativa']   = True
    estado['materia'] = materia
    _salvar_estado(estado)

    return (
        f"🧠 **Active Recall iniciado — {materia}**\n\n"
        f"{estado['pergunta']}\n\n"
        f"_(Responda com suas próprias palavras e envie quando terminar.)_"
    )


def avaliar_resposta_recall(resposta_usuario: str) -> str:
    """
    Avalia a resposta do usuário em uma sessão de active recall ativa.
    Encerra a sessão após a avaliação.

    Params:
        resposta_usuario: texto enviado pelo usuário como resposta

    Returns:
        Feedback detalhado com nota, acertos, lacunas e dica de reforço.
    """
    estado = get_recall_ativo()

    if not estado:
        return (
            "Não há sessão de active recall ativa. "
            "Digite 'iniciar active recall de [matéria]' para começar."
        )

    pergunta          = estado.get('pergunta', '')
    resposta_esperada = estado.get('resposta_esperada', '')
    materia           = estado.get('materia', '')
    topico            = estado.get('topico', materia)

    prompt = f"""Você é um professor universitário avaliando a resposta de um aluno.

MATÉRIA: {materia} | Tópico: {topico}
PERGUNTA: {pergunta}
RESPOSTA DO ALUNO: {resposta_usuario}
RESPOSTA ESPERADA: {resposta_esperada}

Avalie nos seguintes pontos:
1. **Nota** (0–10): seja justo, não punitivo demais com detalhes menores
2. **Acertos**: o que o aluno entendeu corretamente
3. **Lacunas**: o que faltou ou está incorreto
4. **Dica de reforço**: um ponto específico e concreto para revisar

Seja encorajador, didático e objetivo. Responda em português."""

    mensagens = [
        {'role': 'system', 'content': (
            'Você é um professor universitário avaliando respostas de alunos. '
            'Seja construtivo, preciso e encorajador.'
        )},
        {'role': 'user', 'content': prompt},
    ]

    feedback = perguntar(mensagens)
    _limpar_estado()  # encerra a sessão

    return (
        f"{feedback}\n\n"
        f"---\n"
        f"_Sessão encerrada. Digite 'iniciar active recall de {materia}' para uma nova pergunta._"
    )
