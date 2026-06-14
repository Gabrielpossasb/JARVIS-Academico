import os
import json
import faiss
import numpy as np
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Modelo de embeddings
modelo = SentenceTransformer('all-MiniLM-L6-v2')

# Armazena os chunks e o índice FAISS
chunks_globais = []
indice_faiss = None

# Arquivos recuperados na última chamada a buscar_material (para avaliação)
_ultimos_documentos = []

# --- NOVO: caminhos do cache em disco ---
CACHE_DIR         = 'data/cache'
CACHE_INDICE      = os.path.join(CACHE_DIR, 'faiss_index.bin')
CACHE_CHUNKS      = os.path.join(CACHE_DIR, 'chunks.json')
CACHE_FINGERPRINT = os.path.join(CACHE_DIR, 'fingerprint.json')


EXTENSOES_SUPORTADAS = ('.pdf', '.docx', '.txt')

def _fingerprint_docs(pasta='data/docs'):
    """Gera um retrato da pasta {arquivo: tamanho_bytes} para PDF, DOCX e TXT.
    Se qualquer documento for adicionado, removido ou modificado, o retrato muda."""
    resultado = {}
    for arquivo in sorted(os.listdir(pasta)):
        if arquivo.endswith(EXTENSOES_SUPORTADAS):
            resultado[arquivo] = os.path.getsize(os.path.join(pasta, arquivo))
    return resultado


def _cache_valido(pasta='data/docs'):
    """Retorna True se os arquivos de cache existem E os documentos não mudaram."""
    for caminho in [CACHE_INDICE, CACHE_CHUNKS, CACHE_FINGERPRINT]:
        if not os.path.exists(caminho):
            return False
    with open(CACHE_FINGERPRINT, 'r', encoding='utf-8') as f:
        fingerprint_salvo = json.load(f)
    return fingerprint_salvo == _fingerprint_docs(pasta)


def _salvar_cache(chunks, indice, pasta='data/docs'):
    os.makedirs(CACHE_DIR, exist_ok=True)
    faiss.write_index(indice, CACHE_INDICE)
    with open(CACHE_CHUNKS, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False)
    with open(CACHE_FINGERPRINT, 'w', encoding='utf-8') as f:
        json.dump(_fingerprint_docs(pasta), f, ensure_ascii=False)
    print('Cache salvo em disco.')


def _carregar_cache():
    indice = faiss.read_index(CACHE_INDICE)
    with open(CACHE_CHUNKS, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    return chunks, indice
# --- FIM DAS FUNÇÕES NOVAS ---

def carregar_docs(pasta='data/docs'):
    textos = []
    for arquivo in os.listdir(pasta):
        caminho = os.path.join(pasta, arquivo)
        texto = ''
        if arquivo.endswith('.pdf'):
            reader = PdfReader(caminho)
            for pagina in reader.pages:
                texto += pagina.extract_text() or ''
        elif arquivo.endswith('.docx'):
            doc = Document(caminho)
            texto = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        elif arquivo.endswith('.txt'):
            with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
                texto = f.read()
        else:
            continue
        textos.append({'arquivo': arquivo, 'texto': texto})
        print(f'Carregado: {arquivo}')
    return textos

def dividir_chunks(textos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,   # maior para capturar mais contexto de slides
        chunk_overlap=100  # mais sobreposição para não quebrar conceitos no meio
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
    # Normaliza para usar similaridade cosseno (IndexFlatIP com vetores normalizados)
    faiss.normalize_L2(embeddings)
    indice = faiss.IndexFlatIP(embeddings.shape[1])
    indice.add(embeddings)
    return indice

def buscar_material(pergunta: str, top_k=5) -> str:
    """Busca os top_k chunks mais relevantes, garantindo diversidade de fontes.
    Busca top_k * 5 candidatos e seleciona no máximo 2 chunks por arquivo."""
    global chunks_globais, indice_faiss, _ultimos_documentos
    vetor = modelo.encode([pergunta]).astype('float32')
    faiss.normalize_L2(vetor)

    # Busca mais candidatos para garantir diversidade
    n_candidatos = min(top_k * 5, len(chunks_globais))
    distancias, indices = indice_faiss.search(vetor, n_candidatos)

    # Seleciona até top_k chunks garantindo no máximo 2 por arquivo
    MAX_POR_ARQUIVO = 2
    contagem_por_arquivo = {}
    resultados = []

    for i in indices[0]:
        if len(resultados) >= top_k:
            break
        chunk = chunks_globais[i]
        arquivo = chunk['arquivo']
        count = contagem_por_arquivo.get(arquivo, 0)
        if count < MAX_POR_ARQUIVO:
            contagem_por_arquivo[arquivo] = count + 1
            resultados.append(f"[{arquivo}]\n{chunk['conteudo']}")

    _ultimos_documentos = list(contagem_por_arquivo.keys())
    return '\n\n---\n\n'.join(resultados)


def get_ultimos_documentos() -> list:
    """Retorna os arquivos recuperados na última chamada a buscar_material."""
    return list(_ultimos_documentos)


def resetar_ultimos_documentos() -> None:
    """Limpa o registro de documentos recuperados (usado entre perguntas na avaliação)."""
    global _ultimos_documentos
    _ultimos_documentos = []

def inicializar_rag(pasta='data/docs'):
    global chunks_globais, indice_faiss

    if _cache_valido(pasta):
        print('Cache encontrado, carregando índice do disco...')
        chunks_globais, indice_faiss = _carregar_cache()
        print(f'RAG pronto! ({len(chunks_globais)} chunks carregados do cache)')
    else:
        print('Construindo índice RAG (primeira vez ou PDFs alterados)...')
        textos = carregar_docs(pasta)
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