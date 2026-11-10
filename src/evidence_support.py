"""Triagem local de extrapolações frequentes; não valida o mérito semântico."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from src.atomic_files import write_json

NOTE = ('Triagem por regras, sem IA. Verifica citações e alguns padrões de extrapolação; '
        'não valida integralmente a interpretação nem substitui conferência humana. '
        'Ausência de avisos não confirma a conclusão. O resultado original foi preservado.')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold()) if not unicodedata.combining(c))


ABSENCE_PREFIX = r'(?:nao (?:ha|havera|envolve|implica|preve|existe)|sem|ausencia de)\s+(?:qualquer\s+)?'
ABSENCE_FAMILIES = [r'(?:repasse|transferencia (?:de recursos|financeira))',
                    r'(?:onerosidade|onus|encargo financeiro)', r'(?:custo (?:direto|para)|desembolso)']
PAYMENT = r'(?:pagamento (?:foi )?(?:realizado|efetuado|quitado)|(?:foi|foram) pag[oa]s?\b|formaliza.{0,100}pagamento)'
HEDGE = r'\b(?:pode|podem|possivel|hipotese|sugere|sugerem|nao (?:comprova|confirma|permite|significa)|a confirmar|a verificar|se confirmado)\b'
LEGAL = r'\b(?:configura|comprova|demonstra|constitui|houve|ha|e)\s+(?:(?:uma?|o)\s+)?(?:fraude|ilegalidade|superfaturamento|dano ao erario)\b'


def positive_match(pattern, text):
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if re.search(HEDGE, sentence):
            continue
        for match in re.finditer(pattern, sentence):
            if not sentence[:match.start()].rstrip().endswith('nao'):
                return True
    return False


def check_item(item):
    citations = item['evidencias']
    evidence = normalized(' '.join(e['trecho'] for e in citations))
    warnings = []
    for e in citations:
        source = e.get('fonte', {})
        if (e['trecho'] not in source.get('texto', '') or source.get('id') != e['fonte_id'] or
                not e['fonte_id'].startswith(f'L{item["linha"]}-')):
            warnings.append({'codigo': 'citacao_incompativel', 'trecho': e['trecho'],
                'mensagem': 'Citação incompatível com a fonte ou com a linha do contrato. Confira o registro original.'})
    for sentence in re.split(r'(?<=[.!?])\s+', item['explicacao_simples']):
        text = normalized(sentence)
        if re.search(HEDGE, text):
            continue
        if any(re.search(ABSENCE_PREFIX + family, text) and not positive_match(ABSENCE_PREFIX + family, evidence) for family in ABSENCE_FAMILIES):
            warnings.append({'codigo': 'ausencia_financeira_sem_suporte', 'trecho': sentence,
                'mensagem': 'As citações não declaram explicitamente a ausência de repasse ou de ônus. Valor zero e natureza do ajuste, isoladamente, não bastam para essa conclusão.'})
        if positive_match(PAYMENT, text) and not positive_match(r'pagamento (?:foi )?(?:realizado|efetuado|quitado)|foi pag[oa]\b|valor pago', evidence):
            warnings.append({'codigo': 'pagamento_sem_comprovacao', 'trecho': sentence,
                'mensagem': 'A redação pode confundir reconhecimento de dívida ou previsão de pagamento com quitação efetiva. Confira comprovantes e a formulação da conclusão.'})
        if positive_match(LEGAL, text):
            warnings.append({'codigo': 'conclusao_juridica_categorica', 'trecho': sentence,
                'mensagem': 'A explicação contém uma conclusão jurídica categórica. Exige conferência humana do contexto e das fontes, mesmo quando há citação literal.'})
    return {'linha': item['linha'], 'revisao_original': item,
        'status': 'conferir' if warnings else 'sem_alertas_nas_regras', 'avisos': warnings}


def check_saved_review(folder):
    folder = Path(folder)
    def read(name):
        path = folder / name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    review, records, audit = read('revisao_agentes.json'), read('contratos.json'), read('parecer.json')
    if not review or not review.get('itens'):
        raise ValueError('Nenhuma revisão disponível. Execute Revisar com agentes primeiro.')
    documents, gazette = read('documentos.json'), read('diario_oficial.json')
    if ((review.get('documentos_assinatura') != (documents or {}).get('assinatura')) or
            review.get('diario_assinatura') != (gazette or {}).get('assinatura') or
            review.get('diario_consultado_em') != (gazette or {}).get('consultado_em')):
        raise ValueError('As fontes mudaram após a revisão. Revise com os agentes antes de conferir o suporte.')
    for item in review['itens']:
        line = item['linha']
        reasons = sorted(set(f['motivo_suspeita'] for f in audit['suspeitos'] if f['linha'] == line))
        if not 1 <= line <= len(records) or item['registro_original'] != records[line - 1] or sorted(item['motivos_originais']) != reasons:
            raise ValueError('Coleta ou alertas mudaram após a revisão. Execute Revisar com agentes novamente.')
    result = {'versao': 1, 'verificado_em': datetime.now(timezone.utc).isoformat(),
        'revisao_sha256': digest(review), 'revisao_atualizado_em': review.get('atualizado_em'),
        'nota': NOTE, 'itens': [check_item(item) for item in review['itens']]}
    result['contratos_com_avisos'] = sum(bool(i['avisos']) for i in result['itens'])
    path = folder / 'verificacao_evidencias.json'
    write_json(path, result)
    return result
