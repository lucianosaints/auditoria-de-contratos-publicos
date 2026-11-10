import logging
import argparse
import os
import re
from datetime import datetime, timezone
from uuid import uuid4

from crewai import LLM
from dotenv import load_dotenv
from src.config import ROOT
from src.batch_pipeline import AuditValidationError, BatchSettings, find_pending, is_quota_error, load_records, run_pipeline, split_batches
from src.database import init_db


def create_audit_llm():
    # O modelo selecionado no Codex não altera o provedor do aplicativo.
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        raise ValueError('Configure GEMINI_API_KEY no arquivo .env.')
    return LLM(model=os.getenv('GEMINI_MODEL', 'gemini/gemini-3.5-flash-lite'),
               api_key=api_key, temperature=0, timeout=120)


def main(argv=None, *, run_id=None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Auditoria Cidadã — análise em lotes')
    parser.add_argument('--retomar', nargs='?', const='latest', metavar='EXECUCAO',
                        help='Reutiliza a coleta pendente mais recente ou o ID informado.')
    parser.add_argument('--planejar', action='store_true', help='Mostra os lotes de uma coleta salva sem chamar Gemini ou banco.')
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env", override=False)
    output_dir = None
    try:
        settings = BatchSettings.from_env()
        if args.retomar or args.planejar:
            if args.retomar in (None, 'latest'):
                output_dir = find_pending(ROOT / 'data' / 'reports')
            else:
                output_dir = (ROOT / 'data' / 'reports' / args.retomar).resolve()
                if output_dir.parent != (ROOT / 'data' / 'reports').resolve():
                    raise ValueError('Informe somente o ID de uma execução em data/reports.')
            records = load_records(output_dir)
            batches = split_batches(records, settings)
            logging.info('Coleta salva: %s; %d contratos em %d lotes.', output_dir.name, len(records), len(batches))
            if args.planejar:
                print(f'Planejamento local: {len(records)} contratos, {len(batches)} lotes; máximo {settings.max_records} registros e {settings.max_bytes} bytes por lote.')
                print(f'Intervalo: {settings.interval_seconds:g}s; aproximadamente {max(0, len(batches)-1)*settings.interval_seconds/60:.0f} minutos só em pausas, além da análise. Checkpoints concluídos são reutilizados.')
                print('Nenhuma chamada ao Gemini, portal ou banco foi realizada.')
                return 0
        else:
            run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
            if not re.fullmatch(r'\d{8}T\d{6}Z_[a-f0-9]{8}', run_id):
                raise ValueError('ID de nova execução inválido.')
            output_dir = ROOT / 'data' / 'reports' / run_id
            if output_dir.exists():
                raise ValueError('Esta execução já existe; use retomar para continuar.')
    except (ValueError, OSError) as exc:
        logging.error('Não foi possível preparar a execução: %s', exc)
        return 1
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logging.error("Configure GEMINI_API_KEY no arquivo .env.")
        return 1
    try:
        init_db()
        llm = create_audit_llm()
        result = run_pipeline(llm, output_dir, settings, resume=bool(args.retomar))
        print((output_dir / "relatorio.md").read_text(encoding="utf-8"))
        print(result)
        print(f"\nArquivos da execução: {output_dir}")
        return 0
    except KeyboardInterrupt:
        logging.error('Execução interrompida pelo usuário. Use retomar_auditoria.bat para continuar os lotes salvos.')
        return 130
    except Exception as exc:
        if isinstance(exc, AuditValidationError):
            logging.error('%s', exc)
        elif is_quota_error(exc):
            logging.error('Gemini atingiu a cota de uso. Os lotes concluídos foram preservados. Aguarde e use retomar_auditoria.bat. Consulte a cota ativa no Google AI Studio.')
        else:
            logging.exception("Execução interrompida. Não foi possível concluir a auditoria.")
        logging.error('Arquivos preservados em: %s', output_dir)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
