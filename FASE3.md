# Fase 3 — coleta completa, parecer estruturado e PostgreSQL

## PDFs grandes e retomada seletiva — 23/10/2026

`DOCUMENT_MAX_MB` mantém padrão 10 e admite 1..50 MB por PDF, com verificação
do cabeçalho e do fluxo recebido. `.env` real preservado. Para retomar apenas
IDs escolhidos, use `python -m src.documents --execucao ID --documento SHA_ID
--max-mb 50` (comando em uma linha). Repita `--documento` para outros IDs.
Exige manifesto compatível e PDFs preservados íntegros; não chama IA/banco.
Reconstrua RAG e indicadores após alteração documental. Procedimento e
resultado real das linhas 60/280 em PNCP.md.

## Consulta financeira limitada

A política de identidade 2 confere também processo e referências de contrato
no resumo, além do CNPJ da consulta quando disponível. Divergências rejeitam
saldos mesmo que o número do empenho coincida. A linha 96 foi rejeitada por
processo divergente; a 175 permanece pendente. Veja EXECUCAO_FINANCEIRA.md.

**Consultar financeiro** no painel consulta até 10 combinações CNPJ/exercício
e 30 detalhes de empenhos para contratos com alertas, sem IA/banco. Confere
filtros e número/ano; conflitos são rejeitados e saldos compatíveis continuam
pendentes de vínculo ao contrato. Há cache, histórico, progresso e interrupção.
Artefato separado `financeiro.json`, ocultado quando fontes mudam. A execução
principal já recebeu consulta real limitada; não repetir auditoria ou revisão.
Não calcula gasto por contrato. Consulte [EXECUCAO_FINANCEIRA.md](EXECUCAO_FINANCEIRA.md).

O caderno local `data/avaliacao_humana_caderno_20261021/avaliar.html` prepara
os 40 casos para decisão humana e exporta referência para o avaliador. Não
preenche decisões nem calcula precisão sem avaliações. Uso e limites em
[QUALIDADE_ANALITICA.md](QUALIDADE_ANALITICA.md).

Gravações de progresso/checkpoints/estado do executor e conferência de suporte
usam publicação atômica com temporário exclusivo e tentativas limitadas para
bloqueios transitórios de arquivos no Windows. Falha permanente preserva o
JSON anterior. O painel identifica WinError de gravação separadamente de
rejeições da IA. Estimar revisão usa a identidade do modelo normalizada pelo
adaptador Gemini, compatível com os checkpoints reais.

## Retomada da revisão por contrato

No painel, **Revisar com agentes** reaproveita cada contrato com contexto,
modelo e procedimentos compatíveis. **Estimar revisão** informa quantos
serão reaproveitados e quantos exigem novas etapas. A primeira revisão com
PDFs/RAG pode reanalisar todos os contratos que ganharam contexto; chamadas
não são dispensadas apenas porque uma revisão anterior foi concluída.

Checkpoints individuais ficam em `agentes/por_contrato/<linha>.json`, com
assinatura do dossiê, modelo, skills e política, e saídas de investigação e
revisão novamente validadas ao recuperar. Alterar só um contrato reprocessa
somente ele; mudar modelo/procedimentos pode afetar todos. O hash global do
índice RAG é excluído da comparação individual, mantendo fontes, trechos,
consulta, limites e assinatura documental da própria linha.

Checkpoints legados só alimentam o cache individual após conferir a assinatura
do lote completo e validar ambas as etapas. As políticas anteriores são uma
lista explícita; assinatura desconhecida não é aceita. Novos lotes ficam em
`agentes/incremental/<assinatura>/`, preservando os lotes originais. Resultados
anteriores são copiados para `agentes/historico/<hash>/` antes da publicação da
nova revisão. A revisão direta em Python mantém o modo legado, salvo chamada
programática com `incremental=True`; o painel usa o novo modo automaticamente.

Testes confirmam zero IA em retomada sem mudanças, envio de só uma linha
alterada, rejeição de citação/cache legado adulterados, migração de lote
validado e preservação de histórico. Não há paralelismo de chamadas Gemini;
os intervalos de cota continuam respeitados.

## Fontes citadas e conferência de suporte

O painel apresenta por contrato a quantidade de campos do portal, fontes e
páginas do Diário, PDFs/páginas citados e uso registrado de RAG/MCP. Fontes
citadas não equivalem à leitura integral. Inventário atual e pendências são
mostrados separadamente, com avisos de OCR e ficha cadastral quando citados.

**Conferir suporte** aplica regras locais à explicação da revisão salva e às
citações. Sinaliza ausência de repasse/ônus sem apoio explícito nas citações,
possível confusão entre dívida e quitação, conclusões jurídicas categóricas e
citações incompatíveis. Trata negação e linguagem condicional em padrões
conhecidos; não faz validação semântica completa. **Nenhum alerta nas regras
verificadas** não significa conclusão confirmada. Falsos positivos/negativos
continuam possíveis; os avisos pedem conferência humana, não mudam a classificação.

Saída separada: `verificacao_evidencias.json`, com hash da revisão, instante,
avisos por linha e cópia do item original para vincular a conferência à versão
correta. A apresentação descarta conferência de outro item/data da revisão;
mudanças nas fontes/coleta/alertas continuam sujeitas à compatibilidade da revisão.
Importação opcional desse JSON é suportada junto aos arquivos da auditoria.
A ação integra o executor local (origem/token, seleção explícita, bloqueio de
concorrência), sem IA ou banco. Revisar com agentes no painel a executa ao final.
O comando direto de revisão em Python não gera essa conferência automaticamente;
nesse caso, use o botão depois. A auditoria, revisão, relatório e checkpoints
originais não são reescritos pela conferência local.

Em 21/10/2026, a conferência dos 94 itens reais produziu avisos em 13 linhas:
17, 75, 84, 257, 284, 293, 312, 383, 409, 422, 432, 440 e 450. São candidatos
à conferência humana, sem nova conclusão de irregularidade. Prova local em
`data/raw/suporte_verificacao/verificacao.json`, originais preservados e zero IA.
Passaram 120 testes Python, 36 Node/frontend, build e QA visual desktop/mobile.

## RAG e MCP local

O painel agora inclui Preparar RAG, Verificar MCP e busca de evidências por
contrato. Após Ler documentos, prepare o índice: os agentes consultarão os
trechos por MCP stdio antes de montar os dossiês. Sem índice, permanece a
leitura inicial anterior. Busca BM25 local, sem embeddings ou novas chamadas
de IA para indexar/pesquisar. Veja [RAG_MCP.md](RAG_MCP.md) para arquitetura,
limites, cliente externo opcional e verificações realizadas.

## Citações por catálogo — revisão dos especialistas

Para evitar cópias longas, moeda reformatada e IDs de fonte incorretos, os
especialistas selecionam `citacao_id` de um catálogo gerado pelo Python. Cada
trecho tem no máximo 700 caracteres e é uma substring literal da mesma fonte
e linha. Fontes longas são divididas com sobreposição de 100 caracteres, sem
unir partes afastadas. Campos curtos entram somente completos e não truncados.
O catálogo do revisor contém exclusivamente citações aceitas na investigação.

O Python resolve a seleção para `fonte_id`/`trecho` e aplica novamente a
validação de cobertura, fonte e literalidade. O formato publicado no painel
e nos checkpoints é preservado. IDs inventados/de outra linha, texto extra
em uma seleção e referência não aprovada pelo investigador são rejeitados.
O catálogo garante a correspondência ao trecho, não a interpretação da IA.

A política de revisão imediatamente anterior tem migração explícita:
assinatura exata dos mesmos dossiês/modelo/skills e saída revalidada permitem
reaproveitar as duas etapas já concluídas do primeiro lote, sem novas chamadas.
Políticas desconhecidas ou fontes/modelo/skills diferentes não são migradas.
O procedimento foi conferido em cópia dos checkpoints reais, sem modificar
os originais. A auditoria base e o arquivamento não precisam ser repetidos.

Teste real autorizado em 20/10/2026: as cinco linhas do segundo lote
(43,46,48,57,60) concluíram investigação e revisão com o catálogo, sem
rejeições/repetições. Teste isolado em
`data/raw/agent_catalogo_20261021T012102Z/`, com duas chamadas de etapas.
O lote 1 copiado recuperou duas etapas sem IA, com hashes dos originais
intactos. Os cinco resultados reais passaram na validação frontend.
Esse ensaio não foi publicado como checkpoint da auditoria principal.
Validação local: 108 testes Python, 32 Node/frontend e build.

## Respostas JSON dos especialistas — correção de formato

Respostas podem vir como JSON puro ou um único bloco Markdown ```json. O
parser aceita esse envelope sem alterar os valores, aplicando depois a mesma
validação estrutural, cobertura e citações. Texto externo, vários objetos e
chaves duplicadas são rejeitados. A resposta bruta permanece preservada nos
diagnósticos; a interface diferencia falha de formato JSON das demais falhas.

A correção foi conferida com as duas respostas reais da tentativa de
20/10/2026 às 21h56, sem nova chamada à IA: leitura e validação passaram para
os cinco contratos do lote. A etapa do revisor ainda requer execução. Passaram
104 testes Python, 32 Node/frontend e build.

## Correção da revisão de valores curtos — 20/10/2026

Corrigida a falha repetida do primeiro lote dos especialistas: `R$ 0.00` tem
sete caracteres e era rejeitado pela exigência geral de oito. O esquema de
transporte recebe 1..700 caracteres; `validate_stage` exige 8..700 para prosa
e permite menos somente quando a citação é o **valor inteiro de um campo do
portal não truncado**, com igualdade literal à fonte da mesma linha.
Ponto/vírgula não são normalizados. Fragmentos curtos, documentos/Diário,
citações inventadas e fontes de outra linha permanecem rejeitados. O revisor
continua limitado aos pares fonte/trecho aceitos pelo investigador.

Os especialistas retornam JSON bruto com esquema explícito no prompt; a
validação é executada em Python, preservando a resposta rejeitada antes de
uma tentativa adicional. Isso evita que a conversão estruturada do CrewAI
interrompa a etapa antes da captura do texto. Feedback usa exemplos exatos
do lote atual e não modifica respostas para forçar aceitação. Modelo,
intervalos e checkpoints base continuam preservados; a política da revisão
adicional mudou para invalidar saídas incompatíveis.

Validado com 100 testes da suíte Python e um teste adicional de transporte
CrewAI com chamada do provedor substituída, 32 Node/frontend e build. Ensaio
local dos cinco contratos do primeiro lote (linhas 6, 17, 31, 40, 41) concluiu
as duas etapas com respostas simuladas: valores monetários completos aceitos,
respostas antigas não literais ainda rejeitadas e hashes dos quatro arquivos
originais preservados. Prova em `data/raw/agent_citacoes_20261021T004943Z/`.
Não foi executada nova revisão real do Gemini nesse ensaio.

## Andamento visível — 20/10/2026

O destaque antes dos botões informa se há ação ativa, contadores de lotes ou
documentos, etapa da revisão, tempo decorrido e último horário de verificação.
Pausas entre chamadas/cota têm contagem regressiva; o tempo total de término
não é prometido. Falha de conexão é diferenciada de processo encerrado.
Auditoria base concluída e revisão adicional interrompida aparecem separadas,
com motivo resumido e horário de término. Logs completos continuam expansíveis.

As fases são gravadas antes da chamada/espera em progresso.json ou
revisao_agentes.json. A instrumentação não modifica os prompts/validadores da
auditoria. Verificação: 96 testes Python, 31 frontend/Node, build e UI
desktop/mobile simulando parada e atualização automática sem IA/banco.

## Dossiês de PDFs e revisão humana — 20/10/2026

Primeira entrega do plano em `PESQUISA_EVOLUCAO_AUDITORIA.md`. No painel:

1. Selecione uma execução local com parecer e clique **Planejar documentos**.
   Conta links já inventariados dos contratos com achados, sem download/IA/banco.
2. Clique **Ler documentos**. Baixa PDFs oficiais, extrai texto/tabelas e tenta
   OCR local nas páginas com pouco texto ou grandes imagens. Mostra progresso
   na central de execução; Interromper e retomada usam o executor existente.
3. Abra um contrato para conferir páginas, tabelas, original preservado, hash,
   fonte oficial, método e limites. Registre responsável, situação e justificativa
   em **Salvar revisão humana**. Cada registro acrescenta uma versão no histórico.
4. Para análise por IA dos novos trechos, use **Revisar com agentes**. A leitura
   dos documentos por si só não inicia Gemini nem altera o parecer.

`src/documents.py` não usa IA/banco. Só segue URLs HTTPS dos três domínios
municipais permitidos, inclusive redirecionamentos e o envelope JSON `{url}`
que o endpoint real de download retorna. Limite fixo de 10 MB por PDF;
HTML, arquivos não PDF e destinos externos são rejeitados. Links de navegação
não são anexos. Não descobre documentos em PNCP nesta etapa nem supre links
ausentes na coleta. Exportações de **Dados do Contrato** são identificadas como
fichas cadastrais, sem apresentá-las como o instrumento contratual integral.

Padrões ajustáveis no ambiente (o `.env` real foi preservado):

```dotenv
DOCUMENT_MAX_LINKS=5
DOCUMENT_MAX_TOTAL=300
DOCUMENT_MAX_PAGES=30
DOCUMENT_OCR_ENABLED=true
```

Faixas: 1..20 links por contrato, 1..500 PDFs únicos por ação, 1..100 páginas
por PDF. Conteúdo por página limitado a 30000 caracteres; até 10 tabelas,
100 linhas, 30 colunas e 2000 caracteres por célula. Omissões e falhas ficam
explícitas. Os limites tornam a cobertura parcial; não equivalem a ausência
de documentos no processo.

OCR usa `Windows.Media.Ocr` pelo script fixo `src/windows_ocr.ps1`, com idioma
pt-BR, execução oculta e timeout de 60s por página. Não instala programas,
não altera a política de execução e não envia imagens a serviços externos.
Requer Windows com o reconhecimento pt-BR instalado. Se indisponível, o
texto nativo é preservado e a falha consta no dossiê. A renderização limita
a maior dimensão a 2400 pixels. OCR é identificado e requer conferir a imagem;
não há garantia de reconhecimento correto de números, datas e colunas.

Artefatos: `documentos.json`, `documentos/<id>.pdf` e `<id>.json` na pasta da
execução. Cache valida hash do PDF; política/limites alterados reextraem o
original preservado. Extrações parciais podem ser tentadas novamente; PDFs
íntegros não precisam ser baixados outra vez. Não há atualização automática
do conteúdo remoto de um PDF já arquivado nesta etapa. A coleta documental
é manual pelos novos botões, sem mudar a auditoria base automática.

Os agentes recebem até 3 páginas/5000 caracteres por contrato (até 2000 por
página), com tipo, página, hash, OCR e omissões. O orçamento do lote permanece
vigente: dossiê grande demais exige ajustar limites, sem descartar achados.
Novas fontes/política invalidam checkpoints de revisão afetados, preservando
os da auditoria base. Revisões antigas incompatíveis são ocultadas no painel.

Revisão humana é local em `revisoes_humanas/<linha>.json`: nome informado
pelo usuário (sem autenticação), data, nota e situação, vinculados ao registro,
motivos e assinatura documental. Cada salvamento acrescenta um evento, com
controle de concorrência; histórico anterior permanece disponível com aviso
se as fontes mudaram. Não modifica motivos, fingerprints nem banco. Rotas
`/api/runs/<id>/revisoes/<linha>` usam token/origem locais na gravação. PDFs
preservados são servidos por ID inventariado com verificação de integridade,
sem aceitar caminhos arbitrários. Reabrir o painel mantém o histórico.

Importação aceita `documentos.json` junto de contratos/parecer e demais JSONs;
o original local e a gravação humana ficam disponíveis apenas nas execuções
locais. Inclua o mesmo dossiê documental ao importar uma revisão dos agentes.

Validação: 95 testes Python, 26 Node/frontend, build e Playwright desktop/mobile
390px. UI com fixtures demonstrativas; API real de histórico testada com
servidores locais e diretórios temporários. Download REAL de UM PDF da linha
109 em `data/raw/document_verificacao_20261020T235654Z/`: 1 página, 3004
caracteres nativos; é ficha cadastral do portal. OCR real sobre a imagem dessa
página reconheceu 1437 caracteres, com erros visíveis em data — conferência
manual continua necessária. Retomada local provou zero requisições, assinatura
estável e hashes dos originais preservados. Não houve envio ao Gemini,
gravação no banco ou processamento documental dos 94 contratos. PNCP, sanções
e preços continuam nas próximas entregas.

## Botões de execução no painel — 20/10/2026

O frontend agora executa ações na **Central de execução**, além de apresentar
resultados. Abrir `iniciar_painel.bat` e usar os botões; após atualização do
código, reabrir o painel para garantir a nova configuração Node.

| Botão | Efeito |
| --- | --- |
| Nova auditoria | Cria execução própria, coleta, analisa, consulta/revisa e pode arquivar no banco. |
| Retomar auditoria | Continua os lotes da execução selecionada, com as mesmas etapas restantes do pipeline. |
| Consultar Diário | Executa DOM/JOM na execução selecionada, sem IA/banco. |
| Revisar com agentes | Investiga/revisa achados da execução selecionada com Gemini, sem nova coleta/banco. |
| Estimar revisão | Calcula contratos/lotes/chamadas/pausas sem IA/portal/banco. |
| Interromper | Solicita parada da ação ativa, preservando checkpoints já concluídos. |

O painel atualiza ação/logs a cada três segundos e dados da execução a cada
aproximadamente seis segundos. Nova auditoria passa a ser selecionada quando a
coleta fica disponível. Trocar a seleção manualmente cancela esse acompanhamento
da seleção anterior. Demonstração/importados não podem disparar ações sobre
dados existentes; Nova auditoria continua disponível com executor conectado.
Execuções com arquivo confirmado e status concluído não oferecem retomada.

`frontend/server/jobs.js` mantém endpoints locais `/api/control`, `/api/jobs`
e `/api/jobs/<id>`, com POST para início e `/stop` para interrupção. Só aceita
ações fixas, IDs locais, origem/host loopback e token efêmero de controle. Não
aceita shell, argumentos arbitrários ou chaves vindas do navegador. Python é
iniciado por `spawn` com argumentos separados, `shell:false`, janela oculta e
stdout/stderr em arquivo. O `.env` é carregado só no executor Python.

`src/ui_jobs.py` mantém estado em `data/ui_jobs/` e trava entre ações. Reserva
Node também impede pedidos simultâneos em processos Vite distintos. Estados
e logs sobrevivem ao fechamento da aba/Vite; o Python é independente e o painel
recupera a ação ao abrir novamente. Processo encerrado inesperadamente aparece
interrompido. A trava por execução do pipeline continua em vigor para `.bat`.
Iniciar uma nova auditoria usa ID reservado interno de `src.main.main`; a CLI
anterior foi mantida. Os checkpoints base não tiveram seus critérios alterados.

Interrupção é cooperativa: um sinal de arquivo aciona KeyboardInterrupt no
processo gerenciado, sem matar processos arbitrários. Uma espera/requisição
em curso pode demorar até encerrar/atingir timeout. O estado permanece
Interrompendo e bloqueia novo início até a parada efetiva.

Validação: 83 testes Python, 19 Node/frontend, build e Playwright desktop/mobile.
Os cliques de auditoria/retomada/consulta/revisão foram simulados sem IA/banco.
O botão de estimativa foi REAL: execução 20261020T015002Z_72b23869, 94 contratos,
19 lotes, 38 chamadas de etapas, 41 minutos em pausas; hashes dos relatórios
originais preservados. Prova em `frontend/qa/controls-verificacao.json` e
`data/ui_jobs/20261020T051339Z_416602cf.json`. Capturas em controls-desktop.png e
controls-mobile.png. Nenhuma auditoria completa ou revisão dos 94 foi iniciada.

## Agentes especialistas com skills — 20/10/2026

O fluxo padrão preserva o Auditor de Contratos em lotes e acrescenta, depois
da consulta ao Diário, dois especialistas CrewAI: Investigador Documental e
Revisor dos Achados. A coleta, a busca DOM/JOM, a validação de citações e o
arquivamento continuam em Python. O aplicativo continua usando o Gemini
configurado; selecionar outro modelo no Codex não troca o modelo do sistema.

Os procedimentos em `src/audit_skills/*.md` são carregados pelo aplicativo,
selecionados conforme objeto/motivos e incluídos nas tarefas. Não são skills
instaladas no Codex nem dependem da API de skills de uma versão nova do CrewAI.
Há cinco procedimentos: documental, cobertura contratual/reconhecimento de
dívida, preços/escopo, atas e revisão/comunicação. A seleção de uma skill não
constitui achado. O prompt e a assinatura dos lotes da auditoria base foram
preservados para não invalidar trabalho já concluído.

Cada lote adicional executa investigação e revisão sequenciais, sem delegação,
memória compartilhada ou ferramentas de execução arbitrária. O investigador
recebe apenas os contratos sinalizados do lote, seus motivos e fontes locais:
campos do portal, até três referências candidatas do DOM/JOM e, quando houver
dossiê compatível, trechos dos PDFs extraídos pela etapa Ler documentos.
Não pesquisa PNCP nem executa OCR ou downloads pelo LLM. A consulta real
ao Diário e a extração documental são operações Python separadas da revisão.

O validador exige cobertura exata das linhas globais, sem duplicação, fontes
pertencentes à mesma linha e citações literais de 8..700 caracteres. A revisão
só pode reutilizar pares fonte/citação já aceitos na investigação. Esses
controles validam a referência, não a verdade da interpretação. A saída oferece
`contextualizado`, `necessita_documentos` e `rever_alerta`, explicação simples,
limitação e diligência sugerida. Não são estados de aprovação jurídica/humana.
Os motivos originais, índices e fingerprints de arquivamento não são alterados.

Configuração padrão (o `.env` real não é sobrescrito):

```dotenv
REVIEW_AGENTS_ENABLED=true
REVIEW_BATCH_SIZE=5
REVIEW_BATCH_MAX_BYTES=48000
```

`REVIEW_AGENTS_ENABLED=false` desativa somente a etapa adicional automática.
Tamanho aceita 1..15 contratos e 2000..80000 bytes. A revisão compartilha
`AUDIT_INTERVAL_SECONDS` (65s) e `AUDIT_QUOTA_RETRIES` (2). Há uma tentativa
adicional para resposta inválida; respostas rejeitadas são preservadas.
429 por minuto respeita espera; cota diária interrompe sem loop. O `.bat`
separado sempre executa a revisão quando solicitado, mesmo com automático
desativado. Falha adicional fica explícita e não impede arquivar a triagem base.

Para uma auditoria salva: `revisar_achados.bat`, sem nova coleta ou banco.
Para inspecionar o volume sem API: `revisar_achados.bat --planejar`.
Escolher execução: acrescentar `--execucao ID`; por padrão usa a mais recente
com parecer, que pode ser diferente da selecionada no painel.
Na auditoria salva de 450 linhas/94 contratos sinalizados, o planejamento local
resultou em 19 lotes e 38 chamadas de etapas antes de tentativas adicionais,
aproximadamente 41 minutos apenas em pausas caso todos sejam novos, mais a
latência do modelo. As etapas compatíveis recuperadas não fazem novas chamadas.

Artefatos no diretório da execução:

- `dossies_agentes.json`: fontes/limites efetivamente fornecidos ao modelo.
- `agentes/NNNN/investigacao.json` e `revisao.json`: checkpoints por etapa.
- `agentes/NNNN/rejeicoes/`: resposta rejeitada e diagnóstico.
- `revisao_agentes.json`: andamento, modelo, skills, resultados e citações.
- Seção idempotente no Markdown/parecer, preservando o conteúdo técnico base.

Assinaturas consideram dossiês, registro original, modelo, código dos agentes,
validadores e conteúdo das skills. Mudar esses critérios invalida somente as
etapas adicionais afetadas. Uma revisão interrompida pode ser retomada pelo
mesmo `.bat`. A investigação já concluída é reutilizada se o revisor falhar.
O bloqueio por execução impede rodar a auditoria/revisão em duas janelas.

O painel mostra contagem de revisados e a seção **O olhar dos agentes
especialistas**, com citações expansíveis. Clique Atualizar após executar.
Importação aceita `revisao_agentes.json` junto de contratos/parecer e, se houver,
`diario_oficial.json`. Revisões cujo registro, motivos ou consulta ao Diário
mudaram são ocultadas com aviso. Nenhuma chave é entregue ao navegador.

Validação: 75 testes Python, 10 testes frontend, build Vite e Playwright em
desktop/390px passaram. As chamadas dos especialistas foram simuladas nesses
testes. Após autorização explícita do usuário, o ensaio REAL da linha 109
(contrato 368/2026, processo 20857/2025) concluiu os dois agentes com duas
chamadas ao Gemini, sem rejeições. Classificação: `necessita_documentos`, com
reconhecimento de dívida distinguido de pagamento comprovado e solicitação
sugerida do processo integral. Citações conferidas literalmente.
`frontend/scripts/verify_agents.py` executou a amostra isolada fora do painel,
sem coleta/banco. Hashes confirmaram os originais preservados. Artefatos em
`data/raw/agent_verificacao_20261020T045515Z/`. Uma segunda execução local com
provider/espera bloqueados recuperou os dois checkpoints sem chamadas à API.
Essa amostra valida a integração técnica de um caso, não todos os achados.
O bloqueio inicial do auto-review foi resolvido com a autorização específica;
a revisão dos 94 contratos completos ainda não foi executada.

## Consulta documental ao DOM/JOM — 20/10/2026

Depois da análise em lotes, `src.gazette` consulta publicações oficiais apenas
para as linhas sinalizadas. Não usa Gemini e não altera os motivos técnicos.
As fontes são os tipos públicos da API WordPress oficial: `dom`,
`dom-extraordinario`, `jom` e `jom-especial`, além dos PDFs ligados pelas páginas
das edições. A Prefeitura mantém o arquivo JOM para publicações históricas.

Para consultar uma auditoria já salva, abra **consultar_diario.bat**. Ele usa
a execução mais recente com parecer, sem refazer auditoria nem gravar no banco.
Também é possível usar `python -m src.gazette --execucao ID_DA_EXECUCAO`.

Configuração padrão, sem necessidade de editar o `.env` para ativar:

```dotenv
GAZETTE_ENABLED=true
GAZETTE_MAX_EDITIONS=40
GAZETTE_CATALOG_PAGES=2
GAZETTE_CACHE_HOURS=24
```

`GAZETTE_ENABLED=false` desativa a etapa automática. O inicializador separado
sempre consulta quando executado. O limite de edições aceita 1..500; páginas
de catálogo por fonte 1..20 (100 itens/página); cache 0..168 horas. Cache 0 força
atualização. A seleção distribui edições por proximidade das datas de assinatura
disponíveis e inclui edições recentes. Datas do catálogo podem ser datas de
cadastro/importação, diferentes das impressas; a busca não cobre automaticamente
todas as edições históricas. Aumentar o escopo eleva downloads e tempo de leitura.

Cada contrato é pesquisado por número **e ano**, ou processo **e ano**.
O ano do processo não é presumido como ano do contrato. CNPJ no mesmo trecho
é apenas um identificador de reforço; CPF não é usado. Resultados são candidatos
para revisão do órgão, fornecedor, objeto e período. Números isolados não
comprovam vínculo. A extração tenta separar duas colunas quando há um corredor
central detectável, sem interpretar automaticamente o mérito jurídico do texto.

Artefatos: `diario_oficial.json` na execução, PDFs e texto por página em
`data/gazette_cache/`, e seção no relatório Markdown/parecer. Cada referência
inclui edição, página, trecho, critérios, link oficial e SHA-256 do PDF.
O painel mostra essas informações nos detalhes do contrato; importação aceita
também `diario_oficial.json` junto dos arquivos de auditoria.

São lidas até 150 páginas por PDF e até 25 MiB por arquivo. PDFs digitalizados
sem texto exigem OCR, ainda não implementado. Limites, páginas sem texto e
falhas ficam registrados como cobertura parcial/indisponível. Não localizar
referência nas edições consultadas não comprova ausência de publicação.
Falha na consulta não invalida o parecer nem impede o arquivamento.

Validação: 61 testes Python, sete frontend, build e UI passaram. Uma edição
real foi baixada e lida: DOM ED.145, 19/10/2026, 11 páginas. A extração localizou
o contrato 415/2026 e processo 21263/2025 na página 4, coluna 2, conferida
visualmente. A busca completa dos 94 contratos da auditoria atual não foi
executada nesta validação; poderá ser feita pelo inicializador separado.

## Resumos em linguagem simples — 20/10/2026

Cada contrato com achados recebe explicação local com introdução, problema
principal, significado prático e próxima diligência sugerida. O catálogo em
`src/summary_rules.json` é compartilhado pelo gerador Python
`src/plain_summary.py` e pelo frontend. Cobre serviços sem cobertura contratual,
valores zero confirmados, preços/custos, atas, quantitativos e coincidências;
outros casos recebem orientação geral com acesso à fundamentação original.
São explicações por regras, sem nova análise Gemini ou nova classificação de
suspeitos. Não alteram motivos técnicos, índices, fingerprints ou recibos.

A consolidação dos lotes salva `resumos.json` e inclui as explicações no
relatório Markdown e no campo correspondente de `parecer.json`. Auditorias
salvas podem ser atualizadas sem APIs com:

```powershell
python -m src.plain_summary ID_DA_EXECUCAO
```

O painel gera a mesma explicação automaticamente ao abrir um contrato com
alertas, incluindo arquivos importados. A fundamentação técnica é expansível.
Resumo sobre dívida só trata falta de cobertura como declaração da fonte se
o objeto efetivamente contiver esse texto; o resumo não transforma dívida
reconhecida em pagamento comprovado nem em conclusão jurídica. Diligências
são sugestões, não requisições enviadas. A política/checkpoints do auditor
continuam iguais, sem necessidade de refazer a análise.

Atualizados os 94 contratos sinalizados de `20261020T015002Z_72b23869`, com
conferência específica da linha 109 (R$ 10.579.129,21, processo 20857/2025).
Passaram 49 testes Python, seis testes frontend, build e verificação de UI.

## Fluxo atual após correção de cota Gemini (19/10/2026)

Consolidação corrigida: para comparar processos em toda a coleta, a fonte
`Detalhe - Processo` tem preferência; a coluna combinada da listagem só é
usada como fallback. Não se tratam as duas fontes como colunas ambíguas.
Verificação com os 32 checkpoints reais de `20261020T015002Z_72b23869`
consolidou 450 linhas e 96 achados em 94 contratos, sem novas chamadas ao
modelo ou banco. Os 45 testes locais passaram. O recibo remoto segue pendente.

Atualização de resiliência: se o guardrail rejeitar o parecer de um lote,
o worker salva a resposta original e o diagnóstico em `lotes/<lote>/rejeicoes/`,
aguarda 65s e pede revisão com o erro e uma tabela de valores publicados por
linha. São até três tentativas de validação por chamada do worker. O limite
de retries de cota continua separado. Nenhuma rejeição vira checkpoint ou
é reclassificada automaticamente como outro indício. Se persistir, a execução
para com diagnóstico curto, preservando os lotes anteriores. A política de
validação e a assinatura dos checkpoints existentes foram mantidas.

`src.main` agora usa `src/batch_pipeline.py`. A coleta Playwright e o
arquivamento são executados diretamente, sem passar seus JSONs inteiros por
agentes LLM. O agente Auditor continua usando CrewAI/Gemini, em uma Crew
independente para cada lote, sem histórico dos lotes anteriores no prompt.
`src/crew.py` permanece como implementação histórica de três agentes.

- `iniciar_auditoria.bat`: nova coleta e análise em lotes.
- `retomar_auditoria.bat`: reutiliza a coleta pendente mais recente e os
  checkpoints válidos, sem repetir a coleta do portal.
- `python -m src.main --retomar ID_DA_EXECUCAO`: retoma um ID específico de
  `data/reports`. `--retomar --planejar` apenas mostra os lotes e pausas,
  sem consultar portal, Gemini ou banco.

Padrões, aplicados mesmo sem acrescentá-los ao `.env` existente:

```dotenv
AUDIT_BATCH_SIZE=15
AUDIT_BATCH_MAX_BYTES=48000
AUDIT_INTERVAL_SECONDS=65
AUDIT_QUOTA_RETRIES=2
```

São limites por quantidade de registros e bytes UTF-8 do JSON, não uma
contagem exata de tokens. Nenhum campo é cortado. Registro que excede sozinho
o limite aborta com diagnóstico. Intervalos aceitam 0 a 3600 segundos (padrão
conservador 65s); quantidade 1 a 100, bytes 1000 a 120000, retries 0 a 5.
Outros usos do mesmo projeto Google também podem consumir a cota; os limites
ativos devem ser conferidos no AI Studio. Aumentar esses valores não aumenta
a cota do provedor.

Em erro 429, espera a indicação `retryDelay` (no mínimo 65s) e tenta novamente
somente o lote atual, até o limite configurado. Cota diária/zero identificada
não entra nessa repetição. O agente não repete automaticamente toda a tarefa.

Cada lote salva checkpoint em `lotes/0001/checkpoint.json` etc. A assinatura
inclui coleta, divisão, modelo e política do auditor; mudanças invalidam
checkpoints incompatíveis. Os índices locais devem cobrir exatamente o lote
e são convertidos para índices globais no parecer final. Não se arquiva lote
parcial. Só depois de todos os lotes validados são produzidos `parecer.json`
e `relatorio.md` consolidados, e então ocorre a gravação com recibo.
`progresso.json` registra a etapa e os lotes concluídos. Trava do sistema
operacional evita duas retomadas simultâneas da mesma execução.

`coincidencias.json` registra comparações exatas em toda a coleta, inclusive
entre lotes: processo repetido ou fornecedor/objeto/valor coincidentes. São
grupos para diligência, sem classificação automática como irregularidade.
Relações semânticas entre lotes não são analisadas globalmente pelo modelo.

A coleta que falhou em `20261020T013117Z_fa0fddf9` contém 450 registros,
distribuídos em 32 lotes pelos padrões acima. São aproximadamente 34 minutos
somente em pausas entre lotes, além de chamadas, retries e demais etapas.
O planejamento foi verificado localmente; não foi executada nova chamada
real ao Gemini ou Supabase após a correção. Os 40 testes locais passaram.

As seções abaixo são histórico de implementação; prevalece o fluxo acima.

Atualização posterior de 19/10/2026: o Playwright usa o filtro real `year` e
interrompe em falha de confirmação do ano/pesquisa. Extrai o objeto expandido,
segue links individuais e inclui campos e seções dos detalhes na coleta.
Salva o HTML consultado em `data/reports/<execução>/detalhes/` e tenta baixar
o CSV para `exportacao_portal.csv`, com status em `exportacao.json`.
Links dos anexos são identificados; o conteúdo dos PDFs ainda não é lido.
Uma consulta real validou um detalhe (19 campos/seções) e o download CSV;
isso não valida a coleta completa, nem integração com Gemini/Supabase.
As referências abaixo a continuar após falha na seleção do ano são históricas.

> Atualização em 19/10/2026: por decisão do usuário, o coletor atual usa
> Playwright. As seções históricas de paginação HTTP abaixo não descrevem
> essa implementação. Ela tenta selecionar o ano 2026, navega por Próximo ou
> número da página e remove registros duplicados. Pode devolver resultados
> parciais nos limites de 50 páginas/500 registros ou em falhas de navegação;
> a seleção do ano não é obrigatória em caso de erro. A completude e o filtro
> real ainda precisam de validação no portal. Os 18 testes locais passaram
> com navegador simulado e persistência SQLite; nenhum serviço remoto foi
> acessado. `ContractBatch` rejeita mensagens de erro do coletor.

O fluxo é Coletor → Auditor → Arquivista. Mantém-se Gemini e a organização
em pacotes `src/agents/` e `src/tasks/` para evitar conflito com arquivos
homônimos `agents.py` e `tasks.py`.

## Configuração

Instale PostgreSQL e inicie seu serviço. No psql, conectado como administrador,
crie um usuário dedicado e o banco (substitua a senha):

```sql
CREATE ROLE auditoria_app LOGIN PASSWORD 'SUBSTITUA_POR_SENHA_FORTE';
CREATE DATABASE auditoria_cidada OWNER auditoria_app;
```

Adicione ao `.env`, preservando `GEMINI_API_KEY` e `GEMINI_MODEL`:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=auditoria_cidada
DB_USER=auditoria_app
DB_PASSWORD="SUBSTITUA_POR_SENHA_FORTE"
DB_SSLMODE=prefer
CONTRACT_YEAR=2026
CONTRACT_TABLE_SELECTOR=table
API_PAGE_PARAM=
API_PAGE_START=1
API_PAGE_STEP=1
API_PAGE_SIZE=100
API_PAGE_SIZE_PARAM=
API_MAX_PAGES=1000
```

Para PostgreSQL remoto com TLS obrigatório, use `DB_SSLMODE=require` ou
`verify-full` conforme o certificado do servidor. A conexão usa `URL.create`,
permitindo caracteres especiais na senha sem codificação manual de URL.
`init_db` cria a tabela, não o banco/usuário, e não substitui migrações de esquema.
Seu `.env` real não foi lido nem modificado nesta implementação.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main
```

`main` inicializa as tabelas antes das chamadas ao modelo. Se a conexão falhar,
a execução para. Saídas em `data/reports/<execução>/`: `contratos.json`,
`parecer.json`, `relatorio.md` e `arquivamento.json`.

## Paginação

Não há mais corte em cinco linhas nem em caracteres. A tabela completa é
extraída quando não há paginação. Links HTML Próxima são seguidos por GET,
com cookies da sessão, respeitando o domínio do portal. A semântica efetiva
dos links/filtros deve ser conferida na resposta real do portal.

O modo parametrizado é opt-in: não se inventa um parâmetro de API. Se o Network
confirmar `page` e `per_page`, por exemplo:

```dotenv
API_PAGE_PARAM=page
API_PAGE_START=1
API_PAGE_STEP=1
API_PAGE_SIZE=100
API_PAGE_SIZE_PARAM=per_page
```

Se confirmar `offset` e `limit`:

```dotenv
API_PAGE_PARAM=offset
API_PAGE_START=0
API_PAGE_STEP=100
API_PAGE_SIZE=100
API_PAGE_SIZE_PARAM=limit
```

Nesse modo, continua até uma página vazia (não presume que uma página curta
seja a última). Página repetida, tabela ambígua, linha malformada ou limite
de segurança causam erro, sem devolver coleta parcial como sucesso.
Não se eliminam linhas duplicadas da fonte; duplicidades são evidência.
Botões JavaScript/formulários sem links precisam dos parâmetros identificados
na rede. Endpoints JSON/DataTables server-side com outro esquema exigem um
adaptador específico; não há detecção universal de paginação invisível no HTML.
Se a fonte muda durante a coleta, offset pode deslocar linhas: para consistência
forte, o servidor precisa oferecer ordenação estável ou snapshot.

## Persistência e rastreabilidade

O auditor produz `ParecerAuditoria` com `linhas_analisadas`, `suspeitos`
(índice da linha e motivo) e `relatorio_markdown`. O guardrail exige cobertura
de todos os índices e suspeitos válidos sem repetição. Isso valida a estrutura,
não prova que o modelo raciocinou corretamente sobre cada contrato.

O arquivista chama uma ferramenta sem argumentos que lê os artefatos validados
da execução, recupera campos da fonte pelo índice e chama `salvar_contratos`.
Ele não precisa reescrever os campos no prompt de uma chamada de gravação.
A confirmação final vem do recibo real da ferramenta, não de texto inventado.

O ORM tem os campos solicitados e um `fingerprint` único adicional, calculado
pela linha original mais o motivo. Repetir o mesmo dado/parecer não duplica o
registro, inclusive em execuções concorrentes; parecer diferente cria outra
versão. Isso não é um identificador jurídico do contrato. Valores monetários
usam Decimal/Numeric(20,2), nunca float. Campos indisponíveis ficam NULL,
nunca zero. Ajuste os aliases em `archive_tool.py` se os nomes das colunas
mudarem; valores monetários ambíguos interrompem o arquivamento.

Somente suspeitos são gravados. Não sinalizados não recebem automaticamente
o status Regular. Suspeito é rótulo de triagem, não conclusão de irregularidade.
Um lote é uma transação com rollback integral em caso de falha. O relatório
fica disponível mesmo se a gravação final falhar; não há recibo de sucesso.

## Limites e validação

Não se usa sumarização automática para caber no contexto do modelo. Coletas
maiores que a janela do Gemini podem interromper a análise; para volumes de
produção, o próximo passo é auditoria em lotes com reconciliação entre lotes
para detectar coincidências globais. A coleta completa por si só não resolve
o limite do LLM nem as cotas gratuitas do provedor.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes locais cobrem paginação simulada, repetição, preservação de linhas
longas, estrutura do parecer, moeda e persistência/idempotência/rollback em
SQLite. Não substituem teste de integração com PostgreSQL nem validação real
da paginação do portal ou do Gemini. Não foram acessados esses serviços no teste.


## PNCP e instrumentos contratuais (21/10/2026)

Consultar PNCP na central relaciona contratos e encontra anexos oficiais.
Ler documentos prioriza PDFs dos vínculos únicos confirmados por regras,
preservando a distinção de fichas cadastrais e PDFs publicados.
Cobertura, uso, testes e limites: [PNCP.md](PNCP.md).
A evolução da qualidade analítica está em [QUALIDADE_ANALITICA.md](QUALIDADE_ANALITICA.md).

## Indicadores de gestão com pandas (21/10/2026)

Gerar indicadores calcula cobertura e distribuição dos valores contratuais
locais, com exclusões e denominadores explícitos. Sem IA, rede ou banco.
O painel e a ferramenta MCP consultar_indicadores consultam o resultado
salvo e ocultam versões incompatíveis com as fontes atuais.
Critérios e resultado real: [INDICADORES.md](INDICADORES.md).
