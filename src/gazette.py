"""Consulta documental ao DOM/JOM oficial, restrita aos contratos com achados.

Correspondências são candidatas para revisão, nunca confirmação automática de
irregularidade. A cobertura e os arquivos sem texto pesquisável ficam explícitos.
"""
import argparse
import hashlib
import io
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from src.office_activity import source_request
from bs4 import BeautifulSoup

from src.audit_models import ParecerAuditoria
from src.tools.archive_tool import field, normalized

BASE = 'https://www.marica.rj.gov.br'
TYPES = ('dom', 'dom-extraordinario', 'jom', 'jom-especial')
START, END = '<!-- diario-oficial:inicio -->', '<!-- diario-oficial:fim -->'


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def official_url(raw):
    value = urljoin(BASE, raw)
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.hostname not in {'www.marica.rj.gov.br', 'marica.rj.gov.br'}
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        raise ValueError('Endereço fora da fonte oficial permitida.')
    return value


@dataclass(frozen=True)
class GazetteSettings:
    max_editions: int = 40
    catalog_pages: int = 2
    per_page: int = 100
    max_file_bytes: int = 25 * 1024 * 1024
    max_pdf_pages: int = 150
    pause_seconds: float = 0.4
    cache_hours: float = 24

    @classmethod
    def from_env(cls):
        result = cls(max_editions=int(os.getenv('GAZETTE_MAX_EDITIONS', '40')),
                     catalog_pages=int(os.getenv('GAZETTE_CATALOG_PAGES', '2')),
                     cache_hours=float(os.getenv('GAZETTE_CACHE_HOURS', '24')))
        if not (1 <= result.max_editions <= 500 and 1 <= result.catalog_pages <= 20 and 0 <= result.cache_hours <= 168):
            raise ValueError('GAZETTE_MAX_EDITIONS: 1..500; GAZETTE_CATALOG_PAGES: 1..20; GAZETTE_CACHE_HOURS: 0..168.')
        return result


def identifier(record):
    detail = field(record, ('detalhe - numero',))
    contract = None
    if detail:
        match = re.fullmatch(r'\s*0*(\d+)\s*[-/]\s*((?:19|20)\d{2})\s*', detail)
        if match:
            contract = f'{int(match[1])}/{match[2]}'
    process_raw = field(record, ('detalhe - processo',)) or field(record, ('numero do processo', 'nr [nr processo]', 'nr processo', 'processo'))
    process = None
    if process_raw:
        matches = re.findall(r'(?<!\d)(\d+)\s*/\s*((?:19|20)\d{2})(?!\d)', process_raw)
        if len(matches) == 1:
            process = f'{int(matches[0][0])}/{matches[0][1]}'
    if not contract:
        listed = field(record, ('nr [nr processo]',)) or ''
        number = re.match(r'^\s*(\d+)\s*\[', listed)
        signed = field(record, ('detalhe - assinatura',)) or field(record, ('data assinatura',)) or ''
        year = re.search(r'\d{2}/\d{2}/((?:19|20)\d{2})', signed)
        if number and year:
            contract = f'{int(number[1])}/{year[1]}'
    document = field(record, ('detalhe - cpf/cnpj',)) or ''
    cnpj = re.sub(r'\D', '', document)
    if len(cnpj) != 14:
        cnpj = None  # Não pesquisa CPF de pessoas físicas como identificador de contrato.
    signed = field(record, ('detalhe - assinatura',)) or field(record, ('data assinatura',))
    try:
        date = datetime.strptime(signed, '%d/%m/%Y').date().isoformat() if signed else None
    except ValueError:
        date = None
    return {'contrato': contract, 'processo': process, 'cnpj': cnpj, 'assinatura': date}


def reference_pattern(reference):
    number, year = reference.split('/')
    return re.compile(r'(?<!\d)0*' + re.escape(number) + r'\s*/\s*' + year + r'(?!\d)')


def match_page(text, identifiers):
    """Restringe a evidência ao entorno da referência, não à página inteira."""
    text = re.sub(r'\s+', ' ', text).strip()
    contract_pattern = reference_pattern(identifiers['contrato']) if identifiers.get('contrato') else None
    process_pattern = reference_pattern(identifiers['processo']) if identifiers.get('processo') else None
    candidates = []
    if contract_pattern:
        for match in contract_pattern.finditer(text):
            prefix = normalized(text[max(0, match.start() - 65):match.start()])
            # Número/ano isolado pode se referir a licitação ou a outro instrumento.
            if not re.search(r'\bcontrato\b.{0,55}$', prefix):
                continue
            candidates.append((match.start(), match.end(), 'contrato_e_ano'))
    if process_pattern:
        candidates += [(m.start(), m.end(), 'processo_e_ano') for m in process_pattern.finditer(text)
                       if re.search(r'\bprocesso\b.{0,65}$', normalized(text[max(0, m.start() - 75):m.start()]))]
    results = []
    for start, end, basis in candidates:
        snippet = text[max(0, start - 180):min(len(text), end + 550)]
        indicators = [basis]
        if process_pattern and process_pattern.search(snippet) and basis != 'processo_e_ano':
            indicators.append('processo_e_ano_no_trecho')
        cnpj = identifiers.get('cnpj')
        if cnpj and cnpj in re.sub(r'\D', '', snippet):
            indicators.append('cnpj_no_trecho')
        reinforced = len(indicators) > 1
        result = {'trecho': snippet, 'criterios': indicators,
                  'correspondencia': 'candidata_com_identificador_adicional' if reinforced else 'candidata_para_conferencia',
                  'limite': 'Conferir órgão, fornecedor, objeto e período no documento original; coincidência não confirma irregularidade.'}
        if not any(abs(start - previous) < 220 for previous, _ in results):
            results.append((start, result))
    return [result for _, result in results[:5]]


def extract_pdf(data, max_pages):
    import pdfplumber
    pages, blank = [], 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        total = len(pdf.pages)
        for index, page in enumerate(pdf.pages[:max_pages], 1):
            chars = getattr(page, 'chars', [])
            columns = False
            if isinstance(chars, list) and len(chars) > 500:
                middle = page.width / 2
                body = [c for c in chars if 50 < c['top'] < page.height - 30]
                crossing = sum(c['x0'] < middle + 3 and c['x1'] > middle - 3 for c in body)
                left = sum(c['x1'] < middle - 3 for c in body)
                right = sum(c['x0'] > middle + 3 for c in body)
                columns = (len(body) > 500 and min(left, right) > len(body) * .2
                           and crossing < max(3, len(body) * .003))
            if columns:
                texts = [page.crop((0, 0, page.width / 2, page.height)).extract_text() or '',
                         page.crop((page.width / 2, 0, page.width, page.height)).extract_text() or '']
            else:
                texts = [page.extract_text() or '']
            if sum(len(text.strip()) for text in texts) < 30:
                blank += 1
            for column, text in enumerate(texts, 1):
                pages.append({'pagina': index, 'coluna': column if columns else None, 'texto': text})
    return {'paginas': pages, 'total_paginas': total, 'paginas_sem_texto': blank,
            'limitado': total > max_pages, 'ocr_realizado': False}


class GazetteClient:
    def __init__(self, cache_dir, settings):
        self.cache_dir, self.settings = Path(cache_dir), settings
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'AuditoriaCidada/1.0 (consulta de publicacoes oficiais)'

    def close(self):
        self.session.close()

    def fetch(self, url, *, params=None):
        url = official_url(url)
        for _ in range(4):
            time.sleep(self.settings.pause_seconds)
            with source_request(url, 'Prefeitura de Maricá · Diário Oficial'), self.session.get(url, params=params, timeout=(10, 35), stream=True, allow_redirects=False) as response:
                if response.is_redirect:
                    url = official_url(urljoin(url, response.headers['Location']))
                    params = None
                    continue
                response.raise_for_status()
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > self.settings.max_file_bytes:
                        raise ValueError('Arquivo excede o limite de download configurado.')
                    chunks.append(chunk)
                return b''.join(chunks), dict(response.headers)
        raise ValueError('Redirecionamentos excederam o limite.')

    def catalog(self):
        editions, coverage = [], []
        for kind in TYPES:
            count, total, error = 0, None, None
            for number in range(1, self.settings.catalog_pages + 1):
                try:
                    raw, headers = self.fetch(f'{BASE}/wp-json/wp/v2/{kind}', params={
                        'per_page': self.settings.per_page, 'page': number, 'orderby': 'date', 'order': 'desc',
                        '_fields': 'id,date,link,title,acf'})
                    items = json.loads(raw)
                    if not isinstance(items, list):
                        raise ValueError('Catálogo oficial em formato inesperado.')
                    total = int(headers.get('X-WP-Total') or headers.get('x-wp-total') or len(items))
                    for item in items:
                        editions.append({'id': item['id'], 'tipo': kind, 'url': official_url(item['link']),
                            'titulo': BeautifulSoup(item['title']['rendered'], 'html.parser').get_text(' ', strip=True),
                            'data_catalogo': item['date'][:10]})
                    count += len(items)
                    if count >= total or not items:
                        break
                except Exception as exc:
                    error = str(exc)
                    break
            coverage.append({'fonte': kind, 'listadas': count, 'total_informado': total,
                             'catalogo_parcial': error is not None or total is None or count < total, 'erro': error})
        return editions, coverage

    def read_edition(self, edition):
        key = hashlib.sha256(edition['url'].encode()).hexdigest()
        cached = self.cache_dir / (key + '.json')
        if cached.exists() and time.time() - cached.stat().st_mtime < self.settings.cache_hours * 3600:
            try:
                value = json.loads(cached.read_text(encoding='utf-8'))
                if value.get('max_paginas') == self.settings.max_pdf_pages:
                    if value.get('versao') == 2:
                        return value
                    old_pdf = self.cache_dir / (key + '.pdf')
                    if value.get('versao') == 1 and old_pdf.exists():
                        pdf = old_pdf.read_bytes()
                        if hashlib.sha256(pdf).hexdigest() == value.get('sha256_pdf'):
                            value.update(extract_pdf(pdf, self.settings.max_pdf_pages), versao=2)
                            save_json(cached, value)
                            return value
            except (ValueError, OSError):
                pass
        raw, _ = self.fetch(edition['url'])
        soup = BeautifulSoup(raw, 'html.parser')
        assets = {}
        for anchor in soup.select('a[href]'):
            label = normalized(anchor.get_text(' ', strip=True))
            if 'baixar arquivo pdf' in label:
                assets['pdf'] = official_url(anchor['href'])
            elif 'baixar arquivo txt' in label:
                assets['txt'] = official_url(anchor['href'])
        if 'pdf' not in assets:
            raise ValueError('PDF da edição não localizado na página oficial.')
        pdf, _ = self.fetch(assets['pdf'])
        if not pdf.startswith(b'%PDF-'):
            raise ValueError('O arquivo recebido não é um PDF.')
        filename = self.cache_dir / (key + '.pdf')
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_bytes(pdf)
        extracted = extract_pdf(pdf, self.settings.max_pdf_pages)
        value = {**edition, **extracted, 'versao': 2, 'max_paginas': self.settings.max_pdf_pages,
                 'url_pdf': assets['pdf'], 'sha256_pdf': hashlib.sha256(pdf).hexdigest(), 'arquivo_local': str(filename)}
        save_json(cached, value)
        return value


def select_editions(editions, targets, limit):
    # Distribui a cobertura entre as datas dos contratos, em vez de olhar só a edição mais recente.
    dates = list(dict.fromkeys(t['identificadores']['assinatura'] for t in targets if t['identificadores']['assinatura']))
    ranked = []
    for date in dates:
        day = datetime.fromisoformat(date)
        ranked.append(sorted(editions, key=lambda e: (abs((datetime.fromisoformat(e['data_catalogo']) - day).days), e['url'])))
    ranked.append(sorted(editions, key=lambda e: e['data_catalogo'], reverse=True))
    selected, seen = [], set()
    for offset in range(len(editions)):
        for group in ranked:
            if offset < len(group) and group[offset]['url'] not in seen:
                item = group[offset]
                selected.append(item)
                seen.add(item['url'])
                if len(selected) >= limit:
                    return selected
    return selected


def consult_gazette(records, audit, output_dir, settings=None, *, client=None):
    settings = settings or GazetteSettings.from_env()
    lines = sorted({f.linha for f in audit.suspeitos if 1 <= f.linha <= len(records)})
    targets = [{'linha': line, 'identificadores': identifier(records[line - 1]), 'resultados': []} for line in lines]
    signature = hashlib.sha256(json.dumps({'alvos': targets, 'limite': settings.max_editions,
        'paginas_catalogo': settings.catalog_pages, 'paginas_pdf': settings.max_pdf_pages,
        'itens_catalogo': settings.per_page, 'versao': 2}, sort_keys=True).encode()).hexdigest()
    artifact = output_dir / 'diario_oficial.json'
    if artifact.exists():
        try:
            saved = json.loads(artifact.read_text(encoding='utf-8'))
            if saved.get('assinatura') == signature and saved.get('edicoes_lidas', 0) > 0 and time.time() - artifact.stat().st_mtime < settings.cache_hours * 3600:
                return saved
        except (ValueError, OSError):
            pass
    result = {'versao': 1, 'assinatura': signature, 'consultado_em': datetime.now(timezone.utc).isoformat(),
              'status': 'sem_achados' if not targets else 'consulta_parcial', 'consultas': targets,
              'edicoes_lidas': 0, 'edicoes_consultadas': [], 'falhas': [],
              'limite': 'Não localizar uma referência nas edições consultadas não comprova falta de publicação. '
                        'Correspondências precisam de revisão humana; datas do catálogo podem diferir da data impressa da edição.'}
    if not targets:
        save_json(artifact, result)
        return result
    owns_client = client is None
    client = client or GazetteClient(Path(__file__).resolve().parents[1] / 'data' / 'gazette_cache', settings)
    try:
        editions, catalog_coverage = client.catalog()
        result['catalogos'] = catalog_coverage
        selected = select_editions(editions, targets, settings.max_editions)
        result.update(edicoes_catalogadas=len(editions), edicoes_planejadas=len(selected),
                      limite_edicoes=settings.max_editions, paginas_sem_texto=0,
                      limitado=len(selected) < len(editions) or any(c['catalogo_parcial'] for c in catalog_coverage))
        for number, edition in enumerate(selected, 1):
            logging.info('Diário Oficial: consultando edição %d/%d (%s).', number, len(selected), edition['titulo'])
            try:
                document = client.read_edition(edition)
                result['edicoes_lidas'] += 1
                result['paginas_sem_texto'] += document['paginas_sem_texto']
                result['limitado'] |= document['limitado'] or document['paginas_sem_texto'] > 0
                result['edicoes_consultadas'].append({k: document[k] for k in ('titulo', 'url', 'url_pdf', 'data_catalogo', 'sha256_pdf', 'total_paginas', 'paginas_sem_texto', 'limitado')})
                for page in document['paginas']:
                    for target in targets:
                        for hit in match_page(page['texto'], target['identificadores']):
                            target['resultados'].append({**hit, 'edicao': document['titulo'], 'fonte': document['tipo'],
                                'url_edicao': document['url'], 'url_pdf': document['url_pdf'],
                                'data_catalogo': document['data_catalogo'], 'pagina': page['pagina'],
                                'coluna': page.get('coluna'),
                                'sha256_pdf': document['sha256_pdf']})
            except Exception as exc:
                result['falhas'].append({'url': edition['url'], 'erro': str(exc)})
        result['status'] = 'consulta_parcial' if result['limitado'] or result['falhas'] else 'consulta_concluida_no_catalogo'
        if not result['edicoes_lidas']:
            result['status'] = 'consulta_indisponivel'
        for target in targets:
            has_id = target['identificadores']['contrato'] or target['identificadores']['processo']
            target['status'] = ('candidatos_localizados' if target['resultados'] else
                                'identificacao_insuficiente' if not has_id else
                                'consulta_indisponivel' if result['status'] == 'consulta_indisponivel' else
                                'nao_localizado_nas_edicoes_consultadas')
    except Exception as exc:
        result['status'] = 'consulta_indisponivel'
        result['falhas'].append({'erro': str(exc)})
    finally:
        if owns_client:
            client.close()
    save_json(artifact, result)
    return result


def gazette_report(report, result):
    clean = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', '', report, flags=re.S)
    parts = [START, '## Consulta ao Diário Oficial e ao Jornal Oficial',
             f'Consulta documental: {result["status"]}. Edições lidas: {result["edicoes_lidas"]}.', result['limite']]
    for target in result['consultas']:
        parts.append(f'### Linha {target["linha"]} — {target.get("status", "consulta indisponível")}')
        for hit in target['resultados']:
            parts += [f'- {hit["edicao"]}, página {hit["pagina"]}: [abrir PDF oficial]({hit["url_pdf"]}#page={hit["pagina"]}). '
                      f'Critérios: {", ".join(hit["criterios"])}. Correspondência candidata, sujeita a conferência.',
                      '> ' + hit['trecho']]
    parts += [END, '']
    return clean.rstrip() + '\n\n' + '\n\n'.join(parts)


def enrich_saved_audit(output_dir, records, audit, settings=None, *, client=None):
    result = consult_gazette(records, audit, output_dir, settings, client=client)
    updated = audit.model_copy(update={'relatorio_markdown': gazette_report(audit.relatorio_markdown, result)})
    save_json(output_dir / 'parecer.json', updated.model_dump())
    (output_dir / 'relatorio.md').write_text(updated.relatorio_markdown, encoding='utf-8')
    return updated


def main():
    from src.batch_pipeline import execution_lock, load_records
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Consultar DOM/JOM para achados de uma auditoria salva, sem Gemini/banco.')
    parser.add_argument('--execucao', help='ID da execução; padrão é a mais recente com parecer.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / 'data' / 'reports'
    candidates = sorted(root.iterdir(), reverse=True) if root.exists() else []
    folder = (root / args.execucao).resolve() if args.execucao else next(
        (p for p in candidates if p.is_dir() and (p / 'parecer.json').exists()), None)
    if folder is None:
        parser.error('Nenhuma auditoria salva com parecer foi encontrada.')
    if folder.parent != root.resolve():
        parser.error('Informe apenas um ID de data/reports.')
    with execution_lock(folder):
        records = load_records(folder)
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        enrich_saved_audit(folder, records, audit)
        result = json.loads((folder / 'diario_oficial.json').read_text(encoding='utf-8'))
    print(f'Status: {result["status"]}; edições lidas: {result["edicoes_lidas"]}.')
    print(f'Consulta salva em {folder / "diario_oficial.json"}. Gemini e banco não foram chamados.')


if __name__ == '__main__':
    main()
