"""Indicadores reproduzíveis da coleta com pandas; sem IA, rede ou banco."""
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.atomic_files import write_json
from src.documents import digest

VERSION = 1
INPUTS = ('contratos.json', 'parecer.json', 'documentos.json', 'pncp.json')
LIMIT = ('Indicadores descritivos da coleta salva, sem certificação de completude municipal. '
         'Valores contratuais não são pagamentos nem entregas comprovadas. '
         'Participação por fornecedor descreve somente o recorte elegível e não comprova concentração de mercado ou fraude. '
         'Ausências e ambiguidades são informadas e não recebem risco zero.')


def cents(raw):
    """Texto monetário -> centavos inteiros, sem passagem por float."""
    if raw is None or str(raw).strip() in ('', '-', '—'):
        return None, 'ausente'
    if not isinstance(raw, str):
        return None, 'invalido'
    text = raw.replace('R$', '').replace('\xa0', '').replace(' ', '').strip()
    if ',' in text:
        if not re.fullmatch(r'-?(?:\d+|\d{1,3}(?:\.\d{3})+),\d{2}', text):
            return None, 'invalido'
        text = text.replace('.', '').replace(',', '.')
    elif not re.fullmatch(r'-?\d+(?:\.\d{2})?', text):
        return None, 'invalido'
    sign = -1 if text.startswith('-') else 1
    whole, _, fraction = text.lstrip('-').partition('.')
    try:
        return sign * (int(whole) * 100 + int(fraction or '0')), 'valido'
    except ValueError:
        return None, 'invalido'


def currency(value):
    value = int(value)
    whole, fraction = divmod(abs(value), 100)
    return f'{"-" if value < 0 else ""}{whole}.{fraction:02d}'


def percent(numerator, denominator):
    return f'{Decimal(numerator) * 100 / Decimal(denominator):.2f}' if denominator else None


def choose(record, *names):
    for name in names:
        if isinstance(record.get(name), str) and record[name].strip():
            return name, record[name].strip()
    return None, None


def normalize_record(line, record):
    amount_key, raw = choose(record, 'Detalhe - Valor Global', 'Valor do Contrato', 'Valor')
    amount, status = cents(raw)
    _, supplier = choose(record, 'Detalhe - Contratado', 'Nome do Beneficiário', 'Fornecedor')
    _, identifier = choose(record, 'Detalhe - CPF/CNPJ', 'CNPJ')
    identifier = re.sub(r'[.\-/\s]', '', identifier or '')
    identifier = identifier if re.fullmatch(r'\d{14}', identifier) else None
    _, number = choose(record, 'Detalhe - Número')
    _, process = choose(record, 'Detalhe - Processo', 'Processo')
    num_match = re.fullmatch(r'\s*0*(\d+)\s*[/\-]\s*(20\d{2})\s*', number or '')
    proc_match = re.fullmatch(r'\s*0*(\d+)\s*/\s*(20\d{2})\s*', process or '')
    identity = f'{int(num_match[1])}/{num_match[2]}|{int(proc_match[1])}/{proc_match[2]}|{identifier}' if num_match and proc_match and identifier else None
    issues = []
    if status != 'valido':
        issues.append('valor_' + status)
    if amount is not None and amount < 0:
        issues.append('valor_negativo')
    if identifier is None:
        issues.append('cnpj_fornecedor_ausente_ou_formato_invalido')
    if not identity:
        issues.append('identidade_contratual_incompleta')
    _, obj = choose(record, 'Detalhe - Objeto', 'Objeto')
    if not obj:
        issues.append('objeto_ausente')
    _, department = choose(record, 'Detalhe - Departamento', 'Órgão', 'Orgao')
    return {'linha': line, 'registro_sha256': digest(record), 'fornecedor_cnpj': identifier,
            'fornecedor_nome': supplier, 'departamento': department or 'Não informado',
            'chave_identidade': identity, 'valor_centavos': amount, 'valor_status': status,
            'campo_valor': amount_key, 'avisos_dados': issues}


def source_rows(records, audit, documents, pncp):
    flagged = set()
    for finding in (audit or {}).get('suspeitos', []):
        line = finding.get('linha')
        if type(line) is not int or not 1 <= line <= len(records):
            raise ValueError('Achado fora da coleta nos indicadores.')
        flagged.add(line)

    def indexed(manifest):
        entries = {}
        for entry in (manifest or {}).get('consultas', []):
            line = entry.get('linha')
            if type(line) is not int or not 1 <= line <= len(records) or line in entries:
                raise ValueError('Linha inválida ou duplicada no manifesto de indicadores.')
            entries[line] = entry
        return entries

    doc_map, pncp_map = indexed(documents), indexed(pncp)
    pncp_current = bool(pncp and pncp.get('coleta_sha256') == digest(records) and
                        pncp.get('linhas') == sorted(flagged) and pncp.get('assinatura') ==
                        digest({k: v for k, v in pncp.items() if k != 'assinatura'}))
    rows = []
    for line, record in enumerate(records, 1):
        doc = doc_map.get(line)
        if doc is None:
            doc_status, read, partial, failed = 'nao_processado', 0, 0, 0
        elif doc.get('registro_sha256') != digest(record):
            doc_status, read, partial, failed = 'fonte_desatualizada', 0, 0, 0
        else:
            files = doc.get('documentos', [])
            read = sum(d['status'] == 'lido' for d in files)
            partial = sum(d['status'] == 'parcial' for d in files)
            failed = sum(d['status'] in ('falhou', 'nao_lido') for d in files)
            non_sheet = any(d.get('tipo_documento') == 'pdf_publicado' and d['status'] in ('lido', 'parcial') for d in files)
            doc_status = 'pdf_publicado_extraido' if non_sheet else 'somente_fichas_ou_sem_tipo_validado' if read or partial else 'sem_texto_extraido'
        remote = pncp_map.get(line)
        remote_status = ('nao_consultado' if remote is None else 'fonte_desatualizada' if not pncp_current or
                         remote.get('registro_sha256') != digest(record) else remote['situacao'])
        rows.append({'linha': line, 'com_alerta': line in flagged, 'cobertura_documental': doc_status,
                     'documentos_lidos_declarados': read, 'documentos_parciais_declarados': partial,
                     'documentos_sem_leitura': failed, 'situacao_pncp': remote_status})
    return rows


def analyze(records, audit=None, documents=None, pncp=None):
    import pandas as pd
    if not isinstance(records, list) or any(not isinstance(r, dict) or
            any(not isinstance(v, str) for v in r.values()) for r in records):
        raise ValueError('Coleta deve conter registros com campos textuais.')
    columns = ['linha', 'registro_sha256', 'fornecedor_cnpj', 'fornecedor_nome', 'departamento',
               'chave_identidade', 'valor_centavos', 'valor_status', 'campo_valor', 'avisos_dados']
    frame = pd.DataFrame([normalize_record(i, r) for i, r in enumerate(records, 1)], columns=columns, dtype=object)
    coverage_columns = ['linha', 'com_alerta', 'cobertura_documental', 'documentos_lidos_declarados',
                        'documentos_parciais_declarados', 'documentos_sem_leitura', 'situacao_pncp']
    coverage = pd.DataFrame(source_rows(records, audit, documents, pncp), columns=coverage_columns, dtype=object)
    frame = frame.merge(coverage, on='linha', how='left', validate='one_to_one', indicator=True)
    if not frame['_merge'].eq('both').all():
        raise ValueError('Não foi possível reconciliar todas as linhas dos indicadores.')
    frame = frame.drop(columns='_merge')
    frame['identidade_repetida'] = frame['chave_identidade'].notna() & frame['chave_identidade'].duplicated(keep=False)
    frame['elegivel_distribuicao'] = pd.Series([not repeated and identity is not None and amount is not None and amount >= 0
        for repeated, identity, amount in zip(frame['identidade_repetida'], frame['chave_identidade'], frame['valor_centavos'])], index=frame.index, dtype=bool)
    eligible = frame.loc[frame['elegivel_distribuicao']].copy()
    total = sum((int(v) for v in eligible['valor_centavos']), 0)
    suppliers = []
    # Centavos permanecem objetos Python; não se usam floats ou int64 em somas monetárias.
    for supplier, group in eligible.groupby('fornecedor_cnpj', sort=True, dropna=False):
        amount = sum((int(v) for v in group['valor_centavos']), 0)
        names = sorted({str(v) for v in group['fornecedor_nome'] if v is not None})
        suppliers.append({'cnpj': str(supplier), 'nomes_publicados': names, 'contratos': len(group),
                          'valor_contratual': currency(amount), 'participacao_percentual': percent(amount, total),
                          'linhas': [int(v) for v in group['linha']], '_centavos': amount})
    suppliers.sort(key=lambda s: (-s['_centavos'], s['cnpj']))
    top5 = sum(s['_centavos'] for s in suppliers[:5])
    for item in suppliers:
        item.pop('_centavos')
    items = []
    for row in frame.to_dict('records'):
        row['valor_contratual'] = currency(row['valor_centavos']) if row['valor_centavos'] is not None else None
        row.pop('valor_centavos')
        row['identidade_repetida'] = bool(row['identidade_repetida'])
        row['elegivel_distribuicao'] = bool(row['elegivel_distribuicao'])
        if row['identidade_repetida']:
            row['avisos_dados'] = row['avisos_dados'] + ['identidade_contratual_repetida']
        items.append(row)
    counts = lambda key: {str(k): int(v) for k, v in frame.groupby(key, dropna=False).size().items()}
    return {'versao': VERSION, 'motor': 'pandas', 'pandas_versao': pd.__version__, 'limite': LIMIT,
            'gerado_em': datetime.now(timezone.utc).isoformat(),
            'resumo': {'linhas_coletadas': len(records), 'linhas_com_alerta': sum(bool(r['com_alerta']) for r in items),
                       'linhas_elegiveis_distribuicao': len(eligible), 'linhas_excluidas_distribuicao': len(frame) - len(eligible),
                       'linhas_identidade_repetida': int(frame['identidade_repetida'].sum()),
                       'fornecedores_no_recorte_elegivel': len(suppliers), 'valor_contratual_elegivel': currency(total),
                       'participacao_cinco_maiores_percentual': percent(top5, total)},
            'cobertura': {'valores': counts('valor_status'), 'documentos': counts('cobertura_documental'), 'pncp': counts('situacao_pncp')},
            'execucao_financeira': {'situacao': 'nao_avaliavel', 'motivo': 'Empenhos, liquidações, pagamentos e entregas ainda não foram reconciliados em dados estruturados.'},
            'metodologia': {'valor': 'Preferência por Detalhe - Valor Global; depois Valor do Contrato ou Valor. Ausência/erro não é zero.',
                            'identidade': 'Número/ano, processo/ano e CNPJ de 14 dígitos. Formato não é validação cadastral.',
                            'exclusoes': 'Todas as linhas de identidade repetida são excluídas da distribuição, sem escolher uma versão. Exclui identidade incompleta, valor ausente/inválido ou negativo.',
                            'denominador': 'Soma dos valores contratuais não negativos das linhas elegíveis; não representa gasto, orçamento municipal ou universo completo de contratações.',
                            'documentos': 'Cobertura declarada no manifesto compatível; PDF publicado extraído não significa instrumento integral validado.'},
            'fornecedores': suppliers, 'itens': items}


def read_inputs(folder):
    values, hashes = {}, {}
    for name in INPUTS:
        path = Path(folder) / name
        content = path.read_bytes() if path.exists() else None
        hashes[name] = hashlib.sha256(content).hexdigest() if content is not None else None
        values[name] = json.loads(content.decode('utf-8-sig')) if content is not None else None
    if values['contratos.json'] is None:
        raise ValueError('Coleta não disponível para os indicadores.')
    return values, hashes


def build_indicators(folder):
    folder = Path(folder)
    values, hashes = read_inputs(folder)
    result = analyze(*(values[name] for name in INPUTS))
    result['fontes_sha256'] = hashes
    result['assinatura'] = digest(result)
    path = folder / 'indicadores.json'
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        write_json(folder / 'indicadores/historico' / f'{digest(previous)}.json', previous)
    if read_inputs(folder)[1] != hashes:
        raise ValueError('Fontes alteradas durante o cálculo. Gere os indicadores novamente.')
    write_json(path, result)
    return result


def saved_indicators(folder, line=None, limit=10):
    if type(limit) is not int or not 1 <= limit <= 50 or line is not None and (type(line) is not int or line < 1):
        raise ValueError('Informe linha positiva e limite entre 1 e 50.')
    path = Path(folder) / 'indicadores.json'
    if not path.exists():
        return {'status': 'nao_preparado', 'mensagem': 'Use Gerar indicadores no painel.'}
    result = json.loads(path.read_text(encoding='utf-8'))
    if (result.get('versao') != VERSION or result.get('fontes_sha256') != read_inputs(folder)[1] or
            result.get('assinatura') != digest({k: v for k, v in result.items() if k != 'assinatura'})):
        return {'status': 'desatualizado', 'mensagem': 'As fontes ou o artefato mudaram. Gere indicadores novamente.'}
    if line is not None and line > len(result['itens']):
        raise ValueError('Linha fora da coleta.')
    return {'status': 'pronto', **{k: v for k, v in result.items() if k not in ('itens', 'fornecedores')},
            'fornecedores': result['fornecedores'][:limit], 'fornecedores_omitidos': max(0, len(result['fornecedores']) - limit),
            'item': result['itens'][line - 1] if line is not None else None}
