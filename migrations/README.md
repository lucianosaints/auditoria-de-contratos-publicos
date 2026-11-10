# Correção de UNIQUE(fingerprint)

O ORM usa `UniqueConstraint("fingerprint", name="uq_contratos_auditados_fingerprint")`.
A inserção mantém `ON CONFLICT (fingerprint) DO NOTHING`: o PostgreSQL infere
o índice por coluna, não pelo nome. Constraints com outros nomes continuam
compatíveis se forem UNIQUE, imediatas e não parciais sobre fingerprint.
Uma UNIQUE composta por fingerprint e outra coluna não equivale a isso.

`create_all()` cria tabelas ausentes, mas não acrescenta constraints às existentes.
No Supabase, abra o SQL Editor no mesmo projeto/banco da aplicação e execute
o conteúdo de `001_unique_fingerprint.sql`. O script usa a tabela resolvida
pelo `search_path`; confirme antes:

```sql
SELECT current_database(), current_schema(), current_setting('search_path'),
       to_regclass('contratos_auditados');

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'contratos_auditados';

SELECT fingerprint, count(*)
FROM contratos_auditados
WHERE fingerprint IS NOT NULL
GROUP BY fingerprint
HAVING count(*) > 1;
```

Se necessário, selecione explicitamente o schema correto antes da execução,
por exemplo `SET search_path TO public;`. O script não limpa duplicados nem
recalcula hashes. Se encontrar duplicados, a migração aborta e exige revisão.
Ela usa lock exclusivo durante a criação; execute em janela sem gravações.
Timeout de lock é 10 segundos e de instrução é 60 segundos; tabelas grandes
podem exigir uma migração operacional com índice criado concorrentemente.

Depois execute novamente `python -m src.main`. `init_db()` agora verifica se
o índice compatível realmente existe antes de iniciar os agentes.
Este script não foi aplicado ao banco remoto pelo assistente.
