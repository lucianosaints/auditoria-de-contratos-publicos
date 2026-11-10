"""Prepara caderno HTML local para avaliação humana; não preenche decisões."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

from src.atomic_files import write_json
from src.quality_evaluation import evaluate
from src.evidence_support import digest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_url(raw):
    try:
        u = urlsplit(raw)
        return raw if u.scheme == 'https' and u.hostname in ('transparencia.marica.rj.gov.br', 'pncp.gov.br') and not u.username and not u.password and u.port in (None, 443) else None
    except (ValueError, TypeError):
        return None


def build_packet(folder, reference_path, output, *, pilot=False):
    folder, reference_path, output = Path(folder).resolve(), Path(reference_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Caderno de saída já existe. Escolha outra pasta para preservar as versões.')
    records = json.loads((folder / 'contratos.json').read_text(encoding='utf-8'))
    audit = json.loads((folder / 'parecer.json').read_text(encoding='utf-8'))
    reference = json.loads(reference_path.read_text(encoding='utf-8'))
    # Recusa referência incompatível e decisões incompletas, sem tocar nos dados.
    initial = evaluate(records, audit, reference)
    if not reference['itens']:
        raise ValueError('Referência sem casos selecionados.')
    documents_path = folder / 'documentos.json'
    documents = json.loads(documents_path.read_text(encoding='utf-8')) if documents_path.exists() else None
    entries = (documents or {}).get('consultas', [])
    by_line = {}
    for entry in entries:
        line = entry.get('linha')
        if type(line) is not int or line in by_line:
            raise ValueError('Manifesto documental com linhas inválidas ou duplicadas.')
        by_line[line] = entry
    cases = []
    checked_files = {}
    for item in reference['itens']:
        line = item['linha']
        record = records[line - 1]
        case = {'linha': line, 'numero': record.get('Detalhe - Número', ''),
                'processo': record.get('Detalhe - Processo', ''),
                'fornecedor': record.get('Detalhe - Contratado') or record.get('Nome do Beneficiário', ''),
                'objeto': record.get('Detalhe - Objeto') or record.get('Objeto', ''),
                'valor': record.get('Detalhe - Valor Global') or record.get('Valor do Contrato', ''),
                'url_contrato': source_url(record.get('URL do contrato')),
                'motivos_originais': [f['motivo_suspeita'] for f in audit['suspeitos'] if f['linha'] == line],
                'documentos': [], 'nota_documental': 'Sem dossiê documental compatível disponível neste caderno.'}
        entry = by_line.get(line)
        if entry and entry.get('registro_sha256') == digest(record):
            case['nota_documental'] = 'Arquivos e classificação do manifesto local; confira o original. Extração não equivale à validação de conteúdo.'
            for doc in entry.get('documentos', []):
                local = None
                if doc.get('arquivo'):
                    path = (folder / doc['arquivo']).resolve()
                    if path.is_relative_to(folder) and path.suffix.lower() == '.pdf' and path.is_file() and sha(path) == doc.get('sha256'):
                        local = quote(Path(os.path.relpath(path, output)).as_posix(), safe='/')
                        checked_files[str(path.relative_to(folder))] = doc['sha256']
                case['documentos'].append({'rotulo': doc.get('rotulo') or 'Documento', 'tipo': doc.get('tipo_documento'),
                    'nota_tipo': doc.get('nota_tipo'), 'status': doc.get('status'), 'paginas': doc.get('total_paginas'),
                    'sha256': doc.get('sha256'), 'local': local, 'url': source_url(doc.get('url'))})
        cases.append(case)
    packet = {'versao': 1, 'preparado_em': datetime.now(timezone.utc).isoformat(),
              'execucao': folder.name, 'referencia': reference, 'casos': cases,
              'fontes_sha256': {'contratos.json': sha(folder / 'contratos.json'),
                               'parecer.json': sha(folder / 'parecer.json'),
                               'documentos.json': sha(documents_path) if documents_path.exists() else None,
                               'referencia_base': sha(reference_path)},
              'arquivos_documentais_conferidos': checked_files}
    if pilot:
        from src.quality_pilot import initialize
        packet['referencia'] = initialize(reference, packet['fontes_sha256'])
        initial = evaluate(records, audit, packet['referencia'])
    serialized = json.dumps(packet, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = Path(__file__).with_name('quality_pilot.html' if pilot else 'quality_packet.html').read_text(encoding='utf-8')
    assert template.count('__PACKET__') == 1
    output.mkdir(parents=True)
    write_json(output / 'caderno.json', packet)
    write_json(output / 'referencia_base.json', packet['referencia'])
    write_json(output / 'avaliacao_inicial.json', initial)
    (output / 'avaliar.html').write_text(template.replace('__PACKET__', serialized), encoding='utf-8')
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execucao', required=True, type=Path)
    parser.add_argument('--referencia', required=True, type=Path)
    parser.add_argument('--saida', required=True, type=Path)
    parser.add_argument('--piloto', action='store_true', help='Duas etapas, cronômetro e referência independente preservada')
    args = parser.parse_args()
    packet = build_packet(args.execucao, args.referencia, args.saida, pilot=args.piloto)
    print(f'Caderno preparado: {len(packet["casos"])} casos. Decisões humanas preservadas; nenhum preenchimento automático.')


if __name__ == '__main__':
    main()
