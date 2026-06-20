import os
import sys

# Garante que o diretório do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template
from main import (
    decidir_ferramenta,
    executar_ferramenta,
    gerar_resposta_final,
    _resolver_datas_relativas,
    _is_conceitual,
    _MAX_HISTORICO,
)
from tool.rag import inicializar_rag
from llm import perguntar

# Ferramentas que retornam o texto final diretamente, sem pós-processamento via gerar_resposta_final
RETORNO_DIRETO = {'iniciar_active_recall', 'avaliar_resposta_recall'}

app = Flask(__name__)

print("Inicializando RAG, aguarde...")
inicializar_rag()
print("JARVIS pronto!\n")

# Histórico de conversa mantido no servidor (lista de {'role': ..., 'content': ...})
historico = []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    global historico

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Requisição inválida'}), 400

    pergunta = data.get('message', '').strip()
    if not pergunta:
        return jsonify({'error': 'Mensagem vazia'}), 400

    try:
        pergunta = _resolver_datas_relativas(pergunta)
        decisao = decidir_ferramenta(pergunta, historico)

        if not decisao.get('usar_ferramenta') and _is_conceitual(pergunta):
            decisao = {
                'usar_ferramenta': True,
                'ferramenta': 'buscar_material',
                'parametros': {'pergunta': pergunta}
            }

        tool_used = None
        if decisao.get('usar_ferramenta'):
            tool_used = decisao.get('ferramenta')
            contexto = executar_ferramenta(decisao)

            if tool_used in RETORNO_DIRETO:
                resposta = contexto  # pula o gerar_resposta_final
            else:
                resposta = gerar_resposta_final(pergunta, contexto, historico)
        else:
            msgs = [{'role': 'system', 'content': 'Você é o JARVIS, assistente acadêmico. Responda em português.'}]
            msgs.extend(historico)
            msgs.append({'role': 'user', 'content': pergunta})
            resposta = decisao.get('resposta_direta') or perguntar(msgs)

        historico.append({'role': 'user', 'content': pergunta})
        historico.append({'role': 'assistant', 'content': resposta})
        if len(historico) > _MAX_HISTORICO * 2:
            historico = historico[-(_MAX_HISTORICO * 2):]

        return jsonify({'response': resposta, 'tool_used': tool_used})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/reset', methods=['POST'])
def reset():
    global historico
    historico = []
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    # use_reloader=False evita inicializar o RAG duas vezes no modo debug
    app.run(debug=True, port=5000, use_reloader=False)
