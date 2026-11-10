"""Explicações locais de achados, sem nova chamada ao Gemini ou mudança no parecer técnico."""
import argparse
import json
import re
from pathlib import Path

from src.audit_models import ParecerAuditoria
from src.tools.archive_tool import field, normalized, parse_brl

CATALOG_PATH = Path(__file__).with_name('summary_rules.json')
CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
START = '<!-- resumos-simples:inicio -->'
END = '<!-- resumos-simples:fim -->'


def first_source(record, primary, fallback=()):
    return field(record, primary) or (field(record, fallback) if fallback else None)


def plain_summary(record, reasons):
    source = normalized(' '.join(first_source(record, (key,)) or '' for key in
                                 ('detalhe - objeto', 'objeto', 'objeto do contrato')))
    reason_text = normalized(' '.join(reasons))
    value = first_source(record, ('valor do contrato', 'valor contratado', 'valor'), ('detalhe - valor global',))
    process = first_source(record, ('detalhe - processo',), ('numero do processo', 'nr [nr processo]', 'nr processo', 'processo'))
    try:
        amount = parse_brl(value)
    except ValueError:
        amount = None
    rule = CATALOG['regras'][-1]
    for candidate in CATALOG['regras'][:-1]:
        if candidate['id'] == 'valor_zero' and amount != 0:
            continue
        if (any(marker in source for marker in candidate.get('fonte_contem', []))
                or any(marker in reason_text for marker in candidate.get('parecer_contem', []))):
            rule = candidate
            break
    money = ('R$ ' + f'{amount:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')) if amount is not None else None
    context = {'valor_trecho': f' no valor de {money}' if money else '',
               'processo_trecho': f' nº {process}' if process else ''}
    intro = rule['em_resumo']
    if rule['id'] == 'sem_cobertura' and any(term in source for term in ('reconhec', 'divida', 'indeniz')):
        intro = rule['em_resumo_divida']
    return {
        'tipo': rule['id'], 'titulo': rule['titulo'], 'em_resumo': intro.format(**context),
        'problema_principal': rule['problema_principal'].format(**context),
        'significado_pratico': rule['significado_pratico'].format(**context),
        'proxima_diligencia': rule['proxima_diligencia'].format(**context),
        'valor_publicado': money, 'processo': process, 'nota': CATALOG['nota'],
    }


def build_summaries(records, audit):
    grouped = {}
    for finding in audit.suspeitos:
        if 1 <= finding.linha <= len(records):
            grouped.setdefault(finding.linha, []).append(finding.motivo_suspeita)
    return {'versao': CATALOG['versao'], 'origem': 'explicação local por regras; não é nova auditoria',
            'achados': [{'linha': line, **plain_summary(records[line - 1], reasons)} for line, reasons in sorted(grouped.items())]}


def report_with_summaries(report, summaries):
    clean = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', '', report, flags=re.S)
    if not summaries['achados']:
        return clean
    parts = [START, '## Entenda os achados em linguagem simples',
             'As explicações abaixo ajudam a ler os alertas. Os detalhes e as evidências permanecem na fundamentação técnica.']
    for summary in summaries['achados']:
        context = ' · '.join(item for item in (
            f'Valor publicado: {summary["valor_publicado"]}' if summary['valor_publicado'] else '',
            f'Processo: {summary["processo"]}' if summary['processo'] else '') if item)
        parts += [f'### Linha {summary["linha"]} — {summary["titulo"]}', context, summary['em_resumo'],
                  f'- **O problema principal:** {summary["problema_principal"]}',
                  f'- **O que isso significa na prática:** {summary["significado_pratico"]}',
                  f'- **Próxima diligência sugerida:** {summary["proxima_diligencia"]}']
    parts += [CATALOG['nota'], END, '']
    block = '\n\n'.join(parts)
    marker = '## Achados por linha global'
    if marker in clean:
        position = clean.index(marker)
        return clean[:position] + block + '\n' + clean[position:]
    return clean.rstrip() + '\n\n' + block


def save_summaries(folder, records, audit):
    summaries = build_summaries(records, audit)
    (folder / 'resumos.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    updated = audit.model_copy(update={'relatorio_markdown': report_with_summaries(audit.relatorio_markdown, summaries)})
    (folder / 'parecer.json').write_text(updated.model_dump_json(indent=2), encoding='utf-8')
    (folder / 'relatorio.md').write_text(updated.relatorio_markdown, encoding='utf-8')
    return updated


def main():
    parser = argparse.ArgumentParser(description='Adicionar resumos simples a uma auditoria salva, sem APIs.')
    parser.add_argument('execucao', help='ID da execução em data/reports')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / 'data' / 'reports'
    folder = (root / args.execucao).resolve()
    if folder.parent != root.resolve():
        parser.error('Informe apenas o ID da execução.')
    from src.batch_pipeline import execution_lock, load_records
    with execution_lock(folder):
        records = load_records(folder)
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        save_summaries(folder, records, audit)
    print(f'Resumos atualizados: {folder / "resumos.json"}. Nenhuma chamada externa.')


if __name__ == '__main__':
    main()
