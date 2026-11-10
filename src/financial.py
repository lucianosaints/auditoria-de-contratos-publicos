"""Consulta financeira municipal limitada, sem IA e sem atribuição automática de gasto."""
import hashlib
import copy
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from src.office_activity import source_activity, source_request
from bs4 import BeautifulSoup

from src.atomic_files import write_json
from src.pncp import cnpj, number_year, money

BASE = 'https://transparencia.marica.rj.gov.br'
SEARCH = BASE + '/e-cidade/consulta-empenhos'
HEADERS = ['Empenho', 'Data de Emissão', 'Beneficiário', 'CPF/CNPJ', 'Unidade Orçamentária',
           'Procedimento', 'Nº do Procedimento', 'Objeto', 'Empenhado', 'Liquidado', 'Pago', 'Detalhar']
LIMIT = ('Consulta limitada aos contratos com alertas e às fontes identificadas. '
         'Número, fornecedor e processo podem ser compartilhados entre contratos. '
         'Nenhum saldo é somado ou atribuído automaticamente ao contrato. '
         'Ausência no recorte não comprova ausência de despesa; pagamento publicado não comprova entrega.')
IDENTITY_POLICY = 2


def explicit_references(text, label):
    """Somente identificadores explicitamente rotulados; nunca completa ou corrige anos."""
    prefix = (r'(?<!\w)(?:PROCESSO(?:\s+ADMINISTRATIVO)?|P\.?\s*A\.?)' if label == 'processo'
              else r'\bCONTRATO')
    values = re.findall(prefix + r'\s*(?:N[º°o.]*\s*)?[:.]?\s*(\d+\s*/\s*\d{4,})(?!\d)', str(text or ''), re.I)
    valid, invalid = [], []
    for raw in values:
        parsed = number_year(raw)
        if parsed:
            if list(parsed) not in valid:
                valid.append(list(parsed))
        elif raw not in invalid:
            invalid.append(raw)
    return {'validas': valid, 'invalidas': invalid}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def allowed_url(raw):
    try:
        u = urlsplit(raw)
        return (u.scheme == 'https' and u.netloc == 'transparencia.marica.rj.gov.br' and not u.fragment and
                (u.path in ('/e-cidade/consulta-empenhos', '/e-cidade/consulta-empenhos/pesquisar') and not u.query or
                 re.fullmatch(r'/e-cidade/contratos/padrao/\d+/empenho', u.path) and not u.query or
                 re.fullmatch(r'/e-cidade/consulta-empenhos/\d+/visualizar', u.path) and
                 u.query in ('', 'origin=detailed-encumbrance-search')))
    except (ValueError, TypeError):
        return False


def fields(soup):
    result = {}
    for el in soup.select('.content .width-100'):
        name = el.get_text(' ', strip=True).rstrip(':')
        sibling = el.find_next_sibling()
        if sibling and name != 'Exportar':
            if name in result:
                raise ValueError('Campo financeiro repetido: ' + name)
            result[name] = sibling.get_text(' ', strip=True)
    return result


def parse_detail(html):
    soup = BeautifulSoup(html, 'html.parser')
    if not soup.select_one('.content') or 'Dados do Empenho' not in soup.get_text(' ', strip=True):
        raise ValueError('Resposta não contém Dados do Empenho.')
    data = fields(soup)
    number = number_year(data.get('Número'))
    if not number:
        raise ValueError('Detalhe financeiro sem número/ano válido.')
    balances = {}
    for name in ('Empenhado', 'Liquidado', 'Anulado', 'Pago'):
        value = money(data.get(name))
        balances[name] = format(value, '.2f') if value is not None and value.as_tuple().exponent >= -2 else None
    movements = []
    for table in soup.select('.content table'):
        headers = [h.get_text(' ', strip=True) for h in table.select('thead th')]
        if headers != ['Data', 'Tipo', 'Valor', 'Histórico']:
            continue
        for tr in table.select('tbody tr'):
            cells = [td.get_text(' ', strip=True) for td in tr.select('td')]
            if len(cells) != 4:
                raise ValueError('Movimentação com colunas inconsistentes.')
            movements.append(dict(zip(headers, cells)))
    return {'numero_ano': list(number), 'campos': data, 'saldos_publicados': balances,
            'movimentacoes': movements, 'reconciliacao_eventos': 'nao_realizada'}


def parse_listing(html, supplier, year):
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.select_one('form[action="' + SEARCH + '/pesquisar"]')
    if not form:
        raise ValueError('Formulário de consulta financeira ausente.')
    document = form.select_one('[name="document"]')
    selected = form.select_one('[name="year"] option[selected]')
    if document is None or cnpj(document.get('value', '')) != supplier or selected is None or selected.get('value') != str(year):
        raise ValueError('Portal não confirmou os filtros de CNPJ e exercício.')
    tables = [t for t in soup.select('table') if [h.get_text(' ', strip=True) for h in t.select('thead th')] == HEADERS]
    if len(tables) != 1:
        raise ValueError('Tabela financeira com estrutura inesperada.')
    result = []
    seen = set()
    for tr in tables[0].select('tbody tr'):
        cells = tr.select('td')
        if len(cells) == 1 and cells[0].has_attr('colspan') and re.search('nenhum|não (?:há|foram)', cells[0].get_text(), re.I):
            continue
        if len(cells) != len(HEADERS):
            raise ValueError('Linha financeira com colunas inconsistentes.')
        data = dict(zip(HEADERS[:-1], [c.get_text(' ', strip=True) for c in cells[:-1]]))
        identity = number_year(data['Empenho'])
        if not identity or identity[1] != year or cnpj(data['CPF/CNPJ']) != supplier or identity in seen:
            raise ValueError('Consulta retornou identidade repetida ou fora dos filtros.')
        seen.add(identity)
        links = [urljoin(SEARCH, a['href']) for a in cells[-1].select('a[href]')]
        links = [u for u in links if allowed_url(u) and '/visualizar' in u]
        if len(links) != 1:
            raise ValueError('Empenho sem link de detalhe único e permitido.')
        data['url'] = links[0]
        result.append(data)
    return result


@dataclass(frozen=True)
class FinancialSettings:
    max_suppliers: int = 10
    max_details: int = 30
    cache_hours: int = 24
    max_bytes: int = 8 * 1024 * 1024

    def __post_init__(self):
        if not (1 <= self.max_suppliers <= 50 and 1 <= self.max_details <= 100 and
                0 <= self.cache_hours <= 24 and 1024 <= self.max_bytes <= 8 * 1024 * 1024):
            raise ValueError('Limites financeiros inválidos.')


class FinancialClient:
    def __init__(self, folder, settings, session=None):
        self.folder, self.settings = Path(folder), settings
        self.session = session or requests.Session()
        self.owned = session is None
        if self.owned:
            self.session.trust_env = False

    def close(self):
        if self.owned:
            self.session.close()

    def request(self, url, data=None):
        method = 'POST' if data is not None else 'GET'
        for _ in range(4):
            if not allowed_url(url):
                raise ValueError('Destino financeiro não permitido.')
            with source_request(url, 'Portal da Transparência de Maricá · financeiro'), self.session.request(method, url, data=data, allow_redirects=False,
                                      timeout=(10, 45), stream=True) as response:
                if response.status_code in (301, 302, 303) and response.headers.get('Location'):
                    url = urljoin(url, response.headers['Location'])
                    method, data = 'GET', None
                    continue
                if response.status_code != 200:
                    raise ValueError(f'Portal financeiro retornou HTTP {response.status_code}.')
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > self.settings.max_bytes:
                        raise ValueError('Resposta financeira excedeu o limite de bytes.')
                return bytes(content).decode('utf-8-sig')
        raise ValueError('Redirecionamentos financeiros excedidos.')

    def cached(self, key, loader):
        path = self.folder / 'financeiro/cache' / (digest(key) + '.json')
        try:
            cached = json.loads(path.read_text(encoding='utf-8'))
            age = datetime.now(timezone.utc) - datetime.fromisoformat(cached['consultado_em'])
            if (cached['chave'] == key and cached['sha256'] == digest(cached['html']) and
                    timedelta(0) <= age < timedelta(hours=self.settings.cache_hours)):
                source_activity(key[1] if key[0] == 'detalhe' else SEARCH, 'Portal da Transparência de Maricá · financeiro', 'cache_local')
                return cached
        except (OSError, ValueError, KeyError, TypeError):
            pass
        html = loader()
        cached = {'chave': key, 'html': html, 'sha256': digest(html), 'consultado_em': now()}
        write_json(path, cached)
        return cached

    def listing(self, supplier, year):
        def load():
            initial = self.request(SEARCH)
            soup = BeautifulSoup(initial, 'html.parser')
            form = soup.select_one('form[action="' + SEARCH + '/pesquisar"]')
            token = form.select_one('[name="_token"]') if form else None
            if token is None or not token.get('value'):
                raise ValueError('Consulta financeira sem token de sessão pública.')
            return self.request(SEARCH + '/pesquisar', {'_token': token['value'], 'year': str(year),
                'month': '', 'unit': '', 'beneficiary': '', 'document': supplier, 'encumbrance_number': ''})
        saved = self.cached(['lista', supplier, year], load)
        return parse_listing(saved['html'], supplier, year), saved

    def detail(self, url):
        if not allowed_url(url) or url in (SEARCH, SEARCH + '/pesquisar'):
            raise ValueError('Link de empenho não permitido.')
        saved = self.cached(['detalhe', url], lambda: self.request(url))
        return parse_detail(saved['html']), saved


def source_links(folder, record):
    name = record.get('Arquivo HTML dos detalhes')
    if not name:
        return [], None
    path = (Path(folder) / name).resolve()
    if not path.is_relative_to(Path(folder).resolve()) or not path.is_file():
        return [], None
    soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
    local = fields(soup)
    if (number_year(local.get('Número')) != number_year(record.get('Detalhe - Número')) or
            not number_year(local.get('Número')) or
            local.get('Processo') != record.get('Detalhe - Processo') or
            cnpj(local.get('CPF/CNPJ')) != cnpj(record.get('Detalhe - CPF/CNPJ'))):
        raise ValueError('HTML de origem incompatível com a identidade do contrato.')
    links = []
    for table in soup.select('.content table'):
        if [h.get_text(' ', strip=True) for h in table.select('thead th')] != ['Número', 'Resumo', 'Detalhar']:
            continue
        for tr in table.select('tbody tr'):
            cells = tr.select('td')
            if len(cells) != 3:
                raise ValueError('Tabela de vínculos com colunas inconsistentes.')
            expected = number_year(cells[0].get_text(' ', strip=True))
            for anchor in cells[-1].select('a[href]'):
                url = anchor['href']
                if allowed_url(url) and re.fullmatch(r'/e-cidade/contratos/padrao/\d+/empenho', urlsplit(url).path) and expected:
                    links.append({'numero_ano_esperado': list(expected), 'url': url,
                                  'origem': 'link_publicado_no_contrato'})
    return links, {'arquivo': name, 'sha256': file_hash(path)}


def check_detail(expected, detail, record=None, listing=None):
    if list(expected) != detail['numero_ano']:
        return {'situacao': 'conflito_identidade', 'numero_ano_observado': detail['numero_ano'],
                'motivo': 'O número/ano do detalhe difere do empenho esperado. Saldos rejeitados.'}
    if record is not None:
        comparisons = []
        for field, local, refs in (
            ('processo_resumo', number_year(record.get('Detalhe - Processo')),
             explicit_references(detail['campos'].get('Resumo'), 'processo')),
            ('contrato_resumo', number_year(record.get('Detalhe - Número')),
             explicit_references(detail['campos'].get('Resumo'), 'contrato')),
        ):
            values = refs['validas']
            status = ('nao_comparavel' if not local or not values else
                      'ambiguo' if len(values) > 1 else 'igual' if list(local) == values[0] else 'divergente')
            comparisons.append({'campo': field, 'contrato': list(local) if local else None,
                                'empenho': values, 'referencias_invalidas': refs['invalidas'], 'resultado': status})
        supplier = cnpj(record.get('Detalhe - CPF/CNPJ'))
        other = cnpj((listing or {}).get('CPF/CNPJ'))
        comparisons.append({'campo': 'cnpj_consulta', 'contrato': supplier, 'empenho': other,
                            'resultado': 'nao_comparavel' if not supplier or not other else 'igual' if supplier == other else 'divergente'})
        if listing:
            processes = explicit_references(listing.get('Objeto'), 'processo')['validas']
            local = number_year(record.get('Detalhe - Processo'))
            comparisons.append({'campo': 'processo_consulta', 'contrato': list(local) if local else None,
                                'empenho': processes, 'resultado': 'nao_comparavel' if not local or not processes else
                                'ambiguo' if len(processes) > 1 else 'igual' if list(local) == processes[0] else 'divergente'})
        if any(c['resultado'] == 'divergente' for c in comparisons):
            return {'situacao': 'conflito_identidade', 'numero_ano_observado': detail['numero_ano'],
                    'comparacoes': comparisons,
                    'motivo': 'O número do empenho coincide, mas processo, contrato ou CNPJ diverge. Saldos rejeitados.'}
    else:
        comparisons = []
    return {'situacao': 'vinculo_pendente', 'numero_ano_observado': detail['numero_ano'],
            'comparacoes': comparisons,
            'motivo': 'Número/ano do empenho coincide. Identidade contratual e eventos ainda não reconciliados.',
            'detalhe': detail}


def collect_financial(folder, records, audit, settings=None, client=None):
    folder, settings = Path(folder), settings or FinancialSettings()
    client = client or FinancialClient(folder, settings)
    owned = isinstance(client, FinancialClient) and client.owned
    target = folder / 'financeiro.json'
    if target.exists():
        previous = json.loads(target.read_text(encoding='utf-8'))
        write_json(folder / 'financeiro/historico' / (digest(previous) + '.json'), previous)
    lines = sorted({f.linha for f in audit.suspeitos if 1 <= f.linha <= len(records)})
    result = {'versao': 1, 'politica_identidade': IDENTITY_POLICY, 'consultado_em': now(), 'status': 'em_andamento', 'limite': LIMIT,
              'coleta_sha256': file_hash(folder / 'contratos.json'),
              'parecer_sha256': file_hash(folder / 'parecer.json'), 'fontes_html': [],
              'linhas': lines, 'configuracao': asdict(settings), 'processados': 0,
              'consultas': [], 'consultas_fornecedores': [], 'detalhes_consultados': 0,
              'execucao_financeira': 'nao_avaliavel', 'vinculos_confirmados': 0}

    def publish():
        result['atualizado_em'] = now()
        result['assinatura'] = digest({k: v for k, v in result.items() if k != 'assinatura'})
        write_json(target, result)

    listings, details = {}, {}
    publish()
    try:
        for line in lines:
            record = records[line - 1]
            entry = {'linha': line, 'situacao': 'conferida', 'vinculos': [], 'omitidos_por_limite': 0}
            result['consultas'].append(entry)
            identifier = cnpj(record.get('Detalhe - CPF/CNPJ'))
            number = number_year(record.get('Detalhe - Número'))
            process = number_year(record.get('Detalhe - Processo'))
            candidates = []
            try:
                candidates, source = source_links(folder, record)
                if source and source not in result['fontes_html']:
                    result['fontes_html'].append(source)
            except (ValueError, OSError) as exc:
                entry['erro_fonte'] = str(exc)
                entry['situacao'] = 'fonte_incompativel'
            if identifier and number:
                key = (identifier, number[1])
                entry['filtros'] = {'cnpj': identifier, 'exercicio': number[1]}
                if key not in listings and len(listings) < settings.max_suppliers:
                    query = {'cnpj': identifier, 'exercicio': number[1], 'situacao': 'consultada'}
                    try:
                        rows, saved = client.listing(*key)
                        query.update(registros=len(rows), consultado_em=saved['consultado_em'], sha256=saved['sha256'])
                        listings[key] = rows
                    except (ValueError, requests.RequestException, OSError) as exc:
                        query.update(situacao='consulta_falhou', erro=str(exc))
                        listings[key] = None
                    result['consultas_fornecedores'].append(query)
                if key not in listings:
                    entry['situacao_consulta'] = 'limite_fornecedores'
                elif listings[key] is None:
                    entry['situacao_consulta'] = 'consulta_falhou'
                else:
                    entry['situacao_consulta'] = 'consultada'
                    for row in listings[key]:
                        processes = {tuple(x) for x in explicit_references(row['Objeto'], 'processo')['validas']}
                        if process and processes == {process}:
                            candidates.append({'numero_ano_esperado': list(number_year(row['Empenho'])),
                                               'url': row['url'], 'origem': 'candidato_cnpj_processo',
                                               'registro_consulta': row})
            else:
                entry['situacao_consulta'] = 'identificacao_insuficiente'
            seen = set()
            for candidate in candidates:
                key = (candidate['url'], tuple(candidate['numero_ano_esperado']))
                if key in seen:
                    continue
                seen.add(key)
                link = dict(candidate)
                if candidate['url'] not in details:
                    if len(details) >= settings.max_details:
                        entry['omitidos_por_limite'] += 1
                        continue
                    try:
                        detail, saved = client.detail(candidate['url'])
                        details[candidate['url']] = (detail, saved)
                    except (ValueError, requests.RequestException, OSError) as exc:
                        details[candidate['url']] = str(exc)
                fetched = details[candidate['url']]
                if isinstance(fetched, str):
                    link.update(situacao='consulta_falhou', motivo=fetched)
                else:
                    detail, saved = fetched
                    listing = candidate.get('registro_consulta')
                    if listing is None and identifier and number:
                        matches = [r for r in (listings.get((identifier, number[1])) or [])
                                   if list(number_year(r['Empenho']) or []) == candidate['numero_ano_esperado']]
                        if len(matches) == 1:
                            listing = matches[0]
                    link.update(check_detail(candidate['numero_ano_esperado'], detail, record, listing))
                    # O registro bruto fica no cache; a relação rejeitada não transporta saldos.
                    link.pop('registro_consulta', None)
                    link.update(consultado_em=saved['consultado_em'], sha256_resposta=saved['sha256'])
                entry['vinculos'].append(link)
                result['detalhes_consultados'] = len(details)
                publish()
            result['processados'] += 1
            print(f'Financeiro: {result["processados"]}/{len(lines)} contratos; {len(listings)} consultas; {len(details)} detalhes.', flush=True)
            publish()
        result['status'] = 'concluida_com_limites'
        publish()
        return result
    except BaseException:
        result['status'] = 'interrompida'
        publish()
        raise
    finally:
        if owned:
            client.close()


def recheck_saved_detail(folder, line, url, saved):
    """Reavalia uma relação salva com HTML rastreável; sem rede ou inferência de vínculo."""
    folder = Path(folder)
    target = folder / 'financeiro.json'
    previous = json.loads(target.read_text(encoding='utf-8'))
    source_hashes = {name: file_hash(folder / name) for name in ('contratos.json', 'parecer.json')}
    if (type(line) is not int or previous.get('versao') != 1 or
            previous.get('politica_identidade') != IDENTITY_POLICY or
            previous.get('assinatura') != digest({k: v for k, v in previous.items() if k != 'assinatura'}) or
            previous.get('coleta_sha256') != source_hashes['contratos.json'] or
            previous.get('parecer_sha256') != source_hashes['parecer.json']):
        raise ValueError('Resultado financeiro incompatível com as fontes atuais.')
    records = json.loads((folder / 'contratos.json').read_text(encoding='utf-8'))
    if not 1 <= line <= len(records):
        raise ValueError('Linha fora da coleta.')
    for source in previous['fontes_html']:
        path = (folder / source['arquivo']).resolve()
        if not path.is_relative_to(folder.resolve()) or file_hash(path) != source['sha256']:
            raise ValueError('HTML contratual de origem alterado.')
    if (not allowed_url(url) or saved.get('chave') != ['detalhe', url] or
            not isinstance(saved.get('html'), str) or saved.get('sha256') != digest(saved['html'])):
        raise ValueError('Resposta financeira sem origem ou hash compatível.')
    result = copy.deepcopy(previous)
    entries = [e for e in result['consultas'] if e['linha'] == line]
    links = [v for e in entries for v in e['vinculos'] if v['url'] == url]
    if len(entries) != 1 or len(links) != 1:
        raise ValueError('Relação financeira ausente ou ambígua.')
    link = links[0]
    candidates, _ = source_links(folder, records[line - 1])
    if not any(c['url'] == url and c['numero_ano_esperado'] == link['numero_ano_esperado'] for c in candidates):
        raise ValueError('Relação não foi publicada no contrato de origem.')
    instant = datetime.fromisoformat(saved['consultado_em'])
    old_instant = datetime.fromisoformat(link['consultado_em'])
    if instant.tzinfo is None or instant < old_instant or instant > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('Data de reconsulta inválida ou anterior à fonte salva.')
    assessed = check_detail(link['numero_ano_esperado'], parse_detail(saved['html']), records[line - 1])
    replaced = {k: link[k] for k in ('numero_ano_esperado', 'url', 'origem')}
    replaced.update(assessed, consultado_em=saved['consultado_em'], sha256_resposta=saved['sha256'])
    link.clear(); link.update(replaced)
    result.setdefault('reverificacoes', []).append({'linha': line, 'url': url,
        'consultado_em': saved['consultado_em'], 'sha256_resposta': saved['sha256'],
        'situacao': assessed['situacao'], 'financeiro_anterior_sha256': digest(previous),
        'limite': 'Somente este detalhe foi reconsultado; demais relações mantêm suas datas e cobertura.'})
    result['atualizado_em'] = now()
    result['assinatura'] = digest({k: v for k, v in result.items() if k != 'assinatura'})
    if any(file_hash(folder / name) != value for name, value in source_hashes.items()) or json.loads(target.read_text(encoding='utf-8')) != previous:
        raise ValueError('Fontes alteradas durante a reavaliação.')
    # Histórico e evidência ficam disponíveis antes da substituição atômica do resultado.
    write_json(folder / 'financeiro/historico' / (digest(previous) + '.json'), previous)
    write_json(folder / 'financeiro/cache' / (digest(saved['chave']) + '.json'), saved)
    write_json(target, result)
    return result


def main():
    import argparse
    from src.audit_models import ParecerAuditoria
    from src.batch_pipeline import execution_lock, load_records
    from src.rag import run_folder
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execucao', required=True)
    args = parser.parse_args()
    folder = run_folder(args.execucao)
    with execution_lock(folder):
        collect_financial(folder, load_records(folder),
            ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
