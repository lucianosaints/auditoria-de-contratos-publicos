import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any
from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr
from src.audit_models import ParecerAuditoria
from src.database import ContratoParaSalvar, evidence_fingerprint, salvar_contratos
from src.tasks.collect_contracts import ContractBatch

def normalized(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold().split())

def field(record: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    matches = [v.strip() for k, v in record.items() if normalized(k) in aliases]
    if len(matches) > 1:
        raise ValueError(f"Colunas ambíguas para {aliases[0]}")
    return (matches[0] or None) if matches else None

def parse_brl(value: str | None) -> Decimal | None:
    if value is None or value.strip() in {"", "-", "—"}:
        return None
    # Aceita moeda brasileira e o decimal com ponto usado na integração.
    clean = value.replace("R$", "").replace("\xa0", "").replace(" ", "").strip()
    
    if "," in clean:
        if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:\.\d{3})+),\d{2}", clean):
            raise ValueError(f"Valor monetário não pôde ser convertido: {value}")
        clean = clean.replace(".", "").replace(",", ".")
    elif not re.fullmatch(r"-?\d+(?:\.\d{2})?", clean):
        raise ValueError(f"Valor monetário inválido ou ambíguo: {value}")
    return Decimal(clean)

def prepare_records(
    records: list[dict[str, str]],
    audit: ParecerAuditoria,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[ContratoParaSalvar]:
    warnings = diagnostics if diagnostics is not None else []
    expected = set(range(1, len(records) + 1))
    analyzed = set(audit.linhas_analisadas)
    if analyzed != expected or len(audit.linhas_analisadas) != len(analyzed):
        warnings.append({
            "tipo": "cobertura_incompleta_ou_inconsistente",
            "linhas_na_coleta": len(records),
            "linhas_nao_declaradas": sorted(expected - analyzed),
            "indices_analisados_fora_da_base": sorted(analyzed - expected),
            "mensagem": "Cobertura declarada não bloqueia o salvamento dos suspeitos localizáveis.",
        })
    # Nunca desloca, limita ou converte automaticamente a base dos índices:
    # isso poderia atribuir a suspeita a outro contrato.
    grouped: dict[int, list[str]] = {}
    for finding in audit.suspeitos:
        if finding.linha not in expected:
            warnings.append({
                "tipo": "indice_fora_da_base", "linha": finding.linha,
                "motivo_suspeita": finding.motivo_suspeita,
                "mensagem": "Achado ignorado: não existe posição base 1 correspondente na coleta.",
            })
            continue
        reasons = grouped.setdefault(finding.linha, [])
        reason = finding.motivo_suspeita.strip()
        if reason and reason not in reasons:
            reasons.append(reason)

    result = []
    for line, reasons in grouped.items():
        if not reasons:
            warnings.append({"tipo": "motivo_vazio", "linha": line, "mensagem": "Achado ignorado: motivo sem conteúdo."})
            continue
        record = records[line - 1]
        reason = "\n".join(reasons)
        result.append(ContratoParaSalvar(
            # Adicionado o mapeamento exato "nr [nr processo]"
            numero_processo=field(record, ("numero do processo", "nr processo", "nº processo", "processo", "nr [nr processo]")),
            beneficiario=field(record, ("nome do beneficiario", "beneficiario", "fornecedor", "contratado")),
            objeto=field(record, ("objeto", "objeto do contrato")),
            valor=parse_brl(field(record, ("valor do contrato", "valor contratado", "valor"))),
            situacao_auditoria="Suspeito", 
            motivo_suspeita=reason,
            fingerprint=evidence_fingerprint(record, reason),
        ))
    return result

class ArchiveInput(BaseModel):
    """Sem argumentos: lê os artefatos desta execução."""

class ArquivarContratosTool(BaseTool):
    name: str = "arquivar_contratos_suspeitos"
    description: str = "Salva os suspeitos do parecer validado no PostgreSQL. Chame sem argumentos."
    args_schema: type[BaseModel] = ArchiveInput
    output_dir: Path
    _receipt: dict[str, Any] | None = PrivateAttr(default=None)

    def _run(self) -> str:
        if self._receipt is not None:
            return json.dumps(self._receipt, ensure_ascii=False)
        try:
            records = ContractBatch.model_validate_json((self.output_dir / "contratos.json").read_text(encoding="utf-8")).root
            audit = ParecerAuditoria.model_validate_json((self.output_dir / "parecer.json").read_text(encoding="utf-8"))
            warnings: list[dict[str, Any]] = []
            prepared = prepare_records(records, audit, warnings)
            # Sem correspondências, não abre uma conexão nem anuncia inserções.
            counters = salvar_contratos(prepared) if prepared else {
                "recebidos": 0, "inseridos": 0, "ja_existentes": 0,
            }
            ignored = sum(w["tipo"] in {"indice_fora_da_base", "motivo_vazio"} for w in warnings)
            self._receipt = {
                "ok": True, **counters,
                "status": "concluido_com_avisos" if warnings else "concluido",
                "suspeitos_no_parecer": len(audit.suspeitos),
                "contratos_localizados": len(prepared),
                "ignorados": ignored,
                "avisos": warnings,
            }
            return json.dumps(self._receipt, ensure_ascii=False)
        except Exception as e:
            # Mostramos o erro real no log para não ficarmos no escuro
            raise RuntimeError(f"Arquivamento falhou. Motivo técnico: {str(e)}") from None

    def validate_receipt(self, output: Any) -> tuple[bool, Any]:
        if self._receipt is None:
            return False, "Execute a ferramenta; não invente confirmação de gravação."
        return True, json.dumps(self._receipt, ensure_ascii=False)
