"""Inspeciona isoladamente documento PNCP candidato da linha 175; nunca confirma o vínculo."""
import argparse
import hashlib
import json
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
site.addsitedir(str(ROOT / '.venv/Lib/site-packages'))


def main():
    from src.atomic_files import write_json
    from src.pncp import PublicClient, PncpSettings, API, ORGAO, file_links
    from src.documents import DocumentSettings, download_pdf, extract_pdf
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    out = ROOT / 'data/raw/financial_alternative175_20261023'
    entries = json.loads((source / 'pncp.json').read_text(encoding='utf-8'))['consultas']
    entry = next(e for e in entries if e['linha'] == 175)
    match = next(c for c in entry['candidatos'] if c['numero_controle_pncp'] == f'{ORGAO}-2-000413/2026')
    names = ['contratos.json', 'parecer.json', 'documentos.json', 'pncp.json', 'financeiro.json',
             'relatorio.md', 'revisao_agentes.json', 'indicadores.json', 'arquivamento.json']
    hashes = lambda: {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    before = hashes()
    if args.real:
        client = PublicClient(out, PncpSettings(max_files=3))
        try:
            data = client.get(f'{API}/orgaos/{ORGAO}/contratos/2026/413/arquivos')
            links, omitted = file_links(data, match, PncpSettings(max_files=3))
            write_json(out / 'inventario_pncp.json', {'situacao': 'candidato_com_data_divergente',
                'documentos': links, 'omitidos': omitted, 'comparacoes': match['comparacoes']})
            if len(links) != 1:
                raise ValueError('Inventário não tem documento único; inspecionar antes de baixar.')
            link = links[0]
            settings = DocumentSettings(max_bytes=50 * 1024 * 1024)
            target = out / f'{link["id"]}.pdf'
            final_url = download_pdf(client.session, link['url'], target, settings)
            document = extract_pdf(target, settings)
            write_json(out / 'documento_candidato.json', {**document, **link, 'url_final': final_url,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size,
                'arquivo': str(target.relative_to(ROOT)), 'limite': 'Inspeção isolada; vínculo PNCP continua conflitante.'})
        finally:
            client.close()
    document = json.loads((out / 'documento_candidato.json').read_text(encoding='utf-8'))
    proof = {'id': document['id'], 'status': document['status'], 'paginas': len(document['paginas']),
             'bytes': document['bytes'], 'nove_artefatos_preservados': before == hashes(),
             'vinculo_pncp': 'conflitante', 'chamadas_ia': 0, 'chamadas_banco': 0}
    write_json(out / 'verificacao_pncp.json', proof)
    assert proof['nove_artefatos_preservados']
    print(json.dumps(proof, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
