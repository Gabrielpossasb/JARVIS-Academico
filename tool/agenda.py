import json
import re
from datetime import date, timedelta

CAMINHO = 'data/agenda.json'

ABREVIACOES = {
    'ia': 'inteligência artificial',
    'ed': 'estruturas de dados',
    'ihc': 'interação humano-computador',
    'web': 'programação para web',
    'apoo': 'análise e projeto de software',
}

def _match_materia(titulo_evento: str, termo: str) -> bool:
    titulo_lower = titulo_evento.lower()
    termo_lower = termo.lower().strip()
    if termo_lower in titulo_lower:
        return True
    expandido = ABREVIACOES.get(termo_lower, '')
    if expandido and expandido in titulo_lower:
        return True
    palavras = [p for p in termo_lower.split() if len(p) > 3]
    return bool(palavras) and any(p in titulo_lower for p in palavras)

def carregar_agenda():
    with open(CAMINHO, 'r', encoding='utf-8') as f:
        return json.load(f)['eventos']

def consultar_agenda(periodo: str = 'hoje') -> str:
    eventos = carregar_agenda()
    hoje = date.today()

    if periodo == 'hoje':
        filtrados = [e for e in eventos if e['data'] == str(hoje)]
        label = 'hoje'
    elif periodo == 'amanha':
        amanha = hoje + timedelta(days=1)
        filtrados = [e for e in eventos if e['data'] == str(amanha)]
        label = 'amanhã'
    elif periodo == 'semana':
        fim_semana = hoje + timedelta(days=7)
        filtrados = [e for e in eventos if str(hoje) <= e['data'] <= str(fim_semana)]
        label = 'essa semana'
    elif re.match(r'\d{4}-\d{2}-\d{2}$', periodo):
        filtrados = [e for e in eventos if e['data'] == periodo]
        label = f'em {periodo}'
    else:
        filtrados = eventos
        label = 'na agenda completa'

    filtrados = sorted(filtrados, key=lambda e: (e['data'], e['horario']))

    if not filtrados:
        return f'Nenhum evento encontrado para {label}.'

    resultado = f'Eventos {label}:\n'
    for e in filtrados:
        tipo = e['tipo'].upper()
        resultado += f"\n• [{tipo}] {e['titulo']}"
        resultado += f"\n  Data: {e['data']} às {e['horario']}"
        resultado += f"\n  Local: {e['local']}"
        resultado += f"\n  Professor: {e.get('professor', 'N/A')}\n"

    return resultado

def verificar_provas(dias: int = 7) -> str:
    eventos = carregar_agenda()
    hoje = date.today()
    limite = hoje + timedelta(days=dias)

    provas = [
        e for e in eventos
        if e['tipo'] == 'prova' and str(hoje) <= e['data'] <= str(limite)
    ]

    if not provas:
        return f'Nenhuma prova nos próximos {dias} dias.'

    resultado = f'Provas nos próximos {dias} dias:\n'
    for p in sorted(provas, key=lambda e: e['data']):
        resultado += f"\n• {p['titulo']} — {p['data']} às {p['horario']}"
    return resultado

def adicionar_evento(titulo: str, tipo: str, data: str, horario: str = '', local: str = '', materia: str = '') -> str:
    if re.match(r'\d{4}-\d{2}-\d{2}$', data):
        data_formatada = data
    elif re.match(r'\d{2}/\d{2}/\d{4}$', data):
        d, m, a = data.split('/')
        data_formatada = f'{a}-{m}-{d}'
    elif re.match(r'\d{1,2}/\d{1,2}$', data):
        partes = data.split('/')
        d = partes[0].zfill(2)
        m = partes[1].zfill(2)
        data_formatada = f'{date.today().year}-{m}-{d}'
    else:
        return f'Formato de data inválido: "{data}". Use DD/MM/AAAA ou DD/MM.'

    tipo_normalizado = tipo.lower()
    if tipo_normalizado not in ('prova', 'atividade', 'trabalho', 'aula'):
        tipo_normalizado = 'atividade'

    with open(CAMINHO, 'r', encoding='utf-8') as f:
        agenda = json.load(f)

    # Auto-preenche local e professor buscando aulas da mesma matéria
    professor = ''
    termo_busca = materia.strip() if materia.strip() else titulo

    # Prioridade: aulas no mesmo dia; fallback: qualquer aula da matéria
    aulas_ref = [
        e for e in agenda['eventos']
        if e['tipo'] == 'aula' and e['data'] == data_formatada
        and _match_materia(e['titulo'], termo_busca)
    ]
    if not aulas_ref:
        aulas_ref = [
            e for e in agenda['eventos']
            if e['tipo'] == 'aula' and _match_materia(e['titulo'], termo_busca)
        ]

    if aulas_ref:
        ref = aulas_ref[0]
        if not horario:
            horario = ref['horario']
        if not local:
            local = ref['local']
        professor = ref.get('professor', '')

    if not horario:
        horario = '00:00'

    # Verifica duplicata: mesmo título, tipo, data e horário
    for e in agenda['eventos']:
        if (
            e['titulo'].lower() == titulo.lower()
            and e['tipo'] == tipo_normalizado
            and e['data'] == data_formatada
            and e.get('horario', '') == horario
        ):
            return f'Evento já existe na agenda: [{tipo_normalizado.upper()}] {titulo} — {data_formatada} às {horario}.'

    novo_id = max((e['id'] for e in agenda['eventos']), default=0) + 1
    agenda['eventos'].append({
        'id': novo_id,
        'titulo': titulo,
        'tipo': tipo_normalizado,
        'data': data_formatada,
        'horario': horario,
        'local': local,
        'professor': professor
    })

    with open(CAMINHO, 'w', encoding='utf-8') as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

    detalhes = ''
    if local:
        detalhes += f', Local: {local}'
    if professor:
        detalhes += f', Professor: {professor}'
    return f'Evento adicionado: [{tipo_normalizado.upper()}] {titulo} — {data_formatada} às {horario}{detalhes}.'


def remover_evento(titulo: str = '', data: str = '', id_evento: int = None) -> str:
    with open(CAMINHO, 'r', encoding='utf-8') as f:
        agenda = json.load(f)

    eventos = agenda['eventos']

    # Normaliza data se fornecida
    data_fmt = ''
    if data:
        if re.match(r'\d{4}-\d{2}-\d{2}$', data):
            data_fmt = data
        elif re.match(r'\d{2}/\d{2}/\d{4}$', data):
            d, m, a = data.split('/')
            data_fmt = f'{a}-{m}-{d}'
        elif re.match(r'\d{1,2}/\d{1,2}$', data):
            partes = data.split('/')
            d = partes[0].zfill(2)
            m = partes[1].zfill(2)
            data_fmt = f'{date.today().year}-{m}-{d}'

    def deve_remover(e):
        # Nunca remove aulas regulares
        if e['tipo'] == 'aula':
            return False
        # Remove por ID exato
        if id_evento is not None:
            return e['id'] == id_evento
        # Remove por título (e opcionalmente data)
        match_titulo = (
            titulo.lower() in e['titulo'].lower()
            or _match_materia(e['titulo'], titulo)
        )
        if data_fmt:
            return match_titulo and e['data'] == data_fmt
        return match_titulo

    if not titulo and id_evento is None:
        return 'Informe o título ou o ID do evento a remover.'

    removidos = [e for e in eventos if deve_remover(e)]

    if not removidos:
        detalhe = f' na data {data_fmt}' if data_fmt else ''
        return f'Nenhum evento "{titulo}"{detalhe} encontrado na agenda.'

    agenda['eventos'] = [e for e in eventos if not deve_remover(e)]

    with open(CAMINHO, 'w', encoding='utf-8') as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

    linhas = [
        f"• [{e['tipo'].upper()}] {e['titulo']} — {e['data']} às {e['horario']}"
        for e in removidos
    ]
    return f"{len(removidos)} evento(s) removido(s):\n" + '\n'.join(linhas)


# Teste direto
if __name__ == '__main__':
    print('=== HOJE ===')
    print(consultar_agenda('hoje'))

    print('=== AMANHÃ ===')
    print(consultar_agenda('amanha'))

    print('=== SEMANA ===')
    print(consultar_agenda('semana'))

    print('=== PROVAS ===')
    print(verificar_provas(30))
