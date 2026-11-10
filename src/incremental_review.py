"""Cache por contrato: escopo, modelo, procedimentos e contexto verificáveis."""
import copy
import json
import shutil
from pathlib import Path
from src.batch_pipeline import fingerprint, write_json


def archive_previous(folder):
    path = folder / 'revisao_agentes.json'
    if not path.exists():
        return
    previous = json.loads(path.read_text(encoding='utf-8'))
    if not previous.get('itens'):
        return
    target = folder / 'agentes/historico' / fingerprint(previous)
    target.mkdir(parents=True, exist_ok=True)
    for name in ('revisao_agentes.json', 'dossies_agentes.json', 'verificacao_evidencias.json', 'parecer.json', 'relatorio.md'):
        if (folder / name).exists() and not (target / name).exists():
            shutil.copy2(folder / name, target / name)


def context(dossier):
    value = copy.deepcopy(dossier)
    # O hash global muda quando OUTRO contrato é indexado. As fontes, consulta,
    # limites e assinatura documental desta linha continuam na comparação.
    value.get('documentos', {}).pop('rag_assinatura', None)
    return value


def signature(dossier, model, skills, policy):
    return fingerprint({'dossie': context(dossier), 'modelo': model, 'skills': skills, 'politica': policy})


def save_contract(folder, dossier, investigation, review, model, skills, policy):
    path = Path(folder) / 'agentes/por_contrato' / f'{dossier["linha"]}.json'
    write_json(path, {'assinatura': signature(dossier, model, skills, policy),
        'investigacao': investigation, 'revisao': review})


def legacy_pairs(folder, dossiers, settings, model, skills, policies, validate, split):
    """Só importa checkpoints antigos após conferir as assinaturas dos lotes inteiros."""
    try:
        previous = json.loads((folder / 'dossies_agentes.json').read_text(encoding='utf-8'))['contratos']
        old_batches = split(previous, settings)
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    current = {d['linha']: d for d in dossiers}
    recovered = {}
    for number, batch in enumerate(old_batches, 1):
        investigation = None
        outputs = {}
        for stage in ('investigacao', 'revisao'):
            try:
                cached = json.loads((folder / 'agentes' / f'{number:04d}' / f'{stage}.json').read_text(encoding='utf-8'))
                matches = any(cached.get('assinatura') == fingerprint({'dossies': batch, 'skills': skills,
                    'modelo': model, 'politica': policy, 'prompt': prompt, 'etapa': stage,
                    'investigacao': investigation}) for policy, prompt in policies)
                if not matches:
                    break
                outputs[stage] = validate(stage, cached['saida'], batch, investigation)
                if stage == 'investigacao':
                    investigation = outputs[stage]
            except (OSError, ValueError, KeyError, TypeError):
                break
        if len(outputs) != 2:
            continue
        investigators = {i['linha']: i for i in outputs['investigacao']['itens']}
        reviewers = {i['linha']: i for i in outputs['revisao']['itens']}
        for old in batch:
            line = old['linha']
            if line in current and context(old) == context(current[line]):
                recovered[line] = (investigators[line], reviewers[line])
    return recovered


def prepare(folder, dossiers, settings, model, skills, policy, policies, validate, split):
    recovered = {}
    legacy = legacy_pairs(folder, dossiers, settings, model, skills, policies, validate, split)
    for dossier in dossiers:
        line = dossier['linha']
        try:
            saved = json.loads((folder / 'agentes/por_contrato' / f'{line}.json').read_text(encoding='utf-8'))
            if saved.get('assinatura') == signature(dossier, model, skills, policy):
                inv = validate('investigacao', {'itens': [saved['investigacao']]}, [dossier])
                rev = validate('revisao', {'itens': [saved['revisao']]}, [dossier], inv)
                recovered[line] = (inv['itens'][0], rev['itens'][0])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if line not in recovered and line in legacy:
            recovered[line] = legacy[line]
    return recovered, [d for d in dossiers if d['linha'] not in recovered]


def published_item(dossier, record, review):
    sources = {s['id']: {**s, 'url': s.get('url', dossier['url_portal'])} for s in dossier['fontes']}
    return {**review, 'skills': dossier['skills'], 'registro_original': record,
        'motivos_originais': dossier['motivos_originais'],
        'evidencias': [{**e, 'fonte': sources[e['fonte_id']]} for e in review['evidencias']]}
