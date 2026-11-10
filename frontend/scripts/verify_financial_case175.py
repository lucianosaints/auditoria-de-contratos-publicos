"""Confere evidências da linha 175 isoladamente; --real atualiza fontes públicas limitadas."""
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
    from src.financial import (FinancialClient, FinancialSettings, digest, check_detail,
                              parse_detail, parse_listing, recheck_saved_detail)
    from src.atomic_files import write_json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true')
    parser.add_argument('--publicar', action='store_true', help='Publica somente a reavaliação do detalhe da linha 175')
    args = parser.parse_args()
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    out = ROOT / 'data/raw/financial_case175_20261023'
    record = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))[174]
    financial = json.loads((source / 'financeiro.json').read_text(encoding='utf-8'))
    entry = next(e for e in financial['consultas'] if e['linha'] == 175)
    link = next(v for v in entry['vinculos'] if v['numero_ano_esperado'] == [4003, 2026])
    names = ['contratos.json', 'parecer.json', 'relatorio.md', 'revisao_agentes.json', 'documentos.json',
             'pncp.json', 'indicadores.json', 'arquivamento.json', 'financeiro.json']
    hashes = lambda: {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    before = hashes()
    snapshot = out / 'fontes.json'
    if args.real:
        client = FinancialClient(out, FinancialSettings(max_suppliers=1, max_details=1, cache_hours=0))
        try:
            rows, listed = client.listing('27595780000116', 2026)
            detail, detailed = client.detail(link['url'])
            write_json(snapshot, {'consulta': rows, 'detalhe': detail,
                                 'fontes': [listed, detailed], 'coleta_sha256': before['contratos.json']})
        finally:
            client.close()
    saved = json.loads(snapshot.read_text(encoding='utf-8'))
    if saved['coleta_sha256'] != before['contratos.json'] or any(digest(s['html']) != s['sha256'] for s in saved['fontes']):
        raise ValueError('Fontes locais alteradas ou de outra coleta.')
    saved['consulta'] = parse_listing(saved['fontes'][0]['html'], '27595780000116', 2026)
    saved['detalhe'] = parse_detail(saved['fontes'][1]['html'])
    matches = [row for row in saved['consulta'] if row['Empenho'] == '4003/2026']
    result = check_detail([4003, 2026], saved['detalhe'], record, matches[0] if len(matches) == 1 else None)
    publication = None
    if args.publicar:
        from src.batch_pipeline import execution_lock
        independent = json.loads((out / 'controle_independente/resposta.json').read_text(encoding='utf-8'))
        control = independent['fonte']
        if control['sha256'] != digest(control['html']) or parse_detail(control['html'])['numero_ano'] != saved['detalhe']['numero_ano']:
            raise ValueError('Controle independente não confirma a identidade observada.')
        with execution_lock(source):
            publication = recheck_saved_detail(source, 175, link['url'], saved['fontes'][1])
        other_entries = [e for e in financial['consultas'] if e['linha'] != 175]
        if other_entries != [e for e in publication['consultas'] if e['linha'] != 175]:
            raise AssertionError('Outras linhas foram alteradas.')
    proof = {'linha': 175, 'resultado': result,
             'consulta_cnpj': {'registros': len(saved['consulta']), 'correspondencias_empenho': len(matches)},
             'fontes': [{k: v for k, v in s.items() if k != 'html'} for s in saved['fontes']],
             'nove_artefatos_preservados': before == hashes(), 'antes': before, 'depois': hashes(),
             'oito_outros_artefatos_preservados': all(hashes()[n] == before[n] for n in names if n != 'financeiro.json'),
             'publicado': publication is not None,
             'demais_linhas_preservadas': publication is None or other_entries == [e for e in publication['consultas'] if e['linha'] != 175],
             'chamadas_ia': 0, 'chamadas_banco': 0}
    write_json(out / ('publicacao.json' if args.publicar else 'verificacao.json'), proof)
    assert proof['oito_outros_artefatos_preservados']
    print(json.dumps({k: v for k, v in proof.items() if k not in ('antes', 'depois')}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
