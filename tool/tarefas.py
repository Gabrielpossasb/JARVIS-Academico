import json
import unicodedata
from datetime import date

CAMINHO = 'data/tarefas.json'

def _normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para comparação flexível."""
    return unicodedata.normalize('NFD', texto.lower()).encode('ascii', 'ignore').decode('ascii')

def _match_titulo(busca: str, titulo: str) -> bool:
    """
    Verifica se a busca corresponde ao título, tolerando:
    - diferenças de acentuação  (arvore == árvore)
    - singular/plural           (arvore ∈ arvores)
    - maiúsculas/minúsculas
    Estratégia: match direto primeiro; depois verifica palavra a palavra.
    """
    b = _normalizar(busca)
    t = _normalizar(titulo)
    if b in t:
        return True
    # Palavras com mais de 2 letras devem aparecer como substring no título
    palavras = [p for p in b.split() if len(p) > 2]
    return bool(palavras) and all(p in t for p in palavras)

def carregar_tarefas():
    with open(CAMINHO, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_tarefas(dados):
    with open(CAMINHO, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def listar_tarefas(apenas_pendentes: bool = True) -> str:
    dados = carregar_tarefas()
    tarefas = dados['tarefas']

    if apenas_pendentes:
        tarefas = [t for t in tarefas if not t['concluida']]
        label = 'pendentes'
    else:
        label = 'cadastradas'

    if not tarefas:
        return 'Nenhuma tarefa encontrada.'

    resultado = f'Tarefas {label}:\n'
    for t in tarefas:
        status = '✓' if t['concluida'] else '○'
        resultado += f"\n{status} [ID {t['id']}] {t['titulo']}"
        resultado += f"\n  Matéria: {t['materia']} | Prioridade: {t['prioridade']}\n"

    return resultado

def adicionar_tarefa(titulo: str, materia: str = 'Geral', prioridade: str = 'média') -> str:
    dados = carregar_tarefas()
    tarefas = dados['tarefas']

    novo_id = max([t['id'] for t in tarefas], default=0) + 1

    nova = {
        'id': novo_id,
        'titulo': titulo,
        'materia': materia,
        'prioridade': prioridade,
        'concluida': False,
        'data_criacao': str(date.today())
    }

    tarefas.append(nova)
    salvar_tarefas(dados)
    return f"Tarefa '{titulo}' adicionada com ID {novo_id}."

def concluir_tarefa(id_tarefa: int = 0, titulo: str = '') -> str:
    dados = carregar_tarefas()
    tarefas = dados['tarefas']

    for t in tarefas:
        # Busca por ID (prioritário) ou por título (flexível: sem acentos, singular/plural)
        match_id = id_tarefa and t['id'] == id_tarefa
        match_titulo = titulo and _match_titulo(titulo, t['titulo'])

        if match_id or match_titulo:
            if t['concluida']:
                return f"Tarefa '{t['titulo']}' já estava marcada como concluída."
            t['concluida'] = True
            salvar_tarefas(dados)
            return f"Tarefa '{t['titulo']}' marcada como concluída!"

    if id_tarefa:
        return f'Tarefa com ID {id_tarefa} não encontrada.'
    return f"Nenhuma tarefa encontrada com o título '{titulo}'."

# Teste direto
if __name__ == '__main__':
    print('=== LISTAR ===')
    print(listar_tarefas()) 

    print('=== ADICIONAR ===')
    print(adicionar_tarefa('Revisar árvores de decisão', 'Inteligência Artificial', 'alta'))

    print('=== LISTAR APÓS ADICIONAR ===')
    print(listar_tarefas())

    print('=== CONCLUIR ID 1 ===')
    print(concluir_tarefa(1))

    print('=== LISTAR APÓS CONCLUIR ===')
    print(listar_tarefas())