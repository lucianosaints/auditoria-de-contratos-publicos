"""Execução financeira publicada: vínculos explícitos, identidade conferida e valores exatos."""
import hashlib
import json
import re
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from src.atomic_files import write_json
from src.documents import digest
from src.management_analytics import cents, currency
from src.pncp import number_year, cnpj
from src.tools.portal_details import parse_details

BASE = 'https://transparencia.marica.rj.gov.br/e-cidade/consulta-empenhos'
LIMIT = ('Valores e movimentações declarados pelo portal, sem confirmação bancária ou comprovação de entrega. '
         'Consulta aos exercícios e quadros renderizados identificados; completude municipal não comprovada. '
         'Ausência no recorte não significa ausência de empenho ou pagamento. '
         'Associação exige empenho publicado na ficha do contrato, CNPJ e processo; nomes isolados não vinculam registros.')


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold()) if not unicodedata.combining(c))


def processes(value):
    return {(int(a), int(b)) for a, b in re.findall(
        r'\bprocesso(?:\s+administrativo)?\s*(?:n[.º°o]*\s*)?[:.]?\s*(\d+)\s*/\s*(20\d{2})', normalized(value))}


def date_now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_path(folder, name):
    if not re.fullmatch(r'detalhes/[a-f0-9]{64}\.html', name or ''):
        raise ValueError('Caminho da ficha do contrato não permitido.')
    folder = Path(folder).resolve()
    path = (folder / name).resolve()
    if not path.is_relative_to(folder / 'detalhes'):
        raise ValueError('Caminho da ficha fora da execução.')
    return path


def plan_financial(folder, records):
    entries, hashes = [], {}
    for line, record in enumerate(records, 1):
        entry = {'linha': line, 'registro_sha256': digest(record), 'vinculos': [], 'avisos': []}
        try:
            name = record.get('Arquivo HTML dos detalhes')
            path = source_path(folder, name)
            expected_name = hashlib.sha256(record['URL do contrato'].encode()).hexdigest() + '.html'
            if path.name != expected_name:
                raise ValueError('Ficha HTML não corresponde à URL do contrato.')
            html = path.read_text(encoding='utf-8')
            parsed = parse_details(html, record['URL do contrato'])
            if any(record.get(k) != v for k, v in parsed.items()):
                raise ValueError('Ficha HTML e registro salvo divergem; atualize a coleta antes de vincular.')
            hashes[name] = file_hash(path)
            soup = BeautifulSoup(html, 'html.parser')
            label = next((e for e in soup.select('.width-100') if normalized(e.get_text(' ', strip=True)).rstrip(':') == 'empenhos'), None)
            section = label.find_next_sibling() if label else None
            for row in section.select('tbody tr') if section else []:
                cells = row.select('td')
                if len(cells) != 3:
                    raise ValueError('Estrutura dos empenhos publicados no contrato mudou.')
                identifier = number_year(cells[0].get_text(' ', strip=True))
                anchor = cells[-1].select_one('a[href]')
                url = anchor['href'] if anchor else None
                if not identifier or not url or not re.fullmatch(
                        r'https://transparencia\.marica\.rj\.gov\.br/e-cidade/contratos/padrao/\d+/empenho', url):
                    raise ValueError('Vínculo de empenho inválido na ficha do contrato.')
                value = {'empenho': f'{identifier[0]}/{identifier[1]}', 'ano': identifier[1],
                         'resumo_publicado': cells[1].get_text(' ', strip=True), 'url_publicada_no_contrato': url}
                if value not in entry['vinculos']:
                    entry['vinculos'].append(value)
            entry['status_ficha'] = 'compativel'
        except (OSError, ValueError, KeyError, TypeError) as exc:
            entry.update(status_ficha='indisponivel_ou_divergente', vinculos=[])
            entry['avisos'].append(str(exc)[:300])
        entries.append(entry)
        if line % 50 == 0:
            print(f'Planejamento financeiro: {line}/{len(records)} fichas conferidas.', flush=True)
    return {'consultas': entries, 'fontes_fichas_sha256': hashes,
            'exercicios': sorted({v['ano'] for e in entries for v in e['vinculos']}),
            'vinculos_publicados': sum(len(e['vinculos']) for e in entries)}


def read_amount(value):
    amount, status = cents(value)
    if status != 'valido':
        raise ValueError('Valor financeiro ausente ou em formato inválido na fonte.')
    return amount


def parse_catalog(html, year, max_rows=5000):
    soup = BeautifulSoup(html, 'html.parser')
    selected = soup.select_one('select[name=year] option[selected]')
    if not selected or selected.get('value') != str(year):
        raise ValueError('Exercício financeiro não foi confirmado na fonte.')
    table = next((t for t in soup.select('table') if
                  [normalized(h.get_text(' ', strip=True)) for h in t.select('thead th')][:2] == ['empenho', 'data de emissao']), None)
    if table is None or len(table.select('thead th')) != 12:
        raise ValueError('Tabela de empenhos não reconhecida.')
    if normalized(table.select('thead th')[10].get_text(' ', strip=True)) != 'pago':
        raise ValueError('Colunas financeiras do portal mudaram.')
    rows, seen = [], set()
    for tr in table.select('tbody tr'):
        cells = tr.select('td')
        if len(cells) == 1 and 'nenhum' in normalized(cells[0].get_text()):
            continue
        if len(cells) != 12 or len(rows) >= max_rows:
            raise ValueError('Tabela parcial, excessiva ou com colunas inconsistentes.')
        text = [c.get_text(' ', strip=True) for c in cells]
        identifier = number_year(text[0])
        anchor = cells[-1].select_one('a[href]')
        url = anchor['href'] if anchor else ''
        if not identifier or identifier[1] != year or not re.fullmatch(
                re.escape(BASE) + r'/\d+/visualizar\?origin=detailed-encumbrance-search', url) or url in seen:
            raise ValueError('Identidade, exercício ou link repetido/inválido no catálogo financeiro.')
        seen.add(url)
        rows.append({'empenho': f'{identifier[0]}/{identifier[1]}', 'cnpj': cnpj(text[3]),
                     'beneficiario': text[2], 'unidade': text[4], 'procedimento': text[6],
                     'objeto': text[7], 'url': url,
                     'totais': {k: currency(read_amount(text[i])) for k, i in [('empenhado', 8), ('liquidado', 9), ('pago', 10)]}})
    footer = table.select('tfoot td')
    if len(footer) != 12:
        raise ValueError('Totais do quadro financeiro não disponíveis para conferência.')
    totals = {}
    for key, pos in [('empenhado', 8), ('liquidado', 9), ('pago', 10)]:
        total = read_amount(footer[pos].get_text(' ', strip=True))
        if total != sum(read_amount(row['totais'][key]) for row in rows):
            raise ValueError('Soma das linhas financeiras difere do rodapé do quadro.')
        totals[key] = currency(total)
    if soup.select('.pagination a[href]'):
        raise ValueError('Paginação adicional detectada; consulta não apresentada como completa.')
    return rows, totals


def parse_encumbrance(html, expected, expected_process):
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.select_one('.content')
    if content is None or 'Dados do Empenho' not in content.get_text(' ', strip=True):
        raise ValueError('Resposta não contém Dados do Empenho.')
    fields = {}
    for label in content.select('.width-100'):
        sibling = label.find_next_sibling()
        if sibling is not None:
            fields[normalized(label.get_text(' ', strip=True)).rstrip(':')] = sibling.get_text(' ', strip=True)
    if number_year(fields.get('numero')) != number_year(expected):
        raise ValueError('A URL retornou outro empenho; valores rejeitados por identidade incompatível.')
    if normalized(fields.get('instituicao', '')) != 'prefeitura municipal de marica':
        raise ValueError('Instituição do empenho fora da cobertura inicial (Prefeitura).')
    if processes(fields.get('resumo', '')) != {expected_process}:
        raise ValueError('Processo no resumo do empenho ausente, ambíguo ou divergente.')
    totals = {k: currency(read_amount(fields.get(k))) for k in ('empenhado', 'anulado', 'liquidado', 'pago')}
    events = []
    event_table = next((t for t in content.select('table') if [normalized(h.get_text(' ', strip=True))
                       for h in t.select('thead th')] == ['data', 'tipo', 'valor', 'historico']), None)
    if event_table is None:
        raise ValueError('Movimentações não disponíveis no detalhe financeiro.')
    for position, tr in enumerate(event_table.select('tbody tr'), 1):
        cells = [c.get_text(' ', strip=True) for c in tr.select('td')]
        if len(cells) != 4 or len(events) >= 1000:
            raise ValueError('Movimentações incompletas ou acima do limite de 1000 por empenho.')
        datetime.strptime(cells[0], '%d/%m/%Y')
        kind = normalized(cells[1])
        category = 'reversao_ou_anulacao' if any(s in kind for s in ('estorno', 'anulacao')) else (
            'pagamento' if kind.startswith('pagamento') else 'liquidacao' if kind.startswith('liquidacao') else 'empenho' if kind == 'empenho' else 'outro')
        events.append({'posicao_na_fonte': position, 'data': cells[0], 'tipo_publicado': cells[1],
                       'categoria': category, 'valor': currency(read_amount(cells[2])), 'historico': cells[3]})
    warnings = []
    if read_amount(totals['pago']) > read_amount(totals['liquidado']):
        warnings.append('Pago informado supera liquidado informado: conferir período, restos a pagar e estornos. Não é conclusão de irregularidade.')
    if read_amount(totals['anulado']) > read_amount(totals['empenhado']):
        warnings.append('Anulado informado supera empenhado informado; conferir definição e período dos campos.')
    fingerprints = [digest({k: v for k, v in event.items() if k != 'posicao_na_fonte'}) for event in events]
    if len(set(fingerprints)) != len(fingerprints):
        warnings.append('Há movimentações idênticas sem ID público: preservadas sem deduplicação ou soma automática.')
    return {'empenho': expected, 'instituicao': fields['instituicao'], 'emissao': fields.get('emissao'),
            'resumo': fields['resumo'], 'totais_informados': totals, 'movimentacoes': events, 'avisos': warnings}


@dataclass(frozen=True)
class FinancialSettings:
    max_details: int = 100
    max_bytes: int = 8 * 1024 * 1024
    cache_hours: int = 1


class FinancialClient:
    def __init__(self, folder, settings, session=None):
        self.folder, self.settings = Path(folder), settings
        self.owned = session is None
        self.session = session or requests.Session()
        if self.owned:
            self.session.trust_env = False

    def close(self):
        if self.owned:
            self.session.close()

    def get(self, url, data=None):
        if not (url in (BASE, BASE + '/pesquisar') or re.fullmatch(re.escape(BASE) + r'/\d+/visualizar\?origin=detailed-encumbrance-search', url)):
            raise ValueError('Endpoint financeiro não permitido.')
        parameters = {k: v for k, v in (data or {}).items() if k != '_token'}
        key = digest([url, parameters])
        meta_path = self.folder / 'financeiro/cache' / f'{key}.json'
        html_path = meta_path.with_suffix('.html')
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            age = datetime.now(timezone.utc) - datetime.fromisoformat(meta['coletado_em'])
            if timedelta(0) <= age < timedelta(hours=self.settings.cache_hours) and file_hash(html_path) == meta['sha256']:
                return html_path.read_text(encoding='utf-8'), meta
        except (ValueError, OSError, KeyError, TypeError):
            pass
        for attempt in range(3):
            method = 'POST' if data is not None else 'GET'
            with self.session.request(method, url, data=data, timeout=(10, 40), stream=True, allow_redirects=False) as response:
                if response.status_code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(attempt + 1); continue
                if response.status_code != 200:
                    raise ValueError(f'Consulta financeira retornou HTTP {response.status_code}.')
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > self.settings.max_bytes:
                        raise ValueError('Resposta financeira excede 8 MB.')
                html = bytes(body).decode('utf-8-sig')
                html_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = html_path.with_suffix('.tmp')
                temporary.write_text(html, encoding='utf-8'); temporary.replace(html_path)
                meta = {'url': url, 'parametros': parameters, 'sha256': file_hash(html_path),
                        'coletado_em': date_now(), 'arquivo': html_path.relative_to(self.folder).as_posix()}
                write_json(meta_path, meta)
                return html, meta
        raise ValueError('Consulta financeira indisponível.')


def collect_financial(folder, records, settings=None, *, session=None):
    folder, settings = Path(folder), settings or FinancialSettings()
    plan = plan_financial(folder, records)
    result = {'versao': 1, 'status': 'em_andamento', 'consultado_em': date_now(), 'limite': LIMIT,
              'fontes_sha256': {'contratos.json': file_hash(folder / 'contratos.json'), **plan['fontes_fichas_sha256']},
              'vinculos_publicados': plan['vinculos_publicados'], 'catalogos': [], 'processados': 0,
              'consultas': [{**e, 'situacao': 'pendente', 'empenhos': []} for e in plan['consultas']]}
    path = folder / 'financeiro.json'
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        write_json(folder / 'financeiro/historico' / f'{digest(old)}.json', old)

    def publish():
        result['assinatura'] = digest({k: v for k, v in result.items() if k != 'assinatura'})
        write_json(path, result)

    client = FinancialClient(folder, settings, session)
    publish()
    try:
        initial, _ = client.get(BASE)
        initial_soup = BeautifulSoup(initial, 'html.parser')
        token = initial_soup.select_one('input[name=_token]')
        available = {o.get('value') for o in initial_soup.select('select[name=year] option')}
        catalog = []
        for year in plan['exercicios']:
            try:
                if not token or str(year) not in available:
                    raise ValueError('Exercício não disponível no formulário financeiro.')
                html, meta = client.get(BASE + '/pesquisar', {'_token': token['value'], 'year': str(year),
                    'month': '', 'unit': '', 'beneficiary': '', 'document': '', 'encumbrance_number': ''})
                rows, totals = parse_catalog(html, year)
                for row in rows:
                    row['fonte_catalogo'] = meta
                catalog.extend(rows)
                result['catalogos'].append({'ano': year, 'status': 'quadro_conferido', 'linhas': len(rows),
                    'totais_do_quadro': totals, 'fonte': meta, 'completude_municipal': 'nao_comprovada'})
            except (ValueError, requests.RequestException) as exc:
                result['catalogos'].append({'ano': year, 'status': 'falhou', 'erro': str(exc)[:300]})
            publish()
        claims = Counter((v['empenho'], cnpj(records[e['linha']-1].get('Detalhe - CPF/CNPJ')))
                         for e in plan['consultas'] for v in e['vinculos'])
        cached_details, queries = {}, 0
        for entry in result['consultas']:
            record = records[entry['linha'] - 1]
            supplier = cnpj(record.get('Detalhe - CPF/CNPJ'))
            process = number_year(record.get('Detalhe - Processo'))
            for link in entry['vinculos']:
                remote = [r for r in catalog if r['empenho'] == link['empenho'] and supplier and r['cnpj'] == supplier
                          and process and processes(r['objeto']) == {process}]
                detail = {**link, 'situacao': 'nao_localizado_no_recorte'}
                if claims[(link['empenho'], supplier)] > 1:
                    detail['situacao'] = 'vinculo_compartilhado_conferir'
                elif len(remote) > 1:
                    detail['situacao'] = 'candidatos_ambiguos'
                elif len(remote) == 1:
                    source = remote[0]
                    try:
                        if source['url'] not in cached_details:
                            if queries >= settings.max_details:
                                raise ValueError('Limite de detalhes financeiros atingido; retome os caches concluídos.')
                            queries += 1
                            html, meta = client.get(source['url'])
                            parsed = parse_encumbrance(html, link['empenho'], process)
                            if any(parsed['totais_informados'][k] != source['totais'][k] for k in source['totais']):
                                raise ValueError('Totais do detalhe e catálogo divergem; não agregados.')
                            cached_details[source['url']] = {**parsed, 'fonte': meta, 'fonte_catalogo': source['fonte_catalogo']}
                        detail.update(situacao='vinculo_conferido', **cached_details[source['url']],
                                      criterio='Empenho publicado na ficha + CNPJ e processo no catálogo + número, processo e instituição no detalhe.')
                    except (ValueError, requests.RequestException) as exc:
                        detail.update(situacao='falhou_ou_divergente', erro=str(exc)[:300])
                entry['empenhos'].append(detail)
            entry['situacao'] = ('fonte_contratual_indisponivel' if entry['status_ficha'] != 'compativel' else
                'sem_vinculos_na_ficha' if not entry['vinculos'] else
                'conferida_no_recorte' if all(d['situacao'] == 'vinculo_conferido' for d in entry['empenhos']) else 'com_pendencias')
            result['processados'] += 1
            if entry['vinculos']:
                print(f'Financeiro linha {entry["linha"]}: {entry["situacao"]}.', flush=True)
            publish()
        verified = {d['fonte']['url']: d for e in result['consultas'] for d in e['empenhos'] if d['situacao'] == 'vinculo_conferido'}
        result['resumo'] = {'linhas': len(records), 'linhas_com_vinculos_publicados': sum(bool(e['vinculos']) for e in result['consultas']),
            'linhas_com_empenhos_conferidos': sum(any(d['situacao'] == 'vinculo_conferido' for d in e['empenhos']) for e in result['consultas']),
            'empenhos_unicos_conferidos': len(verified), 'totais_informados_do_recorte': {
                k: currency(sum(read_amount(d['totais_informados'][k]) for d in verified.values())) if verified else None
                for k in ('empenhado', 'anulado', 'liquidado', 'pago')},
            'entrega': 'nao_avaliavel_sem_medicoes_e_atestos'}
        result['status'] = 'consulta_com_pendencias' if any(e['situacao'] in ('com_pendencias', 'fonte_contratual_indisponivel') for e in result['consultas']) else 'concluida_no_recorte'
        publish(); return result
    except BaseException:
        result['status'] = 'interrompida'; publish(); raise
    finally:
        client.close()


def saved_financial(folder, line=None):
    folder = Path(folder)
    path = folder / 'financeiro.json'
    if not path.exists():
        return {'status': 'nao_consultado'}
    result = json.loads(path.read_text(encoding='utf-8'))
    intact = result.get('assinatura') == digest({k: v for k, v in result.items() if k != 'assinatura'})
    current = all(file_hash(folder / name if name == 'contratos.json' else source_path(folder, name)) == value
                  for name, value in result.get('fontes_sha256', {}).items())
    if not intact or not current:
        return {'status': 'desatualizado', 'mensagem': 'Coleta ou fichas mudaram. Consulte a execução financeira novamente.'}
    if line is not None and (type(line) is not int or not 1 <= line <= len(result['consultas'])):
        raise ValueError('Linha financeira fora da coleta.')
    return {'status': 'pronto', 'status_consulta': result['status'], 'limite': LIMIT,
            'consultado_em': result['consultado_em'], 'resumo': result.get('resumo'),
            'catalogos': result['catalogos'], 'item': result['consultas'][line-1] if line is not None else None}
