"""RAG textual local: trechos literais, filtrados por execução e contrato."""
import argparse
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import closing
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 1
LIMIT = 'Busca textual BM25 nos PDFs já extraídos. Não lê páginas ausentes, não comprova ausência de fatos e OCR exige conferir a imagem.'
STOP = set('a o as os de da do das dos e em um uma para por com no na nos nas que se ao aos ou não nao contrato contratos documento documentos solicitar conferir verificar'.split())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def run_folder(run, root=ROOT):
    if not isinstance(run, str) or not re.fullmatch(r'[A-Za-z0-9_][\w-]{0,99}', run, re.ASCII):
        raise ValueError('Execução inválida.')
    base = (Path(root) / 'data/reports').resolve()
    folder = (base / run).resolve()
    if folder.parent != base or not (folder / 'contratos.json').is_file():
        raise ValueError('Execução local não encontrada.')
    return folder


def inputs(folder):
    folder = Path(folder).resolve()
    files = [folder / 'contratos.json', folder / 'documentos.json']
    stamps = tuple((p.stat().st_mtime_ns, p.stat().st_ctime_ns, p.stat().st_size) if p.exists() else None for p in files)
    return cached_inputs(str(folder), stamps)


@lru_cache(maxsize=2)
def cached_inputs(directory, stamps):
    # Uma sessão MCP faz várias buscas; não relê todo o OCR a cada contrato.
    folder = Path(directory)
    records = json.loads((folder / 'contratos.json').read_text(encoding='utf-8'))
    path = folder / 'documentos.json'
    manifest = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    return records, manifest, digest({'versao': VERSION, 'registros': records, 'documentos': manifest})


def database(folder):
    folder = Path(folder).resolve()
    path = folder / 'rag' / 'indice.sqlite3'
    if not path.resolve().is_relative_to(folder):
        raise ValueError('Caminho do índice não permitido.')
    return path


def connect(folder):
    return sqlite3.connect(database(folder).resolve().as_uri() + '?mode=ro', uri=True)


def status(folder):
    _, _, signature = inputs(folder)
    if not database(folder).exists():
        return {'status': 'nao_preparado', 'limite': LIMIT}
    try:
        with closing(connect(folder)) as conn:
            meta = json.loads(conn.execute('SELECT valor FROM meta').fetchone()[0])
        return {**meta, 'status': 'pronto' if meta['assinatura'] == signature else 'desatualizado'}
    except (sqlite3.Error, ValueError, TypeError, KeyError):
        return {'status': 'invalido', 'limite': LIMIT}


def verify_pdf(folder, document):
    folder = Path(folder).resolve()
    identifier = document.get('documento_id', document.get('id', ''))
    if not re.fullmatch('[a-f0-9]{64}', identifier):
        raise ValueError('Identificador de PDF inválido.')
    path = (folder / 'documentos' / (identifier + '.pdf')).resolve()
    if not path.is_relative_to(folder) or hashlib.sha256(path.read_bytes()).hexdigest() != document.get('sha256_pdf', document.get('sha256')):
        raise ValueError('O PDF local mudou. Execute Ler documentos e Preparar RAG novamente.')


def page_source(line, doc, page, start):
    text = page['texto']
    snippet = text[start:start + 700]
    return {'id': f'L{line}-R' + digest([doc['id'], page['pagina'], start, snippet])[:24],
        'tipo': 'anexo_portal', 'linha': line, 'rotulo': doc['rotulo'],
        'tipo_documento': doc.get('tipo_documento'), 'nota_tipo': doc.get('nota_tipo'),
        **({k: doc[k] for k in ('origem', 'tipo_informado_pncp', 'numero_controle_pncp') if k in doc}),
        'url': doc['url'], 'documento_id': doc['id'], 'sha256_pdf': doc['sha256'],
        'pagina': page['pagina'], 'inicio': start, 'fim': start + len(snippet),
        'texto': snippet, 'metodo': page['metodo'], 'qualidade': page['qualidade'],
        'aviso': page.get('aviso'), 'truncado': bool(page.get('truncado')),
        'recorte_pagina': start > 0 or len(snippet) < len(text), 'rag': True}


def build_index(folder):
    folder = Path(folder)
    records, manifest, signature = inputs(folder)
    if not manifest:
        raise ValueError('Use Ler documentos antes de preparar o RAG.')
    path = database(folder)
    path.parent.mkdir(exist_ok=True)
    temporary = path.with_name(uuid.uuid4().hex + '.tmp')
    count, pages, lines = 0, set(), set()
    try:
        with closing(sqlite3.connect(temporary)) as conn, conn:
            conn.execute('CREATE TABLE meta(valor TEXT NOT NULL)')
            conn.execute('CREATE TABLE trechos(id TEXT PRIMARY KEY, linha INTEGER NOT NULL, fonte TEXT NOT NULL)')
            conn.execute("CREATE VIRTUAL TABLE busca USING fts5(id UNINDEXED, linha UNINDEXED, texto, tokenize='unicode61 remove_diacritics 2')")
            for entry in manifest.get('consultas', []):
                line = entry['linha']
                if type(line) is not int or not 1 <= line <= len(records) or entry.get('registro_sha256') != digest(records[line - 1]):
                    raise ValueError('Documentos incompatíveis com a coleta. Execute Ler documentos novamente.')
                for doc in entry['documentos']:
                    if doc['status'] not in ('lido', 'parcial'):
                        continue
                    verify_pdf(folder, doc)
                    for page in doc['paginas']:
                        text = page['texto']
                        for start in range(0, len(text), 600):
                            snippet = text[start:start + 700]
                            if len(snippet.strip()) < 8:
                                continue
                            source = page_source(line, doc, page, start)
                            identifier = source['id']
                            conn.execute('INSERT INTO trechos VALUES(?,?,?)', (identifier, line, json.dumps(source, ensure_ascii=False)))
                            conn.execute('INSERT INTO busca VALUES(?,?,?)', (identifier, line, snippet))
                            count += 1
                            pages.add((line, doc['id'], page['pagina'])); lines.add(line)
            if not count:
                raise ValueError('Nenhum texto disponível para indexar. Confira Ler documentos e os avisos de OCR.')
            if inputs(folder)[2] != signature:
                raise ValueError('Os documentos mudaram durante a indexação. Tente novamente.')
            meta = {'versao': VERSION, 'assinatura': signature, 'trechos': count, 'paginas': len(pages),
                'contratos': len(lines), 'preparado_em': datetime.now(timezone.utc).isoformat(),
                'motor': 'SQLite FTS5 / BM25', 'limite': LIMIT}
            conn.execute('INSERT INTO meta VALUES(?)', (json.dumps(meta, ensure_ascii=False),))
        temporary.replace(path)
        return {**meta, 'status': 'pronto'}
    finally:
        temporary.unlink(missing_ok=True)


def search(folder, line, query, limit=5):
    records, manifest, signature = inputs(folder)
    if type(line) is not int or not 1 <= line <= len(records):
        raise ValueError('Linha fora da coleta.')
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 2000 or type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError('Informe consulta de até 2000 caracteres e limite de 1 a 5.')
    tokens = list(dict.fromkeys(t.casefold() for t in re.findall(r'\w+', query, re.UNICODE) if len(t) > 1 and t.casefold() not in STOP))[:64]
    with closing(connect(folder)) as conn:
        meta = json.loads(conn.execute('SELECT valor FROM meta').fetchone()[0])
        if meta['assinatura'] != signature:
            raise ValueError('Índice desatualizado. Use Preparar RAG novamente.')
        expression = ' OR '.join('"' + t.replace('"', '""') + '"' for t in tokens)
        rows = conn.execute('SELECT t.fonte FROM busca b JOIN trechos t ON b.id=t.id WHERE busca MATCH ? AND t.linha=? ORDER BY bm25(busca), t.id LIMIT ?', (expression, line, limit)).fetchall() if tokens else []
    sources = [json.loads(row[0]) for row in rows]
    checked = set()
    for source in sources:
        entry = next((e for e in manifest['consultas'] if e['linha'] == line), {})
        doc = next((d for d in entry.get('documentos', []) if d['id'] == source.get('documento_id')), {})
        page = next((p for p in doc.get('paginas', []) if p['pagina'] == source.get('pagina')), None)
        start = source.get('inicio')
        if page is None or type(start) is not int or start < 0 or start >= len(page['texto']) or source != page_source(line, doc, page, start):
            raise ValueError('Trecho indexado incompatível com a extração. Use Preparar RAG novamente.')
        if source['documento_id'] not in checked:
            verify_pdf(folder, source)
            checked.add(source['documento_id'])
    return {'linha': line, 'fontes': sources, 'assinatura': signature, 'consulta': query,
            'status': 'disponivel' if sources else 'sem_correspondencia', 'limite': LIMIT}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'search', 'check'])
    parser.add_argument('--execucao', required=True)
    parser.add_argument('--linha', type=int)
    parser.add_argument('--consulta')
    args = parser.parse_args()
    folder = run_folder(args.execucao)
    if args.action == 'check':
        from src.rag_client import check_connection
        value = check_connection(folder)
    else:
        value = status(folder) if args.action == 'status' else search(folder, args.linha, args.consulta)
    print(json.dumps(value, ensure_ascii=False))


if __name__ == '__main__':
    main()
