"""Diligência documental local: citação de empenho não é nota de empenho nem pagamento."""
import copy
import hashlib
import re
from pathlib import Path

from src.documents import official_url
from src.financial import digest, now
from src.pncp import cnpj, number_year


def normalize(text):
    text = re.sub(r'(?<=\w)-\s*\n\s*(?=\w)', '', text)
    return ' '.join(text.split())


def analyze_reference(text, record, expected):
    """Confere identificadores explícitos no escopo selecionado; nunca confirma gasto."""
    text = normalize(text)
    references = {}
    for name, label in (('contratos', r'CONTRATO'),
                        ('processos', r'PROCESSO(?:\s+ADMINISTRATIVO)?'),
                        ('empenhos', r'NOTA\s+DE\s+EMPENHO')):
        raw = re.findall(r'\b' + label + r'\s*(?:N[.º°o\s]*)?[:.]?\s*(\d+\s*/\s*\d{4,})(?!\d)', text, re.I)
        parsed = [number_year(value) for value in raw]
        if any(value is None for value in parsed):
            raise ValueError('Referência documental com identificador malformado.')
        references[name] = sorted(set(parsed))
    contract = number_year(record.get('Detalhe - Número'))
    process = number_year(record.get('Detalhe - Processo'))
    supplier = normalize(str(record.get('Detalhe - Contratado') or '')).casefold()
    if (not contract or not process or contract not in references['contratos'] or
            process not in references['processos'] or not supplier or supplier not in text.casefold()):
        raise ValueError('Documento não apresenta contrato, processo e fornecedor esperados no escopo selecionado.')
    if references['empenhos'] != [tuple(expected)]:
        raise ValueError('Nota de empenho ausente, divergente ou ambígua no escopo selecionado.')
    values = {}
    for name, label in (('programa_trabalho', r'PROGRAMA\s+DE\s+TRABALHO'),
                        ('elemento_despesa', r'ELEMENTO\s+DE\s+DESPESA'),
                        ('origem_recurso', r'(?:ORIGEM|FONTE)\s+D[OE]\s+RECURSO')):
        found = sorted(set(re.findall(label + r'\s*:\s*([\d.]+)', text, re.I)))
        if len(found) > 1:
            raise ValueError('Dotação ambígua no escopo selecionado.')
        values[name] = found[0].rstrip('.') if found else None
    dates = sorted(set(re.findall(r'DATA\s+DA\s+ASSINATURA\s*:\s*(\d{2}/\d{2}/\d{4})', text, re.I)))
    position = re.search(r'NOTA\s+DE\s+EMPENHO', text, re.I).start()
    return {'contrato': list(contract), 'processo': list(process), 'empenho_citado': list(expected),
            'cnpj_localizado_no_escopo': bool(cnpj(record.get('Detalhe - CPF/CNPJ')) and
                cnpj(record.get('Detalhe - CPF/CNPJ')) in
                {cnpj(value) for value in re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text)}),
            'datas_assinatura_publicadas': dates, 'dotacao': values,
            'trecho': text[max(0, position - 250):position + 150],
            'normalizacao_trecho': 'Espaços consolidados e hifenização de quebra de linha removida.',
            'limite': 'Citação documental de empenho; não é a nota original nem comprovação de execução financeira.'}


def read_reference(path, url, record, expected, pages, *, column=None, start=None, end=None):
    import pdfplumber
    path = Path(path)
    if not official_url(url) or not pages or column not in (None, 1, 2):
        raise ValueError('Fonte oficial ou seleção de páginas inválida.')
    texts = []
    with pdfplumber.open(path) as pdf:
        if any(type(n) is not int or not 1 <= n <= len(pdf.pages) for n in pages):
            raise ValueError('Página documental fora do PDF.')
        for number in pages:
            page = pdf.pages[number - 1]
            area = page.crop(((column - 1) * page.width / 2, 0, column * page.width / 2, page.height)) if column else page
            texts.append(area.extract_text() or '')
    text = normalize('\n'.join(texts))
    if start:
        if text.count(start) != 1:
            raise ValueError('Início do extrato ausente ou ambíguo.')
        text = text.split(start, 1)[1]
        text = start + text
    if end:
        if end not in text:
            raise ValueError('Fim do extrato ausente.')
        text = text.split(end, 1)[0]
    return {**analyze_reference(text, record, expected), 'url': url, 'paginas': list(pages),
            'coluna': column, 'sha256_pdf': hashlib.sha256(path.read_bytes()).hexdigest(),
            'registro_sha256': digest(record), 'escopo_texto_sha256': digest(text)}


def build_diligence(records, financial, line, references, *, coleta_sha256):
    if type(line) is not int or not 1 <= line <= len(records) or not references:
        raise ValueError('Linha e referências documentais são obrigatórias.')
    record = records[line - 1]
    if any(ref.get('registro_sha256') != digest(record) for ref in references):
        raise ValueError('Referência documental pertence a outro contrato.')
    if (financial.get('coleta_sha256') != coleta_sha256 or
            financial.get('assinatura') != digest({k: v for k, v in financial.items() if k != 'assinatura'})):
        raise ValueError('Resultado financeiro alterado.')
    entries = [entry for entry in financial['consultas'] if entry['linha'] == line]
    if len(entries) != 1:
        raise ValueError('Linha financeira ausente ou ambígua.')
    links = entries[0]['vinculos']
    expected = {tuple(ref['empenho_citado']) for ref in references}
    if len(expected) != 1 or not any(tuple(v['numero_ano_esperado']) in expected for v in links):
        raise ValueError('Referências não correspondem ao empenho esperado no resultado financeiro.')
    packet = {'versao': 1, 'preparado_em': now(), 'linha': line, 'registro_sha256': digest(record),
        'financeiro_assinatura': financial['assinatura'],
        'situacao': 'nota_citada_documentalmente_original_nao_obtido',
        'nota': 'A referência nos documentos não confirma o destino financeiro rejeitado. Nenhum pagamento foi atribuído.',
        'contrato': list(number_year(record['Detalhe - Número'])),
        'processo': list(number_year(record['Detalhe - Processo'])),
        'cnpj_fornecedor': cnpj(record.get('Detalhe - CPF/CNPJ')),
        'fornecedor': record.get('Detalhe - Contratado'), 'empenho': list(next(iter(expected))),
        'referencias': copy.deepcopy(references),
        'vinculos_publicados': [{k: copy.deepcopy(v.get(k)) for k in (
            'numero_ano_esperado', 'numero_ano_observado', 'url', 'situacao', 'consultado_em')} for v in links],
        'solicitacoes': [
            'Nota de empenho original, incluindo número, exercício, instituição, CNPJ do credor, processo e dotação.',
            'Processo administrativo e versão assinada do contrato, com esclarecimento da divergência de datas.',
            'Demonstrativo de liquidações, pagamentos, anulações e estornos com documentos e vínculo ao empenho.',
            'Notas fiscais, medições, atestos e identificação dos responsáveis pela fiscalização.'],
        'revisao_humana': {'situacao': 'pendente', 'responsavel': '', 'decisao': None}}
    packet['assinatura'] = digest(packet)
    return packet


def request_text(packet):
    fmt = lambda value: '/'.join(map(str, value))
    return (f"Solicito acesso aos documentos do contrato {fmt(packet['contrato'])}, processo administrativo "
            f"{fmt(packet['processo'])}, fornecedor {packet['fornecedor']}, CNPJ {packet['cnpj_fornecedor']}.\n\n"
            f"As publicações consultadas citam a nota de empenho {fmt(packet['empenho'])}. "
            'Solicito os seguintes documentos e esclarecimentos:\n\n' +
            '\n'.join(f'{i}. {text}' for i, text in enumerate(packet['solicitacoes'], 1)) +
            '\n\nSolicito também indicação do endereço público correto do detalhe financeiro, pois o link '
            'publicado apresentou número/exercício divergentes nas consultas registradas. '
            'Esta solicitação busca esclarecimentos documentais e não pressupõe irregularidade.\n')
