-- Execute no SQL Editor do Supabase ou psql, no banco/schema da aplicação.
-- Não apaga nem altera registros. Se houver duplicados, aborta para revisão.
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';

DO $$
DECLARE
    target regclass := to_regclass('contratos_auditados');
    has_duplicates boolean;
BEGIN
    IF target IS NULL THEN
        RAISE EXCEPTION 'Tabela contratos_auditados não encontrada no search_path atual.';
    END IF;

    -- Impede novas duplicações entre a verificação e a criação da constraint.
    EXECUTE format('LOCK TABLE %s IN ACCESS EXCLUSIVE MODE', target);

    IF EXISTS (
        SELECT 1
        FROM pg_index AS i
        JOIN pg_attribute AS a
          ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
        WHERE i.indrelid = target
          AND i.indisunique AND i.indisvalid AND i.indimmediate
          AND i.indnkeyatts = 1 AND i.indpred IS NULL
          AND i.indexprs IS NULL AND a.attname = 'fingerprint'
    ) THEN
        RAISE NOTICE 'UNIQUE(fingerprint) compatível já existe; nenhuma alteração necessária.';
        RETURN;
    END IF;

    EXECUTE format(
        'SELECT EXISTS (SELECT 1 FROM %s WHERE fingerprint IS NOT NULL GROUP BY fingerprint HAVING count(*) > 1)',
        target
    ) INTO has_duplicates;

    IF has_duplicates THEN
        RAISE EXCEPTION 'Há fingerprints duplicados. Revise-os antes de criar UNIQUE; nenhum registro foi removido.';
    END IF;

    EXECUTE format(
        'ALTER TABLE %s ADD CONSTRAINT uq_contratos_auditados_fingerprint UNIQUE (fingerprint) NOT DEFERRABLE',
        target
    );
END $$;

COMMIT;
