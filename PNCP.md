# PNCP: reconciliação e documentos oficiais

Implementação inicial em 21/10/2026. Não usa IA ou banco.

## Retomada seletiva e PDFs grandes — 23/10/2026

Retomada REAL concluída: linha 60, contrato 403/2026, 13.116.015 bytes e 17
páginas; linha 280, contrato 299/2026, 12.415.084 bytes e 16 páginas. Ambas
receberam extração de todas as páginas, sem avisos do extrator. Primeira,
intermediária e última páginas de cada PDF foram conferidas visualmente:
instrumentos com cláusulas e assinaturas, sujeitos a erros de OCR e cortes
laterais da digitalização. Não houve validação integral do conteúdo.

Preservados os 214 outros documentos, os PDFs anteriores e nove artefatos
principais por comparação de hashes/metadados. RAG reconstruído: 2.995 trechos,
470 pares contrato/página, 94 contratos; não são 470 páginas físicas únicas.
MCP stdio real recuperou trechos dos dois PDFs com página/hash. Indicadores
regenerados com histórico: 22 linhas com PDF publicado extraído, 72 com fichas
ou tipo não validado e 356 não processadas. Sem nova auditoria ou revisão IA.

O padrão permanece 10 MB por PDF. `DOCUMENT_MAX_MB` permite limite explícito
de 1 a 50 MB; limites inválidos são recusados antes de consultar a rede. O
download confere o tamanho declarado e a quantidade efetivamente recebida.
A mensagem informa o limite aplicado. O `.env` real não foi modificado.

É possível retomar IDs específicos sem reextrair os outros documentos:

```powershell
python -m src.documents --execucao 20261020T015002Z_72b23869 --documento ID_DO_DOCUMENTO --max-mb 50
```

Repita `--documento` para selecionar mais de um ID. A retomada exige manifesto
anterior compatível com registros e links atuais e verifica os hashes dos PDFs
preservados. Mantém os demais documentos inclusive em caso de interrupção,
arquiva o manifesto anterior e registra IDs, limites e contagem preservada.
Não altera a triagem, revisão dos agentes ou banco. Após mudança nas fontes,
reconstrua o RAG; a revisão antiga permanece preservada e pode ficar oculta
por incompatibilidade de contexto. Não inicia nova revisão Gemini.

O script `frontend/scripts/verify_large_pncp_documents.py` descreve o recorte
sem rede por padrão. `--real` retoma somente os dois IDs pendentes das linhas
60 e 280, com até 50 MB e 30 páginas por PDF, OCR local e preservação dos demais
documentos; também arquiva/reconstrói o RAG. Prova em
`data/raw/large_pncp_20261023/verificacao.json`. Extração concluída não certifica
integralidade, identidade documental ou correção de todas as páginas.

## Uso no painel

Reabra `iniciar_painel.bat` para carregar a nova ação. Selecione uma execução local com parecer e clique **Consultar PNCP**. A ação consulta o catálogo público e identifica candidatos para os contratos com achados. Mostra os registros comparados nos detalhes de cada contrato.

Depois use **Planejar documentos → Ler documentos → Preparar RAG → Verificar MCP**. A leitura prioriza PDFs PNCP com vínculo confirmado e inclui os anexos municipais inventariados. A presença de um link não significa download ou leitura. **Revisar com agentes** continua sendo uma ação separada, que usa a IA configurada. A integração não inicia essa revisão automaticamente.

As fontes novas tornam o índice anterior desatualizado até Preparar RAG. A revisão antiga permanece salva e pode ficar oculta no painel por incompatibilidade documental. Isso não significa falha ou perda da auditoria anterior.

## Correspondência entre fontes

O vínculo automático exige candidato único, número e ano do contrato, CNPJ do fornecedor e processo coincidentes. Valores iniciais e assinaturas, quando comparáveis, não podem divergir. O identificador PNCP também deve corresponder ao CNPJ, ano e sequencial retornados. Não usa similaridade textual para confirmar identidade. Não compara o valor global atual a um valor inicial como se fossem o mesmo campo.

Resultados possíveis:

- **Confirmado por regras:** apto à consulta de anexos, sujeito a conferência humana.
- **Candidato:** identificadores incompletos ou mais de um candidato; sem download automático.
- **Conflitante:** há diferenças entre os candidatos comparados. Podem ser contratos distintos que compartilham número ou processo; não representa irregularidade nem identidade estabelecida.
- **Não localizado no recorte:** catálogo paginado concluído sem candidato pelos identificadores disponíveis.
- **Consulta incompleta:** falha ou limite de paginação; ausência de resultado não é interpretada como ausência de publicação.

Neste estágio não há confirmação manual de candidatos no painel, descoberta automática em outras entidades, inventário dos termos aditivos nem consulta adicional dos documentos da licitação. A lista do contrato pode referenciar documentos da compra associada; esses links são validados pela identidade dessa compra.

## Cobertura e limites

CNPJ consultado: **29.131.075/0001-93 — Município de Maricá**. Não abrange automaticamente autarquias, empresas municipais ou outros CNPJs. O intervalo vai de 1º de janeiro do menor ano dos contratos selecionados à data da consulta em São Paulo. O filtro da API é **data de publicação**, não assinatura nem vigência. Publicações fora desse intervalo não são cobertas.

Paginação: 500 registros/página e limite de 20 páginas. Totais inconsistentes, identificadores repetidos, órgão diferente e páginas vazias prematuras produzem consulta incompleta. Uma busca completa no recorte não comprova completude de todos os dados do Município.

Cache JSON por URL/parâmetros, integridade SHA-256 e validade de até 24h. Respostas inválidas não são reutilizadas. As requisições têm timeout, limite de 8 MB, até duas repetições para alguns erros transitórios e não seguem redirecionamentos. A lista de anexos é limitada a 20 documentos por contrato, com omissões explícitas.

Downloads admitem somente HTTPS municipal autorizado ou rotas estritas de arquivos no domínio `pncp.gov.br`, conferidas contra contrato/compra. HTML, outros formatos e redirecionamentos externos não são processados como PDF. Permanecem os limites de **10 MB/PDF, 30 páginas/PDF e 5 links/contrato**. O limite padrão total passou a **300 PDFs por ação** para comportar a combinação portal/PNCP; um `DOCUMENT_MAX_TOTAL` explicitamente configurado continua prevalecendo. O `.env` existente não foi alterado. Limites atingidos ficam explícitos, sem presunção de leitura integral.

O tipo informado pelo PNCP é metadado da fonte. A classificação local continua distinguindo ficha cadastral de PDF publicado; não certifica automaticamente que todo documento é um instrumento integral. OCR e tabelas exigem conferência visual.

## Artefatos e preservação

- `pncp.json`: vínculos, identificadores comparados, diferenças, recorte e inventário de anexos.
- `pncp/cache/`: respostas públicas, parâmetros, data e hash.
- `pncp/catalogo_<hash>.json`: catálogo recebido e cobertura.
- `pncp/historico/`: versões anteriores da reconciliação.
- `documentos/historico/`: versões anteriores do manifesto antes de nova leitura.
- `documentos.json`, PDFs e extrações: fluxo documental existente, com origem PNCP e identificador correspondente.

As publicações JSON usam a gravação atômica comum. Coleta, parecer, recibo e revisão dos agentes não são reescritos pela consulta PNCP nem pela leitura documental. Arquivos originais já baixados são reutilizados após verificação do hash; a política de extração também é considerada pelo cache.

CLI alternativa, na raiz:

```powershell
python -m src.pncp --execucao 20261020T015002Z_72b23869
```

## Fontes oficiais verificadas

- [Esquema atual da API de consulta](https://pncp.gov.br/api/consulta/v3/api-docs): `GET /v1/contratos`, parâmetros `cnpjOrgao`, `dataInicial`, `dataFinal`, `pagina`, `tamanhoPagina`.
- [Consulta de documentos de contrato](https://pncp.gov.br/manual/pt-br/latest/contrato_empenho/consultar_todos_os_documentos_de_um_contrato_ou_empenho.html): lista e metadados dos anexos.
- [Consulta de contrato por identificador](https://pncp.gov.br/manual/pt-br/latest/contrato_empenho/consultar_contrato_ou_empenho.html).

O esquema e uma resposta reais foram salvos em `data/raw/pncp_verificacao_20261021/`. O script `frontend/scripts/verify_pncp.py` verifica arquivos locais por padrão; `--real` consulta a API pública. A verificação de PDFs está em `frontend/scripts/verify_pncp_documents.py` e usa rede. Ambos foram preparados para a execução principal indicada acima, sem IA/banco.

## Resultado real desta entrega

Na execução `20261020T015002Z_72b23869`, o recorte de 01/01/2026 a 21/10/2026 retornou 577 registros em duas páginas. Para os 94 contratos com achados: 22 vínculos confirmados por regras, 62 com diferenças entre candidatos, três candidatos e sete não localizados no recorte. Não se validou o mérito dessas diferenças.

Os 22 vínculos disponibilizaram 21 PDFs únicos. Destes, 18 receberam extração concluída, um recebeu leitura parcial e dois excederam 10 MB (linhas 60 e 280). Os 19 PDFs extraídos forneceram 223 páginas. A leitura parcial da linha 274 tem aviso de conferência de imagem na página 10.

O conjunto documental agora tem 216 IDs únicos, incluindo os dois downloads pendentes. O RAG reúne 2.838 trechos e 437 pares contrato/página, em 94 contratos. Essa contagem inclui páginas de um mesmo PDF associadas a linhas diferentes e não representa 437 páginas físicas únicas. O MCP real recuperou trechos PNCP da linha 31 com origem, página e hash do original.

Foi conferida visualmente uma amostra de instrumento contratual de dez páginas (primeira, segunda e última páginas). Essa amostra não valida o conteúdo de todos os documentos nem a associação de todos os candidatos. Os PDFs novos continuam classificados como `pdf_publicado`, sem certificação automática de integralidade.

Foram preservados por comparação de hashes coleta, parecer, relatório, revisão, recibo, conferência de suporte e todos os PDFs anteriores. O manifesto anterior e índice anterior foram arquivados. Nenhuma revisão Gemini foi iniciada nesta entrega. Validação: 141 testes Python, 39 testes frontend, build e QA Playwright desktop/mobile; MCP real verificado sem IA ou rede externa.
