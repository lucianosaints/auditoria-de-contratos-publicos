import unittest
from unittest.mock import MagicMock

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.schema import CreateTable

from src.database import ContratoAuditado, validar_indice_fingerprint


class DatabaseConstraintTests(unittest.TestCase):
    def test_model_unique_matches_insert_target(self):
        constraints = [c for c in ContratoAuditado.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertEqual(len(constraints), 1)
        self.assertEqual(list(constraints[0].columns.keys()), ["fingerprint"])
        self.assertEqual(constraints[0].name, "uq_contratos_auditados_fingerprint")
        ddl = str(CreateTable(ContratoAuditado.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn("CONSTRAINT uq_contratos_auditados_fingerprint UNIQUE (fingerprint)", ddl)
        statement = insert(ContratoAuditado).values(fingerprint="a" * 64).on_conflict_do_nothing(
            index_elements=[ContratoAuditado.fingerprint]
        )
        self.assertIn("ON CONFLICT (fingerprint) DO NOTHING", str(statement.compile(dialect=postgresql.dialect())))

    def test_existing_schema_missing_index_has_actionable_error(self):
        engine = MagicMock()
        engine.dialect.name = "postgresql"
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.scalar_one.return_value = False
        with self.assertRaisesRegex(RuntimeError, "001_unique_fingerprint.sql"):
            validar_indice_fingerprint(engine)
        connection.execute.return_value.scalar_one.return_value = True
        validar_indice_fingerprint(engine)

    def test_other_dialect_does_not_query_postgres_catalog(self):
        engine = MagicMock()
        engine.dialect.name = "sqlite"
        validar_indice_fingerprint(engine)
        engine.connect.assert_not_called()
