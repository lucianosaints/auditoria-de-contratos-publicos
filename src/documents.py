"""Dossiês locais de anexos: downloads oficiais limitados, extração e OCR local.

Não chama IA nem banco e nunca modifica contratos/parecer/relatório originais.
"""
import hashlib
import copy
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urljoin

import requests
from src.atomic_files import write_json

VERSION = 1
HOSTS = {'transparencia.marica.rj.gov.br', 'www.marica.rj.gov.br', 'marica.rj.gov.br'}
LIMIT = ('Links de anexos inventariados no portal ou recuperados de vínculos PNCP confirmados por regras. '
         'Vínculos candidatos ou conflitantes não alimentam a leitura automática. '
         'Extração automática sujeita a erro; tabelas e OCR exigem conferência visual. '
         'Documento vinculado pelo portal, sem validação automática de seu mérito ou conteúdo.')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save_json(path, value):
    write_json(path, value)


@dataclass(frozen=True)
class DocumentSettings:
    max_links: int = 5
    max_documents: int = 300
    max_pages: int = 30
    max_bytes: int = 10 * 1024 * 1024
    ocr: bool = True

    def __post_init__(self):
        for name, upper in (('max_links', 20), ('max_documents', 500),
                            ('max_pages', 100), ('max_bytes', 50 * 1024 * 1024)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError(f'Limite documental inválido: {name}.')

    @classmethod
    def from_env(cls):
        value = cls(max_links=int(os.getenv('DOCUMENT_MAX_LINKS', '5')),
                    max_documents=int(os.getenv('DOCUMENT_MAX_TOTAL', '300')),
                    max_pages=int(os.getenv('DOCUMENT_MAX_PAGES', '30')),
                    max_bytes=int(os.getenv('DOCUMENT_MAX_MB', '10')) * 1024 * 1024,
                    ocr=os.getenv('DOCUMENT_OCR_ENABLED', 'true').lower() == 'true')
        if not (1 <= value.max_links <= 20 and 1 <= value.max_documents <= 500 and 1 <= value.max_pages <= 100):
            raise ValueError('Limites documentais inválidos; consulte FASE3.md.')
        return value


def official_url(value):
    try:
        url = urlsplit(value)
        if url.hostname == 'pncp.gov.br':
            from src.pncp import official_file_url
            return value if official_file_url(value) else None
        if url.scheme == 'https' and url.hostname in HOSTS and not url.username and not url.password and url.port in (None, 443):
            return value.split('#')[0]
    except (TypeError, ValueError):
        pass
    return None


def inventory(record):
    try:
        links = json.loads(record.get('Links publicados nos detalhes', '[]'))
    except (ValueError, TypeError):
        return [], ['Inventário de links ilegível.']
    if not isinstance(links, list):
        return [], ['Inventário de links não é uma lista.']
    accepted, warnings = [], []
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get('url'), str):
            warnings.append('Link sem URL válida.'); continue
        raw, label = link['url'], str(link.get('rotulo', 'Documento'))[:200]
        if not official_url(raw):
            warnings.append('Link fora dos domínios HTTPS permitidos não foi seguido.'); continue
        url = official_url(raw)
        path = urlsplit(url).path.lower()
        if path.endswith('/visualizar') or not (path.endswith('.pdf') or 'download' in path or
                re.search(r'anexo|documento|arquivo|edital|termo|contrato|aditivo|ata\b', label, re.I)):
            continue  # Navegação do portal não é anexo.
        if not any(item['url'] == url for item in accepted):
            accepted.append({'url': url, 'rotulo': label or 'Documento publicado', 'id': hashlib.sha256(url.encode()).hexdigest()})
    return accepted, list(dict.fromkeys(warnings))


def plan_documents(records, audit, settings=None, *, pncp=None):
    settings = settings or DocumentSettings()
    lines = sorted({f.linha for f in audit.suspeitos})
    if any(not 1 <= line <= len(records) for line in lines):
        raise ValueError('Achado fora da coleta: não é possível associar documentos.')
    from src.pncp import document_links
    pncp_links = document_links(pncp, records, lines)
    entries, unique = [], set()
    for line in lines:
        links, warnings = inventory(records[line - 1])
        links = pncp_links.get(line, []) + [link for link in links
                  if link['id'] not in {d['id'] for d in pncp_links.get(line, [])}]
        if pncp:
            remote = next((e for e in pncp.get('consultas', []) if e['linha'] == line), None)
            if remote and remote.get('documentos_omitidos'):
                warnings.append(f'PNCP: {remote["documentos_omitidos"]} documentos omitidos no inventário por limite.')
        chosen = []
        for link in links[:settings.max_links]:
            if link['id'] in unique or len(unique) < settings.max_documents:
                chosen.append(link); unique.add(link['id'])
        entries.append({'linha': line, 'registro_original': records[line - 1],
                        'registro_sha256': digest(records[line - 1]), 'links': chosen,
                        'links_disponiveis': len(links), 'links_omitidos': len(links) - len(chosen), 'avisos': warnings})
    return {'contratos': len(lines), 'documentos': len(unique),
            'contratos_sem_links': sum(not e['links'] for e in entries),
            'links_omitidos': sum(e['links_omitidos'] for e in entries), 'consultas': entries}


def download_pdf(session, url, target, settings):
    current = url
    for _ in range(4):
        if not official_url(current):
            raise ValueError('Redirecionamento para domínio não permitido.')
        with session.get(current, timeout=(10, 40), stream=True, allow_redirects=False) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                current = urljoin(current, response.headers.get('Location', ''))
                continue
            response.raise_for_status()
            if int(response.headers.get('Content-Length', '0')) > settings.max_bytes:
                raise ValueError(f'PDF excede o limite de {settings.max_bytes} bytes ({settings.max_bytes / 1048576:g} MB).')
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > settings.max_bytes:
                    raise ValueError(f'PDF excede o limite de {settings.max_bytes} bytes ({settings.max_bytes / 1048576:g} MB).')
            # O endpoint de download de Maricá responde {"url": "...pdf"}.
            # Seguir somente esse envelope documentado, com a mesma validação de origem.
            if 'application/json' in response.headers.get('Content-Type', '') and len(content) <= 2000:
                envelope = json.loads(content)
                if not isinstance(envelope, dict) or not isinstance(envelope.get('url'), str):
                    raise ValueError('Resposta de download sem URL de PDF.')
                current = urljoin(current, envelope['url'])
                continue
            if not bytes(content[:1024]).lstrip().startswith(b'%PDF-'):
                raise ValueError('O link não retornou um PDF legível; HTML e outros formatos não foram processados.')
            tmp = target.with_suffix('.download')
            tmp.write_bytes(content); tmp.replace(target)
            return current
    raise ValueError('Limite de redirecionamentos excedido.')


def windows_ocr(page, directory):
    if os.name != 'nt':
        raise RuntimeError('OCR local requer Windows com reconhecimento pt-BR instalado.')
    # Renderização limitada antes de alocar pixels; nenhum serviço externo de OCR.
    resolution = min(180, 2400 * 72 / max(page.width, page.height))
    with tempfile.TemporaryDirectory(prefix='ocr-', dir=directory) as temp:
        image = Path(temp) / 'pagina.png'
        rendered = page.to_image(resolution=resolution)
        rendered.original.save(image)
        # Código fixo do aplicativo; não altera a política de execução do Windows.
        script = Path(__file__).with_name('windows_ocr.ps1').read_text(encoding='utf-8')
        literal_path = str(image.resolve()).replace("'", "''")
        command = "& {\n" + script + "\n} -ImagePath '" + literal_path + "'"
        args = ['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', command]
        child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            stdout, stderr = child.communicate(timeout=60)
            if child.returncode:
                raise RuntimeError('OCR local não disponível ou falhou; confira o idioma pt-BR no Windows.')
            return json.loads(stdout.decode('utf-8-sig'))['texto']
        finally:
            if child.poll() is None:
                child.kill(); child.communicate()


def extract_pdf(path, settings, *, ocr=windows_ocr):
    import pdfplumber
    pages, warnings = [], []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for number, page in enumerate(pdf.pages[:settings.max_pages], 1):
            native = page.extract_text(layout=True) or ''
            text, method, error = native.strip(), 'texto_pdf', None
            image_area = sum(abs(i['x1']-i['x0']) * abs(i['bottom']-i['top']) for i in page.images)
            needs_ocr = len(re.sub(r'\s', '', text)) < 40 or image_area > page.width * page.height * .5
            if needs_ocr:
                if settings.ocr:
                    try:
                        recognized = ocr(page, path.parent).strip()
                        if recognized and len(recognized) >= len(text):
                            text, method = recognized, 'ocr_windows'
                            if len(re.sub(r'\s', '', text)) < 40:
                                error = 'OCR encontrou pouco texto; conferir imagem e cobertura da extração.'
                        elif recognized:
                            error = 'Página contém imagem; OCR retornou menos conteúdo que o texto nativo, que foi preservado. Conferir imagem.'
                        else:
                            error = 'OCR não encontrou texto; pode ser página em branco ou imagem não reconhecida.'
                    except Exception as exc:
                        error = str(exc)
                else:
                    error = 'Página requer conferência de imagem; OCR desativado.'
            try:
                tables = page.extract_tables() if method == 'texto_pdf' else []
            except Exception:
                tables = []
                error = (error + ' ' if error else '') + 'Não foi possível extrair as tabelas desta página.'
            table_limited = len(tables) > 10 or any(len(t) > 100 or any(len(r) > 30 or any(len(str(c or '')) > 2000 for c in r) for r in t) for t in tables)
            limited = len(text) > 30000 or table_limited
            pages.append({'pagina': number, 'texto': text[:30000], 'metodo': method,
                          'tabelas': [[[str(c or '')[:2000] for c in row[:30]] for row in table[:100]] for table in tables[:10]],
                          'truncado': limited, 'aviso': error,
                          'qualidade': 'conferir_imagem' if method.startswith('ocr') or needs_ocr else 'texto_extraido_nao_validado'})
            if error or limited:
                warnings.append(f'Página {number}: {error or "texto/tabelas limitados"}')
            page.close()
    if total > len(pages):
        warnings.append(f'Limite de páginas: {len(pages)} de {total} processadas.')
    readable = sum(bool(p['texto']) for p in pages)
    status = 'nao_lido' if not readable else 'parcial' if warnings or readable < total else 'lido'
    return {'status': status, 'total_paginas': total, 'paginas': pages, 'avisos': warnings}


def read_manifest(folder):
    path = Path(folder) / 'documentos.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def classify_document(document):
    text = ' '.join(p['texto'] for p in document['paginas'][:2]).casefold()
    if 'dados do contrato' in text and ('portal da transparência' in text or 'portal da transparencia' in text):
        document['tipo_documento'] = 'ficha_portal'
        document['nota_tipo'] = 'Exportação da ficha cadastral do portal; não é o instrumento contratual integral nem seus anexos.'
    else:
        document['tipo_documento'] = 'pdf_publicado'
        document['nota_tipo'] = 'PDF publicado: conferir identidade e tipo documental no original.'
    return document


def collect_documents(folder, records, audit, settings=None, *, session=None, extractor=extract_pdf,
                      retry_ids=None):
    settings = settings or DocumentSettings.from_env()
    from src.pncp import read_pncp
    plan = plan_documents(records, audit, settings, pncp=read_pncp(folder))
    target = folder / 'documentos'
    target.mkdir(exist_ok=True)
    previous = read_manifest(folder)
    preserved = {}
    if retry_ids is not None:
        retry_ids = set(retry_ids)
        planned_ids = {link['id'] for entry in plan['consultas'] for link in entry['links']}
        if not previous or not retry_ids or not retry_ids <= planned_ids:
            raise ValueError('Retomada exige manifesto anterior e IDs presentes no planejamento atual.')
        old_entries = {entry['linha']: entry for entry in previous['consultas']}
        if len(old_entries) != len(previous['consultas']) or set(old_entries) != {e['linha'] for e in plan['consultas']}:
            raise ValueError('Manifesto anterior não cobre o planejamento atual.')
        for entry in plan['consultas']:
            old = old_entries[entry['linha']]
            if (old.get('registro_sha256') != entry['registro_sha256'] or
                    old.get('assinatura') != digest({k: v for k, v in old.items() if k != 'assinatura'}) or
                    old.get('links') != entry['links']):
                raise ValueError('Fontes do manifesto anterior incompatíveis com a retomada.')
            link_urls = {link['id']: link['url'] for link in entry['links']}
            seen = set()
            for document in old['documentos']:
                identifier = document['id']
                if (identifier in seen or identifier not in link_urls or
                        document.get('url') != link_urls[identifier]):
                    raise ValueError('Documento anterior incompatível com os links do contrato.')
                seen.add(identifier)
                if identifier in preserved and preserved[identifier] != {
                        k: v for k, v in document.items() if k not in ('rotulo', 'origem', 'tipo_informado_pncp', 'numero_controle_pncp')}:
                    raise ValueError('Documento anterior tem versões divergentes.')
                if identifier not in retry_ids:
                    # Caminho derivado do ID validado pelo planejamento, nunca do manifesto.
                    if identifier not in planned_ids:
                        raise ValueError('Documento anterior fora do planejamento.')
                    if document.get('status') in ('lido', 'parcial') and not document.get('sha256'):
                        raise ValueError('Documento extraído sem hash de origem.')
                    if document.get('sha256'):
                        raw = folder / 'documentos' / f'{identifier}.pdf'
                        if not raw.exists() or hashlib.sha256(raw.read_bytes()).hexdigest() != document['sha256']:
                            raise ValueError('Original preservado ausente ou alterado; refaça a leitura documental.')
                    preserved[identifier] = {k: v for k, v in document.items()
                        if k not in ('rotulo', 'origem', 'tipo_informado_pncp', 'numero_controle_pncp')}
        if not planned_ids - retry_ids <= preserved.keys():
            raise ValueError('Manifesto anterior incompleto para retomada seletiva.')
    if previous:
        save_json(target / 'historico' / f'{digest(previous)}.json', previous)
    owned = session is None
    if owned:
        session = requests.Session(); session.trust_env = False
    policy = digest({'settings': asdict(settings), 'codigo': Path(__file__).read_text(encoding='utf-8'),
                     'ocr': Path(__file__).with_name('windows_ocr.ps1').read_text(encoding='utf-8')})
    result = {'versao': VERSION, 'status': 'em_andamento', 'atualizado_em': datetime.now(timezone.utc).isoformat(),
              'limite': LIMIT, 'planejamento': {k: v for k, v in plan.items() if k != 'consultas'},
              'limites_aplicados': asdict(settings), 'documentos_preservados': len(preserved),
              'retomada_ids': sorted(retry_ids) if retry_ids is not None else None,
              'documentos_processados': 0,
              'consultas': copy.deepcopy(previous['consultas']) if retry_ids is not None else []}
    completed = dict(preserved)

    def publish():
        # Assinatura considera evidência e limites; não muda só por reabrir/reutilizar cache.
        for entry in result['consultas']:
            entry['assinatura'] = digest({k: v for k, v in entry.items() if k != 'assinatura'})
        result['assinatura'] = digest({'consultas': result['consultas'], 'politica': policy})
        save_json(folder / 'documentos.json', result)

    publish()
    try:
        for original in plan['consultas']:
            if retry_ids is not None:
                entry = next(e for e in result['consultas'] if e['linha'] == original['linha'])
            else:
                entry = {**original, 'documentos': []}
                result['consultas'].append(entry)
            for link in entry['links']:
                identifier = link['id']
                if identifier not in completed:
                    pdf_path = target / f'{identifier}.pdf'
                    cache_path = target / f'{identifier}.json'
                    try:
                        try:
                            cached = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
                            if not isinstance(cached, dict):
                                cached = {}
                        except (OSError, ValueError):
                            cached = {}  # Cache ilegível não impede reconstruir o documento.
                        raw_valid = (pdf_path.exists() and cached.get('sha256') == hashlib.sha256(pdf_path.read_bytes()).hexdigest())
                        valid = raw_valid and cached.get('politica') == policy and cached.get('status') == 'lido'
                        if valid:
                            document = cached
                        else:
                            final_url = cached['url_final'] if raw_valid else download_pdf(session, link['url'], pdf_path, settings)
                            document = {**classify_document(extractor(pdf_path, settings)), 'id': identifier,
                                'url': link['url'], 'url_final': final_url, 'politica': policy,
                                'sha256': hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                                'coletado_em': cached['coletado_em'] if raw_valid else datetime.now(timezone.utc).isoformat(),
                                'arquivo': f'documentos/{identifier}.pdf'}
                            save_json(cache_path, document)
                        completed[identifier] = document
                    except Exception as exc:
                        completed[identifier] = {'id': identifier, 'url': link['url'], 'status': 'falhou',
                                                 'erro': str(exc)[:300], 'paginas': []}
                    result['documentos_processados'] += 1
                    print(f'Documento {result["documentos_processados"]}/{plan["documentos"]}: {completed[identifier]["status"]}', flush=True)
                value = {**completed[identifier], 'rotulo': link['rotulo'],
                    **({k: link[k] for k in ('origem', 'tipo_informado_pncp', 'numero_controle_pncp') if k in link})}
                if retry_ids is not None:
                    entry['documentos'] = [value if d['id'] == identifier else d for d in entry['documentos']]
                    if not any(d['id'] == identifier for d in entry['documentos']):
                        entry['documentos'].append(value)
                else:
                    entry['documentos'].append(value)
                publish()
            publish()
        pending = any(e['avisos'] or e['links_omitidos'] or not e['documentos'] or
                      any(d['status'] != 'lido' for d in e['documentos']) for e in result['consultas'])
        result['status'] = 'com_pendencias' if pending else 'concluida'
        publish()
        return result
    except BaseException:
        result['status'] = 'interrompida'; publish(); raise
    finally:
        if owned:
            session.close()


def document_sources(manifest, line, record):
    """Fornece somente páginas extraídas compatíveis, com orçamento explícito."""
    entry = next((e for e in (manifest or {}).get('consultas', []) if e['linha'] == line), None)
    if not entry or entry['registro_sha256'] != digest(record):
        return [], {'status': 'nao_disponivel', 'paginas_incluidas': 0}
    sources, remaining = [], 5000
    pages = [(d, p) for d in entry['documentos'] if d['status'] in ('lido', 'parcial')
             for p in d['paginas'] if len(p['texto'].strip()) >= 8]
    for document, page in pages:
        if remaining < 8 or len(sources) >= 3:
            break
        text = page['texto'][:min(2000, remaining)]
        remaining -= len(text)
        sources.append({'id': f'L{line}-A{len(sources)+1}', 'tipo': 'anexo_portal',
                        'rotulo': ('Ficha cadastral do portal · ' if document.get('tipo_documento') == 'ficha_portal' else '') + document['rotulo'],
                        'tipo_documento': document.get('tipo_documento'), 'nota_tipo': document.get('nota_tipo'),
                        **({k: document[k] for k in ('origem', 'tipo_informado_pncp', 'numero_controle_pncp') if k in document}),
                        'url': document['url'], 'documento_id': document['id'],
                        'pagina': page['pagina'], 'sha256_pdf': document['sha256'],
                        'texto': text, 'truncado': page['truncado'] or len(text) < len(page['texto']),
                        'metodo': page['metodo'], 'qualidade': page['qualidade'], 'aviso': page['aviso']})
    return sources, {'status': 'disponivel' if sources else 'sem_texto_disponivel', 'assinatura': entry['assinatura'],
                     'paginas_incluidas': len(sources), 'paginas_nao_incluidas': len(pages)-len(sources),
                     'limite': 'Trechos iniciais de até 3 páginas e 5000 caracteres por contrato; conteúdo restante não foi fornecido ao modelo. OCR exige conferir a imagem.'}


def main():
    import argparse
    from dataclasses import replace
    from src.audit_models import ParecerAuditoria
    from src.batch_pipeline import execution_lock, load_records
    from src.rag import run_folder
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execucao', required=True)
    parser.add_argument('--documento', action='append', required=True,
                        help='ID do documento a retomar; repetir para vários IDs')
    parser.add_argument('--max-mb', type=int, default=10, choices=range(1, 51), metavar='1..50')
    args = parser.parse_args()
    settings = replace(DocumentSettings.from_env(), max_bytes=args.max_mb * 1024 * 1024)
    folder = run_folder(args.execucao)
    with execution_lock(folder):
        records = load_records(folder)
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        result = collect_documents(folder, records, audit, settings, retry_ids=args.documento)
    print(f'Retomada documental: {result["documentos_processados"]} documentos processados; {result["status"]}. Sem IA ou banco.')


if __name__ == '__main__':
    main()
