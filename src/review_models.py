"""Saídas fechadas para investigação/revisão com citações por fonte."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2500)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Citation(StrictModel):
    fonte_id: Text
    # O validador contextual exige >=8 para prosa; campos escalares completos
    # (ex.: R$ 0,00) podem ser menores somente por igualdade com a fonte indicada.
    trecho: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=700)]


class InvestigationItem(StrictModel):
    linha: int = Field(strict=True, ge=1)
    observacao: Text
    limite: Text
    evidencias: list[Citation] = Field(min_length=1, max_length=8)


class Investigation(StrictModel):
    itens: list[InvestigationItem]


class ReviewItem(StrictModel):
    linha: int = Field(strict=True, ge=1)
    situacao: Literal['contextualizado', 'necessita_documentos', 'rever_alerta']
    explicacao_simples: Text
    limite: Text
    proxima_diligencia: Text
    evidencias: list[Citation] = Field(min_length=1, max_length=8)


class Review(StrictModel):
    itens: list[ReviewItem]


class CitationChoice(StrictModel):
    citacao_id: Text


class InvestigationChoiceItem(InvestigationItem):
    evidencias: list[CitationChoice] = Field(min_length=1, max_length=8)


class InvestigationChoices(StrictModel):
    itens: list[InvestigationChoiceItem]


class ReviewChoiceItem(ReviewItem):
    evidencias: list[CitationChoice] = Field(min_length=1, max_length=8)


class ReviewChoices(StrictModel):
    itens: list[ReviewChoiceItem]
