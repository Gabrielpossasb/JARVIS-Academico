"""
tool/planejamento.py — Funcionalidade 3.4: Planejamento de estudos
Combina agenda, tarefas pendentes e materiais via RAG para gerar um plano personalizado.
"""
from datetime import date
from tool.agenda import consultar_agenda, verificar_provas
from tool.tarefas import listar_tarefas
from tool.rag import buscar_material


def planejar_estudos(objetivo: str, dias: int = 7) -> str:
    """
    Gera um plano de estudos personalizado combinando:
    - Agenda da semana (aulas e eventos)
    - Provas e entregas nos próximos N dias
    - Tarefas pendentes
    - Materiais relevantes via RAG

    Params:
        objetivo: matéria ou assunto foco do plano (ex: 'prova de IA')
        dias: janela de dias para verificar provas/entregas (padrão: 7)

    Returns:
        Contexto estruturado para o LLM gerar o plano final em linguagem natural.
    """
    hoje = date.today()
    agenda_semana     = consultar_agenda('semana')
    provas_proximas   = verificar_provas(dias)
    tarefas_pendentes = listar_tarefas()
    material_relevante = buscar_material(objetivo)

    contexto = f"""
=== DADOS PARA PLANEJAMENTO: {objetivo.upper()} ===

[AGENDA DA SEMANA]
(Hoje é {hoje.strftime('%d/%m/%Y')} — ignore eventos anteriores a esta data ao montar o plano)
{agenda_semana}

[PROVAS E ENTREGAS NOS PRÓXIMOS {dias} DIAS]
{provas_proximas}

[TAREFAS PENDENTES]
{tarefas_pendentes}

[MATERIAL RELEVANTE PARA: {objetivo}]
{material_relevante}
"""
    return contexto