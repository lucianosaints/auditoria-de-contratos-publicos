"""Campos e links observados no HTML público de contratos de Maricá."""

import json
from hashlib import sha256
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def portal_link(raw: str, base_url: str) -> str | None:
    url = urljoin(base_url, raw)
    parsed, base = urlsplit(url), urlsplit(base_url)
    if (parsed.scheme != 'https' or parsed.hostname != base.hostname
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        return None
    if not raw or raw.startswith('#'):
        return None
    return url


def row_details(row, base_url: str) -> dict[str, str]:
    result = {}
    obj = row.select_one('.aviso-resposta')
    if obj:
        result['Objeto'] = obj.get_text(' ', strip=True)
    for anchor in row.select('a[href]'):
        url = portal_link(anchor['href'], base_url)
        if url and urlsplit(url).path.endswith('/visualizar'):
            result['URL do contrato'] = url
            break
    return result


def parse_details(html: str, url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.select_one('.content')
    if content is None or 'Dados do Contrato' not in content.get_text(' ', strip=True):
        raise ValueError('Página recebida não contém Dados do Contrato.')
    result = {}
    for label in content.select('.width-100'):
        name = label.get_text(' ', strip=True).rstrip(':')
        value = label.find_next_sibling()
        if not name or name == 'Exportar' or value is None:
            continue
        result[f'Detalhe - {name}'] = value.get_text(' ', strip=True)
    links = []
    for anchor in content.select('a[data-href], a[href]'):
        link = portal_link(anchor.get('data-href') or anchor.get('href', ''), url)
        if link:
            entry = {'rotulo': anchor.get_text(' ', strip=True), 'url': link}
            if entry not in links:
                links.append(entry)
    result['Links publicados nos detalhes'] = json.dumps(links, ensure_ascii=False)
    result['Status dos detalhes'] = 'consultado'
    return result


def enrich_contracts(browser, records: list[dict[str, str]], output_dir=None) -> None:
    """Usa a mesma sessão; falhas ficam explícitas sem inventar dados/documentos."""
    from src.office_activity import source_request
    cache = {}
    page = browser.new_page()
    try:
        for record in records:
            url = record.get('URL do contrato')
            if not url:
                record['Status dos detalhes'] = 'link não encontrado'
                continue
            if url not in cache:
                try:
                    with source_request(url, 'Portal da Transparência de Maricá · contratos'):
                        response = page.goto(url, timeout=60000)
                    if response is not None and not response.ok:
                        raise ValueError(f'HTTP {response.status}')
                    page.wait_for_selector('.content', timeout=20000)
                    html = page.content()
                    details = parse_details(html, url)
                    if output_dir is not None:
                        target = output_dir / 'detalhes'
                        target.mkdir(parents=True, exist_ok=True)
                        filename = target / (sha256(url.encode('utf-8')).hexdigest() + '.html')
                        filename.write_text(html, encoding='utf-8')
                        details['Arquivo HTML dos detalhes'] = filename.relative_to(output_dir).as_posix()
                    cache[url] = details
                except Exception as exc:
                    cache[url] = {'Status dos detalhes': 'falhou', 'Erro ao consultar detalhes': str(exc)}
            record.update(cache[url])
    finally:
        page.close()
