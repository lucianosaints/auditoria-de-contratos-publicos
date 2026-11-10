"""Avaliação local da triagem contra referência humana explicitamente registrada."""
import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from src.atomic_files import write_json
from src.evidence_support import digest


def audit_lines(records, audit):
    lines = set()
    for finding in audit['suspeitos']:
        line = finding['linha']
        if type(line) is not int or not 1 <= line <= len(records):
            raise ValueError('Achado com linha inválida.')
        lines.add(line)
    return lines


def make_sample(records, audit, per_group=20, seed=42):
    if type(per_group) is not int or per_group < 1:
        raise ValueError('A amostra por grupo deve ser positiva.')
    flagged = audit_lines(records, audit)
    rng = random.Random(seed)
    selected = []
    for group in (sorted(flagged), sorted(set(range(1, len(records) + 1)) - flagged)):
        selected.extend(rng.sample(group, min(per_group, len(group))))
    return {'versao': 1, 'coleta_sha256': digest(records), 'parecer_sha256': digest(audit),
            'metodo': 'aleatoria_estratificada_por_alerta', 'semente': seed,
            'nota': 'Avaliar necessidade de diligência com evidências; não classificar fraude. '
                    'Amostra estratificada: métricas descrevem a amostra, sem extrapolação populacional.',
            'itens': [{'linha': line, 'registro_sha256': digest(records[line - 1]),
                       'exige_diligencia': None, 'responsavel': '', 'justificativa': '',
                       'fontes': []} for line in sorted(selected)]}


def evaluate(records, audit, reference):
    if (reference.get('coleta_sha256') != digest(records) or
            reference.get('parecer_sha256') != digest(audit)):
        raise ValueError('Referência pertence a outra coleta ou versão do parecer.')
    flagged = audit_lines(records, audit)
    pilot = None
    if 'piloto' in reference:
        from src.quality_pilot import analyze
        pilot = analyze(reference)
    excluded = set(pilot['linhas_nao_elegiveis_para_metricas']) if pilot else set()
    counts = dict(verdadeiros_positivos=0, falsos_positivos=0,
                  verdadeiros_negativos=0, falsos_negativos=0)
    seen, pending = set(), 0
    cases = []
    coverage = {group: {'selecionados': 0, 'avaliados': 0, 'pendentes': 0}
                for group in ('com_alerta', 'sem_alerta')}
    for item in reference['itens']:
        line = item['linha']
        if type(line) is not int or not 1 <= line <= len(records) or line in seen:
            raise ValueError('Linha inválida ou duplicada na referência.')
        seen.add(line)
        if item.get('registro_sha256') != digest(records[line - 1]):
            raise ValueError('Registro da referência foi alterado.')
        group = 'com_alerta' if line in flagged else 'sem_alerta'
        coverage[group]['selecionados'] += 1
        decision = item.get('exige_diligencia')
        if line in excluded:
            pending += 1
            coverage[group]['pendentes'] += 1
            cases.append({'linha': line, 'resultado': 'nao_elegivel_piloto', 'grupo': group,
                          'registro_sha256': item['registro_sha256']})
            continue
        if decision is None:
            pending += 1
            coverage[group]['pendentes'] += 1
            cases.append({'linha': line, 'resultado': 'pendente', 'grupo': group,
                          'registro_sha256': item['registro_sha256']})
            continue
        if type(decision) is not bool:
            raise ValueError('Decisão humana deve ser true, false ou null.')
        if (not isinstance(item.get('responsavel'), str) or not item['responsavel'].strip() or
                not isinstance(item.get('justificativa'), str) or not item['justificativa'].strip() or
                not isinstance(item.get('fontes'), list) or not item['fontes'] or
                any(not isinstance(s, str) or not s.strip() for s in item['fontes'])):
            raise ValueError('Decisão exige responsável, justificativa e fontes conferidas.')
        key = ('verdadeiros_positivos' if decision else 'falsos_positivos') if line in flagged else (
            'falsos_negativos' if decision else 'verdadeiros_negativos')
        counts[key] += 1
        coverage[group]['avaliados'] += 1
        cases.append({'linha': line, 'resultado': key, 'grupo': group,
                      'registro_sha256': item['registro_sha256'],
                      'exige_diligencia': decision, 'responsavel': item['responsavel'],
                      'justificativa': item['justificativa'], 'fontes': list(item['fontes'])})
    tp, fp, fn = counts['verdadeiros_positivos'], counts['falsos_positivos'], counts['falsos_negativos']
    ratio = lambda n, d: n / d if d else None
    return {'versao': 1, 'avaliado_em': datetime.now(timezone.utc).isoformat(),
            'coleta_sha256': digest(records), 'parecer_sha256': digest(audit),
            'referencia_sha256': digest(reference), 'escopo': 'somente_amostra_avaliada',
            'nota': 'Diligência não é irregularidade comprovada. Métricas não extrapolam a amostra. '
                    'Denominador zero produz null; decisões pendentes não contam como acerto.',
            'selecionados': len(seen), 'avaliados': sum(counts.values()), 'pendentes': pending,
            **({'piloto': pilot} if pilot else {}),
            'cobertura_por_grupo': coverage, 'casos': cases,
            'linhas_para_segunda_conferencia': [case['linha'] for case in cases
                if case['resultado'] in ('falsos_positivos', 'falsos_negativos')],
            **counts, 'precisao': ratio(tp, tp + fp), 'sensibilidade': ratio(tp, tp + fn),
            'f1': ratio(2 * tp, 2 * tp + fp + fn)}


def render_report(result):
    """Resumo legível sem atribuir decisões ou notas ausentes na referência."""
    metric = lambda value: 'não calculável' if value is None else f'{value:.2%}'
    lines = ['# Diagnóstico da qualidade da triagem', '',
             'Escopo: somente os casos avaliados da amostra; não extrapolar à população.',
             'Necessidade de diligência não representa irregularidade comprovada.', '',
             f"Selecionados: {result['selecionados']}. Avaliados: {result['avaliados']}. "
             f"Pendentes: {result['pendentes']}.", '',
             '| Grupo | Selecionados | Avaliados | Pendentes |',
             '| --- | ---: | ---: | ---: |']
    for group, label in (('com_alerta', 'Com alerta'), ('sem_alerta', 'Sem alerta')):
        counts = result['cobertura_por_grupo'][group]
        lines.append(f"| {label} | {counts['selecionados']} | {counts['avaliados']} | {counts['pendentes']} |")
    lines += ['', f"Precisão: {metric(result['precisao'])}.",
              f"Sensibilidade: {metric(result['sensibilidade'])}.",
              f"F1: {metric(result['f1'])}.", '',
              '## Divergências para segunda conferência', '',
              'A segunda conferência deve ser independente; esta lista não registra sua conclusão.', '']
    divergent = [case for case in result['casos']
                 if case['resultado'] in ('falsos_positivos', 'falsos_negativos')]
    for case in divergent:
        label = 'Alerta sem apoio na decisão humana' if case['resultado'] == 'falsos_positivos' else 'Caso perdido pela triagem'
        lines.append(f"- Linha {case['linha']}: {label}. Consulte justificativa e fontes no JSON rastreável.")
    if not divergent:
        lines.append('Nenhuma divergência identificada nas decisões disponíveis. '
                     'Casos pendentes não contam como acertos.')
    lines += ['', '## Rastreabilidade', '',
              f"Coleta SHA-256: {result['coleta_sha256']}", '',
              f"Parecer SHA-256: {result['parecer_sha256']}", '',
              f"Referência SHA-256: {result['referencia_sha256']}", '']
    if result.get('piloto'):
        pilot = result['piloto']
        duration = lambda value: 'não medido' if value is None else f'{value:g} segundos'
        lines += ['## Piloto supervisionado', '',
            f"Etapas independentes encerradas: {pilot['encerrados_independentes']}. "
            f"Triagens consultadas: {pilot['triagens_consultadas']}.",
            f"Reavaliações comparáveis: {pilot['reavaliacoes_comparaveis']}; "
            f"mudanças de decisão após consulta: {pilot['mudancas_de_decisao_apos_consulta']} (não representa acerto confirmado).",
            f"Casos fora das métricas por etapa não encerrada ou exposição prévia: {len(pilot['linhas_nao_elegiveis_para_metricas'])}.",
            f"Tempo independente: {duration(pilot['conferencia_independente']['total_segundos'])} "
            f"({pilot['conferencia_independente']['casos_com_tempo']} casos com medição).",
            f"Tempo adicional de consulta: {duration(pilot['consulta_posterior_ao_sistema']['total_segundos'])} "
            f"({pilot['consulta_posterior_ao_sistema']['casos_com_tempo']} casos com medição).",
            'Tempo economizado: não estimável neste desenho.', pilot['limite'], '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execucao', required=True, type=Path, help='Pasta da execução')
    parser.add_argument('--referencia', type=Path, help='Referência preenchida para avaliar')
    parser.add_argument('--por-grupo', type=int, default=20)
    parser.add_argument('--saida', required=True, type=Path)
    parser.add_argument('--relatorio', type=Path, help='Resumo Markdown opcional da avaliação')
    args = parser.parse_args()
    if args.relatorio and not args.referencia:
        parser.error('--relatorio exige --referencia.')
    for path in (args.saida, args.relatorio):
        if path is not None and path.exists():
            parser.error('Saída já existe. Escolha outro arquivo para preservar versões anteriores.')
    if args.relatorio and args.relatorio.resolve() == args.saida.resolve():
        parser.error('JSON e relatório devem usar caminhos diferentes.')
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    records, audit = read(args.execucao / 'contratos.json'), read(args.execucao / 'parecer.json')
    result = evaluate(records, audit, read(args.referencia)) if args.referencia else make_sample(records, audit, args.por_grupo)
    if args.saida.exists():
        parser.error('Saída já existe. Escolha outro arquivo para preservar versões anteriores.')
    write_json(args.saida, result)
    if args.relatorio:
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        with args.relatorio.open('x', encoding='utf-8') as output:
            output.write(render_report(result))
    print(f'Arquivo criado: {args.saida}')


if __name__ == '__main__':
    main()
