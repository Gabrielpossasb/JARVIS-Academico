import os
import json
import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Modelo de embeddings
modelo = SentenceTransformer('all-MiniLM-L6-v2')

# Armazena os chunks e o índice FAISS
chunks_globais = []
indice_faiss = None

# --- NOVO: caminhos do cache em disco ---
CACHE_DIR         = 'data/cache'
CACHE_INDICE      = os.path.join(CACHE_DIR, 'faiss_index.bin')
CACHE_CHUNKS      = os.path.join(CACHE_DIR, 'chunks.json')
CACHE_FINGERPRINT = os.path.join(CACHE_DIR, 'fingerprint.json')


def _fingerprint_pdfs(pasta='data/docs'):
    """Gera um retrato da pasta {arquivo: tamanho_bytes}.
    Se qualquer PDF for adicionado, removido ou modificado, o retrato muda."""
    resultado = {}
    for arquivo in sorted(os.listdir(pasta)):
        if arquivo.endswith('.pdf'):
            resultado[arquivo] = os.path.getsize(os.path.join(pasta, arquivo))
    return resultado


def _cache_valido(pasta='data/docs'):
    """Retorna True se os arquivos de cache existem E os PDFs não mudaram."""
    for caminho in [CACHE_INDICE, CACHE_CHUNKS, CACHE_FINGERPRINT]:
        if not os.path.exists(caminho):
            return False
    with open(CACHE_FINGERPRINT, 'r', encoding='utf-8') as f:
        fingerprint_salvo = json.load(f)
    return fingerprint_salvo == _fingerprint_pdfs(pasta)


def _salvar_cache(chunks, indice, pasta='data/docs'):
    os.makedirs(CACHE_DIR, exist_ok=True)
    faiss.write_index(indice, CACHE_INDICE)
    with open(CACHE_CHUNKS, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False)
    with open(CACHE_FINGERPRINT, 'w', encoding='utf-8') as f:
        json.dump(_fingerprint_pdfs(pasta), f, ensure_ascii=False)
    print('Cache salvo em disco.')


def _carregar_cache():
    indice = faiss.read_index(CACHE_INDICE)
    with open(CACHE_CHUNKS, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    return chunks, indice
# --- FIM DAS FUNÇÕES NOVAS ---

def carregar_pdfs(pasta='data/docs'):
    textos = []
    for arquivo in os.listdir(pasta):
        if arquivo.endswith('.pdf'):
            caminho = os.path.join(pasta, arquivo)
            reader = PdfReader(caminho)
            texto = ''
            for pagina in reader.pages:
                texto += pagina.extract_text() or ''
            textos.append({'arquivo': arquivo, 'texto': texto})
            print(f'Carregado: {arquivo}')
    return textos

def dividir_chunks(textos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = []
    for doc in textos:
        partes = splitter.split_text(doc['texto'])
        for parte in partes:
            chunks.append({'arquivo': doc['arquivo'], 'conteudo': parte})
    print(f'Total de chunks: {len(chunks)}')
    return chunks

def construir_indice(chunks):
    conteudos = [c['conteudo'] for c in chunks]
    embeddings = modelo.encode(conteudos, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')
    indice = faiss.IndexFlatL2(embeddings.shape[1])
    indice.add(embeddings)
    return indice

def buscar_material(pergunta: str, top_k=3) -> str:
    global chunks_globais, indice_faiss
    vetor = modelo.encode([pergunta]).astype('float32')
    distancias, indices = indice_faiss.search(vetor, top_k)
    resultados = []
    for i in indices[0]:
        chunk = chunks_globais[i]
        resultados.append(f"[{chunk['arquivo']}]\n{chunk['conteudo']}")
    return '\n\n---\n\n'.join(resultados)

def inicializar_rag(pasta='data/docs'):
    global chunks_globais, indice_faiss

    # CÓDIGO ANTIGO (sempre reconstruía tudo do zero a cada inicialização):
    # textos = carregar_pdfs()
    # chunks_globais = dividir_chunks(textos)
    # indice_faiss = construir_indice(chunks_globais)
    # print('RAG pronto!')

    # CÓDIGO NOVO: carrega do cache se possível, reconstrói só se os PDFs mudaram
    if _cache_valido(pasta):
        print('Cache encontrado, carregando índice do disco...')
        chunks_globais, indice_faiss = _carregar_cache()
        print(f'RAG pronto! ({len(chunks_globais)} chunks carregados do cache)')
    else:
        print('Construindo índice RAG (primeira vez ou PDFs alterados)...')
        textos = carregar_pdfs(pasta)
        chunks_globais = dividir_chunks(textos)
        indice_faiss = construir_indice(chunks_globais)
        _salvar_cache(chunks_globais, indice_faiss, pasta)
        print('RAG pronto!')

# Teste direto
if __name__ == '__main__':
    inicializar_rag()
    resultado = buscar_material('O que é KNN?')
    print('\nResultado da busca:')
    print(resultado)