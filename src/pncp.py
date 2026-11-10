"""Consulta pública PNCP e reconciliação conservadora; sem IA ou banco."""
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

import requests
from src.office_activity import source_activity, source_request

from src.atomic_files import write_json
from src.documents import digest

ORGAO = '29131075000193'
CONSULTA = 'https://pncp.gov.br/api/consulta/v1/contratos'
API = 'https://pncp.gov.br/api/pncp/v1'
LIMIT = ('Consulta ao CNPJ 29.131.075/0001-93, Município de Maricá, por data de publicação. '
         'Não cobre automaticamente autarquias, empresas municipais ou publicações fora do intervalo. '
         'Não localizado neste recorte não comprova falta de publicação. '
         'Vínculo confirmado por regras não é conferência humana nem validação do conteúdo do PDF.')


def now():
    return datetime.now(timezone.utc).isoformat()


def number_year(value, year=None):
    match = re.fullmatch(r'\s*0*(\d+)\s*(?:[/\-]\s*(20\d{2}))?\s*', str(value or ''))
    return (int(match[1]), int(match[2] or year)) if match and (match[2] or year) else None


def process_id(value):
    # Aceita somente número/ano completo; não adivinha prefixos ou anos abreviados.
    return number_year(value)


def cnpj(value):
    raw = re.sub(r'[.\-/\s]', '', str(value or ''))
    return raw if re.fullmatch(r'\d{14}', raw) else None


def money(value):
    raw = str(value if value is not None else '').replace('R$', '').replace(' ', '')
    if ',' in raw:
        if not re.fullmatch(r'-?(?:\d+|\d{1,3}(?:\.\d{3})+),\d{2}', raw):
            return None
        raw = raw.replace('.', '').replace(',', '.')
    elif not re.fullmatch(r'-?\d+(?:\.\d+)?', raw):
        return None
    try:
        result = Decimal(raw)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def local_identity(record):
    return {'numero_ano': number_year(record.get('Detalhe - Número')),
            'processo': process_id(record.get('Detalhe - Processo')),
            'cnpj_fornecedor': cnpj(record.get('Detalhe - CPF/CNPJ'))}


def official_file_url(value):
    try:
        url = urlsplit(value)
        return (url.scheme == 'https' and url.hostname == 'pncp.gov.br' and
                not url.username and not url.password and url.port in (None, 443) and
                re.fullmatch(r'/(?:api/pncp|pncp-api)/v1/orgaos/\d{14}/(?:contratos|compras)/20\d{2}/\d+/arquivos/\d+', url.path)
                is not None and not url.query and not url.fragment)
    except (ValueError, TypeError):
        return False


def candidate(record, remote):
    local = local_identity(record)
    remote_number = number_year(remote.get('numeroContratoEmpenho'), remote.get('anoContrato'))
    same_number = bool(local['numero_ano'] and local['numero_ano'] == remote_number)
    same_process = bool(local['processo'] and local['processo'] == process_id(remote.get('processo')))
    same_supplier = bool(local['cnpj_fornecedor'] and local['cnpj_fornecedor'] == cnpj(remote.get('niFornecedor')))
    if not same_number and not (same_process and same_supplier):
        return None
    comparisons = []
    for name, source, target in (
        ('numero_ano', local['numero_ano'], remote_number),
        ('processo', local['processo'], process_id(remote.get('processo'))),
        ('cnpj_fornecedor', local['cnpj_fornecedor'], cnpj(remote.get('niFornecedor'))),
        ('valor_inicial', money(record.get('Detalhe - Valor Inicial')), money(remote.get('valorInicial'))),
    ):
        comparisons.append({'campo': name, 'portal': str(source) if source is not None else None,
                            'pncp': str(target) if target is not None else None,
                            'resultado': 'nao_comparavel' if source is None or target is None else
                            'igual' if source == target else 'divergente'})
    local_date = record.get('Detalhe - Assinatura', '')
    try:
        local_date = datetime.strptime(local_date, '%d/%m/%Y').date().isoformat()
    except (ValueError, TypeError):
        local_date = None
    remote_date = str(remote.get('dataAssinatura') or '')[:10] or None
    comparisons.append({'campo': 'data_assinatura', 'portal': local_date, 'pncp': remote_date,
                        'resultado': 'nao_comparavel' if not local_date or not remote_date else
                        'igual' if local_date == remote_date else 'divergente'})
    strong = same_number and same_process and same_supplier
    conflict = any(c['resultado'] == 'divergente' for c in comparisons)
    org = (remote.get('orgaoEntidade') or {}).get('cnpj')
    year, seq = remote.get('anoContrato'), remote.get('sequencialContrato')
    valid_id = (org == ORGAO and type(year) is int and 2000 <= year <= 2100 and
                type(seq) is int and seq > 0 and remote.get('numeroControlePNCP') == f'{ORGAO}-2-{seq:06d}/{year}')
    return {'numero_controle_pncp': remote.get('numeroControlePNCP'),
            'ano': year, 'sequencial': seq, 'cnpj_orgao': org,
            'url': f'https://pncp.gov.br/app/contratos/{ORGAO}/{year}/{seq}' if valid_id else None,
            'forte': bool(strong and valid_id), 'conflitante': conflict,
            'comparacoes': comparisons, 'objeto': remote.get('objetoContrato'),
            'fornecedor': remote.get('nomeRazaoSocialFornecedor'), 'registro_pncp': remote}


@dataclass(frozen=True)
class PncpSettings:
    max_pages: int = 20
    page_size: int = 500
    cache_hours: int = 24
    max_files: int = 20

    def __post_init__(self):
        if not (1 <= self.max_pages <= 100 and 10 <= self.page_size <= 500 and
                0 <= self.cache_hours <= 24 and 1 <= self.max_files <= 100):
            raise ValueError('Limites PNCP inválidos.')


class PublicClient:
    def __init__(self, folder, settings, session=None, wait=time.sleep):
        self.folder, self.settings, self.wait = Path(folder), settings, wait
        self.owned = session is None
        self.session = session or requests.Session()
        if self.owned:
            self.session.trust_env = False

    def close(self):
        if self.owned:
            self.session.close()

    def get(self, url, params=None):
        # URL é construída pelo módulo. Nenhum endpoint arbitrário é aceito.
        if not (url == CONSULTA or re.fullmatch(re.escape(API) + r'/orgaos/' + ORGAO + r'/contratos/20\d{2}/\d+/arquivos', url)):
            raise ValueError('Endpoint PNCP não permitido.')
        key = digest([url, params])
        cache = self.folder / 'pncp/cache' / f'{key}.json'
        try:
            saved = json.loads(cache.read_text(encoding='utf-8'))
            age = datetime.now(timezone.utc) - datetime.fromisoformat(saved['consultado_em'])
            if (saved['url'] == url and saved['parametros'] == params and
                    saved['sha256'] == digest(saved['resposta']) and
                    timedelta(0) <= age < timedelta(hours=self.settings.cache_hours)):
                source_activity(url, 'PNCP · contratos e anexos', 'cache_local')
                return saved['resposta']
        except (OSError, ValueError, TypeError, KeyError):
            pass
        for attempt in range(3):
            with source_request(url, 'PNCP · contratos e anexos'), self.session.get(url, params=params, timeout=(10, 50), stream=True,
                                  allow_redirects=False, headers={'Accept': 'application/json'}) as response:
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    retry = response.headers.get('Retry-After', '')
                    if retry.isdigit() and int(retry) > 5:
                        raise ValueError('PNCP solicitou pausa maior; tente novamente mais tarde. Cache preservado.')
                    self.wait(int(retry) if retry.isdigit() else attempt + 1)
                    continue
                if response.status_code == 204:
                    data = None
                else:
                    if response.status_code != 200:
                        raise ValueError(f'Consulta PNCP retornou HTTP {response.status_code}.')
                    content = bytearray()
                    for chunk in response.iter_content(65536):
                        content.extend(chunk)
                        if len(content) > 8 * 1024 * 1024:
                            raise ValueError('Resposta PNCP excedeu 8 MB.')
                    data = json.loads(content)
                write_json(cache, {'url': url, 'parametros': params, 'consultado_em': now(),
                                   'sha256': digest(data), 'resposta': data})
                return data
        raise ValueError('Consulta PNCP indisponível.')


def catalog(client, start, end, settings):
    records, seen, pages, expected = [], set(), 0, None
    try:
        for page in range(1, settings.max_pages + 1):
            data = client.get(CONSULTA, {'dataInicial': start, 'dataFinal': end,
                              'cnpjOrgao': ORGAO, 'pagina': page, 'tamanhoPagina': settings.page_size})
            if data is None and page == 1:
                return {'completo': True, 'registros': [], 'paginas': 1, 'total_informado': 0}
            if not isinstance(data, dict) or not isinstance(data.get('data'), list):
                raise ValueError('Página PNCP sem lista de contratos.')
            total, total_pages = data.get('totalRegistros'), data.get('totalPaginas')
            if (type(total) is not int or total < 0 or type(total_pages) is not int or total_pages < 1 or
                    data.get('numeroPagina') != page or
                    expected is not None and expected != (total, total_pages)):
                raise ValueError('Paginação PNCP mudou ou é inválida; consulta parcial.')
            expected = total, total_pages
            if not data['data'] and total > 0:
                raise ValueError('Página vazia antes do fim do catálogo PNCP.')
            for item in data['data']:
                identifier = item.get('numeroControlePNCP') if isinstance(item, dict) else None
                if not isinstance(identifier, str) or identifier in seen or (item.get('orgaoEntidade') or {}).get('cnpj') != ORGAO:
                    raise ValueError('Identificador repetido, ausente ou órgão diferente no catálogo PNCP.')
                seen.add(identifier); records.append(item)
            pages = page
            print(f'PNCP: página {page}/{total_pages}; {len(records)}/{total} registros.', flush=True)
            if page == total_pages:
                if len(records) != total:
                    raise ValueError('Total PNCP difere dos registros recebidos.')
                return {'completo': True, 'registros': records, 'paginas': pages, 'total_informado': total}
        raise ValueError('Limite de páginas PNCP atingido; consulta parcial.')
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        return {'completo': False, 'registros': records, 'paginas': pages,
                'total_informado': expected[0] if expected else None, 'erro': str(exc)[:300]}


def file_links(data, match, settings):
    if data is None:
        return [], 0
    if not isinstance(data, list) or any(not isinstance(d, dict) for d in data):
        raise ValueError('Lista de arquivos PNCP inválida.')
    links = []
    for doc in data:
        seq = doc.get('sequencialDocumento')
        url = doc.get('url') or doc.get('uri')
        # A lista do contrato pode conter anexos da compra, mas só aceita a compra associada.
        contract_path = f'/orgaos/{ORGAO}/contratos/{match["ano"]}/{match["sequencial"]}/arquivos/{seq}'
        purchase = re.fullmatch(r'(\d{14})-1-(\d+)/(20\d{2})', str(match['registro_pncp'].get('numeroControlePncpCompra') or ''))
        purchase_path = f'/orgaos/{purchase[1]}/compras/{purchase[3]}/{int(purchase[2])}/arquivos/{seq}' if purchase else None
        path = urlsplit(url).path if isinstance(url, str) else ''
        if (type(seq) is not int or seq < 1 or not official_file_url(url) or
                not any(path.endswith(p) for p in (contract_path, purchase_path) if p)):
            raise ValueError('Arquivo PNCP fora do contrato ou da contratação associada; não será baixado.')
        if not any(link['url'] == url for link in links):
            links.append({'id': hashlib.sha256(url.encode()).hexdigest(), 'url': url,
                          'rotulo': str(doc.get('titulo') or 'Documento PNCP')[:200], 'origem': 'pncp',
                          'tipo_informado_pncp': str(doc.get('tipoDocumentoNome') or ''),
                          'numero_controle_pncp': match['numero_controle_pncp']})
    return links[:settings.max_files], max(0, len(links) - settings.max_files)


def reconcile(records, lines, remote, complete):
    entries = []
    for line in lines:
        record = records[line - 1]
        matches = [hit for item in remote if (hit := candidate(record, item))]
        strong = [m for m in matches if m['forte'] and not m['conflitante']]
        if not matches:
            status = 'nao_localizado_no_recorte' if complete else 'consulta_incompleta'
        elif len(matches) == 1 and len(strong) == 1 and complete:
            status = 'confirmado_por_regras'
        elif any(m['conflitante'] for m in matches):
            status = 'conflitante'
        else:
            status = 'candidato'
        entries.append({'linha': line, 'registro_original': record, 'registro_sha256': digest(record),
                        'situacao': status, 'candidatos': matches, 'documentos': [],
                        'status_documentos': 'nao_consultado', 'documentos_omitidos': 0})
    return entries


def collect_pncp(folder, records, audit, settings=None, *, session=None, end=None):
    folder, settings = Path(folder), settings or PncpSettings()
    lines = sorted({f.linha for f in audit.suspeitos})
    if any(type(line) is not int or not 1 <= line <= len(records) for line in lines):
        raise ValueError('Achado fora da coleta.')
    end = end or datetime.now(timezone(timedelta(hours=-3))).date()
    years = [identity['numero_ano'][1] for line in lines
             if (identity := local_identity(records[line - 1]))['numero_ano']]
    start_year = min(years, default=end.year)
    if not 2000 <= start_year <= end.year:
        raise ValueError('Ano dos contratos incompatível com a data da consulta.')
    result = {'versao': 1, 'status': 'em_andamento', 'consultado_em': now(), 'limite': LIMIT,
              'coleta_sha256': digest(records), 'linhas': lines, 'processados': 0,
              'recorte': {'cnpj_orgao': ORGAO, 'data_inicial': f'{start_year}0101',
                          'data_final': end.strftime('%Y%m%d'), 'criterio_data': 'publicacao'}, 'consultas': []}
    path = folder / 'pncp.json'
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        write_json(folder / 'pncp/historico' / f'{digest(old)}.json', old)

    def publish():
        result['assinatura'] = digest({k: v for k, v in result.items() if k != 'assinatura'})
        write_json(path, result)

    client = PublicClient(folder, settings, session)
    publish()
    try:
        if not lines:
            result.update(status='concluida', catalogo={'completo': True, 'paginas': 0, 'total_informado': 0})
            publish(); return result
        data = catalog(client, result['recorte']['data_inicial'], result['recorte']['data_final'], settings)
        result['catalogo'] = {k: v for k, v in data.items() if k != 'registros'}
        write_json(folder / 'pncp' / f'catalogo_{digest(data)}.json', data)
        result['consultas'] = reconcile(records, lines, data['registros'], data['completo'])
        publish()
        for entry in result['consultas']:
            if entry['situacao'] == 'confirmado_por_regras':
                match = entry['candidatos'][0]
                try:
                    files = client.get(f'{API}/orgaos/{ORGAO}/contratos/{match["ano"]}/{match["sequencial"]}/arquivos')
                    entry['documentos'], entry['documentos_omitidos'] = file_links(files, match, settings)
                    entry['status_documentos'] = 'consultado'
                except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
                    entry.update(status_documentos='falhou', erro_documentos=str(exc)[:300])
            print(f'PNCP linha {entry["linha"]}: {entry["situacao"]}; {len(entry["documentos"])} documentos disponíveis.', flush=True)
            result['processados'] += 1
            publish()
        result['status'] = 'concluida' if data['completo'] else 'consulta_incompleta'
        publish(); return result
    except BaseException:
        result['status'] = 'interrompida'; publish(); raise
    finally:
        client.close()


def document_links(manifest, records, lines):
    """Somente vínculos únicos confirmados na coleta e conjunto de achados atuais."""
    if not manifest:
        return {}
    if (manifest.get('versao') != 1 or manifest.get('coleta_sha256') != digest(records) or
            manifest.get('linhas') != sorted(lines) or manifest.get('assinatura') !=
            digest({k: v for k, v in manifest.items() if k != 'assinatura'})):
        raise ValueError('Reconciliação PNCP incompatível. Execute Consultar PNCP novamente.')
    links = {}
    for entry in manifest['consultas']:
        if entry['situacao'] != 'confirmado_por_regras' or entry['status_documentos'] != 'consultado':
            continue
        line = entry['linha']
        if line not in lines or entry['registro_sha256'] != digest(records[line - 1]):
            raise ValueError('Registro PNCP incompatível com a coleta.')
        if len(entry['candidatos']) != 1:
            raise ValueError('Vínculo PNCP ambíguo.')
        rebuilt = candidate(records[line - 1], entry['candidatos'][0]['registro_pncp'])
        if not rebuilt or not rebuilt['forte'] or rebuilt['conflitante']:
            raise ValueError('Vínculo PNCP não confirma os identificadores do contrato.')
        # Revalida também a identidade do contrato no caminho do arquivo.
        rebuilt_files, _ = file_links([{'url': d['url'], 'sequencialDocumento': int(urlsplit(d['url']).path.rsplit('/', 1)[-1]),
                                      'titulo': d['rotulo'], 'tipoDocumentoNome': d.get('tipo_informado_pncp', '')}
                                     for d in entry['documentos']], rebuilt,
                                     PncpSettings(max_files=100))
        if ([d['id'] for d in rebuilt_files] != [d['id'] for d in entry['documentos']]):
            raise ValueError('Identidade de documento PNCP inválida.')
        links[line] = entry['documentos']
    return links


def read_pncp(folder):
    path = Path(folder) / 'pncp.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def main():
    import argparse
    from datetime import date
    from src.audit_models import ParecerAuditoria
    from src.batch_pipeline import execution_lock, load_records
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execucao', required=True)
    parser.add_argument('--data-final', type=date.fromisoformat)
    args = parser.parse_args()
    from src.rag import run_folder
    folder = run_folder(args.execucao)
    with execution_lock(folder):
        records = load_records(folder)
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        result = collect_pncp(folder, records, audit, end=args.data_final)
        return 0 if result['status'] == 'concluida' else 1


if __name__ == '__main__':
    raise SystemExit(main())
