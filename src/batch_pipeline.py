"""Auditoria sequencial em lotes com checkpoint, sem repetir a coleta no LLM."""
import hashlib
import json
import logging
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from crewai import Crew, Process, Task
from crewai.tasks.task_output import TaskOutput

from src.agents.auditor import create_auditor
from src.audit_models import Achado, ParecerAuditoria
from src.tasks.audit_contracts import create_audit_task
from src.tasks.collect_contracts import ContractBatch
from src.tools.archive_tool import ArquivarContratosTool, field, normalized
from src.tools.extrator_api_tool import ExtratorContratosMarica
from src.plain_summary import save_summaries
from src.execution_progress import set_phase
from src.atomic_files import write_json as atomic_write_json
from src.office_activity import activity, saved_activity


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def fingerprint(value) -> str:
    return hashlib.sha256(encoded(value).encode('utf-8')).hexdigest()


def write_json(path: Path, value) -> None:
    atomic_write_json(path, value)
    saved_activity(path, value)


@dataclass(frozen=True)
class BatchSettings:
    max_records: int = 15
    max_bytes: int = 48000
    interval_seconds: float = 65
    quota_retries: int = 2

    @classmethod
    def from_env(cls):
        settings = cls(int(os.getenv('AUDIT_BATCH_SIZE', '15')),
                       int(os.getenv('AUDIT_BATCH_MAX_BYTES', '48000')),
                       float(os.getenv('AUDIT_INTERVAL_SECONDS', '65')),
                       int(os.getenv('AUDIT_QUOTA_RETRIES', '2')))
        if not (1 <= settings.max_records <= 100 and 1000 <= settings.max_bytes <= 120000
                and 0 <= settings.interval_seconds <= 3600 and 0 <= settings.quota_retries <= 5):
            raise ValueError('Configuração de lotes inválida; consulte FASE3.md.')
        return settings


def split_batches(records, settings: BatchSettings):
    batches, current = [], []
    for line, record in enumerate(records, 1):
        if len(encoded([record]).encode('utf-8')) > settings.max_bytes:
            raise ValueError(f'Linha {line} excede AUDIT_BATCH_MAX_BYTES sozinha; nenhum campo foi truncado.')
        candidate = current + [record]
        if current and (len(candidate) > settings.max_records or len(encoded(candidate).encode('utf-8')) > settings.max_bytes):
            batches.append(current)
            current = []
        current.append(record)
    if current:
        batches.append(current)
    return batches


def find_pending(root: Path) -> Path:
    for folder in sorted((p for p in root.iterdir() if p.is_dir()), reverse=True) if root.exists() else []:
        if (folder / 'contratos.json').is_file() and not (folder / 'arquivamento.json').is_file():
            return folder
    raise ValueError('Nenhuma coleta pendente encontrada para retomar.')


def load_records(folder: Path):
    return ContractBatch.model_validate_json((folder / 'contratos.json').read_text(encoding='utf-8')).root


class AuditValidationError(RuntimeError):
    """O lote permaneceu inválido após as tentativas de revisão permitidas."""


@contextmanager
def execution_lock(folder: Path):
    # O sistema operacional libera a trava mesmo se a janela/processo encerrar.
    with (folder / 'execucao.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Esta execução já está em andamento em outra janela.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def batch_worker(llm, records, folder: Path) -> ParecerAuditoria:
    write_json(folder / 'contratos.json', records)
    feedback = ''
    for attempt in range(1, 4):
        auditor = create_auditor(llm)
        # Repetições controladas aqui respeitam a pausa; o agente não reinicia sozinho.
        auditor.max_retry_limit = 0
        context = Task(description='Coleta previamente validada deste lote.', expected_output='JSON', agent=auditor)
        context.output = TaskOutput(description='Coleta local', raw=encoded(records), agent='Coletor determinístico')
        base = create_audit_task(auditor, context, folder / 'parecer.json', strict_batch=True)
        rejected = []
        def capture_validation(output: TaskOutput) -> tuple[bool, str]:
            ok, result = base.guardrail(output)
            if not ok:
                rejected.append(result)
                directory = folder / 'rejeicoes'
                directory.mkdir(exist_ok=True)
                # Nome único preserva também rejeições de retomadas anteriores.
                filename = directory / f'{time.time_ns()}.json'
                write_json(filename, {'tentativa': attempt, 'erro': result, 'resposta_original': output.raw})
            return ok, result
        values = [{'linha_local': i, 'valor_publicado': field(record, ('valor do contrato', 'valor contratado', 'valor'))}
                  for i, record in enumerate(records, 1)]
        instructions = ('\nEste é um lote independente. Use posições LOCAIS de 1 a ' + str(len(records))
                        + '. Declare todas em linhas_analisadas; não use números de processo como índices.'
                        + '\nConferência dos campos monetários (ausente não é zero): ' + encoded(values)
                        + '\nSó use "valor zerado" para o campo monetário de valor exatamente zero. '
                        'Para valor positivo ou ausente, descreva o fato diretamente, evitando essas expressões '
                        'inclusive em negações ou exemplos. Não invente outro risco para substituir um alerta incorreto.'
                        + feedback)
        task = Task(description=base.description + instructions, expected_output=base.expected_output,
                    agent=auditor, context=[context], output_pydantic=ParecerAuditoria,
                    guardrail=capture_validation, guardrail_max_retries=0, callback=base.callback,
                    output_file=str(folder / 'parecer.json'))
        try:
            result = Crew(agents=[auditor], tasks=[task], process=Process.sequential,
                          memory=False, cache=False, verbose=True).kickoff()
            return ParecerAuditoria.model_validate_json(result.raw)
        except Exception as exc:
            if not rejected:
                raise  # Erros de cota, rede ou banco não são erros de validação.
            if attempt == 3:
                raise AuditValidationError(
                    f'Lote {folder.name}: parecer ainda inválido após 3 tentativas. '
                    f'Último diagnóstico: {rejected[-1]} Respostas preservadas em {folder / "rejeicoes"}. '
                    'Os lotes anteriores foram mantidos; nenhum parecer inválido foi arquivado.'
                ) from exc
            feedback = '\nREVISÃO OBRIGATÓRIA: a tentativa anterior foi rejeitada pelo validador: ' + rejected[-1] + '\nRefaça o parecer e o relatório com a coleta original; confira os índices e os valores acima.'
            logging.warning('Lote %s: parecer rejeitado (%s). Nova revisão %d/3 após pausa de cota.',
                            folder.name, rejected[-1], attempt + 1)
            wait_seconds(65)


def validate_batch(audit: ParecerAuditoria, size: int):
    expected = set(range(1, size + 1))
    if (set(audit.linhas_analisadas) != expected or len(audit.linhas_analisadas) != size
            or any(f.linha not in expected for f in audit.suspeitos)):
        raise ValueError('Parecer do lote não cobre todas as linhas ou contém índice inválido. Nada foi arquivado.')


def is_quota_error(error):
    return str(getattr(error, 'code', '')) == '429' or bool(re.search(r'\b429\b|RESOURCE_EXHAUSTED|rate.limit', str(error), re.I))


def quota_delay(error):
    text = str(error)
    delay = re.search(r'(?:retryDelay[\'"\s:]+|retry in\s+)(\d+(?:\.\d+)?)s', text, re.I)
    return max(65.0, float(delay.group(1)) + 2) if delay else 65.0


def wait_seconds(seconds):
    while seconds > 0:
        step = min(seconds, 30)
        logging.info('Controle de cota: aguardando %.0f segundos...', seconds)
        time.sleep(step)
        seconds -= step


def global_coincidences(records):
    """Reconciliação exata global para diligência, não prova de duplicidade."""
    processes, evidence = {}, {}
    for line, record in enumerate(records, 1):
        # A listagem pode combinar número do contrato e processo ("390 [1400/2026]").
        # O detalhe é uma fonte separada, não outro alias da mesma coluna da tabela.
        process = field(record, ('detalhe - processo',)) or field(
            record, ('numero do processo', 'nr [nr processo]', 'nr processo', 'processo'))
        if process:
            processes.setdefault(normalized(process), []).append(line)
        supplier = field(record, ('nome do beneficiario', 'beneficiario', 'fornecedor', 'contratado'))
        obj = field(record, ('objeto', 'objeto do contrato'))
        value = field(record, ('valor do contrato', 'valor contratado', 'valor'))
        if supplier and obj and value:
            evidence.setdefault((normalized(supplier), normalized(obj), normalized(value)), []).append(line)
    result = []
    for criterion, groups in [('processo coincidente', processes), ('fornecedor, objeto e valor coincidentes', evidence)]:
        for lines in groups.values():
            if len(lines) > 1:
                result.append({'criterio': criterion, 'linhas': lines,
                               'limite': 'Conferir se são registros do mesmo contrato, parcelas ou aditivos; não comprova pagamento duplicado.'})
    return result


def merge_audits(records, audits, coincidences):
    findings, analyzed, sections, offset = [], [], [], 0
    for number, (batch, audit) in enumerate(audits, 1):
        validate_batch(audit, len(batch))
        analyzed.extend(offset + i for i in audit.linhas_analisadas)
        findings.extend(Achado(linha=offset + f.linha, motivo_suspeita=f.motivo_suspeita) for f in audit.suspeitos)
        sections.append(f'## Lote {number} — linhas globais {offset + 1} a {offset + len(batch)}\n\n'
                        f'As referências a linhas no texto deste lote são locais: linha global = linha local + {offset}.\n\n'
                        + audit.relatorio_markdown)
        offset += len(batch)
    summary = [f'# Auditoria de contratos — análise em lotes\n\n{len(records)} registros; {len(audits)} lotes concluídos.',
               'Os índices em parecer.json e nesta lista de achados são globais, base 1. Os relatórios dos lotes mantêm índices locais, com o deslocamento indicado.',
               '## Achados por linha global\n']
    summary += [f'- **Linha {f.linha}:** {f.motivo_suspeita}' for f in findings] or ['Nenhum achado sinalizado pelos pareceres. Isso não comprova regularidade.']
    summary += ['\n## Reconciliação entre lotes\n\nComparação determinística exata de processos e combinações de fornecedor/objeto/valor em toda a coleta. Não é comparação semântica nem comprovação de irregularidade. Os grupos completos estão em coincidencias.json.']
    summary += [f'- {g["criterio"]}: linhas {", ".join(map(str, g["linhas"]))}. {g["limite"]}' for g in coincidences]
    summary += ['\n## Limitações\n\nColeta sujeita a limites e falhas de paginação. Análise independente por lote; relações semânticas entre lotes não foram avaliadas pelo modelo. Links de anexos não significam leitura de seus arquivos. Cobertura declarada não comprova o raciocínio.']
    return ParecerAuditoria(linhas_analisadas=analyzed, suspeitos=findings,
                           relatorio_markdown='\n\n'.join(summary + sections))


def audit_in_batches(llm, records, output_dir: Path, settings: BatchSettings, *, worker=batch_worker,
                     wait=wait_seconds, clock=time.monotonic):
    batches = split_batches(records, settings)
    policy = hashlib.sha256(Path(__file__).with_name('tasks').joinpath('audit_contracts.py').read_bytes()).hexdigest()
    completed, offset, last_call = [], 0, None
    signature = fingerprint({'records': records, 'sizes': [len(b) for b in batches],
                             'model': str(getattr(llm, 'model', '')), 'policy': policy, 'pipeline': 1})
    progress = {'status': 'analisando', 'total_contratos': len(records), 'total_lotes': len(batches),
                'lotes_concluidos': 0, 'assinatura': signature}
    progress_path = output_dir / 'progresso.json'
    write_json(progress_path, progress)
    try:
        for number, batch in enumerate(batches, 1):
            folder = output_dir / 'lotes' / f'{number:04d}'
            checkpoint = folder / 'checkpoint.json'
            audit = None
            if checkpoint.exists():
                try:
                    saved = json.loads(checkpoint.read_text(encoding='utf-8'))
                    if saved.get('assinatura') == signature and saved.get('coleta_sha256') == fingerprint(batch):
                        candidate = ParecerAuditoria.model_validate(saved['parecer'])
                        validate_batch(candidate, len(batch))
                        audit = candidate
                except (ValueError, KeyError, TypeError):
                    pass
            if audit is None:
                logging.info('Analisando lote %d/%d: linhas %d a %d (%d bytes).', number, len(batches), offset + 1,
                             offset + len(batch), len(encoded(batch).encode('utf-8')))
                for attempt in range(settings.quota_retries + 1):
                    if last_call is not None:
                        delay = max(0, settings.interval_seconds - (clock() - last_call))
                        if delay:
                            set_phase(progress, 'aguardando_intervalo', delay)
                            write_json(progress_path, progress)
                        wait(delay)
                    try:
                        set_phase(progress, 'chamando_ia')
                        progress['lote_atual'] = number
                        write_json(progress_path, progress)
                        audit = worker(llm, batch, folder)
                        validate_batch(audit, len(batch))
                        last_call = clock()
                        break
                    except Exception as exc:
                        last_call = clock()
                        if not is_quota_error(exc) or attempt == settings.quota_retries:
                            raise
                        if re.search(r'per.?day|daily|quotaValue[\'"\s:]+0\b', str(exc), re.I):
                            raise RuntimeError('Cota diária ou indisponível do Gemini. Retome quando a cota estiver disponível.') from exc
                        logging.warning('Gemini limitou o lote %d; aguardando antes de repetir apenas este lote.', number)
                        delay = max(settings.interval_seconds, quota_delay(exc))
                        set_phase(progress, 'aguardando_cota', delay)
                        write_json(progress_path, progress)
                        wait(delay)
                write_json(checkpoint, {'assinatura': signature, 'coleta_sha256': fingerprint(batch),
                                        'parecer': audit.model_dump()})
            else:
                logging.info('Lote %d/%d recuperado do checkpoint, sem chamada ao Gemini.', number, len(batches))
            completed.append((batch, audit))
            offset += len(batch)
            progress.update(lotes_concluidos=number, linhas_concluidas=offset)
            write_json(progress_path, progress)
        set_phase(progress, 'consolidando')
        write_json(progress_path, progress)
        coincidences = global_coincidences(records)
        write_json(output_dir / 'coincidencias.json', coincidences)
        audit = merge_audits(records, completed, coincidences)
        write_json(output_dir / 'parecer.json', audit.model_dump())
        (output_dir / 'relatorio.md').write_text(audit.relatorio_markdown, encoding='utf-8')
        audit = save_summaries(output_dir, records, audit)
        progress['status'] = 'analise_concluida'
        set_phase(progress, 'analise_concluida')
        write_json(progress_path, progress)
        return audit
    except BaseException:
        progress['status'] = 'interrompido'
        set_phase(progress, 'interrompido')
        write_json(progress_path, progress)
        raise


def run_pipeline(llm, output_dir: Path, settings: BatchSettings, *, resume=False):
    output_dir.mkdir(parents=True, exist_ok=resume)
    with execution_lock(output_dir):
        if resume:
            records = load_records(output_dir)
            logging.info('Retomando coleta salva: %s', output_dir)
        else:
            activity(output_dir, 0)
            raw = ExtratorContratosMarica(output_dir=output_dir)._run()
            records = ContractBatch.model_validate_json(raw).root
            write_json(output_dir / 'contratos.json', records)
        audit_in_batches(llm, records, output_dir, settings)
        if os.getenv('GAZETTE_ENABLED', 'true').strip().lower() in {'true', '1', 'yes', 'sim'}:
            from src.gazette import enrich_saved_audit
            audit = ParecerAuditoria.model_validate_json((output_dir / 'parecer.json').read_text(encoding='utf-8'))
            logging.info('Consultando publicações oficiais para os contratos com achados. Isso não utiliza o Gemini.')
            progress_path = output_dir / 'progresso.json'
            progress = json.loads(progress_path.read_text(encoding='utf-8'))
            progress['status'] = 'consultando_diario'
            write_json(progress_path, progress)
            try:
                enrich_saved_audit(output_dir, records, audit)
            except Exception as exc:
                logging.warning('Consulta ao Diário Oficial indisponível: %s. Parecer e arquivamento foram preservados.', exc)
                write_json(output_dir / 'diario_oficial.json', {'status': 'consulta_indisponivel', 'consultas': [],
                    'edicoes_lidas': 0, 'falhas': [{'erro': str(exc)}],
                    'limite': 'Falha de consulta não comprova falta de publicação.'})
            progress['status'] = 'analise_concluida'
            write_json(progress_path, progress)
        if os.getenv('REVIEW_AGENTS_ENABLED', 'true').strip().lower() in {'true', '1', 'yes', 'sim'}:
            from src.agent_review import review_saved_audit
            progress_path = output_dir / 'progresso.json'
            progress = json.loads(progress_path.read_text(encoding='utf-8'))
            progress['status'] = 'revisando_achados'
            write_json(progress_path, progress)
            review_total = 0
            try:
                audit = ParecerAuditoria.model_validate_json((output_dir / 'parecer.json').read_text(encoding='utf-8'))
                review_total = len({f.linha for f in audit.suspeitos})
                review = review_saved_audit(llm, output_dir, records, audit)
                progress['revisao_agentes'] = review['status']
            except Exception as exc:
                logging.warning('Revisão adicional indisponível: %s. O parecer e o arquivamento foram preservados.', exc)
                write_json(output_dir / 'revisao_agentes.json', {
                    'versao': 1, 'status': 'interrompida', 'total_contratos': review_total,
                    'itens': [], 'erro': str(exc),
                    'nota': 'Revisão não concluída. Retome com revisar_achados.bat; o parecer original permanece válido como triagem.'})
                progress['revisao_agentes'] = 'interrompida'
            progress['status'] = 'analise_concluida'
            write_json(progress_path, progress)
        # Coleta e arquivamento são determinísticos; não precisam reenviar todo o JSON ao LLM.
        activity(output_dir, 2)
        receipt = json.loads(ArquivarContratosTool(output_dir=output_dir)._run())
        write_json(output_dir / 'arquivamento.json', receipt)
        progress_path = output_dir / 'progresso.json'
        progress = json.loads(progress_path.read_text(encoding='utf-8'))
        progress['status'] = 'concluido'
        write_json(progress_path, progress)
        return receipt
