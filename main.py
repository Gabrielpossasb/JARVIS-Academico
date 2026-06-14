import json
import logging
import re
from datetime import date, datetime, timedelta
from llm import perguntar
from tool.agenda import consultar_agenda, verificar_provas, adicionar_evento, remover_evento
from tool.tarefas import listar_tarefas, adicionar_tarefa, concluir_tarefa
from tool.rag import buscar_material, inicializar_rag 
from tool.planejamento import planejar_estudos
from tool.aprendizado  import (
    gerar_exercicios,
    iniciar_active_recall,
    avaliar_resposta_recall,
    get_recall_ativo,
)

_DIAS_SEMANA = {
    'segunda': 0, 'terça': 1, 'terca': 1, 'quarta': 2,
    'quinta': 3, 'sexta': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6,
}

_PATTERN_DIA_REL = re.compile(
    r'(?:pr[oó]xim[ao]\s+|n[ao]\s+|d[ao]\s+)(segunda|ter[cç]a|quarta|quinta|sexta|s[aá]bado|domingo)'
    r'(?:[\s-]feira)?',
    re.IGNORECASE
)

def _proxima_ocorrencia(weekday: int, hoje: date) -> date:
    dias = (weekday - hoje.weekday()) % 7
    return hoje + timedelta(days=dias if dias > 0 else 7)

def _resolver_datas_relativas(texto: str) -> str:
    hoje = date.today()

    def substituir(m):
        base = m.group(1).lower()
        weekday = _DIAS_SEMANA.get(base)
        if weekday is None:
            return m.group(0)
        return _proxima_ocorrencia(weekday, hoje).strftime('%d/%m/%Y')

    return _PATTERN_DIA_REL.sub(substituir, texto)

def _is_conceitual(pergunta: str) -> bool:
    texto = pergunta.lower()
    termos = [
        'explique', 'defina', 'conceito', 'o que é', 'como funciona', 'resuma',
        'diferenças', 'vantagens', 'desvantagens', 'quais são', 'como se calcula'
    ]
    return any(termo in texto for termo in termos)

def _is_prioridade(pergunta: str) -> bool:
    texto = pergunta.lower()
    termos = ['prioriz', 'o que devo priorizar', 'devo priorizar', 'mais importante', 'prioridade', 'priorize']
    return any(termo in texto for termo in termos)

# Logger
logging.basicConfig(
    filename='logs/tool_calls.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    encoding='utf-8'
)

def registrar_log(ferramenta, entrada, saida):
    # Para buscar_material, extrai e exibe todos os arquivos fonte recuperados
    if ferramenta == 'buscar_material':
        import re
        fontes = re.findall(r'\[([^\]]+\.pdf)\]', saida)
        fontes_str = ', '.join(fontes) if fontes else 'nenhuma'
        logging.info(f'FERRAMENTA: {ferramenta} | ENTRADA: {entrada} | FONTES: [{fontes_str}] | SAÍDA: {saida[:150]}')
    else:
        logging.info(f'FERRAMENTA: {ferramenta} | ENTRADA: {entrada} | SAÍDA: {saida[:200]}')

def _get_ferramentas_descricao() -> str:
    hoje = date.today()
    dias_pt = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
               'sexta-feira', 'sábado', 'domingo']
    dia_semana = dias_pt[hoje.weekday()]
    hoje_str = hoje.strftime('%d/%m/%Y')

    recall_aviso = ""
    recall = get_recall_ativo()
    if recall:
        recall_aviso = f"""

⚠️⚠️⚠️ ATENÇÃO MÁXIMA — ACTIVE RECALL ATIVO ⚠️⚠️⚠️
O aluno está no meio de uma sessão de active recall, respondendo a esta pergunta:
"{recall.get('pergunta', '')}"

A PRÓXIMA MENSAGEM DO USUÁRIO É QUASE CERTAMENTE A RESPOSTA A ESSA PERGUNTA, mesmo que pareça
curta, informal, incompleta ou não pareça uma "pergunta". NÃO trate como conversa casual e
NÃO responda diretamente. A ÚNICA EXCEÇÃO é se o usuário pedir explicitamente para cancelar/sair
do recall ou der um comando claramente não relacionado (ex: "cancelar", "ver minha agenda").

Em qualquer outro caso, responda EXATAMENTE com:
{{
  "usar_ferramenta": true,
  "ferramenta": "avaliar_resposta_recall",
  "parametros": {{"resposta_usuario": "<mensagem completa do usuário, copiada literalmente>"}},
  "resposta_direta": null
}}
"""
    return f"""Você é o JARVIS, um assistente acadêmico.
Data de hoje: {hoje_str} ({dia_semana}). Use essa data para calcular datas relativas \
(ex: "próxima segunda" = próxima ocorrência de segunda-feira após hoje). \
Sempre converta datas relativas para o formato YYYY-MM-DD antes de chamar ferramentas.

Você tem acesso às seguintes ferramentas:

1. consultar_agenda(periodo) — consulta aulas e eventos.
   periodo pode ser: 'hoje', 'amanha', 'semana', ou uma data específica 'YYYY-MM-DD'.
2. verificar_provas(dias) — verifica provas próximas. dias é um número inteiro (ex: 7, 30)
3. listar_tarefas() — lista tarefas pendentes
4. adicionar_tarefa(titulo, materia, prioridade) — adiciona uma tarefa. prioridade: 'alta', 'média', 'baixa'
5. concluir_tarefa(id_tarefa, titulo) — marca uma tarefa como concluída.
   Use id_tarefa (inteiro) se souber o ID, ou titulo (string) se souber o nome.
   Prefira id_tarefa quando o ID estiver disponível no contexto da conversa.
6. buscar_material(pergunta) — OBRIGATÓRIO usar quando o usuário pedir para explicar,
   resumir, conceituar, definir ou tirar dúvidas sobre qualquer assunto acadêmico, algoritmo ou
   conteúdo de matéria. NUNCA responda perguntas de conteúdo sem chamar essa ferramenta primeiro.
   Se a pergunta for conceitual ou de definição, use buscar_material mesmo que o modelo já saiba a resposta.
7. adicionar_evento(titulo, tipo, data, materia, horario, local) — adiciona prova/atividade/trabalho
   à agenda. tipo: 'prova', 'atividade' ou 'trabalho'. data: 'DD/MM' ou 'DD/MM/AAAA'.
   materia: nome da disciplina (ex: 'Inteligência Artificial'). horario e local são opcionais.
8. remover_evento(titulo, data) — remove uma prova/trabalho/atividade da agenda.
   titulo: nome do evento ou da matéria (ex: 'Prova de IA', 'IA'). Não remove aulas regulares.
   data: data no formato 'YYYY-MM-DD'. OBRIGATÓRIO se o usuário mencionar um dia específico.
   Se o usuário NÃO mencionar data, omita o campo data (não invente uma data).
9. planejar_estudos(objetivo, dias) — plano de estudos personalizado combinando
   agenda, provas, tarefas e material RAG. Use quando pedirem para montar um
   plano ou perguntar o que priorizar. Para perguntas de prioridade, responda com uma
   lista ordenada e direta do mais importante para o menos importante.
   objetivo: matéria/assunto. dias: janela em dias (padrão 7).
10. gerar_exercicios(materia, quantidade) — gera exercícios com gabarito comentado
    usando os materiais da matéria. Use quando pedirem exercícios, questões ou simulado.
    materia: nome da matéria. quantidade: número de exercícios (padrão 3).
11. iniciar_active_recall(materia) — inicia active recall interativo. Gera uma
    pergunta e aguarda resposta do usuário. Use quando pedirem 'active recall',
    'me teste' ou 'quero ser testado sobre [matéria]'.
12. avaliar_resposta_recall(resposta_usuario) — avalia a resposta numa sessão
    ativa de active recall. SÓ usar quando recall estiver ativo.v

{recall_aviso}    

Quando o usuário fizer uma pergunta, responda com um JSON no seguinte formato:
{{
  "usar_ferramenta": true,
  "ferramenta": "nome_da_ferramenta",
  "parametros": {{"param1": "valor1"}},
  "resposta_direta": null
}}

Se não precisar de ferramenta, responda:
{{
  "usar_ferramenta": false,
  "ferramenta": null,
  "parametros": {{}},
  "resposta_direta": "sua resposta aqui"
}}

Responda APENAS com o JSON, sem texto adicional.
"""

def decidir_ferramenta(pergunta_usuario, historico: list = None):
    mensagens = [{'role': 'system', 'content': _get_ferramentas_descricao()}]
    # Injeta o histórico recente para que o LLM conheça IDs e títulos já vistos
    if historico:
        mensagens.extend(historico)
    mensagens.append({'role': 'user', 'content': pergunta_usuario})

    resposta = perguntar(mensagens)

    # Limpa a resposta caso venha com markdown
    resposta = resposta.strip()
    if resposta.startswith('```'):
        resposta = resposta.split('```')[1]
        if resposta.startswith('json'):
            resposta = resposta[4:]

    try:
        return json.loads(resposta.strip())
    except json.JSONDecodeError:
        return {'usar_ferramenta': False, 'resposta_direta': resposta}

def executar_ferramenta(decisao):
    ferramenta = decisao.get('ferramenta')
    params = decisao.get('parametros', {})

    if ferramenta == 'consultar_agenda':
        resultado = consultar_agenda(params.get('periodo', 'hoje'))

    elif ferramenta == 'verificar_provas':
        resultado = verificar_provas(int(params.get('dias', 7)))

    elif ferramenta == 'listar_tarefas':
        resultado = listar_tarefas()

    elif ferramenta == 'adicionar_tarefa':
        resultado = adicionar_tarefa(
            params.get('titulo', ''),
            params.get('materia', 'Geral'),
            params.get('prioridade', 'média')
        )

    elif ferramenta == 'concluir_tarefa':
        id_raw = params.get('id_tarefa')
        resultado = concluir_tarefa(
            id_tarefa=int(id_raw) if id_raw else 0,
            titulo=params.get('titulo', '')
        )

    elif ferramenta == 'buscar_material':
        resultado = buscar_material(params.get('pergunta', ''))

    elif ferramenta == 'adicionar_evento':
        resultado = adicionar_evento(
            params.get('titulo', ''),
            params.get('tipo', 'atividade'),
            params.get('data', ''),
            params.get('horario', ''),
            params.get('local', ''),
            params.get('materia', '')
        )

    elif ferramenta == 'remover_evento':
        id_raw = params.get('id_evento')
        resultado = remover_evento(
            titulo=params.get('titulo', ''),
            data=params.get('data', ''),
            id_evento=int(id_raw) if id_raw is not None else None
        )

    elif ferramenta == 'planejar_estudos':
        resultado = planejar_estudos(
            objetivo=params.get('objetivo', ''),
            dias=int(params.get('dias', 7)),
        )

    elif ferramenta == 'gerar_exercicios':
        resultado = gerar_exercicios(
            materia=params.get('materia', ''),
            quantidade=int(params.get('quantidade', 3)),
        )

    elif ferramenta == 'iniciar_active_recall':
        resultado = iniciar_active_recall(
            materia=params.get('materia', ''),
        )

    elif ferramenta == 'avaliar_resposta_recall':
        resultado = avaliar_resposta_recall(
            resposta_usuario=params.get('resposta_usuario', ''),
        )

    else:
        resultado = 'Ferramenta não reconhecida.'

    registrar_log(ferramenta, str(params), resultado)
    return resultado

def gerar_resposta_final(pergunta, contexto, historico: list = None):
    if _is_prioridade(pergunta):
        system_content = (
            'Você é o JARVIS, assistente acadêmico. Responda em português de forma clara e útil. '
            'Esta pergunta pede prioridade: devolva uma resposta direta com o que o usuário deve fazer primeiro, '
            'seguida dos próximos passos. Não liste tudo indiscriminadamente, destaque os itens mais importantes.'
        )
    else:
        system_content = 'Você é o JARVIS, assistente acadêmico. Responda em português de forma clara e útil.'

    mensagens = [
        {'role': 'system', 'content': system_content},
    ]
    if historico:
        mensagens.extend(historico)
    mensagens.append({'role': 'user', 'content': f'Pergunta: {pergunta}\n\nInformações encontradas:\n{contexto}'})
    return perguntar(mensagens)

def processar_pergunta(pergunta, historico: list = None):
    print(f'\nJARVIS está pensando...')
    pergunta = _resolver_datas_relativas(pergunta)
    decisao  = decidir_ferramenta(pergunta, historico)

    if not decisao.get('usar_ferramenta') and _is_conceitual(pergunta):
        decisao = {
            'usar_ferramenta': True,
            'ferramenta': 'buscar_material',
            'parametros': {'pergunta': pergunta}
        }

    # Ferramentas que retornam o texto final diretamente
    RETORNO_DIRETO = {'iniciar_active_recall', 'avaliar_resposta_recall'}

    if decisao.get('usar_ferramenta'):
        ferramenta = decisao.get('ferramenta')
        print(f'[Usando ferramenta: {ferramenta}]')
        contexto = executar_ferramenta(decisao)

        if ferramenta in RETORNO_DIRETO:
            return contexto  # ← pula o gerar_resposta_final

        resposta = gerar_resposta_final(pergunta, contexto, historico)
    else:
        msgs = [{'role': 'system', 'content': 'Você é o JARVIS, assistente acadêmico. Responda em português.'}]
        if historico:
            msgs.extend(historico)
        msgs.append({'role': 'user', 'content': pergunta})
        resposta = decisao.get('resposta_direta') or perguntar(msgs)

    return resposta

_MAX_HISTORICO = 10  # turnos (user + assistant) mantidos no contexto

def main():
    print('Inicializando RAG...')
    inicializar_rag()
    print('\n=== JARVIS Acadêmico ===')
    print('Digite "sair" para encerrar.\n')

    historico = []  # lista de {'role': ..., 'content': ...}

    while True:
        pergunta = input('Você: ').strip()
        if not pergunta:
            continue
        if pergunta.lower() == 'sair':
            print('JARVIS encerrado.')
            break

        resposta = processar_pergunta(pergunta, historico)
        print(f'\nJARVIS: {resposta}\n')

        # Atualiza histórico com o turno atual
        historico.append({'role': 'user',      'content': pergunta})
        historico.append({'role': 'assistant', 'content': resposta})

        # Mantém apenas os últimos N turnos para não explodir o contexto
        if len(historico) > _MAX_HISTORICO * 2:
            historico = historico[-(_MAX_HISTORICO * 2):]

if __name__ == '__main__':
    main()