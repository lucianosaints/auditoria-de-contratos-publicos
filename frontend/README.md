# Painel Auditoria Cidadã

Frontend local em React + Vite, com ícones Lucide e relatório Markdown.

## Escritórios dos agentes — 24/10/2026

A Visão geral e Operações mostram cinco salas com agentes animados. Ao iniciar
ou retomar uma auditoria, ou revisar achados, a estação ativa acompanha a etapa
registrada pelo executor. Mudanças entre agentes acionam uma entrega pelo corredor,
inclusive quando várias etapas ocorrem entre duas consultas do painel. O percurso
é uma representação visual da troca registrada; não mede a duração da etapa.
Entregas acumuladas aparecem na fila, separadas do estado atual do executor.

Coleta e arquivamento publicam sua atividade; análise e revisão publicam a partir
dos arquivos de progresso gravados com sucesso. Eventos ficam no registro da ação
em `data/ui_jobs`, sem modificar políticas, checkpoints ou pareceres. Ações antigas
sem essa telemetria mantêm o acompanhamento textual, sem entregas inventadas.
Ao abrir uma ação já em curso, mostra o estado atual sem repetir entregas antigas.
Pausas por cota, interrupção solicitada e perda de conexão suspendem o movimento;
falha, cancelamento ou troca de execução descartam a fila visual. Fechar a animação
ou usar Pausar animação não interrompe o trabalho; use Interromper em Operações.

**Ver prévia do fluxo** continua sendo uma demonstração fictícia, sem executar
ações, e fica desabilitada durante trabalho ativo. QA com executor simulado em
`scripts/verify_agent_office_live.py`; QA desktop/mobile da prévia em
`scripts/verify_agent_office.py`.

O bloco **Coletor · fontes de dados** mostra órgão, URL pública do endpoint ou
documento e estado da consulta. A sequência de fontes acompanha as solicitações
do Portal da Transparência (contratos e financeiro), Diário Oficial, PNCP e
downloads de documentos. Cache PNCP/financeiro aparece como cache local, sem
simular acesso ao site. São exibidas as seis últimas fontes consecutivas desta
ação, com até 50 transições preservadas no registro do executor. Parâmetros de
URL não são publicados para evitar expor tokens de sessão. Resposta recebida
não certifica cobertura integral. O indicador só acompanha consultas previstas
na ação executada; não inicia consultas a outros órgãos automaticamente.

## Navegação reorganizada — 21/10/2026

- **Visão geral:** números essenciais, próximo passo e atalhos para a análise.
- **Contratos:** tabela, filtros, detalhes e revisão dos agentes em seção expansível.
- **Evidências:** abas Documentos, PNCP, Financeiro e Busca local; uma fonte por vez.
- **Indicadores:** cobertura e distribuição dos valores contratuais.
- **Relatório:** parecer e informações de arquivamento.
- **Operações:** grupos Auditoria, Fontes e documentos, Análise e revisão.
- **Como analisamos:** explicação do método e dos limites.

Os comandos não aparecem mais em todas as páginas. O histórico da última
ação e as ferramentas avançadas ficam recolhidos. Uma ação ativa permanece
acompanhada ao navegar, com interrupção disponível; trocar de área não dispara
comandos. **Preparar RAG** e **Verificar MCP** estão em Ferramentas avançadas.
A busca textual fica em Evidências → Busca local. Conflitos financeiros
também ficam em uma lista expansível.

Atualize o navegador com **Ctrl+F5** para carregar o frontend. Nenhuma auditoria
precisa ser repetida. QA da navegação: `scripts/verify_workspace_ui.py`, com
servidor de teste em 4173, dados reais somente para leitura e POSTs simulados.
Verifica desktop/mobile, abas por teclado, seleção da execução, navegação
durante ação ativa, interrupção e preservação dos arquivos.

**Financeiro:** **Consultar financeiro** pesquisa CNPJ/exercício e confere
identidades de empenhos, até 10 consultas e 30 detalhes por ação.
Confere número/ano e processos/contratos explicitamente citados no resumo;
CNPJ é comparado quando há registro correspondente na consulta filtrada.
Conflitos não exibem saldos; números compatíveis continuam pendentes de vínculo
contratual. O painel indica omissões, falhas e fontes desatualizadas. Sem IA/banco
ou totais de pagamento por contrato. A execução principal já tem resultado salvo.
Veja [EXECUCAO_FINANCEIRA.md](../EXECUCAO_FINANCEIRA.md).

**Indicadores:** o botão **Gerar indicadores** calcula localmente cobertura,
exclusões e distribuição de valores contratuais por CNPJ com pandas.
O painel apresenta o denominador e permite abrir as linhas de origem.
Resultados desatualizados são ocultados quando as fontes mudam.
Sem IA/rede/banco; valores contratuais não são pagamentos.
Consulte [INDICADORES.md](../INDICADORES.md).

**PNCP:** o novo botão **Consultar PNCP** relaciona contratos e localiza anexos
oficiais. Nos detalhes, confira identificadores e diferenças entre fontes.
Só vínculos únicos confirmados por regras alimentam automaticamente **Ler
documentos**. Depois prepare o RAG. Candidatos, conflitos e ausência no recorte
não são conclusões de irregularidade. Consulte [PNCP.md](../PNCP.md).
Importação opcional aceita `pncp.json` junto de coleta/parecer compatíveis.

**Revisão incremental:** o botão Revisar com agentes agora reaproveita os
contratos de contexto compatível e envia somente os pendentes para novas
etapas. Use Estimar revisão para ver a divisão antes. O painel informa os
reaproveitados e selecionados para nova análise. A primeira inclusão de
PDFs/RAG pode alterar o contexto de todos os contratos com novos trechos.

**Fontes e suporte:** cada revisão apresenta os campos do portal, fontes do
Diário e páginas de PDFs efetivamente citadas, além do uso registrado de RAG/MCP.
**Conferir suporte** executa triagem por regras locais sobre a revisão salva,
sem IA ou banco. O acompanhamento dos agentes mostra atalhos às linhas com
avisos. Nos detalhes, leia **Fontes e suporte da conclusão**. Resultados
originais são preservados; ausência de avisos não valida a interpretação.
A conferência é executada automaticamente após Revisar com agentes pelo painel.

RAG/MCP: após **Ler documentos**, use **Preparar RAG** e **Verificar MCP**.
Em **Consultar evidências locais**, informe linha e termos para conferir os
trechos e abrir o PDF na página indicada. **Revisar com agentes** usa o MCP
automaticamente quando há índice preparado. Veja [RAG_MCP.md](../RAG_MCP.md).

Na raiz do projeto, dê dois cliques em **iniciar_painel.bat**. O navegador abre
em http://127.0.0.1:5173. Mantenha a janela do painel aberta enquanto o utiliza.
Na **Central de execução**, use Nova auditoria, Retomar auditoria, Consultar
Diário ou Revisar com agentes. As ações sobre dados existentes usam a execução
selecionada no painel. Estimar revisão calcula volume sem IA/portal/banco.
Durante uma ação, os demais botões ficam bloqueados e o progresso é atualizado
automaticamente. Interromper preserva checkpoints concluídos; requisições em
curso podem precisar encerrar ou atingir o timeout antes da interrupção.
Os inicializadores `.bat` anteriores continuam disponíveis como alternativa.
Depois de atualizar o projeto, feche e reabra o painel para carregar o executor.

O destaque acima dos botões informa ação ativa ou encerrada, progresso,
tempo decorrido e fase atual. Pausas da IA têm contagem regressiva. O motivo
de uma falha aparece diretamente no painel, separado da conclusão da auditoria
base e do arquivamento. O horário da última verificação permite distinguir
espera real de perda de conexão com o executor.

## Documentos e revisão humana

Na Central de execução, **Planejar documentos** conta os anexos dos contratos
com achados, sem downloads. **Ler documentos** baixa PDFs oficiais e extrai
texto/tabelas, com OCR local do Windows quando necessário. Essas ações não
usam IA nem banco. O progresso, a interrupção e a retomada usam os controles
existentes. Links ausentes, formatos não PDF e limites ficam explícitos.

Abra um contrato para conferir páginas, tabelas, OCR e fonte preservada.
Fichas exportadas do portal são identificadas e não substituem o contrato
integral. **Salvar revisão humana** acrescenta responsável, situação e
justificativa ao histórico local, preservando versões e fontes. O nome é
autodeclarado. Alterações nas fontes/alertas tornam registros antigos
identificáveis. Demonstração/importação não permitem gravar revisão local.

**Revisar com agentes** passa a aproveitar trechos dos PDFs já lidos; esse
botão usa Gemini. Não é disparado automaticamente por Ler documentos.
Importação também aceita `documentos.json`; inclua o dossiê usado na revisão
dos agentes. Limites e instalação do idioma OCR estão em `../FASE3.md`.

## Dados

- O serviço local do Vite lê `../data/reports/<execução>/contratos.json`,
  `parecer.json`, `relatorio.md` e `arquivamento.json`, sem gravar nesses arquivos.
- Ao abrir, seleciona a execução mais recente com registros e parecer, quando
  disponível. Coletas sem parecer permanecem identificadas.
- Importação: selecione `contratos.json` e `parecer.json` juntos. Só a coleta
  também é aceita. Os arquivos ficam em memória no navegador; não são enviados
  para outro serviço. Cada arquivo tem limite de 15 MB.
- Demonstração é uma opção explícita com dados fictícios e aviso permanente.
- Busca, categorias, filtros, paginação, detalhes, links da fonte, exportação CSV
  da seleção e download do relatório funcionam sobre os dados selecionados.
- Contratos com alertas mostram primeiro um resumo em linguagem simples:
  problema principal, significado prático e diligência sugerida. A fundamentação
  técnica permanece expansível. O catálogo compartilhado `src/summary_rules.json`
  (na raiz do projeto) permite explicar auditorias antigas e arquivos importados,
  sem chamada adicional ao Gemini. É uma explicação por regras, não nova análise.
- Categorias são agrupamentos do texto do parecer, sem nova auditoria por IA.
  A soma de valores representa registros da coleta, podendo incluir repetições.
  Cobertura usa linhas válidas declaradas pelo parecer, sem validar o raciocínio.
- Nos detalhes dos contratos com alertas, a seção Publicações oficiais apresenta
  a consulta DOM/JOM: cobertura, referências candidatas, trechos, páginas e links.
  `consultar_diario.bat` consulta a auditoria salva sem Gemini ou banco; depois use
  Atualizar no painel. Também pode importar `diario_oficial.json` junto dos outros
  JSONs. Ausência de resultado não significa ausência de publicação.
- O navegador não contém chaves do Gemini/Supabase. O serviço Node local aceita
  ações fixas e inicia o executor Python: nova auditoria/retomada podem usar IA e
  arquivar no banco; revisão usa IA sem banco; consulta ao Diário não usa IA.
  Os arquivos de relatórios não são copiados para `public/`.
- Acompanhamento dos agentes: contagem de contratos com revisão adicional e,
  nos detalhes, explicação, limite, diligência, skills e citações expansíveis.
  O botão Revisar com agentes executa/retoma a revisão salva com Gemini, sem
  banco; Estimar revisão mostra o volume sem chamadas à IA.
  Nas novas auditorias a revisão é automática, após a consulta ao Diário.
  Revisão por IA continua sujeita a conferência humana e não altera os alertas.
- Importação também aceita `revisao_agentes.json`. Inclua o Diário usado na
  revisão quando disponível. Alterações no registro, motivos ou consulta ao
  Diário ocultam resultados anteriores incompatíveis com os dados atuais.

## Desenvolvimento

Requer Node.js 20.19+ ou 22.12+ (verificado com Node 24).

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

`preview` serve a build em http://127.0.0.1:4173 e mantém o serviço de leitura
local. Hospedar apenas `dist/` permite importar arquivos e usar a demonstração;
o acesso a `data/reports` depende do serviço Node local. Nenhum site foi publicado.

Os controles dependem também do serviço Node e do Python/dependências locais.
Não estão disponíveis para arquivos importados ou demonstração, exceto Nova
auditoria quando o executor local estiver conectado. Histórico/logs das ações
ficam em `data/ui_jobs/`; fechar a aba/painel não encerra o Python já iniciado.
Ao reabrir, o painel recupera a ação ativa. Os botões não abrem novos terminais.

`iniciar_painel.bat --verificar` gera a build sem abrir o navegador ou executar
a auditoria Python. O serviço escuta somente em loopback para uso nesta máquina.
