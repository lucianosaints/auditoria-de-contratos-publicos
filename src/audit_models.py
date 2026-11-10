from pydantic import BaseModel, ConfigDict, Field


class Achado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # A ferramenta descarta índices fora da base, sem invalidar os demais achados.
    linha: int = Field(strict=True, description="Posição base 1 em contratos.json; índices inválidos serão ignorados.")
    motivo_suspeita: str = Field(min_length=1)


class ParecerAuditoria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    linhas_analisadas: list[int]
    suspeitos: list[Achado]
    relatorio_markdown: str = Field(min_length=1)
