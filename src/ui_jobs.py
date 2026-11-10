"""Executor local dos comandos permitidos pelo painel; estado independe do Vite."""
import argparse
import json
import logging
import os
import re
import threading
import _thread
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from src.atomic_files import write_json as atomic_write_json
from src.office_activity import observe_activity

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = {'nova_auditoria', 'retomar_auditoria', 'consultar_diario', 'revisar_achados', 'planejar_revisao',
           'planejar_documentos', 'coletar_documentos', 'preparar_rag', 'verificar_mcp', 'conferir_suporte', 'consultar_pncp', 'gerar_indicadores', 'consultar_financeiro'}
ID = re.compile(r'^[A-Za-z0-9_][\w-]{0,99}$', re.ASCII)


def now():
    return datetime.now(timezone.utc).isoformat()


def sanitize(value):
    text = str(value)
    text = re.sub(r'([?&](?:key|api_key|token)=)[^&\s]+', r'\1[oculto]', text, flags=re.I)
    return re.sub(r'AIza[\w-]{20,}|sk-[\w-]{16,}', '[credencial oculta]', text)


def write_json(path, value):
    atomic_write_json(path, value)


@contextmanager
def job_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'runner.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('Outra ação do painel já está em execução.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def execute_action(action, run_id):
    """Lista fechada. Nunca executa comando, caminho ou código vindo do navegador."""
    if action not in ACTIONS or not ID.fullmatch(run_id):
        raise ValueError('Ação ou execução inválida.')
    folder = ROOT / 'data' / 'reports' / run_id
    if action == 'nova_auditoria':
        from src.main import main
        return main([], run_id=run_id), {}
    if not (folder / 'contratos.json').is_file():
        raise ValueError('A execução selecionada não tem coleta salva.')
    if action == 'retomar_auditoria':
        from src.main import main
        return main(['--retomar', run_id]), {}
    from src.batch_pipeline import execution_lock, load_records
    from src.audit_models import ParecerAuditoria
    with execution_lock(folder):
        records = load_records(folder)
        audit = ParecerAuditoria.model_validate_json((folder / 'parecer.json').read_text(encoding='utf-8'))
        if action == 'consultar_financeiro':
            from src.financial import collect_financial
            result = collect_financial(folder, records, audit)
            summary = {'contratos': result['processados'], 'consultas': len(result['consultas_fornecedores']),
                       'detalhes': result['detalhes_consultados'],
                       'conflitos': sum(v['situacao'] == 'conflito_identidade' for e in result['consultas'] for v in e['vinculos'])}
            print(f'Financeiro: {summary}. Saldos sem atribuição ao contrato; sem IA ou banco.', flush=True)
            return 0, {'financeiro': summary}
        if action == 'gerar_indicadores':
            from src.management_analytics import build_indicators
            result = build_indicators(folder)
            print(f'Indicadores pandas: {result["resumo"]}. Sem IA, rede ou banco.', flush=True)
            return 0, {'indicadores': result['resumo']}
        if action == 'consultar_pncp':
            from src.pncp import collect_pncp
            result = collect_pncp(folder, records, audit)
            summary = {'status': result['status'], 'contratos': len(result['consultas']),
                       'confirmados': sum(e['situacao'] == 'confirmado_por_regras' for e in result['consultas']),
                       'documentos_disponiveis': sum(len(e['documentos']) for e in result['consultas'])}
            print(f'PNCP: {summary}. Sem IA ou banco. Para extrair os PDFs, use Ler documentos.', flush=True)
            return (0 if result['status'] == 'concluida' else 1), {'pncp': summary}
        if action == 'conferir_suporte':
            from src.evidence_support import check_saved_review
            result = check_saved_review(folder)
            print(f'Conferência local: {len(result["itens"])} contratos; {result["contratos_com_avisos"]} com avisos para conferência humana. Sem IA ou banco.', flush=True)
            return 0, {'suporte_verificado': len(result['itens']), 'suporte_com_avisos': result['contratos_com_avisos']}
        if action == 'preparar_rag':
            from src.rag import build_index
            print('Preparando índice RAG dos textos extraídos. Sem IA ou banco.', flush=True)
            summary = build_index(folder)
            print(f'RAG pronto: {summary["trechos"]} trechos, {summary["paginas"]} páginas, {summary["contratos"]} contratos.', flush=True)
            return 0, {'rag': summary}
        if action == 'verificar_mcp':
            from src.rag_client import check_connection
            summary = check_connection(folder)
            print('MCP conectado por stdio. Ferramentas: ' + ', '.join(summary['ferramentas']), flush=True)
            return 0, {'mcp': summary}
        if action in {'planejar_documentos', 'coletar_documentos'}:
            from src.documents import DocumentSettings, plan_documents, collect_documents
            settings = DocumentSettings.from_env()
            if action == 'planejar_documentos':
                from src.pncp import read_pncp
                plan = plan_documents(records, audit, settings, pncp=read_pncp(folder))
                summary = {k: v for k, v in plan.items() if k != 'consultas'}
                print(f'Documentos: {summary["documentos"]} links em {summary["contratos"]} contratos. Sem downloads, IA ou banco.', flush=True)
                return 0, summary
            import requests
            from src.office_activity import DocumentSourceSession
            with requests.Session() as session:
                session.trust_env = False
                result = collect_documents(folder, records, audit, settings, session=DocumentSourceSession(session))
            return 0, {'status_documentos': result['status'], 'documentos_processados': result['documentos_processados']}
        if action == 'consultar_diario':
            from src.gazette import enrich_saved_audit
            enrich_saved_audit(folder, records, audit)
            result = json.loads((folder / 'diario_oficial.json').read_text(encoding='utf-8'))
            summary = {'status_diario': result['status'], 'edicoes_lidas': result['edicoes_lidas']}
            print(f'Diário: {result["status"]}; {result["edicoes_lidas"]} edições lidas.', flush=True)
            return (1 if result['status'] == 'consulta_indisponivel' else 0), summary
        from src.agent_review import ReviewSettings, build_dossiers, read_gazette, review_saved_audit, split_dossiers
        settings = ReviewSettings.from_env()
        if action == 'planejar_revisao':
            from src.agent_review import plan_saved_review
            # O adaptador Gemini do CrewAI remove o prefixo do nome do modelo.
            # Use a mesma identidade no planejamento e na execução real.
            model = os.getenv('GEMINI_MODEL', 'gemini/gemini-3.5-flash-lite').removeprefix('gemini/')
            summary = plan_saved_review(folder, records, audit, settings, model=model)
            print(f'Estimativa: {summary["contratos_reaproveitados"]} reaproveitados, {summary["contratos_pendentes"]} pendentes; até {summary["chamadas_maximas_de_etapas"]} chamadas de etapas antes de repetições. Sem IA, portal ou banco.', flush=True)
            return 0, summary
        from src.main import create_audit_llm
        has_findings = bool(audit.suspeitos)
        result = review_saved_audit(create_audit_llm() if has_findings else None, folder, records, audit, settings, incremental=True)
        if result['itens']:
            from src.evidence_support import check_saved_review
            check_saved_review(folder)
        summary = {'status_revisao': result['status'], 'contratos_revisados': len(result['itens']),
                   'total_contratos': result['total_contratos'], 'contratos_reaproveitados': result.get('contratos_reaproveitados', 0)}
        print(f'Revisão: {result["status"]}; {len(result["itens"])}/{result["total_contratos"]} contratos.', flush=True)
        return (0 if result['status'] in {'concluida', 'sem_achados'} else 1), summary


def run_job(job_id, *, jobs_root=None, operation=execute_action, monitor_cancel=True):
    jobs_root = jobs_root or ROOT / 'data' / 'ui_jobs'
    if not ID.fullmatch(job_id):
        raise ValueError('Identificador da ação inválido.')
    path = jobs_root / f'{job_id}.json'
    job = json.loads(path.read_text(encoding='utf-8'))
    if job.get('id') != job_id or job.get('action') not in ACTIONS or not ID.fullmatch(job.get('run_id', '')):
        raise ValueError('Descrição da ação inválida.')
    stop_monitor = threading.Event()
    cancel_path = jobs_root / f'{job_id}.cancel'
    def monitor():
        while not stop_monitor.wait(1):
            if cancel_path.exists():
                _thread.interrupt_main()
                return
    exit_code = 1
    try:
        with job_lock(jobs_root):
            job.update(status='em_andamento', pid=os.getpid(), started_at=now())
            write_json(path, job)
            if cancel_path.exists():
                raise KeyboardInterrupt
            if monitor_cancel:
                threading.Thread(target=monitor, daemon=True).start()
            print(f'Ação iniciada: {job["action"]}. Execução: {job["run_id"]}.', flush=True)
            def report_activity(agent, phase):
                office = job.setdefault('office', {'events': [], 'agent': None})
                if agent is not None and (not office['events'] or office['events'][-1]['agent'] != agent):
                    office['events'].append({'seq': len(office['events']) + 1, 'agent': agent, 'at': now()})
                office.update(agent=agent, phase=phase)
                write_json(path, job)
            def report_source(name, url, status):
                office = job.setdefault('office', {'events': [], 'agent': None})
                history = office.setdefault('sources', [])
                host = url.split('/')[2]
                if not history or (history[-1]['name'], history[-1]['host']) != (name, host):
                    history.append({'name': name, 'host': host, 'started_at': now(), 'requests': 0})
                    del history[:-50]
                entry = history[-1]
                entry.update(url=url, status=status, updated_at=now())
                if status == 'consultando':
                    entry['requests'] += 1
                office['source'] = dict(entry)
                write_json(path, job)
            with observe_activity(ROOT / 'data' / 'reports' / job['run_id'], report_activity, report_source):
                exit_code, summary = operation(job['action'], job['run_id'])
            stop_monitor.set()
            job['resultado'] = summary
            job['status'] = 'concluido' if exit_code == 0 else 'falhou'
            if cancel_path.exists():
                job['status'] = 'interrompido'
                exit_code = 130
    except KeyboardInterrupt:
        job.update(status='interrompido', mensagem='Interrompido pelo usuário. Checkpoints já concluídos foram preservados.')
        exit_code = 130
    except Exception as exc:
        job.update(status='falhou', mensagem=sanitize(exc))
        logging.error('%s', sanitize(exc))
    finally:
        stop_monitor.set()
        job.update(exit_code=exit_code, finished_at=now())
        write_json(path, job)
        print(f'Ação encerrada: {job["status"]}.', flush=True)
    return exit_code


def main():
    parser = argparse.ArgumentParser(description='Executor local das ações do painel')
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=False)
    logging.basicConfig(level=logging.INFO)
    os.environ.setdefault('CREWAI_STORAGE_DIR', str(ROOT / 'data' / 'ui_jobs' / 'runtime'))
    return run_job(args.job)


if __name__ == '__main__':
    raise SystemExit(main())
