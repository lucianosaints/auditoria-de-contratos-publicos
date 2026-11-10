import hashlib
import json
import os
from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import CheckConstraint, Numeric, String, Text, UniqueConstraint, create_engine, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class ContratoAuditado(Base):
    __tablename__ = "contratos_auditados"
    __table_args__ = (
        CheckConstraint("situacao_auditoria IN ('Suspeito', 'Regular')"),
        UniqueConstraint("fingerprint", name="uq_contratos_auditados_fingerprint"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    numero_processo: Mapped[str | None] = mapped_column(Text)
    beneficiario: Mapped[str | None] = mapped_column(Text)
    objeto: Mapped[str | None] = mapped_column(Text)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    situacao_auditoria: Mapped[str] = mapped_column(String(20))
    motivo_suspeita: Mapped[str] = mapped_column(Text)
    # Identidade da evidência + parecer, nunca apenas número de processo.
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class ContratoParaSalvar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero_processo: str | None
    beneficiario: str | None
    objeto: str | None
    valor: Decimal | None = Field(max_digits=20, decimal_places=2, allow_inf_nan=False)
    situacao_auditoria: Literal["Suspeito", "Regular"]
    motivo_suspeita: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def evidence_fingerprint(record: dict[str, str], reason: str) -> str:
    data = json.dumps({"registro": record, "motivo": reason}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    if any(not os.getenv(key) for key in required):
        raise ValueError("Configure DB_HOST, DB_NAME, DB_USER e DB_PASSWORD no .env.")
    url = URL.create(
        "postgresql+psycopg2", username=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "5432")), database=os.environ["DB_NAME"],
        query={"sslmode": os.getenv("DB_SSLMODE", "prefer"), "connect_timeout": "10"},
    )
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def init_db(engine: Engine | None = None) -> None:
    db = engine if engine is not None else get_engine()
    Base.metadata.create_all(db)
    validar_indice_fingerprint(db)


def validar_indice_fingerprint(engine: Engine) -> None:
    """Detecta divergência de esquema existente sem alterar dados ou constraints."""
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as connection:
        valid = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_index AS i
                JOIN pg_attribute AS a
                  ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
                WHERE i.indrelid = to_regclass('contratos_auditados')
                  AND i.indisunique AND i.indisvalid AND i.indimmediate
                  AND i.indnkeyatts = 1 AND i.indpred IS NULL
                  AND i.indexprs IS NULL AND a.attname = 'fingerprint'
            )
        """)).scalar_one()
    if not valid:
        raise RuntimeError(
            "A tabela contratos_auditados não possui índice UNIQUE não parcial "
            "e imediato sobre fingerprint. create_all() não migra tabelas existentes. "
            "Execute migrations/001_unique_fingerprint.sql no mesmo banco e schema "
            "da aplicação. Nenhum dado foi removido."
        )


def salvar_contratos(contratos: list[ContratoParaSalvar], engine: Engine | None = None) -> dict[str, int]:
    db = engine if engine is not None else get_engine()
    inserted = 0
    # Um lote é uma transação: falha implica rollback integral.
    with Session(db) as session, session.begin():
        for contrato in contratos:
            statement = insert(ContratoAuditado).values(**contrato.model_dump()).on_conflict_do_nothing(
                # Inferência por coluna: aceita qualquer nome de constraint/index
                # UNIQUE equivalente, inclusive de tabelas antigas.
                index_elements=[ContratoAuditado.fingerprint]
            ).returning(ContratoAuditado.id)
            if session.execute(statement).scalar_one_or_none() is not None:
                inserted += 1
    return {"recebidos": len(contratos), "inseridos": inserted, "ja_existentes": len(contratos) - inserted}
