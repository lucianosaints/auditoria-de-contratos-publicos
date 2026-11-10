# Fase 2 — coleta e triagem de contratos

Execute os comandos na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Execute somente se ainda não tiver .env:
Copy-Item .env.example .env
```

Edite `.env`:

```dotenv
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=openai/gpt-4o-mini
```

```powershell
.\.venv\Scripts\python.exe -m src.main
```

Usa o LLM nativo do CrewAI com temperatura zero, sem precisar de ChatOpenAI.
O coletor possui exclusivamente a ferramenta HTTP existente; o auditor não
possui ferramentas nem delegação. A execução é sequencial com contexto
explícito da coleta para a auditoria. `result_as_answer=True` preserva o retorno
da ferramenta. Um guardrail valida a lista JSON de dicionários textuais antes
de passar ao auditor, mantendo chaves, valores e ordem dos registros. Mensagens
de erro textuais da ferramenta interrompem o fluxo, sem relatório de sucesso.

Saídas em `data/reports/<execução>/`:

- `contratos.json`: dados validados da coleta.
- `relatorio.md`: parecer preliminar em Markdown.

A ferramenta de extração foi preservada. Sua versão atual fixa o exercício
em 2026 e limita a amostra aos primeiros cinco resultados. O relatório deve
reconhecer esses limites; não se validou ordenação por recência. A extração
atual retorna texto para tabela vazia, que será tratado como falha; para
representar ausência de contratos como sucesso, ela deverá retornar `[]`.

O auditor identifica hipóteses para diligência. Não calcula sobrepreço nem
comprova fracionamento sem os dados adicionais necessários. Revise o relatório
antes de utilizá-lo externamente. As chamadas ao modelo enviam o JSON coletado
ao provedor configurado.

O novo `src.main` substitui a entrada CLI antiga de Playwright; seus antigos
argumentos de coleta não se aplicam a esta fase. Arquivos do scraper antigo
permanecem disponíveis, mas não são usados nesta execução.
