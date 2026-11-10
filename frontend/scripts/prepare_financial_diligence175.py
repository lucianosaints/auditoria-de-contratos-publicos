"""Gera pacote local de diligência com PDFs já obtidos; sem rede, IA, banco ou envio."""
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
    from src.financial import digest
    from src.financial_diligence import read_reference, build_diligence, request_text
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=ROOT / 'data/diligencia_financeira_175_20261023')
    args = parser.parse_args()
    if args.saida.exists():
        parser.error('Pasta de saída já existe; escolha outro destino para preservar versões.')
    source = ROOT / 'data/reports/20261020T015002Z_72b23869'
    raw = ROOT / 'data/raw/financial_alternative175_20261023'
    names = ['contratos.json', 'parecer.json', 'documentos.json', 'pncp.json', 'financeiro.json',
             'relatorio.md', 'revisao_agentes.json', 'indicadores.json', 'arquivamento.json']
    hashes = lambda: {n: hashlib.sha256((source / n).read_bytes()).hexdigest() for n in names}
    before = hashes()
    records = json.loads((source / 'contratos.json').read_text(encoding='utf-8'))
    financial = json.loads((source / 'financeiro.json').read_text(encoding='utf-8'))
    record = records[174]
    gazette = json.loads((ROOT / 'data/gazette_cache/a17ade2aeb96aa70b6153edb04167a19928925dfc93bb1661b757507e5e1754c.json').read_text(encoding='utf-8'))
    gazette_pdf = ROOT / 'data/gazette_cache/a17ade2aeb96aa70b6153edb04167a19928925dfc93bb1661b757507e5e1754c.pdf'
    candidate = json.loads((raw / 'documento_candidato.json').read_text(encoding='utf-8'))
    candidate_pdf = ROOT / candidate['arquivo']
    for path, expected_hash in ((gazette_pdf, gazette['sha256_pdf']), (candidate_pdf, candidate['sha256'])):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError('PDF documental alterado.')
    references = [
        {'titulo': 'Diário Oficial Extraordinário 09 — extrato do contrato, página 5',
         **read_reference(gazette_pdf, gazette['url_pdf'], record, [4003, 2026], [5], column=1,
                          start='EXTRATO DO CONTRATO', end='PORTARIA CCC'),
         'situacao_fonte': 'extrato_publicado'},
        {'titulo': 'PDF do candidato PNCP 413/2026 — identificação e dotação',
         **read_reference(candidate_pdf, candidate['url'], record, [4003, 2026], [1, 10]),
         'situacao_fonte': 'candidato_pncp_com_data_divergente',
         'observacao': 'Página 11 apresenta espaços de assinatura sem assinaturas visíveis. Não foi validada assinatura digital.'},
    ]
    if references[0]['dotacao'] != references[1]['dotacao'] or any(v is None for v in references[0]['dotacao'].values()):
        raise ValueError('Dotações documentais não são integralmente comparáveis e coincidentes.')
    packet = build_diligence(records, financial, 175, references, coleta_sha256=before['contratos.json'])
    packet['divergencia_data'] = {'portal': '18/08/2026', 'metadado_pncp': '01/09/2026',
                                 'extrato_diario': '01/09/2026', 'situacao': 'nao_resolvida'}
    packet['resultados_buscas_alternativas'] = json.loads((raw / 'consultas/verificacao.json').read_text(encoding='utf-8'))
    packet['controle_consulta'] = json.loads((raw / 'controle_consulta/verificacao.json').read_text(encoding='utf-8'))
    packet['assinatura'] = digest({k: v for k, v in packet.items() if k != 'assinatura'})
    report = ['# Diligência financeira — contrato 341/2026', '',
        '**Situação: nota 4003/2026 citada em duas fontes; nota original ainda não obtida.**', '',
        'O Diário Oficial Extraordinário 09, página 5, e o PDF do candidato PNCP 413/2026, '
        'página 10, citam a nota 4003/2026 e a mesma dotação. O PDF PNCP também apresenta '
        'contrato, processo e CNPJ do fornecedor na página 1. Isso apoia a busca documental, '
        'sem confirmar o detalhe financeiro rejeitado ou qualquer pagamento.', '',
        'Programa: 68.01.06.181.0018.2076. Elemento: 3.3.3.9.0.39.00.00.00. Recurso: 1704.', '',
        '## Divergências e limites', '',
        '- O link financeiro publicado continua rejeitado: esperado 4003/2026, observado 776/2024.',
        '- Portal: assinatura 18/08/2026. Extrato e metadado PNCP: 01/09/2026. Divergência preservada.',
        '- Página 11 do PDF PNCP: espaços de assinatura sem assinaturas visíveis; não foi validada assinatura digital.',
        '- Buscas por nome, número completo e unidade/número retornaram vazias. Um fornecedor de controle retornou três registros.',
        '- Consulta vazia não prova ausência de despesa. O PDF é uma fonte candidata, sem confirmação automática de vínculo.',
        '- Nenhum valor pago ou total financeiro por contrato foi calculado. Avaliações humanas continuam pendentes.', '',
        '## Fontes conferidas', '']
    report += [f"- [{ref['titulo']}]({ref['url']}#page={ref['paginas'][-1]}). SHA-256: `{ref['sha256_pdf']}`." for ref in references]
    report += ['', '## Próximo passo', '',
        'Usar a minuta `solicitacao.md` para pedir a nota original, a versão assinada, os eventos '
        'e os documentos de entrega. A minuta foi preparada localmente e não foi enviada.', '']
    if hashes() != before:
        raise ValueError('Fontes alteradas durante a preparação.')
    args.saida.mkdir(parents=True)
    write_json(args.saida / 'diligencia.json', packet)
    (args.saida / 'relatorio.md').write_text('\n'.join(report), encoding='utf-8')
    (args.saida / 'solicitacao.md').write_text('# Minuta de solicitação documental\n\n' + request_text(packet), encoding='utf-8')
    proof = {'nove_artefatos_preservados': before == hashes(), 'antes': before, 'depois': hashes(),
             'diligencia_assinatura': packet['assinatura'], 'documentos_citados': len(references),
             'chamadas_ia': 0, 'chamadas_banco': 0, 'requisicoes_rede_na_preparacao': 0, 'solicitacao_enviada': False}
    write_json(args.saida / 'verificacao.json', proof)
    assert proof['nove_artefatos_preservados']
    print(json.dumps({'saida': str(args.saida), 'nove_artefatos_preservados': proof['nove_artefatos_preservados'],
                      'documentos_citados': len(references), 'solicitacao_enviada': False}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
