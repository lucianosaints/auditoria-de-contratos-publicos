"""Protocolo local de piloto: referência independente e consulta posterior separadas."""
import copy
import math
import statistics
from datetime import datetime

from src.evidence_support import digest

FIELDS = ('exige_diligencia', 'responsavel', 'justificativa', 'fontes')


def initialize(reference, source_hashes):
    if 'piloto' in reference:
        raise ValueError('Referência já contém piloto. Retome pelo caderno com Importar progresso salvo.')
    result = copy.deepcopy(reference)
    if any(item['exige_diligencia'] is not None for item in result['itens']):
        raise ValueError('O piloto deve iniciar com referência sem decisões preenchidas.')
    result['piloto'] = {'versao': 1, 'id': digest({'fontes': source_hashes, 'protocolo': 1}),
        'fontes_sha256': copy.deepcopy(source_hashes), 'avaliador': {'nome': '', 'funcao': ''},
        'itens': [{'linha': item['linha'], 'registro_sha256': item['registro_sha256'],
            'rascunho': {field: copy.deepcopy(item[field]) for field in FIELDS},
            'exposicao_previa': False, 'manual_segundos': None, 'sistema_segundos': None,
            'encerrado_em': None, 'avaliacao_independente': None, 'triagem_aberta_em': None,
            'reavaliacao_assistida': {'exige_diligencia': None, 'justificativa': ''}}
            for item in result['itens']]}
    return result


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            return parsed
    except (ValueError, TypeError):
        pass
    raise ValueError('Data do piloto inválida ou sem fuso horário.')


def analyze(reference):
    pilot = reference.get('piloto')
    if not isinstance(pilot, dict) or pilot.get('versao') != 1 or not isinstance(pilot.get('itens'), list):
        raise ValueError('Protocolo de piloto inválido.')
    if pilot.get('id') != digest({'fontes': pilot.get('fontes_sha256'), 'protocolo': 1}):
        raise ValueError('Identidade do piloto incompatível com as fontes registradas.')
    if not isinstance(pilot.get('avaliador'), dict) or any(not isinstance(pilot['avaliador'].get(k), str) for k in ('nome', 'funcao')):
        raise ValueError('Identificação do avaliador inválida.')
    by_line = {i['linha']: i for i in reference['itens']}
    seen, excluded, manual, assisted = set(), [], [], []
    finished, consulted, comparable, changed = 0, 0, 0, 0
    def valid_fields(value):
        return (isinstance(value, dict) and all(field in value for field in FIELDS) and
            (value.get('exige_diligencia') is None or type(value.get('exige_diligencia')) is bool) and
            all(isinstance(value.get(field), str) for field in ('responsavel', 'justificativa')) and
            isinstance(value.get('fontes'), list) and all(isinstance(source, str) for source in value['fontes']))
    for item in pilot['itens']:
        line = item.get('linha')
        if type(line) is not int or line not in by_line or line in seen:
            raise ValueError('Linhas do piloto ausentes, inválidas ou repetidas.')
        seen.add(line)
        base = by_line[line]
        if not valid_fields(base) or not valid_fields(item.get('rascunho')):
            raise ValueError('Campos de avaliação do piloto inválidos.')
        if item.get('registro_sha256') != base['registro_sha256'] or type(item.get('exposicao_previa')) is not bool:
            raise ValueError('Registro ou exposição prévia do piloto inválidos.')
        for key, times in (('manual_segundos', manual), ('sistema_segundos', assisted)):
            value = item.get(key)
            if value is not None:
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 31 * 86400:
                    raise ValueError('Tempo do piloto inválido.')
                times.append(value)
        closed, opened = item.get('encerrado_em'), item.get('triagem_aberta_em')
        if closed is not None:
            close_time = timestamp(closed)
            if (item.get('avaliacao_independente') != {field: base[field] for field in FIELDS} or
                    item['rascunho'] != item['avaliacao_independente']):
                raise ValueError('Decisão independente foi alterada após encerramento.')
            if (item.get('manual_segundos') is None or not base['responsavel'].strip() or not base['justificativa'].strip() or
                    base['exige_diligencia'] is not None and (not base['fontes'] or any(not s.strip() for s in base['fontes']))):
                raise ValueError('Encerramento exige identificação, justificativa, tempo e fontes para decisões.')
            finished += 1
        else:
            if item.get('avaliacao_independente') is not None or base['exige_diligencia'] is not None:
                raise ValueError('Decisão do piloto sem encerramento independente.')
            excluded.append(line)
        if item['exposicao_previa'] and line not in excluded:
            excluded.append(line)
        if opened is not None:
            if closed is None or timestamp(opened) < close_time:
                raise ValueError('Consulta ao sistema anterior ao encerramento independente.')
            consulted += 1
        elif item.get('sistema_segundos') is not None:
            raise ValueError('Tempo de sistema sem consulta registrada.')
        review = item.get('reavaliacao_assistida')
        if (not isinstance(review, dict) or review.get('exige_diligencia') is not None and type(review.get('exige_diligencia')) is not bool or
                not isinstance(review.get('justificativa'), str)):
            raise ValueError('Reavaliação assistida inválida.')
        if review['exige_diligencia'] is not None and (not opened or not review['justificativa'].strip()):
            raise ValueError('Reavaliação assistida exige consulta e justificativa.')
        if opened is not None and base['exige_diligencia'] is not None and review['exige_diligencia'] is not None:
            comparable += 1
            changed += base['exige_diligencia'] != review['exige_diligencia']
    if seen != set(by_line):
        raise ValueError('Piloto não corresponde a todos os casos da referência.')
    stats = lambda values: {'casos_com_tempo': len(values),
        'total_segundos': sum(values) if values else None,
        'mediana_segundos': statistics.median(values) if values else None}
    return {'encerrados_independentes': finished, 'triagens_consultadas': consulted,
        'reavaliacoes_comparaveis': comparable, 'mudancas_de_decisao_apos_consulta': changed,
        'linhas_nao_elegiveis_para_metricas': sorted(excluded),
        'conferencia_independente': stats(manual), 'consulta_posterior_ao_sistema': stats(assisted),
        'tempo_economizado_segundos': None,
        'limite': 'Tempos de cronômetro declarados, incluindo etapas parciais, sujeitos a interrupções. Consulta posterior dos mesmos casos '
                  'não mede economia de tempo; requer comparação independente. Exposição prévia ou etapa '
                  'independente não encerrada fica fora das métricas de acerto.'}
