# Retomada mais recente — encerramento de 24/10/2026

Usuário pediu salvar o que fizemos neste arquivo para voltar depois. Alterações gravadas nos arquivos locais; resumo abaixo prevalece sobre registros históricos.

## Estado atual para retomar

- Frontend com escritório 2D inspirado na referência do usuário: cinco agentes (Coletor, Auditor, Arquivista, Investigador e Revisor), cada um em sala própria, com paredes, porta, placa e cor. Bonequinhos caminham pelo corredor levando documento na mão, entregam ao colega e voltam, com movimento de braços/pernas e pausa da animação.
- Animação conectada aos eventos reais do executor nas próximas ações de auditoria/retomada/revisão. Mudanças de agente geram entregas visuais em fila; a estação ativa mostra a etapa atual. Prévia fictícia continua separada. Ações antigas não têm telemetria retroativa. Espera por cota/desconexão pausam; falha/cancelamento/troca de execução descartam a fila. Pausar animação não para a auditoria.
- Nova auditoria e Retomar auditoria ficam juntos no cabeçalho dos escritórios, na Visão geral e em Operações. Mantidas travas de conexão, executor ocupado e elegibilidade da retomada; removidos cartões inferiores duplicados.
- Coletor mostra órgão, URL pública clicável, estado da consulta e histórico das últimas fontes. Acompanha Portal de Maricá (contratos/financeiro), Diário Oficial, PNCP e downloads de PDFs. Cache PNCP/financeiro aparece separado; parâmetros de URL não são publicados. A troca de fonte reflete consultas existentes na ação, sem agendar novos órgãos automaticamente. Resposta recebida não significa coleta integral.
- Implementação principal: frontend/src/AgentOffice.jsx, CollectorSources.jsx, agentOffice.js, RunControls.jsx, OperationsPanel.jsx, App.jsx e styles.css; src/office_activity.py, ui_jobs.py, batch_pipeline.py e pontos de consulta dos coletores. frontend/README.md documenta o funcionamento.
- Última validação: build e 49 testes Node aprovados; 80 testes Python da última entrega aprovados. Na integração anterior também passaram 32 testes de executor/pipeline/telemetria e 33 de revisão/incremental. QA desktop/mobile e executor simulado aprovados, inclusive clique para iniciar, entrega, pausa por cota, falha, troca de fontes e cache. Capturas em frontend/qa/agent-office-*.png; scripts verify_agent_office.py e verify_agent_office_live.py em frontend/scripts.
- Não iniciamos auditoria real, Gemini, consulta externa real ou gravação no banco durante estas alterações. Ações de QA foram interceptadas/simuladas. Dados e avaliações humanas não foram preenchidos. src/documents.py conferido igual ao backup anterior em texto normalizado para preservar política documental.

## Próxima retomada

1. Ler este resumo e os registros detalhados logo abaixo. Abrir o painel habitual em http://127.0.0.1:5173 e atualizar com Ctrl+F5; se o servidor estiver fechado, usar iniciar_painel.bat. O servidor de QA desta sessão foi iniciado na porta 4173; sua disponibilidade futura deve ser verificada.
2. Continuar conforme a próxima solicitação do usuário. Não iniciar nova auditoria, chamadas de IA ou repetir coletas apenas para demonstrar a animação. Usar Ver prévia do fluxo ou fixtures de QA para verificação visual.
3. Piloto supervisionado de ontem permanece pendente de avaliação humana: abrir iniciar_piloto.bat, avaliar fontes e exportar progresso JSON. Último estado registrado nos arquivos: zero avaliações e 40 pendentes; possíveis rascunhos do navegador não foram verificados nesta sessão.
4. Financeiro segue sem vínculos confirmados; minuta da linha 175 permanece não enviada. Não interpretar melhorias de interface como conclusão da validação analítica.

Este encerramento salva a continuidade e os arquivos locais. Não foi criado backup ZIP novo, commit ou publicação. Último backup completo informado permanece backups/auditoria_salva_20261023_final.zip; ele é anterior às mudanças de frontend de 24/10.

---
## Coletor mostra órgão e URL da fonte — 24/10/2026

- Usuário pediu indicação dos sites consultados pelo Coletor, mudando quando a coleta passa a outra fonte.
- Adicionado CollectorSources acima do cenário: órgão/fonte, URL pública clicável, estado (consultando, resposta recebida, falha, cache local), e sequência das seis últimas fontes. Em desconexão/fim da ação mostra última fonte registrada; não afirma coleta integral nem agenda novos órgãos.
- office_activity observa requests reais e navegação principal/detalhes Playwright; integração com Portal de Maricá, Diário, PNCP, financeiro e PDFs. ui_jobs preserva source/sources no registro da ação com horários e contagem de requests, até 50 transições. Queries/fragments de URLs excluídos da telemetria. Cache PNCP/financeiro identificado sem simular acesso à rede.
- Documentos usam adaptador de sessão no executor; src/documents.py conferido idêntico ao backup de 23/10 em texto normalizado, preservando política de cache. Telemetria não modifica prompts/decisões/checkpoints.
- Validação: build, 49 testes Node e 80 Python (65 fontes/executor/documentos/telemetria; 15 portal/coletor) aprovados. QA com fontes simuladas verificou troca Portal→PNCP, URLs, histórico, cache e desktop/mobile, zero overflow/erros JS. Clique de QA em Nova auditoria foi interceptado; nenhuma consulta externa/auditoria/IA/banco real.
- Provas frontend/qa/agent-office-sources.png e agent-office-sources-mobile.png. README atualizado. Sem backup ou commit novo.
## Retomar auditoria no cabeçalho dos escritórios — 24/10/2026

- Pedido do usuário: mover também Retomar auditoria para perto dos agentes.
- Retomar agora está ao lado de Nova auditoria, na Visão geral e Operações, mantendo as travas existentes: conexão, executor livre e coleta local com auditoria pendente. Tooltip explica quando indisponível.
- Removido cartão inferior duplicado; aba Auditoria orienta usar os botões superiores. Layout adapta os dois botões no celular.
- Build e QA desktop/mobile aprovados, sem erros JS, overflow ou ações reais. Capturas atualizadas. Nenhuma auditoria iniciada.
## Nova auditoria ao lado dos agentes — 24/10/2026

- Usuário pediu botão Nova auditoria no alto, junto da animação.
- Botão movido para o cabeçalho dos escritórios, na Visão geral e Operações. Usa o mesmo executor e travas de conexão/trabalho ativo/carregamento; erros aparecem junto ao botão. Removido cartão duplicado na lista de operações. Retomar continua em Operações.
- Build e QA desktop/mobile aprovados. QA de início por clique no botão novo, com POST interceptado, coleta automática, entrega, pausa por cota e falha aprovado. Nenhuma auditoria real iniciada; capturas atualizadas.
## Animação ligada ao executor real — 24/10/2026

- Usuário pediu que caminhada/entregas acompanhem o início dos trabalhos reais.
- src/office_activity.py observa atividade no escopo da ação e pasta selecionada. ui_jobs guarda agente/fase/eventos sequenciais no próprio JSON da ação. batch_pipeline publica coleta e arquivamento e observa snapshots de progresso/revisão após gravação. agent_review.py, prompts e políticas não foram alterados; nenhum checkpoint ou parecer reescrito nesta entrega.
- AgentOffice agora recebe mudanças reais de agente e faz a entrega entre as salas correspondentes, não necessariamente a próxima sala no desenho. Fila preserva mudanças rápidas entre polls, sem duplicação. A estação ativa representa o estado atual; legenda separa entregas visuais já registradas e fila. A caminhada não mede duração real.
- Ao iniciar Nova auditoria, frontend seleciona a nova execução vazia antes de existir contratos.json para acompanhar coleta. Prévia permanece separada e bloqueada durante ação ativa.
- Falha/cancelamento/troca de execução descartam fila; desconexão, solicitação de parada e espera por cota pausam movimento. Abrir ação em curso não repete histórico antigo. Ações antigas sem telemetria mantêm estado/texto sem inventar entregas.
- Validação: build, 49 testes Node, 32 Python de telemetria/pipeline/executor e 33 Python de revisão/incremental aprovados. QA desktop/mobile da prévia e QA de fluxo com início por clique, entrega, documento na mão, espera por cota e falha aprovados. O único POST de QA foi interceptado; nenhuma auditoria/Gemini/banco executada de verdade. Prova frontend/qa/agent-office-live.png.
- Primeiro teste Python exigiu redirecionar cache CrewAI para data/test_runtime; revisão incremental exigiu tests no sys.path. Rodadas corrigidas passaram. Frontend README atualizado. Sem backup novo ou commit.
## Salas individuais dos agentes — 24/10/2026

- Usuário aprovou a caminhada e pediu cada agente em seu próprio escritório.
- Cinco salas com paredes, portas, placas numeradas, cores próprias e janelas nas três salas superiores. Corredor central conecta todas as portas.
- Rotas da prévia ajustadas para sair pela porta, cruzar o corredor e entrar na sala do próximo agente; mesas inferiores deslocadas para liberar a passagem. Movimento e pausa preservados.
- Build e QA desktop/mobile aprovados; capturas agent-office-desktop.png/mobile.png atualizadas. Nenhuma auditoria ou escrita no executor iniciada.
## Agente caminhando com documento — 24/10/2026

- Pedido do usuário: bonequinho andando e levando documento ao próximo agente.
- Prévia agora usa o próprio personagem: sai da estação, move braços/pernas, leva documento na mão, entrega ao colega e volta. Ciclo de dez segundos por agente, com rotas pelo corredor e abertura na divisória; sem duplicar o personagem na mesa.
- Pausar congela posição e passos; retomar continua a viagem. Entrega continua ilustrativa na prévia, sem ações reais ou alterações na auditoria.
- Build aprovado e QA desktop/mobile aprovado, incluindo movimento de posição, documento na mão e pausa exata. Zero erros JS, overflow ou solicitações de escrita. Capturas agent-office-desktop.png/mobile.png atualizadas.
## Escritório 2D dos agentes — 24/10/2026

- Usuário pediu frontend mais bonito inspirado em escritório 2D, agentes trabalhando e documentos passando entre estações.
- Criados AgentOffice.jsx e agentOffice.js; integrados ao RunControls na Visão geral e Operações, usando o polling existente. SVG/CSS locais, sem dependências ou imagens externas.
- Cinco estações: Coletor, Auditor, Arquivista, Investigador e Revisor. Prévia fictícia percorre as estações com documentos animados; não envia ações ao executor. Pausa, seleção das funções e suporte a movimento reduzido.
- Estado real anima apenas etapas identificadas pelo progresso: análise e investigação/revisão. Coleta/arquivamento não possuem identificação granular disponível nesse componente; não inferir atividade ou conclusão. Passagem de documentos da prévia é ilustrativa, não telemetria de entrega real.
- Build aprovado; 45 testes existentes e dois novos testes do mapeamento aprovados. QA desktop/mobile com prévia/pausa/retorno: zero erros JS, overflow ou envios de ações. Provas em frontend/qa/agent-office-*.png; script frontend/scripts/verify_agent_office.py.
- Servidor de visualização iniciado em http://127.0.0.1:4173. Sem nova auditoria, Gemini, mudança no banco ou avaliações humanas. Piloto continua dependendo do usuário.
# Continuidade — Auditoria Cidadã Automatizada

## Salvamento para retomar amanhã — 23/10/2026

- Confirmação após concluir o backup: 2.412 arquivos, 238.519.596 bytes;
  integridade ZIP e hashes internos conferidos. SHA-256 do ZIP:
  b57e0210ad36f80b5f7457916657f8b9be9c7fe7334709d5deac17e1ee34f295.
  Usuário pediu expressamente registrar também neste continuidade.md.
  Esta confirmação foi acrescentada após o ZIP; o backup contém a versão
  anterior deste arquivo, já com o mesmo roteiro de retomada abaixo.
- Usuário pediu encerrar por hoje e salvar tudo para continuar amanhã.
- Caderno do piloto: data/piloto_supervisionado_20261023/avaliar.html.
  Para abrir no navegador, dar dois cliques em iniciar_piloto.bat na raiz.
  O arquivo aberto no editor é o mesmo HTML; a avaliação é feita no navegador.
- Estado dos arquivos do piloto: referência base com zero decisões preenchidas
  e 40 pendentes. O usuário fará a avaliação; não preencher em seu nome.
  Eventuais rascunhos no navegador não puderam ser verificados/exportados:
  não havia navegador conectado à ferramenta. Exportar progresso do piloto
  é necessário para guardar respostas fora do armazenamento do navegador.
- Retomada: ler este arquivo e PILOTO_SUPERVISIONADO.md; abrir o caderno,
  preencher identificação, avaliar poucos casos pelas fontes, depois comparar
  com a triagem, exportar avaliacao_piloto_preenchida.json e informar o caminho
  para calcular resultados. Importar progresso salvo permite retomar exportações.
- Não reiniciar auditoria ou revisão Gemini para retomar o piloto. Financeiro
  continua sem vínculos confirmados; a minuta de diligência da linha 175 está
  preparada em data/diligencia_financeira_175_20261023/solicitacao.md e NÃO foi enviada.
- Última validação: 188 testes Python e QA do piloto desktop/mobile aprovados;
  decisões e tempos de QA são fictícios. Nenhuma nova rodada nesta finalização.
- Backup completo desta finalização: backups/auditoria_salva_20261023_final.zip.
  Manifesto interno com hashes; integridade ZIP e SHA-256 no metadado
  backups/auditoria_salva_20261023_final.json e backups/ultimo_salvamento.json.
  Código, documentação, dados, cadernos e provas incluídos. Credenciais,
  dependências reinstaláveis, caches transitórios e backups anteriores excluídos.
  Backups anteriores preservados. Não foi criado commit nem feita publicação.

## Piloto supervisionado pronto; usuário fará avaliação — 23/10/2026

- Usuário aceitou o piloto e respondeu que ELE fará a avaliação. Não foi
  inventada identidade, qualificação profissional, decisão ou tempo de trabalho.
  Preparado caderno novo em data/piloto_supervisionado_20261023/avaliar.html;
  atalho iniciar_piloto.bat e roteiro PILOTO_SUPERVISIONADO.md. Mesmos 40 casos,
  20 com alerta/20 sem, ainda zero avaliados e 40 pendentes.
- Novo src/quality_pilot.py valida protocolo, identidade das fontes, registros,
  ordem de etapas, tempos e preservação da avaliação independente. Novo template
  src/quality_pilot.html; opção --piloto em src.quality_packet (caderno antigo
  continua disponível). Fonte/identificação profissional são autodeclaradas.
- Etapa 1: conferir fontes, cronometrar, registrar decisão/justificativa/fontes,
  ou deixar pendente por insuficiência. Marcar se já conhecia a triagem. A etapa
  pode ser reaberta antes de consultar o sistema. Etapa 2 só abre após encerrar
  a primeira; a primeira decisão fica bloqueada e a reavaliação é separada.
- Métricas usam apenas decisões independentes elegíveis; casos com exposição
  prévia ou etapa não encerrada ficam pendentes de validação. Ocultação na UI
  não constitui cegamento formal de pesquisa. Cobertura documental desigual
  permanece explícita; referência humana pode conter erros e pede segunda
  conferência independente das divergências. Não extrapolar aos 450 contratos.
- Cronômetro único por vez, pausa manual nas interrupções e automática ao
  fechar/recarregar; leitura de PDFs em outra aba continua contando. Exportação
  JSON e importação de progresso, com fontes e protocolo compatíveis. Arquivo
  incompatível recusado sem perda do rascunho. Usar uma aba por vez e exportar
  ao terminar cada sessão. Armazenamento do navegador pode não estar disponível.
- Tempo da conferência e tempo adicional de consulta são separados, incluindo
  etapas parciais; NÃO demonstram tempo economizado. Esse campo permanece null
  sem desenho comparativo independente. Mudanças de opinião não medem acerto.
- src.quality_evaluation aceita exportação do piloto e gera relatório com
  exclusões, tempos, reavaliações e métricas. Nenhuma resposta assistida entra
  no cálculo de precisão como referência independente.
- QA em frontend/scripts/verify_quality_pilot_ui.py: real somente leitura,
  40 decisões pendentes; decisões/cronômetros/exportação/importação testados
  SOMENTE em fixtures fictícias. Zero erros JS/rede automática/overflow; capturas
  desktop/mobile conferidas. Provas frontend/qa/quality-pilot-verificacao.json.
  Nove artefatos principais preservados por hashes. Sem frontend React novo,
  auditoria, Gemini, banco, alteração .env/modelo ou envio de decisões.
- Suíte Python: 188 testes aprovados, log data/test_runtime/quality-pilot-suite-20261023.log.
  QUALIDADE_ANALITICA.md e cópia consolidada atualizados. Backup incremental:
  backups/piloto_supervisionado_20261023.zip e metadado/hash no .json homônimo.
- Próximo passo DO USUÁRIO: abrir piloto, preencher identificação, começar
  poucos casos, exportar avaliacao_piloto_preenchida.json e informar seu caminho
  para calcular resultados. Não preencher avaliações pelo usuário nem afirmar
  que o piloto foi executado só porque o formulário está pronto.

## Fontes documentais do empenho e diligência pronta — 23/10/2026

- Usuário autorizou continuar procurando a nota correta da linha 175. Encontrada
  citação expressa da nota 4003/2026 no extrato do contrato 341/2026, processo
  12242/2026, CS BRASIL FROTAS S.A., no DOM Extraordinário 09 de 10/09/2026,
  página 5, coluna esquerda. PDF local com hash conferido, página inspecionada.
- Candidato PNCP 29131075000193-2-000413/2026 inspecionado ISOLADAMENTE:
  um PDF oficial de 1.202.501 bytes, 11 páginas extraídas, hash
  4de7bebd8f8447a5d1fa6b5f6721ba5380afc4290b1fd720846add4e681375cd.
  Identificação do contrato/processo/CNPJ na página 1; nota 4003/2026 na 10.
  Dotação coincide com o extrato: programa 68.01.06.181.0018.2076, elemento
  3.3.3.9.0.39.00.00.00, recurso 1704. Páginas 1,10,11 conferidas visualmente.
- Página 11 contém espaços de assinatura sem assinaturas visíveis; NÃO afirmar
  que foi obtido contrato assinado ou validada assinatura digital. A divergência
  de datas continua: portal 18/08/2026; extrato/metadado PNCP 01/09/2026. Vínculo
  PNCP continua conflitante; PDF não foi importado ao manifesto/RAG principal.
- Três consultas públicas adicionais por nome CS BRASIL, número 4003/2026 e
  unidade 1102/número 4003 vieram vazias, com filtros conferidos. Controle positivo
  por CNPJ encontrado na listagem atual retornou três registros, incluindo o
  empenho 5617/2026. Não extrapolar a cobertura ou afirmar ausência de despesa.
- Novo src/financial_diligence.py confere referências em escopo selecionado e
  gera pacote rastreável/minuta sem inventar decisões humanas ou pagamentos.
  Testes cobrem nota divergente/ambígua/ano malformado, contrato/processo/fornecedor,
  dotação e preservação da rejeição financeira. A nota original NÃO foi obtida.
- Entrega real em data/diligencia_financeira_175_20261023/: relatorio.md,
  diligencia.json, solicitacao.md (minuta NÃO enviada) e verificacao.json.
  Reprodução offline: frontend/scripts/prepare_financial_diligence175.py
  --saida NOVA_PASTA. Recusa pasta existente. Probes de rede separados em
  frontend/scripts/probe_alternative175.py e probe_financial_alternatives175.py
  (--real explícito). Fontes/provas em data/raw/financial_alternative175_20261023/.
- Nove artefatos principais preservados por hashes. Financeiro continua com
  30 relações rejeitadas em 20 contratos, zero confirmadas. Sem frontend novo,
  nova auditoria, Gemini, banco ou alteração .env/modelo. 181 testes Python
  aprovados, log data/test_runtime/financial-diligence-suite-20261023.log.
- EXECUCAO_FINANCEIRA.md e cópia consolidada atualizados. Corrigidas referências
  de caminho do backup anterior na continuidade (o ZIP original foi preservado).
  Backup incremental atual: backups/diligencia_financeira175_20261023.zip;
  metadado/hash em backups/diligencia_financeira175_20261023.json.
- Próxima dependência: obter nota original 4003/2026, versão assinada, processo
  e eventos com identificação por instituição/CNPJ. A minuta está pronta para
  solicitação ao órgão; não foi enviada pelo assistente. Não repetir as mesmas
  buscas vazias sem nova pista. Pode-se avançar em paralelo para outros contratos,
  cobertura documental e as 40 avaliações humanas, ainda pendentes.

## Linha 175: destino mudou e vínculo financeiro rejeitado — 23/10/2026

- Usuário pediu continuar pela identidade financeira da linha 175. Contrato
  341/2026, processo 12242/2026, CNPJ 27595780000116. O URL publicado para
  empenho 4003/2026 retornou agora 776/2024 em duas sessões independentes.
  Causa não determinada. O detalhe de 21/10 apresentava 4003/2026; histórico
  preservado. Associação passou de pendente a conflito, sem saldos atribuídos.
- Pesquisas reais limitadas por número 4003, pista 140921 do histórico e CNPJ/2026
  vieram vazias com filtros conferidos. Não comprova ausência de despesa.
  Provas em data/raw/financial_case175_20261023/, especialmente relatorio.md,
  fontes.json, controle_independente/resposta.json e publicacao.json.
- Novo src.financial.recheck_saved_detail reavalia uma relação com HTML
  rastreável, compara hashes/origem/data/registro e preserva histórico/cache.
  Script frontend/scripts/verify_financial_case175.py: padrão offline, --real
  atualiza duas fontes isoladas, --publicar publica apenas a relação com trava.
  Implementação testada para divergência, fonte adulterada/antiga e preservação
  de outras linhas. Reconsulta não confirma vínculos automaticamente.
- Publicação REAL com evidências locais: só linha 175 alterada; outras 93 e oito
  artefatos principais preservados. Principal agora tem 30 relações rejeitadas
  em 20 contratos, zero confirmadas, nenhum total financeiro por contrato.
  Consultas antigas mantêm cobertura/data; não foram repetidas as 94 linhas.
- UI exibe data da fonte por vínculo e aviso de reconsulta pontual. 177 testes
  Python, 45 frontend/Node e build aprovados; QA real somente leitura na 4173
  desktop/mobile com zero erros JS/overflow. Capturas financial-recheck-175-*
  conferidas. Servidor próprio 4173 encerrado ao concluir; 5173 preservado.
- Sem nova auditoria, Gemini, banco ou alteração de .env/modelo. Documentação e cópia
  consolidada atualizadas. Backup incremental em backups/financeiro_linha175_20261023.zip,
  metadado/hash em backups/financeiro_linha175_20261023.json.
- Próxima diligência: obter nota de empenho/processo 12242/2026 ou destino com
  identidade conferida por número, exercício, instituição e fornecedor. Não somar
  eventos de links divergentes. Restam cobertura documental/PNCP, preços e 40
  avaliações humanas; meta de qualidade integral ainda pendente.

## Dois PDFs grandes PNCP recuperados — 23/10/2026

- Usuário pediu continuar a evolução. Implementados limite documental explícito
  DOCUMENT_MAX_MB (padrão 10, máximo 50), validação dos limites e retomada seletiva
  por ID em src.documents, com CLI --documento ID --max-mb 50. .env real intacto.
- Retomada valida registro/links/assinatura e hashes dos PDFs preservados; rejeita
  documentos de outro contrato. Mantém os demais documentos no manifesto durante
  a execução e interrupção. Histórico anterior preservado. Tamanho conferido no
  cabeçalho e fluxo; erro informa limite real. Sem mudança de interface.
- Execução REAL limitada via frontend/scripts/verify_large_pncp_documents.py --real:
  linha 60, contrato 403/2026, 13.116.015 bytes, 17 páginas; linha 280, contrato
  299/2026, 12.415.084 bytes, 16 páginas. Ambos lidos, sem aviso do extrator.
  OCR local sujeito a erros; amostra visual 1/9/17 e 1/9/16 conferida, instrumentos
  com cláusulas e assinaturas. Digitalização tem cortes laterais; não certifica
  conteúdo integral. Primeira tentativa bloqueada pela rede restrita; nova
  execução com liberação da ferramenta concluiu. Nenhuma aprovação pendente.
- Preservados 214 documentos restantes, PDFs anteriores e nove artefatos
  principais por comparação de hashes/metadados. RAG anterior arquivado e
  reconstruído: 2.995 trechos, 470 pares contrato/página, 94 contratos (não
  significa 470 páginas físicas únicas). MCP stdio real recuperou trechos novos
  de ambas as linhas com hash/página. Não foi iniciada revisão Gemini.
- Indicadores depois regenerados com histórico: 22 linhas com PDF publicado
  extraído, 72 fichas/tipo não validado, 356 não processadas. Oito outros artefatos
  principais continuam intactos. Revisão antiga pode ficar oculta pelo novo
  contexto; não repetir automaticamente. Caderno humano anterior é retrato salvo.
- Provas: data/raw/large_pncp_20261023/verificacao.json e
  verificacao_mcp_indicadores.json; seis capturas de páginas no mesmo diretório.
  Suíte Python final: 175 testes aprovados, log
  data/test_runtime/documents-suite-20261023.log. Sem mudança frontend, banco,
  modelo ou nova auditoria. Documentação e cópia consolidada atualizadas.
- Backup incremental desta etapa: backups/documentos_pncp_20261023.zip;
  hash e conferência ZIP em backups/documentos_pncp_20261023.json. Não substitui
  backup completo anterior. PDFs novos, manifesto/RAG/indicadores, históricos,
  código/documentação e provas incluídos; credenciais não incluídas.
- Próximas frentes: anexos/aditivos e contratos sem instrumentos, vínculos PNCP
  candidatos/conflitantes, identidade e eventos financeiros. 40 avaliações humanas
  seguem pendentes; não preencher como humanas decisões da IA. Meta integral de
  qualidade ainda não atingida. Para ver fontes novas, atualizar o painel.

## Diagnóstico da qualidade retomado — 23/10/2026

- Usuário pediu continuar rumo à meta de qualidade do projeto. Próxima entrega
  realizada: avaliação com análise dos erros, cobertura por grupo e fila de
  segunda conferência independente. Não é atribuição de nota ou certificação.
- src/quality_evaluation.py inclui casos individuais, decisões/fontes humanas,
  cobertura com/sem alerta e linhas de falsos positivos/negativos. Nova opção
  --relatorio gera resumo Markdown; destinos existentes são recusados.
- Resultado REAL local em data/qualidade_diagnostico_20261023.json e .md:
  40 selecionados, zero avaliados, 40 pendentes (20 em cada grupo); precisão,
  sensibilidade e F1 null. Referência inicial e auditoria não foram editadas.
- Validação: suíte Python de 169 testes passou; após acrescentar teste CLI de
  preservação de saídas, os 12 testes de avaliação/caderno passaram. Log da
  suíte em data/test_runtime/quality-suite-20261023.log. Sem mudança frontend.
- Python da .venv continua sem iniciar; usado Python313 local com site.addsitedir
  para dependências da .venv. Caches da suíte apenas em data/test_runtime.
- QUALIDADE_ANALITICA.md e cópia consolidada atualizados. Sem nova auditoria,
  chamadas Gemini, consulta pública real ou gravação no banco nesta entrega.
- Próxima dependência humana: avaliar fontes no caderno e exportar referência;
  não preencher decisões humanas em nome do usuário. Próximas frentes técnicas:
  ampliar cobertura documental/PNCP e financeira, reconciliação de identidade e
  eventos, preços comparáveis e medições reais da operação. Meta integral ainda
  pendente; não interpretar ausência de avaliações como aprovação do sistema.

## Salvamento do frontend reorganizado — 21/10/2026

- Arquivos-fonte, documentação, caderno humano e resultados gravados.
- Backup desta retomada: backups/auditoria_salva_20261022T003026Z.zip.
- Hash SHA-256 e resultado da conferência ZIP em backups/auditoria_salva_20261022T003026Z.json
  e backups/ultimo_salvamento.json. Credenciais e dependências excluídas.
- Validação: 45 testes frontend/Node, build e QA desktop/mobile aprovados.
- Para retomar: ler este arquivo e usar Ctrl+F5 no painel reorganizado.

## Frontend organizado por tarefa — 21/10/2026

- Usuário relatou frontend bagunçado e enviou capturas: comandos, histórico,
  busca e resultados de todas as fontes ocupavam o início e todas as páginas.
  Reorganizado em Visão geral, Contratos, Evidências, Indicadores, Relatório,
  Operações e Como analisamos. Mesmos dados e ações; sem nova auditoria.
- Visão geral agora abre com acompanhamento compacto, quatro métricas,
  próximo passo e atalhos. Removidos a composição promocional e o cartão
  lateral que ficava cortado. Tabela só em Contratos; revisão dos agentes
  em seção expansível. Indicadores e relatório em áreas próprias.
- Evidências usa abas Documentos/PNCP/Financeiro/Busca local, acessíveis por
  teclado. Lista de conflitos financeiros recolhida; vínculos pendentes têm
  atalho. Busca local saiu da central de execução e mantém serviço existente.
- Operações tem grupos Auditoria/Fontes e documentos/Análise e revisão.
  Histórico e ferramentas avançadas recolhidos. RAG/MCP em Avançadas. Polling
  continua montado ao navegar; ação ativa e interrupção aparecem nas demais
  áreas. Navegar, abrir abas ou recarregar não inicia ações.
- Novos componentes Overview.jsx, EvidenceWorkspace.jsx e OperationsPanel.jsx.
  RunControls mantém transporte/token/travas existentes. Corrigidos os textos
  com caracteres quebrados e o progresso financeiro que podia herdar contadores
  de um resultado anterior. CSS revisado para legibilidade e desktop/mobile.
- QA em frontend/scripts/verify_workspace_ui.py: leitura REAL, POSTs somente
  simulados, navegação/abas/ação ativa/interrupção, zero erros JS, nove artefatos
  principais preservados por hashes. QA financeiro adaptado à nova navegação.
  Capturas frontend/qa/workspace-*.png e workspace-verificacao.json.
  45 testes frontend/Node e build aprovados. QA financeiro desktop/mobile
  também aprovado. Servidor próprio de QA 4173 encerrado; painel 5173 preservado.
- Para ver: Ctrl+F5 no painel. Não reiniciar auditoria ou revisão. Dados,
  avaliações humanas e regras do backend preservados. Documentação e cópia
  consolidada atualizadas. O caderno humano continua no caminho já registrado.

## Processo financeiro conferido e caderno humano pronto — 21/10/2026

- Usuário pediu continuar após as prioridades para qualidade. Implementada
  política de identidade financeira 2: além do empenho, compara processo e
  contrato explicitamente citados no resumo e CNPJ/processo da consulta quando
  disponíveis. Múltiplas referências ficam ambíguas; anos inválidos não são
  corrigidos. Divergências rejeitam saldos. Painel exibe as comparações.
- Conferência REAL isolada das linhas 96 e 175, em
  data/raw/financial_two_cases_20261021/verificacao.json. Linha 96: empenho
  5342/2026 coincide, mas P.A 7501/2026 diverge do processo 17900/2025 e há
  referência malformada 374/20260. Agora REJEITADA. Linha 175: empenho e processo
  coincidem, CNPJ não confirmado neste recorte; continua PENDENTE. Não concluir
  ausência de despesa a partir das consultas CNPJ/exercício vazias.
- Resultado principal atualizado com cache, sem novas respostas necessárias:
  job 20261021T195425Z_74b46b7e, CONCLUÍDO às 16:54:40 locais. 94 linhas,
  10 consultas, 30 detalhes; 29 relações rejeitadas em 19 contratos e uma
  pendente. Zero vínculos confirmados ou totais financeiros por contrato.
  Histórico anterior preservado. Oito fontes principais intactas por hashes.
- Criados src/quality_packet.py e template HTML local. Caderno em
  data/avaliacao_humana_caderno_20261021/avaliar.html: mesmos 40 casos,
  50 PDFs locais distintos com hash conferido, links oficiais, triagem original
  inicialmente fechada e campos humanos. Exporta JSON aceito pelo avaliador;
  exige responsável/justificativa/fontes para decisões. Rascunho local opcional.
- Referência REAL permanece zero avaliados/40 pendentes; precisão,
  sensibilidade e F1 null. Não foram inventadas decisões. Preenchimento e
  exportação testados SOMENTE com casos fictícios, sem publicar métricas reais.
  Exportação real sem respostas conferida idêntica à referência original.
- 166 testes Python, 44 frontend/Node, build, QA desktop/mobile financeiro e
  caderno aprovados. Zero erros JS, caderno sem requisições externas, imagens
  frontend/qa/financial-identity-* e quality-packet-* conferidas visualmente.
  Log Python em data/test_runtime/quality-financial-suite.log.
- QUALIDADE_ANALITICA.md e EXECUCAO_FINANCEIRA.md atualizados. Sem IA/banco,
  alteração de .env/modelo ou nova auditoria. Próximo passo humano: abrir
  caderno e avaliar fontes, mantendo insuficientes pendentes; exportar JSON
  para então calcular métricas. Financeiro ainda requer fornecedor/instituição,
  documentos e reconciliação dos eventos. Não repetir auditoria/revisão Gemini.

## Consulta financeira integrada e rodada real limitada — 21/10/2026

- Usuário pediu o próximo passo. Implementado src/financial.py e botão
  Consultar financeiro no executor Python/Node e painel, com visão geral e
  detalhes de identidade/saldos/movimentações por contrato. Sem IA/banco.
- Filtros CNPJ/exercício conferidos no HTML e nas linhas. Rotas municipais
  restritas, timeout, 8 MB/resposta, cache íntegro por até 24h, gravação atômica,
  histórico, trava e interrupção. Limites: 10 combinações CNPJ/exercício e
  30 URLs de detalhe por ação. Repetir mesmos limites revisita o mesmo recorte;
  não amplia automaticamente cobertura. CLI: python -m src.financial --execucao ID.
- Divergência do campo número/ano rejeita saldos do vínculo. Coincidência
  permanece PENDENTE de vínculo contratual, sem soma ou atribuição automática
  ao contrato. Eventos preservados literalmente, sem reconciliação de estornos.
  Dados financeiros não alimentam agentes/RAG/indicadores contratuais nesta versão.
- Rodada REAL na principal: job 20261021T194049Z_26e8a1ca CONCLUÍDO às
  16:41:09 locais. 94 linhas processadas; 10 consultas cobrem 11 linhas,
  69 fora do limite e 14 com identificação insuficiente. 30 detalhes: 28
  relações conflitantes em 19 contratos, rejeitadas; duas com número/ano
  compatível (linhas 96,175), ainda pendentes. 72 relações omitidas pelo limite.
  Zero vínculos financeiros confirmados; não afirmar 94 contratos reconciliados.
- Oito artefatos originais preservados por hashes, .env/modelo inalterados.
  Provas em data/raw/financial_integration_20261021/, logs em data/ui_jobs.
  API real verifica assinatura/hash de coleta, parecer e HTMLs de origem;
  fontes alteradas ocultam resultado. Sem importação financeira nesta versão.
- 159 testes Python, 44 frontend/Node e build passaram. QA Playwright desktop/mobile com POST simulado,
  conflito sem saldos, fonte obsoleta, zero erros JS e sem overflow; API e UI
  principal conferidas com resultado REAL. Capturas frontend/qa/financial-*.png.
  Documentação EXECUCAO_FINANCEIRA.md/FASE3.md/frontend atualizada.
  Código consolidado atualizado. Servidor próprio de QA na porta 4173 encerrado;
  painel do usuário em 5173 não foi encerrado.
- Reabrir iniciar_painel.bat para carregar rotas/ação novas. Resultado principal
  já está salvo. Próximo avanço: ampliar recorte e investigar rota de detalhe
  correta, reconciliar fornecedor/instituição/processo/eventos e obter notas,
  medições e atestos. Execução financeira continua NÃO AVALIÁVEL.

## Disponibilidade financeira e conflito de vínculo — 21/10/2026

- Usuário pediu continuar. Retomada pela verificação de disponibilidade de
  empenhos, liquidações e pagamentos, conforme próxima frente registrada.
  Pesquisa e inspeção pública limitadas concluídas; documentação em
  EXECUCAO_FINANCEIRA.md. Nenhuma funcionalidade financeira do painel entregue.
- Consulta municipal /e-cidade/consulta-empenhos e exportação CSV reais:
  118 registros no recorte inicial 2026, 44.663 bytes; todas as células HTML/CSV
  conferidas, dinheiro exato com Decimal. Não certifica completude municipal.
  Detalhe de um empenho tem itens, anulado e movimentações datadas.
- Inspeção dos 450 HTMLs já salvos: 348 linhas contratuais com tabela de
  empenhos, 102 com mensagem de nenhum empenho; 550 relações/URLs distintas
  inventariadas. Ausência no portal não comprova ausência de despesa.
- ALERTA DE IDENTIDADE: primeira relação da linha contratual 5 apresenta
  empenho 5512/2026, mas /e-cidade/contratos/padrao/26417/empenho retornou
  Número 3832 - 2021, rescisão e eventos de 2021. Associação REJEITADA.
  Não seguir links publicados como identidade comprovada: conferir campos
  específicos, exercício, instituição, fornecedor e processo. Causa não apurada;
  não afirmar que todos os 550 links são incorretos.
- Cruzamento exploratório por CNPJ/processo explícito: 31 pares candidatos
  em 27 linhas, zero confirmados. Não calculados pagamentos por contrato.
  Notas Fiscais do portal municipal apontam para o portal federal; cobertura
  de notas municipais, medições e atestos não demonstrada.
- Evidência e scripts em data/raw/financeiro_verificacao_20261021/: HTML,
  CSV, hashes, inspecao.json, verificacao.json e amostra_vinculada.json.
  conferir.py é offline; validar_link.py --offline revalida amostra salva.
  Requisições reais limitadas com escalonamento aprovado, sem IA/banco.
  Oito artefatos originais preservados por hashes; .env/modelo inalterados.
- Próximo avanço: implementar consulta financeira filtrada e reconciliação
  conservadora com bloqueio de identidade divergente, cobertura, cache e
  tratamento de eventos/estornos. Execução financeira dos contratos continua
  NÃO AVALIÁVEL. Não repetir auditoria ou revisão Gemini para esta evolução.

## Salvamento completo — 21/10/2026, 12h12

- Backup completo gravado em backups/auditoria_salva_20261021T151009Z.zip.
  2207 arquivos, 237,5 MB, integridade ZIP verificada (ok).
  SHA-256: fb2ee3194578008d0c64ca7d5fb3c558a5b1e264b75468b346d8fd81c1ceeeb5.
- Inclui código-fonte, documentação, frontend, dados da execução principal
  20261020T015002Z_72b23869, indicadores, PNCP, documentos, RAG, revisão
  incremental e avaliação humana. Exclui .env, .venv, node_modules e caches.
- Hashes dos artefatos principais preservados no metadado:
  contratos.json=e721481d7dfa1ec7, parecer.json=9c541bd8923bc758,
  relatorio.md=7d901358a704f559, revisao_agentes.json=2a02e5a44b97526d,
  indicadores.json=005ac6edfe64f512, documentos.json=0ed045e47087c7e8.
- Estado: indicadores gerados, PNCP consultado, RAG mcp_stdio ativo,
  revisão incremental concluída, 7 avisos de suporte para conferência humana,
  40 avaliações humanas pendentes em data/avaliacao_humana_20261021.json.
- Para retomar: ler este arquivo; reabrir iniciar_painel.bat; conferir
  execução, avisos e pendências. Não reiniciar revisão sem mudança de contexto.
  Backup anterior (03h04, 44,9 MB, 1342 arquivos) preservado no mesmo diretório.

## Indicadores pandas, painel e MCP — 21/10/2026

- Usuário pediu prosseguir após discutir pandas. Implementado
  src/management_analytics.py, ação Gerar indicadores no executor/painel,
  cobertura, distribuição por CNPJ e detalhes por linha. INDICADORES.md
  documenta regras, limites e resultado. pandas>=2.3,<3 no requirements;
  pandas 2.3.3 instalado na .venv local, sem mudar Python global ou .env.
- Centavos inteiros Python em colunas object: sem float ou soma int64.
  Identificadores textuais, zeros preservados, sem unir homônimos por nome.
  Associação dos quadros com merge one_to_one; manifestos duplicados rejeitados.
  Todas as identidades repetidas são excluídas da distribuição, sem escolher
  versões. Valores ausentes/inválidos não viram zero. Denominador explícito.
- Resultado REAL local em indicadores.json: 450 linhas, 94 com alertas;
  384 elegíveis, 66 excluídas (58 identidade incompleta, 8 repetida).
  321 CNPJs no recorte elegível; R$ 1.127.925.080,43 de valores contratuais;
  cinco maiores agregados=50,86%. Não é gasto, mercado completo ou fraude.
  Cobertura por linha: 20 com PDF publicado extraído, 74 fichas/tipo não
  validado, 356 não processadas. 19 PDFs PNCP físicos podem apoiar 20 linhas.
- Novo MCP consultar_indicadores(execucao, linha=None, limite_fornecedores=10),
  somente leitura de resultado salvo/atual. Não é chamado automaticamente
  pelos agentes. Consulta stdio real da linha 31 passou. Pandas é importado
  só no cálculo, evitando inicialização numérica no worker MCP de leitura.
  O primeiro ensaio MCP com import numérico no worker ficou sem resposta;
  foi interrompido e corrigido com importação tardia, reteste real aprovado.
- Indicadores vinculados a hashes de coleta/parecer/documentos/PNCP e a uma
  assinatura própria. Fontes alteradas ocultam o resultado no painel/MCP.
  Histórico em indicadores/historico. Sem alterar revisão, banco, modelo,
  documentos ou RAG; hashes conferidos. Zero chamadas IA/rede externa/banco.
- Validação: 149 testes Python, 41 frontend, build e QA Playwright com
  leitura REAL e botão POST simulado, desktop/mobile, zero erros JS.
  Imagens analytics-desktop.png e analytics-mobile.png conferidas.
  Provas em data/raw/analytics_verificacao_20261021 e frontend/qa.
- Reabrir iniciar_painel.bat para carregar ação/rotas novas. Indicadores da
  execução principal já foram gerados. Não precisa repetir auditoria/IA.
  Execução financeira continua NÃO AVALIÁVEL: faltam empenhos, liquidações,
  pagamentos, estornos e medições estruturados/reconciliados. Próxima frente
  é verificar disponibilidade desses dados municipais, além das pendências
  documentais/PNCP anteriores. Não inventar pagamentos a partir de contratos.

## Integração PNCP e instrumentos reais — 21/10/2026

- Usuário priorizou documentos completos e integração PNCP. Implementado
  src/pncp.py, ação Consultar PNCP no executor Python/Node, botão e visão
  geral/detalhes/importação no painel. Manual atual em PNCP.md.
- API oficial e resposta reais verificadas. CNPJ fixo do Município
  29131075000193, intervalo por PUBLICAÇÃO 01/01/2026..21/10/2026.
  Não cobre automaticamente outras entidades nem publicações fora do recorte.
  Catálogo real: 577/577 registros, duas páginas. Nos 94 com achados:
  22 confirmados por regras, 62 conflitantes entre candidatos, 3 candidatos,
  7 não localizados no recorte. Diferenças podem ser contratos distintos;
  não foram tratadas como irregularidades ou identidade comprovada.
- Vínculo automático exige candidato único, número/ano, processo e CNPJ
  coincidentes, sem divergência dos campos comparáveis (valor inicial/data).
  Só confirmados alimentam leitura. URLs HTTPS estritas e identidade do
  contrato/compra conferidas. Cache 24h com hashes, paginação e falhas explícitas.
- 22 vínculos disponibilizaram 21 PDFs únicos: 18 lidos, 1 parcial, 2 excedem
  10 MB (linhas 60,280). 19 PDFs extraídos, 223 páginas PNCP. Linha 274:
  parcial por imagem na página 10. Amostra visual do contrato da linha 31
  conferida em páginas 1,2,10; é instrumento com cláusulas/assinaturas,
  não ficha cadastral. Não afirmar validação integral dos 19 documentos.
- Manifesto atual: 216 IDs únicos, incluindo 2 downloads pendentes. Limite
  total padrão passa a 300 (5 links/contrato, 10 MB e 30 páginas/PDF mantidos);
  configuração explícita no .env prevalece. .env real não foi alterado.
- RAG reconstruído: 2838 trechos, 437 pares contrato/página, 94 contratos.
  Não são necessariamente 437 páginas físicas únicas. MCP stdio real
  recuperou trechos PNCP com origem, página e hash da linha 31; zero IA.
- Coleta/parecer/relatório/revisão/recibo/conferência e PDFs anteriores
  preservados por hashes. Manifesto anterior em documentos/historico;
  índice anterior em rag/historico; reconciliações em pncp/historico.
  Revisão anterior preservada pode estar OCULTA por fonte documental alterada.
  NÃO foi reiniciada revisão Gemini. Próxima revisão pode alterar contexto
  individual; usar Estimar revisão antes de decidir nova análise.
- Validação final: 141 testes Python, 39 frontend, build e QA Playwright
  desktop/mobile aprovados; imagens conferidas, zero erros JS. Provas em
  data/raw/pncp_verificacao_20261021/, frontend/qa/pncp-*.png.
- Reabrir iniciar_painel.bat para carregar novo executor. Consultar PNCP →
  Planejar documentos → Ler documentos → Preparar RAG → Verificar MCP.
  A execução principal já recebeu consulta/leitura/índice descritos acima.
  Sem mudanças no banco ou modelo. Não repetir para simples conferência.
- Pendências: conferir candidatos/conflitos e cobertura de outras entidades,
  resolver PDFs grandes com política explícita, obter documentos dos demais
  contratos e anexos/termos aditivos não inventariados nesta primeira versão.
  Não há aprovação manual de vínculos PNCP no painel nesta entrega.

## Evolução da qualidade analítica iniciada — 21/10/2026

- Usuário pediu elevar o projeto a “10 de 10”. Meta traduzida em critérios
  verificáveis em QUALIDADE_ANALITICA.md; não é nota ou certificação alcançada.
- Implementado src/quality_evaluation.py: amostra aleatória estratificada,
  referência humana vinculada por hashes à coleta/parecer/registro e matriz
  de confusão da necessidade de diligência. Conta casos perdidos e falsos
  positivos; pendências não contam como acertos, divisões sem denominador
  geram null. Exige responsável, justificativa e fontes para decisões.
- Criada data/avaliacao_humana_20261021.json na execução principal: 20 com
  alerta e 20 sem alerta, 40 avaliações PENDENTES. Nenhuma decisão humana
  inventada. Métricas futuras são da amostra, sem extrapolação populacional.
- Quatro testes direcionados passaram. Sem chamadas IA/rede/banco, alteração
  de .env ou reexecução da auditoria. Artefatos originais preservados.
- Solicitada preferência entre documentos/PNCP, execução e preços. Evolução
  completa ainda pendente; próxima prioridade sugerida: documentos completos
  e reconciliação PNCP, com validação atual da API e cobertura municipal.

Atualizado em: 21/10/2026.

## Salvamento final e revisão REAL concluída — 21/10/2026

- Usuário pediu salvar tudo. Código e documentação estão gravados; backup
  local em backups/ inclui código, documentação, painel e pasta completa da
  execução principal, sem .env, credenciais ou dependências instaladas.
- Retomada 20261021T043510Z_4dbabc3b CONCLUÍDA em 21/10/2026 às 02:58:05
  (America/Sao_Paulo). Não há mais essa revisão em andamento. Resultado:
  94/94 contratos, 13 reaproveitados, 81 analisados nesta rodada, 36/36 lotes,
  72 chamadas nesta execução, rag_transporte=mcp_stdio, incremental=true.
  Não houve erro final de gravação ou IA registrado.
- Conferência de suporte final gerada para 94 itens: 7 contratos com avisos
  para conferência humana, linhas 157,284,293,347,374,409,432. Esses avisos
  não são conclusões de irregularidade; ausência de aviso não comprova mérito.
- Coleta documental permanece: 195 fichas cadastrais, 192 lidas/3 parciais,
  RAG 1213 trechos, 202 páginas, 94 contratos. Os PDFs não são instrumentos
  contratuais integrais; próximo avanço documental é localizar os instrumentos
  e anexos, especialmente dos casos ainda pendentes. Não se iniciou essa busca.
- Auditoria base preservada: 450 contratos, 32/32 lotes, recibo de 94
  arquivamentos. .env/modelo/banco não foram alterados neste salvamento.
- Validação da correção: 130 testes Python, 36 frontend e build passaram;
  cinco testes de suporte também passaram após adotar a gravação comum.
- Para retomar: ler este arquivo; conferir a execução principal no painel,
  os sete avisos e eventuais novas ações. Não reiniciar a revisão concluída
  sem mudança de contexto ou pedido do usuário. Backup tem manifesto/hash e
  registro instantâneo de estado, com integridade ZIP conferida ao salvar.

## Correção de bloqueio de gravação e retomada REAL — 21/10/2026

- Job 20261021T040258Z_680860ed interrompeu às 01:19:25 locais, 13/94
  contratos, 6/42 lotes, WinError 5 ao substituir revisao_agentes.json.tmp
  por revisao_agentes.json. Não foi a IA: os 13 caches individuais estavam
  salvos. Houve uma rejeição anterior por limite/limites que foi corrigida
  pelo retry normal, sem relação com esta parada de gravação.
- Criado src/atomic_files.py: temporário exclusivo, substituição atômica,
  dez tentativas curtas para PermissionError/bloqueios Windows (até ~4s),
  destino anterior intacto em falha permanente; nenhum fallback de truncar
  JSON publicado. Batch pipeline, estado do executor e relatório de suporte
  passam a usar a função comum. Falhas de disco não são repetidas cegamente.
- Frontend traduz WinError 5/32/33 em motivo de gravação, sem mostrar caminho
  interno, preservando a indicação de checkpoints recuperáveis.
- Conferência REAL do planejamento encontrou um segundo problema: CrewAI
  guarda modelo sem prefixo gemini/, mas o planejamento passava o nome com
  prefixo. Corrigido SOMENTE no executor, sem tocar política/contextos que
  assinam os 13 caches válidos. Contratos recuperados=13, pendentes=81,
  36 lotes, 72 chamadas de etapas antes de repetições, 78 minutos em pausas.
  Prova em data/raw/atomic_verificacao/retomada.json, sem chamadas de IA.
- Testes de falha transitória/permanente, temporários exclusivos, erros de
  disco, leitor REAL bloqueando rename no Windows e identidade do modelo.
  Suíte final: 130 Python aprovados (incluindo bloqueio real e identidade do
  modelo), em data/test_runtime/atomic-suite.log. Após usar a gravação comum
  também na conferência de suporte, cinco testes desse módulo passaram.
  36 testes frontend e build passaram com mensagem de WinError.
- Retomada REAL já autorizada pelo pedido original, escalonamento aprovado:
  job 20261021T043510Z_4dbabc3b. Consultar estado atual; NÃO afirmar conclusão.
  Reaproveita 13, só envia pendentes ao Gemini. Não alterar modelo/.env/banco
  nem reiniciar outra revisão enquanto este job estiver ativo. Processo não
  deve ser encerrado como limpeza de QA.

## Documentos reais, RAG ativo e revisão incremental iniciada — 21/10/2026

- Usuário pediu executar os próximos passos e implementar retomada por
  contrato. src/incremental_review.py implementado; Revisar com agentes no
  painel agora usa incremental=True. Estimar revisão conta reaproveitados e
  pendentes reais. Contratos inalterados: zero novas chamadas; alteração em
  uma linha: somente ela é enviada a investigador/revisor.
- Assinatura individual inclui contexto da linha, modelo, skills e política.
  Exclui somente o hash GLOBAL do índice, preservando consulta, fontes/trechos,
  limites e assinatura documental LOCAL. Citações recuperadas são revalidadas.
- Lotes legados só migram após validar assinatura completa de ambas etapas e
  contexto da linha; política anterior adicional reconhecida explicitamente:
  58df97736b80da4740710d11d7b54391426286c352d2bdb64cfaabaac4e30ccb, prompt 3.
  Novos lotes em agentes/incremental/<hash>, cache por_contrato/<linha>.json;
  histórico anterior em agentes/historico/<hash>/ antes de nova publicação.
- Download inicial sem rede autorizada falhou (job 20261021T035103Z_24459989).
  Foi repetido com escalonamento aprovado: 20261021T035314Z_3528121f,
  concluído. 195 PDFs, 94 contratos, 192 lidos e 3 parciais, 202 páginas
  extraídas. TODOS classificados ficha_portal: não são instrumentos integrais.
  Não afirmar que leitura desses arquivos resolve os 13 avisos humanos.
  documents.save_json ganhou tentativas curtas de rename atômico para tratar
  bloqueio transitório de arquivo no Windows, sem publicação parcial.
- RAG REAL publicado na execução principal 20261020T015002Z_72b23869:
  1213 trechos / 202 páginas / 94 contratos. Job preparar_rag
  20261021T040032Z_be7ee0dd concluído; MCP stdio real confirmado pelo job
  20261021T040046Z_5dcf3b2f. Busca MCP nos 13 casos fez correspondências em 5;
  artefato data/raw/suporte_verificacao/triagem_documental_13.json. Busca não
  equivale a conferência humana; não se alteraram registros de revisão humana.
- Orquestração de vários jobs na MESMA sessão Python de ensaio causou
  I/O operation on closed file no planejamento (Rich/log guardava stream de
  job anterior); executor normal usa subprocesso separado para cada job.
  Planejamento repetido em processo próprio concluiu: job
  20261021T040143Z_61af8ba6, 0 reaproveitados / 94 pendentes / 42 lotes /
  84 chamadas de etapas antes de repetições / 91 minutos só em pausas.
  Todos ganharam contexto novo nesta primeira rodada documental.
- Revisão Gemini REAL solicitada e iniciada com escalonamento aprovado:
  job 20261021T040258Z_680860ed, processo inicial 3572, logs em data/ui_jobs.
  rag_transporte=mcp_stdio, incremental=true. NÃO afirmar conclusão: verificar
  estado atual do job/revisao_agentes.json. Processo independente do painel;
  Interromper usa cancel do executor. Revisão anterior 94/94 preservada em
  agentes/historico antes da publicação do novo contexto.
- Passaram 125 testes Python (cinco novos incrementais), 36 frontend e build.
  QA Playwright mobile/desktop de suporte confirmou contador incremental,
  avisos e atalhos. Sem mudança de modelo/.env ou banco PostgreSQL.
- Próximo acompanhamento: conferir progresso e eventuais rejeições/cota da
  revisão REAL; ao terminar, executor gera conferência de suporte nova. Não
  iniciar outro job enquanto este estiver ativo. Não interromper este processo
  como parte de limpeza de servidores de QA.

## Fontes citadas e triagem local de suporte — 21/10/2026

- Usuário autorizou as melhorias propostas; escopo comunicado: primeiros
  dois itens (transparência das fontes e conferência de extrapolações).
- Revisão real concluída em 20/10 às 23:43:39: 94/94, 19/19 lotes, na
  execução 20261020T015002Z_72b23869. Conferência dos registros confirmou
  rag_transporte=null, documentos_assinatura=null, sem documentos.json ou
  índice. Evidências citadas: 315 campos do portal e 32 publicações candidatas.
- Criado src/evidence_support.py, triagem determinística da explicação e
  citações: ausência financeira sem apoio explícito, pagamento/dívida,
  conclusões jurídicas categóricas, citações incompatíveis. Trata alguns
  padrões condicionais e negações; NÃO é validação semântica completa nem
  elimina falsos positivos/negativos. Ausência de avisos não confirma mérito.
- Novo botão Conferir suporte, fechado no executor Python/Node e rótulos de
  andamento. Sem IA/portal/banco. Gera verificacao_evidencias.json separado;
  exige coleta/alertas/fontes compatíveis. Execução pelo painel após revisão
  também gera a conferência automaticamente. CLI direto de revisão não gera.
- Frontend: fontes/páginas efetivamente citadas por contrato, distinção entre
  RAG citado, consulta MCP sem citação RAG, uso não registrado e não utilizado;
  inventário atual, pendências, OCR/ficha quando citados. Não afirma leitura
  integral nem confunde documentos disponíveis com documentos citados.
- Avisos aparecem antes da explicação original; classificação explicitamente
  identificada como da IA. Resumo possui botões para abrir cada linha com aviso.
  Conferência obsoleta (data/item diferente) é ocultada. Importação opcional do
  JSON de conferência, com validação defensiva na apresentação, também funciona.
- Conferência REAL local aplicada aos 94 itens, 13 com avisos: 17,75,84,257,
  284,293,312,383,409,422,432,440,450. Linha 432: possível confusão dívida e
  pagamento; demais: ausência financeira sem declaração explícita nas citações.
  Prova data/raw/suporte_verificacao/verificacao.json: hashes de contratos,
  parecer, relatório, revisão e recibo preservados; zero chamadas à IA.
  Não se alteraram modelo/.env, banco ou checkpoints dos agentes.
- Passaram 120 testes Python, 36 Node/frontend e build. QA Playwright com
  dados fictícios confirmou botão, seleção, fontes, avisos, atalhos, explicação
  preservada, obsolescência e mobile, zero erros JS. Imagens support-desktop.png
  e support-mobile.png em frontend/qa foram visualmente conferidas. API local
  real publicou 94 verificações/13 com avisos, revisão continua concluída.
- Documentação FASE3.md, frontend/README.md e consolidado atualizados.
  Reabrir painel para carregar novas rotas/ação. Próximas sugestões não feitas
  neste escopo: retomada por contrato com novidades, fila com responsáveis e
  prazos e medição de tempo/consumo/custo da IA.

## RAG textual local e agentes ligados ao MCP — 20/10/2026

- Pedido do usuário: implementar RAG e ligação dos agentes/MCP, com botões.
- Implementados src/rag.py (SQLite FTS5/BM25), src/mcp_server.py (SDK MCP
  oficial 1.28.1, stdio, somente leitura), src/rag_client.py (sessão real
  inicializada uma vez por revisão e consultas isoladas por execução/linha).
- A revisão usa resultados MCP para substituir as páginas iniciais por até
  cinco trechos relevantes de 700 caracteres; mantém catálogo literal e
  validação de evidências. Sem índice, compatibilidade com fluxo anterior;
  índice existente desatualizado bloqueia com instrução para reconstruir.
- Hash da coleta/manifesto, comparação do trecho com extração e SHA do PDF
  conferidos. Construção atômica; índice anterior preservado em falha.
  Não há embeddings ou busca semântica; não promete acelerar cotas/Gemini.
- Frontend: Preparar RAG, Verificar MCP, busca por linha/termos, página,
  link ao PDF preservado e origem/hash. Rotas locais com limites, sem shell.
- requirements.txt inclui mcp>=1.28,<2, já disponível no ambiente.
  requirements-rag.txt não exige mais LangChain/Chroma/OpenAI não usados.
  Entrada opcional mcp_auditoria.py e exemplo mcp.auditoria.example.json;
  nenhum cliente pessoal ou servidor externo foi configurado.
- Migração explícita adicional da política 38aee07c5d409e3842463853ddd94e2fea6487b2acbc841f9ed385a23d6d315c,
  prompt 3: só checkpoints com mesmos dossiês/modelo/skills e saída revalidada.
  Contexto RAG diferente invalida assinatura; base/banco não são refeitos.
- Testes: 115 Python (incluindo sete RAG), 34 Node/frontend e build passaram.
  Retomada em cópia dos checkpoints REAIS do primeiro lote também passou:
  duas etapas migradas/recuperadas, cinco contratos, zero IA; originais
  preservados (data/raw/agent_catalogo_20261021T014942Z/).
  QA Playwright desktop/mobile dos
  novos botões/pesquisa passou, zero erros JS; imagens conferidas.
- Ensaio REAL local, sem IA/rede/banco: cópia temporária do PDF já baixado
  da linha 109, cinco trechos indexados, conexão MCP real e recuperação de
  três trechos. Classificação ficha_portal preservada. Prova em
  data/raw/rag_verificacao/verificacao.json, originais_preservados=true.
  A execução principal ainda não possui documentos.json: usuário deve Ler
  documentos e Preparar RAG nela. Não se iniciou revisão Gemini nem download
  de todos os anexos. Reabra o painel para carregar as novas rotas do Vite.
- Documentação: RAG_MCP.md e READMEs/FASE3 atualizados. Não houve mudança
  em .env/modelo, auditoria principal, checkpoints originais ou PostgreSQL.

## Catálogo de citações e teste REAL autorizado — 20/10/2026, 22h23

Tentativa `20261021T010745Z_529d9fe5` terminou às 22h12min36s: lote 1
concluído (5/94), investigador do lote 2 rejeitado por citações acima de 700.

- Especialistas agora selecionam `citacao_id` de catálogo gerado em Python,
  com trechos literais até 700 caracteres e sobreposição de 100 nas fontes
  longas. Campos curtos só inteiros/não truncados. O revisor só pode selecionar
  pares aprovados pelo investigador. Schemas internos de seleção separados;
  o formato final fonte_id/trecho continua compatível com o painel.
- IDs desconhecidos, de outra linha, campos extras e citações não aprovadas
  são rejeitados. Toda seleção resolvida passa novamente pela validação de
  cobertura/fonte/literalidade. Não garante interpretação semântica.
- Migração explícita da política anterior
  327736634d6f854630f91943e85ccc6c22edb3b46f2639d8e11499f43463893c, prompt 2:
  só assinatura exata de dossiês/modelo/skills e saída revalidada. Permite
  reaproveitar as duas etapas do lote 1; outras políticas não são presumidas
  compatíveis. Auditoria base e arquivamento permanecem preservados.
- Auto-review inicialmente rejeitou o ensaio por envio ao Gemini sem consentir
  explicitamente no payload. Nenhum dado foi enviado nessa tentativa. Depois,
  o usuário respondeu **“Autorizo o teste real desse lote no Gemini”** para
  as linhas 43,46,48,57,60, sem alterar auditoria principal ou banco.
- Teste REAL autorizado concluído em data/raw/agent_catalogo_20261021T012102Z/:
  lote_2_real concluiu os cinco contratos, investigação + revisão, duas chamadas
  de etapas, sem rejeições/repetições. Pausas de 65s respeitadas. Resultado
  aceito no frontend (5 itens, zero incompatíveis). Não valida o mérito de
  todas as categorias nem toda a execução de 94 contratos.
- Subpasta retomada reaproveitou/migrou os dois checkpoints REAIS copiados do
  lote 1: cinco contratos, zero IA/esperas. Hashes de contratos/parecer/relatório/
  revisão e ambos checkpoints ORIGINAIS antes/depois: intactos. Recibo em
  verificacao.json. O ensaio não foi publicado na execução principal.
- Passaram 108 testes Python, 32 Node/frontend e build. Após acrescentar
  contagem de revisados na faixa de falha, cinco testes de status e build
  passaram. Script frontend/scripts/verify_agent_catalog.py: padrão verifica
  somente cache; --real envia apenas o segundo lote e requer autorização.
- Faixa de falha agora mostra também 5/94 e 1/19. Mensagens explicam trechos
  longos e IDs não permitidos. .env/modelo/banco não foram alterados.

Próximo uso: atualizar painel e Revisar com agentes. Preserva lote 1 e continua
pendentes. O lote 2 testado permanece isolado, por autorização explícita, e
não conta como checkpoint da auditoria principal. Não executar os 94 pelo
assistente automaticamente: a autorização desta vez foi para cinco linhas.

## Correção de JSON envolto em Markdown — tentativa das 21h56 (20/10/2026)

O usuário trouxe nova falha, ação `20261021T005416Z_59ca3017`, encerrada às
21h56min43s. Erro real: `Expecting value: line 1 column 1 (char 0)`.
As DUAS respostas completas do investigador estavam em blocos ```json.
O parser tentava `json.loads` diretamente sobre as marcações. Nesta tentativa
os valores curtos e as citações já eram válidos; o problema era só o envelope.

- Adicionado `parse_stage_response` em src/agent_review.py: JSON puro ou um
  único bloco Markdown JSON que contenha a resposta inteira. Aceita BOM/CRLF;
  remove apenas as marcações, sem reformular conteúdo. Prosa externa, vários
  objetos/blocos, fence incompleto e chaves JSON duplicadas são rejeitados.
  Esquemas, cobertura, fontes, literalidade e regras de citações continuam.
- Mensagem no frontend identifica erros de formato JSON, sem aviso genérico
  que obrigue abrir logs. O script de reprodução usa o mesmo parser.
- Revalidadas SEM nova IA as duas respostas REAIS salvas em
  agentes/0001/rejeicoes/investigacao-1792544134914826000.json e
  investigacao-1792544203344103100.json: ambas passaram leitura + validação
  contextual nas linhas 6,17,31,40,41. Não foram publicadas como revisão concluída
  nem inseridas checkpoints manualmente: a etapa do revisor segue pendente.
- Prova com hashes das respostas: data/raw/json_verificacao_20261021T005913Z/.
  Passaram 104 testes Python, 32 Node/frontend e build. Teste de fluxo cobre
  os dois agentes com envelopes simulados, sem repetição, e garante que citação
  inventada continua rejeitada. JSON de objetos duplicados/prosa também testado.
- Não houve chamadas Gemini, alteração de dados reais, .env ou banco. A
  mensagem “falhou” da ação antiga permanece histórica até nova execução pelo
  usuário. A política do especialista muda por código e os checkpoints
  adicionais afetados serão recalculados; a auditoria base não precisa repetir.

Para usar a correção: atualizar o painel e executar Revisar com agentes.
Validação real efetuada foi das respostas já recebidas, não execução completa
dos 94 contratos nem nova chamada ao revisor.

## Correção da falha repetida em Revisar com agentes — 20/10/2026

O usuário informou novamente “Revisar com agentes · falhou.” A tentativa
`20261021T003954Z_4306ae0e` parou às 21h42min22s (Brasília), 0/94 revisados.
Respostas retornaram `R$ 0,00` ou `R$ 0.00` (sete caracteres), rejeitados pelo
mínimo universal de oito. Também havia formatação de moeda divergente e
inclusão indevida do rótulo na citação, cujas rejeições continuam corretas.

- Corrigido `Citation` + `validate_stage`: transporte 1..700; prosa/documentos
  continuam exigindo >=8. Exceção menor que oito só para campo_portal inteiro,
  não truncado e literal da mesma linha. Não normaliza moeda, não aceita
  fragmentos curtos nem citações novas do revisor. Frontend importa com a mesma
  regra. A checagem de suporte semântico continua humana.
- `specialist_worker` fornece esquema JSON no prompt e recebe saída bruta,
  sem `output_pydantic`/`output_json` do CrewAI. Assim o Python captura a resposta
  inválida antes de validar/repetir, evitando diagnósticos com raw=null por
  falha de conversão interna. Não aumenta chamadas/tentativas. Referência:
  https://docs.crewai.com/en/concepts/tasks (TaskOutput RAW).
- Prompt versão 2 e procedimento documental explicitam igualdade literal e
  exceção de campo inteiro. Feedback usa exemplos de campos do próprio lote
  (prioriza valores) ou só pares já aprovados na investigação para o revisor.
  Não corrige silenciosamente a resposta para obter aceitação.
- Passaram 100 testes Python da suíte + um teste de transporte CrewAI separado
  com provider.call substituído (101 testes existentes agora), 32 Node/frontend
  e build. Cobertura: valor curto inteiro, fragmento, vírgula/ponto divergente,
  outra linha, documento curto, truncamento, revisor, JSON bruto/rejeição e retry.
- Reproduzido lote REAL 1 (linhas 6,17,31,40,41) com respostas SIMULADAS, sem
  rede/IA/banco. As duas etapas concluíram; os valores literais (inclusive
  R$ 0.00) passaram e duas respostas antigas não literais seguiram rejeitadas.
  Hashes de contratos, parecer, relatório e revisão originais intactos.
  Artefatos em data/raw/agent_citacoes_20261021T004943Z/, fora do painel.
  Script repetível: frontend/scripts/verify_agent_citations.py.
- `.env`, modelo, prompts/checkpoints da auditoria base e banco não alterados.
  Política/skill da revisão mudou e invalida os checkpoints adicionais afetados.
  O teste de integração real de Gemini após a correção ainda não foi executado;
  o usuário pode iniciar pelo mesmo botão. O histórico “falhou” da tentativa
  anterior permanece verdadeiro até uma nova ação, sem sobrescrever recibos.

## Verificação da execução e andamento visível — 20/10/2026, 21h32

O usuário perguntou se o botão ainda estava executando porque não via
andamento. Conferência de arquivos/processos: nenhuma auditoria Python ativa.

- Ação `20261021T000729Z_7646cdea` (Retomar auditoria) terminou às 21h10min40s
  de 20/10, horário de Brasília. Execução `20261020T015002Z_72b23869`: 450
  contratos, 32/32 lotes, progresso concluído. `arquivamento.json` agora confirma
  ok=true, 94 recebidos, 94 inseridos, zero ignorados. Isso resolve a pendência
  de confirmação de gravação dos blocos históricos; não houve inspeção remota
  do esquema pelo assistente, apenas leitura do recibo produzido pelo usuário.
- Ação `20261021T002030Z_3176ca2f` (Revisar com agentes) começou às 21h20min31s
  e falhou às 21h22min58s. Revisão interrompida no lote 1/19, 0/94 contratos,
  duas chamadas registradas. Primeira rejeição por citação não literal/fora da
  linha; tentativa seguinte falhou no esquema Investigation por citar
  `R$ 0.00` (sete caracteres), abaixo do mínimo de oito. Não foi espera de cota
  nem processamento ainda ativo. Motivo original preservado em revisao_agentes.json.
- Adicionado destaque ANTES dos botões: ação em andamento/nenhuma ação ativa,
  andamento dos lotes/documentos, etapa Investigador/Revisor, tempo decorrido,
  espera com contagem regressiva, horário de término e verificação do executor.
  Falha da revisão é separada do sucesso da auditoria base/arquivamento.
  Se perde conexão, não afirma que a execução parou. Outra execução ativa não
  recebe os contadores da seleção atual. Erros são explicados sem expor pilhas.
- `src/execution_progress.py`, batch_pipeline e agent_review publicam a fase
  antes das chamadas/esperas, sem alterar prompts, validadores ou assinatura dos
  lotes base. Checkpoints dos especialistas consideram código e podem invalidar
  pela alteração; nesta revisão real não havia lote concluído.
- Passaram 96 testes Python, 31 Node/frontend, build e Playwright com fixtures
  para parada/pausa/chamada/progresso automático e mobile. Capturas conferidas:
  frontend/qa/status-falha-desktop.png e status-ativo-mobile.png.
- Não houve reinício de auditoria, chamada Gemini, consulta externa, alteração
  de .env ou banco nesta verificação/correção. A causa da rejeição das citações
  NÃO foi relaxada para forçar aceitação. A revisão adicional continua pendente.

Atualizar a página do painel para carregar o novo destaque. Não pedir ao usuário
que fique aguardando a ação antiga: ela já terminou com falha. Não reexecutar
automaticamente os 94 contratos para testar a apresentação de andamento.

## Nova etapa — documentos/OCR e revisão humana (20/10/2026)

O usuário autorizou começar a evolução pesquisada e pediu incluir botões no
frontend quando necessários. Primeira entrega concluída: dossiês de PDFs e
registro de conferência humana. Plano completo em PESQUISA_EVOLUCAO_AUDITORIA.md;
PNCP, sanções, preços, competição e execução financeira ainda não implementados.

- Botões **Planejar documentos** e **Ler documentos** na central. Usam a
  execução selecionada, progresso/logs, interrupção e trava existentes.
  Planejar só conta; Ler consulta links já inventariados dos contratos com
  achados, sem Gemini/banco. Não inicia automaticamente os 94 contratos.
  Planejamento local REAL: 94 contratos, 195 PDFs candidatos, nenhum link
  omitido pelos padrões atuais. Somente contagem, sem baixar esse conjunto.
- `src/documents.py`: HTTPS/domínios municipais fixos, valida redirecionamentos,
  reconhece envelope JSON `{url}` do portal, limita PDFs a 10 MB, 5 links/contrato,
  200 PDFs/ação e 30 páginas/PDF por padrão. Texto e tabelas limitados com aviso.
  Cache por hash/política; retomada reutiliza originais íntegros e extrações.
- `src/windows_ocr.ps1`: Windows.Media.Ocr pt-BR, local/oculto/60s por página,
  sem instalar software ou alterar políticas. Idioma disponível nesta máquina.
  Erros ficam explícitos. OCR não garante números/datas; imagem deve ser conferida.
- Manifesto `documentos.json` e originais/cache em `documentos/` por execução.
  Exportações da ficha cadastral são diferenciadas do instrumento integral.
  Só links existentes na coleta; sem PNCP ou descoberta externa de anexos.
  PDFs já arquivados não são atualizados automaticamente pelo conteúdo remoto.
- Detalhes do contrato mostram fontes, páginas, tabelas, OCR, limites e hash.
  Importação aceita documentos.json; documentos incompatíveis com o registro
  são ocultados. Originais locais servidos por ID com verificação do hash.
- Histórico humano em `revisoes_humanas/<linha>.json`: responsável autodeclarado,
  nota/situação, instante e vínculo ao registro/motivos/documentos. Append,
  trava recuperável e versão anterior impedem sobrescrita concorrente. Fontes
  alteradas são sinalizadas. Sem alteração do parecer/fingerprint/banco.
- Revisar com agentes usa até 3 páginas/5000 caracteres documentais por contrato,
  com paginação/hash/tipo/OCR/omissões. Chamadas continuam pelo Gemini existente,
  só ao executar a revisão. A etapa documental não envia textos à IA.
  Política adicional mudou e pode invalidar checkpoints dos especialistas;
  checkpoints da auditoria base foram preservados. Nenhuma revisão real nova.
- Passaram 95 testes Python (12 novos), 26 Node/frontend (7 novos), build Vite
  e `frontend/scripts/verify_documents_ui.py` desktop/mobile 390px. Interface
  com fixtures, APIs de histórico/arquivo verificadas com servidores reais de
  teste. Capturas documents-desktop.png/documents-mobile.png conferidas.
- Ensaio REAL de UM PDF da linha 109: download retornou ficha cadastral, 1
  página/3004 caracteres nativos. Imagem conferida e OCR real reconheceu 1437
  caracteres, com erro em data (não usar como dado validado). Artefatos isolados
  em `data/raw/document_verificacao_20261020T235654Z/`, fora da lista do painel.
  Retomada SEM rede: assinatura estável, originais da auditoria intactos.
  Ensaios iniciais registraram restrição de rede e envelope JSON rejeitado;
  autorização automática da ferramenta permitiu testar a rede e o envelope foi
  implementado/validado. Nenhuma rejeição de aprovação pendente.
- `.env` e modelo não alterados. Não foram iniciados auditoria completa,
  documentos dos 94, envio ao Gemini ou gravação no Supabase nesta entrega.
  FASE3.md/README/frontend/código consolidado atualizados. Sem repositório/commit.

Para usar: fechar/reabrir iniciar_painel.bat, selecionar execução, Planejar
documentos → Ler documentos → abrir contrato e conferir/registrar revisão.
Revisar com agentes é uma ação separada com IA. Próxima entrega sugerida:
reconciliação com PNCP e checagem de sanções, validando cobertura de Maricá.

## Botões no frontend — correção concluída (20/10/2026)

O usuário cobrou os botões prometidos. A etapa anterior tinha implementado a
exibição de resultados, mas ainda dependia dos `.bat` para disparar trabalho.
Essa lacuna foi corrigida com a **Central de execução** no painel.

- Botões com ícones: Nova auditoria, Retomar auditoria, Consultar Diário e
  Revisar com agentes. Também Estimar revisão (sem IA) e Interromper enquanto
  houver uma ação ativa. Sem novos terminais, confirmação repetida ou VS Code.
- Ações existentes usam o ID selecionado no painel, não a auditoria mais recente.
  Nova auditoria recebe um ID próprio e passa a ser selecionada quando a coleta
  fica disponível. Mudança manual de seleção impede atualização do alvo anterior.
- Progresso/logs atualizam automaticamente; ações duplicadas são bloqueadas.
  Reabrir/recarregar recupera o processo ativo. Demonstração/importados não podem
  retomar/consultar/revisar; Nova auditoria fica disponível no executor local.
- `frontend/src/RunControls.jsx`: botões, acompanhamento, logs expansíveis,
  interrupção e estimativa. `App.jsx` acompanha dados da execução aproximadamente
  a cada 6s; controla concorrência com a seleção manual. Textos de ajuda antes
  referenciando os .bat agora apontam prioritariamente para os botões.
- `frontend/server/jobs.js`: serviço de ações no Vite/preview. Endpoints
  GET /api/control, GET /api/jobs/<id>, POST /api/jobs e POST /api/jobs/<id>/stop.
  Lista fechada de comandos, origem/host loopback, token efêmero, limite de corpo,
  sem shell/argumentos arbitrários. Logs limitados/redigidos para não mostrar chaves.
- `src/ui_jobs.py`: executor Python independente da vida da aba/Vite, estado/logs
  em `data/ui_jobs` (ignorado pelo Git), trava global entre ações do painel e
  sinal de interrupção por arquivo. Travas por execução existentes mantidas.
  Interrupção cooperativa pode aguardar a requisição/espera atual; não dispara
  nova ação enquanto o processo anterior está vivo. Checkpoints concluídos ficam.
- `src/main.main` aceita ID interno reservado para nova execução; CLI antiga
  preservada, sem mudança do prompt/assinatura dos lotes de auditoria.
- Python detectado pelo venv ou instalação Python313 do usuário, inclusive pelo
  diretório do perfil quando LOCALAPPDATA difere. Spawn com shell:false,
  argumentos separados e windowsHide:true. Credenciais só no Python, não no browser.
- Nova auditoria/retomar podem usar Gemini e gravar no banco; revisar usa Gemini
  sem banco; Diário não usa IA; estimativa não usa IA, portal ou banco. Os botões
  mostram essa distinção. O código foi entregue sem executar a auditoria completa.

### Validação dos controles

- Passaram 83 testes Python (8 novos), 19 Node/frontend (9 novos), build Vite e
  os roteiros Playwright anterior e novo `frontend/scripts/verify_controls.py`.
- Testados: ação/execução correta, comandos/caminhos/origem/token inválidos,
  pedidos simultâneos, recuperação por outro serviço, falha de lançamento, logs
  limitados, parada, recuperação de processo morto, reload, seleção automática
  da nova coleta, erro visível e bloqueios de demonstração/importação.
- Teste REAL do botão Estimar revisão: ação `20261020T051339Z_416602cf`, execução
  `20261020T015002Z_72b23869`, resultado concluído, 94 contratos, 19 lotes, 38
  chamadas de etapas e 41 min em pausas estimadas. Sem IA/banco/portal.
  Hashes de contratos.json, parecer.json e relatorio.md confirmados intactos.
- Primeira estimativa na QA restrita falhou ao criar cache CrewAI no AppData do
  usuário. Reteste passou com LOCALAPPDATA/CREWAI_STORAGE_DIR apenas do servidor
  de QA apontando para data/test_runtime. Ambiente do usuário/.env não foi alterado.
- Os demais cliques foram SIMULADOS via rotas Playwright e processos de teste,
  sem iniciar auditorias nem enviar os 94 contratos à IA. A amostra real da linha
  109 validada anteriormente continua isolada, conforme bloco seguinte.
- Artefatos: frontend/qa/controls-desktop.png, controls-mobile.png,
  controls-verificacao.json; metadados/logs em data/ui_jobs. Capturas conferidas.
  README frontend, FASE3.md e código consolidado atualizados.
- Servidor de QA em 4173 encerrado ao concluir; painel próprio do usuário em
  5173 não foi encerrado. Para carregar tudo, fechar/reabrir iniciar_painel.bat.

Para amanhã: usar os botões no painel para as próximas operações escolhidas pelo
usuário. O volume de 94 contratos/38 etapas segue pendente; não rodar esse lote
automaticamente só por existir implementação dos botões. A chamada a Nova ou
Revisar com agentes realiza o processamento descrito, por iniciativa do usuário.

## Teste real autorizado e concluído — linha 109 (20/10/2026)

O usuário respondeu explicitamente **“linha 109? sim autorizo”**, autorizando
o envio dos dados desse contrato ao Gemini. A pendência de autorização para
esse ensaio foi resolvida. Não estender essa autorização para executar os 94
contratos automaticamente: o teste solicitado era somente desta amostra.

- Executado `frontend/scripts/verify_agents.py` com o Gemini configurado:
  `gemini-3.5-flash-lite`. Ajustado o script para incluir a raiz do projeto em
  `sys.path`, permitindo executá-lo diretamente pelo caminho, e ativado log
  INFO para acompanhar as pausas. Não alterado o `.env` ou o código dos agentes.
- Amostra: linha 109, contrato 368/2026, processo 20857/2025,
  valor R$ 10.579.129,21. Só esse dossiê foi enviado aos dois agentes.
  Sem coleta nova, sem consultar portal/Diário novamente e sem gravar no banco.
- Resultado REAL: `concluida`, um contrato revisado, DUAS chamadas de etapas,
  uma investigação e uma revisão. Sem resposta rejeitada ou repetição necessária.
  Pausas de 65 segundos respeitadas antes das chamadas.
- Investigador identificou a declaração literal de serviços sem cobertura
  contratual e manteve limites quanto a anexos, medições e comprovantes não lidos.
- Revisor classificou `necessita_documentos`, explicou reconhecimento de dívida
  por serviços nos períodos 25/08/2024..31/12/2024 e 01/01/2025..24/07/2025,
  sem afirmar pagamento comprovado ou responsabilidade pessoal. Propôs solicitar
  o processo administrativo completo. Citações literais/linha passaram pelo
  validador e foram conferidas junto à fonte salva.
- Artefatos ISOLADOS em `data/raw/agent_verificacao_20261020T045515Z/`:
  parecer/relatório da amostra, dossiês, revisão, Diário já salvo filtrado à
  linha 109, checkpoints e `verificacao.json`.
- Hashes de `contratos.json`, `parecer.json` e `relatorio.md` da auditoria
  original comparados antes/depois: **original_preservado=true**. Nenhuma
  revisão foi inserida na execução original nem publicada na lista do painel.
- Retomada adicional conferida SEM API: os DOIS checkpoints reais foram
  recuperados e não houve nova chamada ou espera. Worker/espera substituídos
  por funções que falham se acionadas. Prova em `retomada_verificacao.json`.
  Esse reaproveitamento atualizou apenas os artefatos da amostra; o recibo
  inicial `verificacao.json` preserva as duas chamadas reais realizadas.
- A interface validada anteriormente pode importar revisões; esse ensaio não
  mudou o frontend. Os 75 testes Python/10 frontend anteriores permanecem a
  validação local; o ensaio acrescenta integração real de UMA amostra, não
  validação semântica de todas as categorias/contratos.

Para amanhã: decidir quando executar a revisão adicional da auditoria completa
com `revisar_achados.bat --execucao 20261020T015002Z_72b23869`. O planejamento
continua sendo 94 contratos, 19 lotes e 38 chamadas antes de repetições; a
amostra isolada não é um checkpoint dessa execução. Sem iniciar esse volume
automaticamente. Também avaliar outras categorias (preços, atas, quantitativos)
com amostras revisadas por uma pessoa e decidir a evolução de anexos/OCR/PNCP.

## Retomada para amanhã — agentes com skills (20/10/2026)

### Pedido e resultado

O usuário autorizou implementar agentes especializados com skills, integrados
ao sistema e ao painel, e pediu salvar o estado neste arquivo para amanhã.
Selecionou GPT-6.1 Sol no Codex para desenvolvimento. Essa seleção NÃO alterou
o modelo do aplicativo: ele continua usando o Gemini definido no `.env`.
O `.env` não foi editado e nenhuma credencial foi impressa ou copiada ao frontend.

Implementação concluída e salva nos arquivos, com validação local aprovada:

- Auditor original por lotes mantido; seu prompt e assinatura de checkpoints
  não mudaram. Auditorias anteriores não precisam ser refeitas para revisar.
- Dois novos agentes CrewAI em `src/agents/specialists.py`: Investigador
  Documental e Revisor dos Achados/comunicação. Execução sequencial controlada
  pelo Python, sem delegação, memória compartilhada, shell ou navegação pelo LLM.
- Cinco procedimentos locais em `src/audit_skills/`: documental,
  cobertura_contratual, precos_e_escopo, atas e revisao. Carregador/seleção
  condicional em `src/agent_skills.py`; seleção não gera achados. São recursos
  do aplicativo, NÃO skills instaladas no Codex nem dependência de uma nova
  API de skills do CrewAI. Biblioteca instalada foi mantida.
- Orquestrador `src/agent_review.py`, esquemas fechados em `src/review_models.py`.
  Só recebe contratos já sinalizados, seus motivos e campos/trechos documentais.
  Coleta, busca DOM/JOM e arquivamento continuam determinísticos em Python.
- Fluxo padrão: coleta → auditoria em lotes → DOM/JOM → investigação/revisão
  adicionais → arquivamento. Falha da revisão não bloqueia o arquivo da triagem
  original; fica marcada como interrompida e pode ser retomada separadamente.
- `src/main.py` agora expõe `create_audit_llm()` para reutilizar configuração
  sem duplicar chaves/modelos entre auditoria e revisão. Não troca o provedor.

### Evidências, saída e retomada

- Dossiês contêm campos do portal e até três referências candidatas do Diário
  por contrato. Não lê anexos do portal, não faz OCR nem consulta PNCP nesta
  nova etapa. Downloads e busca do Diário continuam em `src/gazette.py`.
- Campos limitados a 5000 caracteres por fonte, com truncamento/hash explícitos.
  Referências omitidas e cobertura parcial são informadas. URL de anexo não
  é tratada como conteúdo lido. Só links oficiais admitidos nos dossiês.
- Validador exige todas as linhas globais do lote, uma vez cada, fonte da mesma
  linha e citação literal de 8..700 caracteres. Revisor só usa pares fonte/trecho
  já aceitos na investigação. Motivos originais nunca são usados como comprovação.
- Saídas: contextualizado, necessita_documentos ou rever_alerta; explicação
  simples, limite, próxima diligência e citações. Não são revisão humana,
  conclusão jurídica ou prova de fraude. A checagem literal não garante a
  interpretação. Não se alteram motivos, índices ou fingerprints do parecer.
- Arquivos: `dossies_agentes.json`, `revisao_agentes.json`,
  `agentes/NNNN/investigacao.json`, `agentes/NNNN/revisao.json` e `rejeicoes/`.
  Relatório recebe seção idempotente com marcadores revisao-agentes.
- Cada etapa tem assinatura com dossiês/registro original, modelo, skills,
  prompts/validadores/código. Alterar evidência/política invalida somente a
  revisão adicional. Se o revisor falhar, investigação concluída é reutilizada.
- Pausas de cota também entre os novos agentes; 429 por minuto respeita espera;
  limite diário interrompe. Até uma repetição por resposta inválida, guardando
  saída original/diagnóstico. Checkpoints recuperados não chamam o modelo.
- `REVIEW_AGENTS_ENABLED=true`, `REVIEW_BATCH_SIZE=5`,
  `REVIEW_BATCH_MAX_BYTES=48000`, documentados em `.env.example` e FASE3.md.
  Usa `AUDIT_INTERVAL_SECONDS=65` e `AUDIT_QUOTA_RETRIES=2` existentes.

### Como usar amanhã

- `revisar_achados.bat --planejar`: somente planejamento, sem Gemini/banco/portal.
- `revisar_achados.bat`: revisa a auditoria salva mais recente com parecer,
  reutiliza checkpoints, chama Gemini, NÃO coleta nem grava no banco.
- Para escolher a mesma execução do painel, usar `--execucao ID_DA_EXECUCAO`.
  Por padrão o .bat não lê a seleção do navegador.
- Equivalente: `python -m src.agent_review --execucao ID [--planejar]`.
- Novas auditorias ativam a revisão automaticamente após o Diário; desativação
  só do automático por `REVIEW_AGENTS_ENABLED=false`. .bat explícito continua
  disponível. Não foi iniciada uma nova auditoria real nesta implementação.
- Planejamento REAL somente local da execução `20261020T015002Z_72b23869`:
  94 contratos com achados, 19 lotes, 38 chamadas de etapas antes de possíveis
  repetições. Aproximadamente 41 minutos apenas em pausas se tudo for novo,
  além da latência do modelo. Não fez chamadas nem modificou o parecer original.
- Painel: clicar Atualizar; bloco de acompanhamento mostra revisados/total.
  Abrir contrato → **O olhar dos agentes especialistas** → expandir citações
  e procedimentos. Importação aceita `revisao_agentes.json` junto de contratos,
  parecer e Diário utilizado. Registros/motivos/consulta do Diário diferentes
  ocultam a revisão antiga com aviso, evitando atribuição a outro contrato.

### Testes e limites da validação

- Passaram 75 testes Python (14 novos), 10 frontend (3 novos), build Vite e
  Playwright desktop/mobile 390px. Cobre retomada de etapa, invalidar por fonte/
  modelo/skill, bloqueio de citação falsa/outra linha, duplicatas/cobertura,
  rejeições com feedback/saída original, cota/minuto/diária, ausência de achados
  sem chamadas e falha adicional sem bloquear arquivamento.
- UI testou importação da revisão, citações expansíveis, acompanhamento, fontes,
  resumo anterior, relatório, downloads e ausência de overflow/erros JS.
  Capturas conferidas visualmente: `frontend/qa/agents-desktop.png` e
  `frontend/qa/agents-mobile.png`; dados demonstrativos, não achados reais.
- As chamadas dos novos agentes foram SIMULADAS nos testes locais. Inicialmente,
  a amostra REAL planejada para a linha 109 NÃO FOI EXECUTADA: auto-review rejeitou a
  execução por envio de dados contratuais ao Gemini sem autorização específica
  do usuário para esse payload. Nenhum dado foi enviado nesse ensaio.
  O usuário autorizou posteriormente e o teste foi concluído: ver bloco acima.
- Script opcional `frontend/scripts/verify_agents.py` foi preparado inicialmente
  e depois executado com autorização. Usa somente a linha 109 da auditoria existente, reaproveita os
  trechos do Diário, salva em `data/raw/agent_verificacao_<UTC>/`, não chama banco
  nem portal, e compara hashes para conferir preservação dos originais.
  Só executar pelo assistente após o usuário autorizar esse envio ao Gemini.
- Não houve gravação real no Supabase nem mudanças nos relatórios reais durante
  esta implementação. A revisão real de uma amostra está isolada; os 94 contratos
  da auditoria original ainda não receberam a nova revisão completa.
- A execução anterior do Diário FEITA PELO USUÁRIO já consta nos arquivos:
  consulta_parcial, 40 edições, 94 consultas, 68 contratos com referências
  candidatas, nenhuma falha registrada. Corrige a pendência histórica abaixo;
  um contrato individual pode não ter correspondência nas edições consultadas.
- `FASE3.md`, `FASE3_CODIGO.md`, README da raiz/frontend atualizados.
  `data/test_runtime/` foi incluído no .gitignore para os caches dos testes.
  Este diretório não é um repositório Git; não foi criado commit.

O passo antes pendente de autorização/ensaio real foi concluído no bloco acima;
para amanhã resta decidir quando rodar as etapas adicionais dos 94 contratos.
As sugestões anteriores de PNCP, OCR/anexos, preços comparáveis e revisão humana
com histórico continuam como evolução futura, não foram implementadas neste lote.

## Retomada em 19/10/2026

### Estado final desta retomada

Consulta ao Diário Oficial / JOM — 20/10/2026:
- Implementado `src/gazette.py`, etapa automática após análise apenas para
  contratos com achados, antes do arquivamento. Não chama Gemini, não muda
  motivos/índices/fingerprints. Falhas de consulta ficam explícitas e não impedem
  o arquivo no banco. `.env` real não foi modificado; padrões estão no código.
- `consultar_diario.bat` permite pesquisar a execução mais recente com parecer,
  sem nova auditoria e sem banco. CLI aceita `--execucao ID`.
- Fontes públicas reais verificadas: API WP tipos dom, dom-extraordinario, jom,
  jom-especial e PDFs das páginas oficiais. Prefeitura indica JOM para arquivo
  histórico até 09/03/2026; DOM atual também tem edições extraordinárias.
- Busca por contrato/ano e processo/ano. CNPJ próximo reforça candidato; CPF não
  é utilizado. Publicações são candidatas, nunca confirmação de irregularidade.
  Texto de colunas diferentes é separado por heurística de corredor central.
- Configurações: GAZETTE_ENABLED=true, MAX_EDITIONS=40, CATALOG_PAGES=2,
  CACHE_HOURS=24 (todos com prefixo GAZETTE_). Limites e falhas explicitados.
  Sem OCR; páginas sem texto ou limites tornam a cobertura parcial.
- Artefatos: diario_oficial.json, seção no Markdown/parecer, PDFs e texto em
  data/gazette_cache (ignorado pelo Git). Interface mostra referência, página,
  trecho, critérios e link. Importação aceita o JSON da consulta.
- Passaram 61 testes Python, sete frontend, build e verificação UI. Validação
  real baixou ED.145 do DOM (11 páginas), localizou contrato 415/2026 e processo
  21263/2025 na página 4, coluna 2; página conferida visualmente. Artefatos de
  QA em data/raw/gazette_verificacao_20261020/. Sem Gemini/Supabase na validação.
- A busca completa dos 94 contratos atuais ainda não foi executada; usar o
  novo .bat. Os resumos/achados anteriores e checkpoints foram preservados.

Resumo simples dos achados — 20/10/2026:
- A pedido do usuário, contratos com achados apresentam uma explicação simples
  em três blocos: problema principal; significado prático; diligência sugerida.
- Catálogo compartilhado `src/summary_rules.json`, gerador Python
  `src/plain_summary.py` e renderer cliente `frontend/src/simpleSummary.js`.
  Explicações por regras, sem chamadas adicionais ao Gemini. Casos não cobertos
  recebem orientação geral e acesso à fundamentação técnica original.
- A consolidação agora inclui resumos no Markdown e `parecer.json`, além de
  `resumos.json`. Não altera motivos, índices ou fingerprints de arquivamento.
- Executado gerador local para `20261020T015002Z_72b23869`: 94 resumos,
  incluindo linha 109 (dívida reconhecida de R$ 10.579.129,21, processo
  20857/2025). Não afirmou pagamento comprovado nem responsabilidade definida.
- Frontend mostra resumo antes da fundamentação técnica expansível; também
  funciona com auditorias antigas/importadas. Vite permite o catálogo JSON
  específico fora do frontend, sem ampliar acesso a pastas de credenciais.
- Passaram 49 testes Python, seis frontend, build e verificação Playwright
  desktop/mobile com resumo e fundamentação expansível. Sem APIs externas.

Correção posterior — consolidação após os 32 lotes concluídos:
- `20261020T015002Z_72b23869` concluiu todos os 32 checkpoints e 450 linhas,
  mas a reconciliação global falhou por misturar `Detalhe - Processo` com
  `Nr [Nr Processo]` na mesma chamada a `field`, que rejeita múltiplas colunas.
- Corrigida a seleção: detalhe do processo é preferido; se vazio/ausente,
  usa os aliases da listagem. Ambiguidade real dentro da mesma fonte continua
  sendo erro. A política de análise/checkpoints não mudou.
- Os 45 testes locais passaram. Consolidação REAL foi executada com provider
  bloqueado por função que falha se algum checkpoint precisar de nova análise.
  Reutilizou os 32 checkpoints e salvou parecer.json, relatorio.md e
  coincidencias.json. Resultado: 450 linhas analisadas, 96 achados, 94 contratos
  preparados para arquivar e 30 grupos de coincidências para diligência.
- Não houve chamadas ao portal, Gemini ou banco nessa consolidação.
  `progresso.json` está em `analise_concluida`; recibo de arquivamento ainda
  pendente. Retomar via `retomar_auditoria.bat` para concluir a gravação.

Correção posterior — rejeição do lote 6 pelo guardrail:
- Execução `20261020T015002Z_72b23869` parou no lote 0006; cinco checkpoints
  concluídos, cobrindo 66 linhas. O motivo informado pelo validador foi referência
  a valor zerado na linha local 10, cujo valor publicado é R$ 312000.00.
  A resposta rejeitada não havia sido salva, portanto não se pôde determinar
  se foi afirmação incorreta do modelo ou expressão negativa/citação capturada
  pelo regex. Não se alterou o validador nem os dados para forçar aceitação.
- `batch_worker` agora salva respostas rejeitadas e diagnósticos em `rejeicoes/`,
  pede revisão com os valores por linha e espera 65s entre tentativas (até 3).
  Falha persistente retorna `AuditValidationError`, com mensagem curta no main.
- Critérios e assinaturas de validação foram mantidos para reutilizar os lotes
  anteriores. Não se descarta achado nem se inventa outro motivo automaticamente.
- Os 42 testes locais passaram, incluindo revisão com feedback, preservação da
  resposta original e interrupção após três falhas. Gemini/portal/Supabase não
  foram chamados nessa verificação. Retomar por `retomar_auditoria.bat`.

Correção posterior — erro 429 do Gemini na nova auditoria:
- Log enviado pelo usuário mostra cota de entrada por minuto excedida,
  250000 tokens, modelo gemini-3.5-flash-lite; retryDelay de 45s.
- Coleta preservada em `data/reports/20261020T013117Z_fa0fddf9/contratos.json`,
  com 450 registros e cerca de 1,5 MB. Não há parecer/recibo dessa execução.
- `src.main` usa agora `src/batch_pipeline.py`: coleta e arquivo determinísticos,
  Auditor CrewAI/Gemini por lote independente (15 registros/48000 bytes padrão),
  65s entre chamadas, retry com espera para 429 e checkpoints por lote.
- `retomar_auditoria.bat` reutiliza a coleta pendente e checkpoints compatíveis.
  `--retomar --planejar` passou: 32 lotes, aproximadamente 34 min em pausas
  além da análise. Planejamento não chamou portal, Gemini ou banco.
- Todos os lotes devem ter cobertura e índices locais válidos antes de converter
  para índices globais. Arquivamento ocorre apenas após consolidar tudo.
- Comparações exatas globais em `coincidencias.json` não equivalem a reconciliação
  semântica por LLM. Limitação aparece no relatório final.
- `progresso.json` é exibido pelo frontend via serviço local, com atualização
  manual. Build passou. Os 40 testes Python locais passaram, com quota simulada,
  retomada, índices, invalidação de cache, trava e bloqueio de arquivo parcial.
- `.env` não foi modificado; novas opções estão em `.env.example` e FASE3.md.
  Não se efetuou nova auditoria real no Gemini/Supabase após esta correção.
- `src/crew.py` (três agentes) está preservado como implementação histórica;
  não é mais o caminho padrão de `src.main`.

Frontend React + Vite criado em `frontend/`, com ícones Lucide, layout
responsivo verde/creme, visão geral, filtros/busca/paginação, detalhes de
evidências, relatório Markdown, exportação CSV e importação de JSON.
`iniciar_painel.bat` abre o painel local em 127.0.0.1:5173 sem VS Code;
`iniciar_auditoria.bat` continua executando a auditoria Python separadamente.
Serviço Vite local somente leitura em `/api/runs` e `/api/runs/<id>` lê os
arquivos de `data/reports`; não usa .env nem grava no Supabase. Demonstração
fictícia é explicitamente rotulada. Não houve publicação na internet.
Dependências npm instaladas, build e quatro testes de dados passaram.
Verificação Playwright passou em desktop e mobile (390 px), cobrindo API local,
filtros, detalhes, importação e downloads, sem erros JS. Capturas em
`frontend/qa/` (ignorado pelo Git). Documentação em `frontend/README.md`.

Atualização posterior — detalhes e exportação do portal:
- Mantido Playwright. Inspeção pública real confirmou `select[name=year]`,
  atualização do ano por PUT `/configurar/ano`, pesquisa por POST `/pesquisar`,
  ícone com link `/<id>/visualizar` e exportação CSV por download do navegador.
- Corrigido seletor `ano` para `year`; falha em confirmar ano/pesquisa interrompe
  a coleta. Espera as respostas dessas operações, que usam AJAX.
- Coletor preserva o texto de `.aviso-resposta` do Objeto e URL individual.
  `src/tools/portal_details.py` consulta os detalhes na mesma sessão, adiciona
  campos `Detalhe - ...`, status e links publicados; salva HTML em `detalhes/`.
  Falha ou link ausente ficam explícitos. URLs externas não são seguidas.
- Na execução pela Crew, tenta salvar `exportacao_portal.csv` e registra status
  em `exportacao.json`, sem presumir completude da exportação. Exportação não
  substitui a tabela usada na auditoria.
- Verificação real com Playwright leu 19 campos/seções de um contrato e baixou
  CSV de 622625 bytes em `data/raw/portal_verificacao_20261019/`, sem Gemini
  nem Supabase. Não foi uma execução integral da aplicação ou de todos os detalhes.
- Os 29 testes locais passaram após essas alterações, incluindo detalhes,
  exportação simulada, falha de filtro e preservação dos dados de origem.
- Links de PDFs/documentos são inventariados, mas seus arquivos não são baixados
  nem lidos automaticamente. Prompt distingue links de conteúdo efetivamente lido.
- Permanecem os limites e falhas de paginação descritos abaixo; a coleta integral
  e o volume de contexto do Gemini continuam pendentes de validação.

Os registros anteriores abaixo descrevem etapas anteriores desta retomada.

Após exemplo enviado pelo usuário sobre escolas modulares, atualizado o prompt
em `src/tasks/audit_contracts.py` para examinar preços comparáveis, composição
de custos, vantajosidade frente a alternativas e origem/situação de atas.
Exige evidência literal, limites, documentos e diligências, com matriz de
avaliabilidade no relatório. Notícias não comprovam fatos automaticamente.
Removida substituição automática de falso valor zerado por suspeita de
sobrepreço. Agora a alegação é rejeitada se não houver zero confirmado, usando
Decimal e aliases monetários. Os 21 testes locais passaram, incluindo três
novos testes de validação. Isso não valida a qualidade do raciocínio do Gemini.
Ainda não há coleta/leitura de PDFs, planilhas de custos, estudos técnicos,
atas, decisões oficiais ou referências de mercado: só a tabela do portal.
Logo, os critérios novos orientam triagem e pedidos de documentos; não
implementam investigação documental automática ou detecção comprovada de
sobrepreço. O relato específico do TCE fornecido pelo usuário não foi verificado.

Criado `iniciar_auditoria.bat`: inicia com dois cliques, usa a pasta do proprio
arquivo, verifica `.env`, ativa saida UTF-8 e preserva a janela ao terminar.
Tenta o Python da `.venv` e, se indisponivel, Python313 no LOCALAPPDATA com
as dependencias da `.venv`. `iniciar_auditoria.bat --verificar` passou sem
acessar servicos externos; a auditoria real nao foi iniciada nessa verificacao.

O usuário escolheu manter Playwright. Os testes da Fase 3 foram adaptados
para navegador simulado: preservação de linhas/textos longos, seleção de 2026,
paginação, botão desabilitado, filtro de vigência e rejeição de erros.
Os 18 testes da suíte passaram, incluindo moeda e persistência local SQLite.
Corrigida a validação `ContractBatch` para rejeitar registros com chave
`Erro`/`error`, também quando lidos pelo arquivista. Removidos emojis dos
prints do coletor para evitar falha de codificação no terminal Windows.
Os itens abaixo descrevem o diagnóstico anterior a esses ajustes.

Limitações atuais do Playwright: pode continuar após falha na seleção do ano,
aceita registros sem vigência mesmo com assinatura de outro ano, ignora linhas
com colunas inconsistentes, elimina duplicatas e pode retornar coleta parcial
após falha de paginação ou limite de 50 páginas/500 registros. Os testes não
comprovam completude real. A migração no Supabase segue sem confirmação.

- O código atual do coletor difere do histórico abaixo: `extrator_api_tool.py`
  usa Playwright, ano 2026 fixo, deduplicação e limite de 500 registros.
  Não estão mais disponíveis `BASE_URL`, `parse_table` e `next_link`, exigidos
  pelos testes da Fase 3. Preservada essa alteração; aguardando escolha do
  usuário entre manter Playwright e retomar HTTP.
- Corrigido `parse_brl` para aceitar `R$ 1.234,56` e `1.234.567,89`, preservando
  decimais com ponto (`1234.56`). Formatos ambíguos e não finitos são rejeitados.
- Onze testes passaram; o módulo `test_phase3` não foi importado por
  incompatibilidade com o coletor atual. Seus seis testes não executaram.
  O parser passou separadamente em onze casos, por extração da função via AST.
- O executável da `.venv` não iniciou. Foi usado Python 3.13.4 em
  `C:\Users\lucia\AppData\Local\Programs\Python\Python313\python.exe`, com
  `site.addsitedir` apontando para `.venv/Lib/site-packages`. Para os testes,
  LOCALAPPDATA e CREWAI_STORAGE_DIR foram redirecionados apenas no processo
  para `data/test_runtime`, e OTEL_SDK_DISABLED=true.
- Nesta retomada não foram acessados Supabase, Gemini ou portal, nem lido o `.env`.
  A migração remota continua sem confirmação. A cópia `FASE3_CODIGO.md` ainda
  não reflete esta correção do parser; priorizar os arquivos-fonte.
Diretório de trabalho: `D:\Auditoria_Cidada`.

## Ponto de retomada mais recente

As alterações estão salvas nos arquivos locais. A última correção foi o
alinhamento de `UNIQUE(fingerprint)` com `ON CONFLICT (fingerprint)`.
O próximo passo é confirmar/aplicar `migrations/001_unique_fingerprint.sql`
no SQL Editor do Supabase, no mesmo banco e schema usados pela aplicação,
seguindo `migrations/README.md`, e então executar novamente `python -m src.main`.
O usuário ainda não confirmou a aplicação dessa migração nem o sucesso de
uma gravação após a correção. O assistente não acessou o banco remoto.

Na última rodada passaram três testes de constraint e seis testes de índices
de arquivamento (nove testes direcionados). Isso não representa uma nova
execução integral de toda a suíte. Os oito testes da Fase 3 descritos adiante
são um registro histórico da implementação inicial.

Alterações locais feitas pelo usuário e preservadas: alias de processo
`nr [nr processo]`, alterações no parser monetário e validação apenas
estrutural do parecer em `audit_contracts.py`. O parser monetário atual
difere do original; convém testar novamente formatos com ponto de milhar
e vírgula decimal antes de processar novos lotes.

Este salvamento atualiza a documentação e a cópia consolidada de código;
não cria commit Git, não publica arquivos e não aplica mudanças no Supabase.

## Objetivo

Construir um sistema Python de coleta e auditoria inicial de contratos públicos
do Portal da Transparência de Maricá/RJ. Identificar indícios para diligência,
como valores zerados, objetos vagos e coincidências entre contratos, preservando
os dados de origem. Indícios não representam comprovação de fraude ou ilegalidade.

## Histórico das decisões e entregas

### Fase 1 — estrutura e coleta

- Criada estrutura modular em `src/agents/`, `src/tasks/` e `src/tools/`.
- Criados arquivos de dependências, `.env.example`, `.gitignore` e pastas
  `data/raw/`, `data/pdfs/` e `data/vectordb/`.
- Implementado inicialmente um coletor Playwright com evidências locais.
- Após inspeção de tráfego pelo usuário, a coleta principal passou a usar HTTP
  POST com `requests`, dispensando o navegador no fluxo atual.
- O usuário finalizou e testou a ferramenta HTTP antes da integração dos agentes.

### Fase 2 — coleta e auditoria com CrewAI

- Criados Agente Coletor e Agente Auditor, com tasks e Crew sequencial.
- Coletor possui acesso exclusivo à ferramenta de extração.
- Auditor não possui ferramentas nem delegação; analisa o contexto coletado.
- Validação Pydantic impede que mensagens de erro sejam tratadas como contratos.
- Criado relatório Markdown com evidências por contrato e diligências sugeridas.
- Inicialmente foi usado o LLM nativo do CrewAI com modelo OpenAI.
- Por decisão do usuário, houve migração para Gemini, usando `GEMINI_API_KEY`.
  O modelo padrão atual do código é `gemini/gemini-3.5-flash-lite`, configurável
  por `GEMINI_MODEL`. O usuário informou que o protótipo funcionou.
- A gratuidade depende das cotas e regras do provedor; não significa uso ilimitado.

### Fase 3 — paginação, PostgreSQL e arquivamento

- Removido o limite de cinco contratos da ferramenta HTTP.
- Parser captura todas as linhas do `tbody`, sem corte de caracteres.
- Implementada navegação por links HTML de próxima página.
- Implementado modo opcional de paginação por parâmetros de página/offset,
  configurados conforme o Network real do portal.
- Páginas repetidas, ciclos, colunas inconsistentes e limite de segurança
  interrompem a coleta em vez de apresentar resultados parciais como completos.
- Criado ORM SQLAlchemy e persistência PostgreSQL com `psycopg2-binary`.
- Criado terceiro agente, Arquivista de Dados, e sua task final.
- Parecer passou a ter estrutura JSON validada, além do relatório Markdown.
- Arquivamento recupera os campos originais da coleta pelos índices indicados
  no parecer, em vez de pedir ao modelo para reescrever os dados do contrato.
- Implementadas transação com rollback e prevenção de duplicações pelo fingerprint.

## Fluxo atual

1. `src/main.py` carrega `.env`, verifica `GEMINI_API_KEY` e chama `init_db()`.
2. Cria LLM Gemini e diretório único em `data/reports/<execução>/`.
3. `src/crew.py` monta três agentes e três tasks sequenciais.
4. Coletor executa `ExtratorContratosMarica`; JSON validado é salvo em `contratos.json`.
5. Auditor recebe a coleta e produz `parecer.json` com índices analisados,
   suspeitos e texto do relatório. O callback salva `relatorio.md`.
6. Arquivista chama `ArquivarContratosTool` sem argumentos. A ferramenta lê os
   artefatos da execução, prepara os registros e chama `salvar_contratos`.
7. O recibo confirmado da gravação é salvo em `arquivamento.json`.

## Arquivos principais

| Arquivo | Responsabilidade |
| --- | --- |
| `src/main.py` | Configuração, inicialização do banco e kickoff |
| `src/crew.py` | Montagem sequencial dos três agentes/tasks |
| `src/config.py` | Raiz do projeto e configuração legada do scraper |
| `src/tools/extrator_api_tool.py` | Coleta HTTP, CSRF, parsing e paginação |
| `src/agents/collector.py` | Agente Coletor |
| `src/agents/auditor.py` | Agente Auditor |
| `src/agents/archivist.py` | Agente Arquivista |
| `src/tasks/collect_contracts.py` | Validação da lista JSON da coleta |
| `src/tasks/audit_contracts.py` | Parecer estruturado e relatório Markdown |
| `src/tasks/archive_contracts.py` | Task final e validação do recibo |
| `src/audit_models.py` | Modelos `Achado` e `ParecerAuditoria` |
| `src/tools/archive_tool.py` | Mapeamento de colunas e gravação dos suspeitos |
| `src/database.py` | ORM, engine, criação de tabela e persistência |
| `tests/test_phase2.py` | Validação da coleta e montagem da Crew |
| `tests/test_phase3.py` | Parsing, paginação simulada, moeda e persistência local |

Os arquivos antigos de Playwright permanecem disponíveis, mas não são usados
pela entrada atual. As antigas opções CLI de coleta não se aplicam a `src.main`.

## API do portal

- Página inicial: `https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao`
- Pesquisa: POST para a URL acima acrescida de `/pesquisar`.
- A ferramenta abre uma sessão, faz GET inicial para obter `_token` e envia
  formulário com exercício, objeto, número do processo e demais filtros.
- O retorno esperado pelo parser é HTML com tabela, convertido em lista JSON.
- Sem parâmetros de paginação configurados, lê a tabela inteira e segue links
  Próxima quando presentes. Links são requisitados por GET.
- Não há descoberta universal de paginação invisível ou API JSON/DataTables.

## Banco de dados

Modelo `ContratoAuditado`, tabela `contratos_auditados`:

- `id`: chave primária.
- `numero_processo`, `beneficiario`, `objeto`: texto, permitindo NULL.
- `valor`: `Numeric(20, 2)`, tratado em Python como `Decimal`, permitindo NULL.
- `situacao_auditoria`: `Suspeito` ou `Regular`.
- `motivo_suspeita`: justificativa textual.
- `fingerprint`: hash único da linha original mais o motivo do parecer.

Somente os sinalizados como suspeitos são gravados no fluxo atual. Contratos
não sinalizados não são automaticamente classificados como regulares.
Repetir a mesma evidência e o mesmo motivo não duplica o registro; um motivo
diferente pode gerar outra versão. O fingerprint não é identidade jurídica.
`init_db` cria tabelas; não cria banco/usuário e não executa migrações.

## Configuração de ambiente

Não registrar credenciais neste documento. O `.env` real não foi lido nem
modificado pelo assistente durante as alterações das Fases 2 e 3.

```dotenv
GEMINI_API_KEY=SUA_CHAVE
GEMINI_MODEL=gemini/gemini-3.5-flash-lite
DB_HOST=localhost
DB_PORT=5432
DB_NAME=auditoria_cidada
DB_USER=auditoria_app
DB_PASSWORD="SUA_SENHA"
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

Para paginação confirmada por página, preencher `API_PAGE_PARAM=page` e, se
aplicável, `API_PAGE_SIZE_PARAM=per_page`. Para offset/limit, usar
`API_PAGE_PARAM=offset`, `API_PAGE_START=0`, `API_PAGE_STEP=100` e
`API_PAGE_SIZE_PARAM=limit`. Os nomes são exemplos: confirmar no Network.

Banco e usuário PostgreSQL precisam existir. Instruções SQL e opções de TLS
estão em `FASE3.md`. Não sobrescrever o `.env` existente com `.env.example`.

## Execução e testes

Na raiz do projeto, em PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Dependências incluem CrewAI com extra Gemini, requests, BeautifulSoup,
Pydantic, python-dotenv, SQLAlchemy e psycopg2-binary. Dependências futuras
de RAG ficam em `requirements-rag.txt`.

## Validação realizada

- Oito testes locais passaram após a implementação da Fase 3.
- Cobertos: validação JSON, montagem dos três agentes, preservação de mais de
  cinco linhas e de textos longos, linhas inválidas, links de paginação,
  paginação HTTP simulada, repetição de páginas, moeda brasileira, cobertura
  dos índices, idempotência e rollback transacional.
- Persistência foi testada localmente em SQLite; não equivale a teste PostgreSQL.
- SQLAlchemy e psycopg2-binary foram instalados no ambiente virtual.
- Nesta validação, não houve chamadas reais ao PostgreSQL, Gemini ou endpoint
  de pesquisa do portal. A página pública foi consultada como referência.
- CrewAI emitiu avisos de depreciação e de serialização de callbacks locais;
  não impediram os testes. Checkpointing não foi validado.

## Pendências e próximos passos

### Ajuste posterior — constraint de fingerprint

- `database.py` passou a declarar explicitamente
  `uq_contratos_auditados_fingerprint UNIQUE(fingerprint)` no ORM.
- O INSERT continua inferindo por coluna com `ON CONFLICT (fingerprint)`,
  aceitando constraints equivalentes com nomes diferentes.
- `init_db` verifica no catálogo PostgreSQL se há índice UNIQUE compatível.
  Não tenta alterar automaticamente tabelas existentes.
- Criada migração `migrations/001_unique_fingerprint.sql`, com instruções em
  `migrations/README.md`. Aborta em duplicações sem excluir registros.
- Três testes específicos de ORM/SQL e diagnóstico passaram. A migração não
  foi aplicada ao Supabase pelo assistente; o esquema remoto não foi inspecionado.

### Ajuste posterior — arquivamento resiliente a índices

- Removida a exigência de cobertura completa de `linhas_analisadas` como
  condição para arquivar suspeitos localizáveis. A divergência aparece em `avisos`.
- Mantida convenção de posições base 1. Índices zero, negativos ou além da
  coleta são ignorados com diagnóstico; não há deslocamento ou inferência
  automática que possa atribuir a suspeita ao contrato errado.
- Achados repetidos da mesma linha são agrupados, preservando motivos distintos.
- Recibo inclui `status`, `suspeitos_no_parecer`, `contratos_localizados`,
  `ignorados` e `avisos`, além dos contadores de persistência existentes.
- Sem correspondências, retorna zero inserções e não conecta ao banco.
- `Achado.linha` aceita inteiros inválidos para permitir descarte individual,
  mas rejeita conversões de tipos como números decimais e booleanos.
- Seis testes específicos passaram em `tests/test_archive_indices.py`, sem
  chamadas ao Supabase, portal ou Gemini. Falhas de banco e valores monetários
  inválidos continuam sendo erros; não se declara sucesso de gravação nesses casos.

1. Validar o fluxo completo com o PostgreSQL configurado pelo usuário.
2. Confirmar no Network a paginação efetiva, nomes dos parâmetros e manutenção
   dos filtros nos links; comparar a contagem extraída com a fonte.
3. Conferir aliases das colunas em `archive_tool.py` com o HTML real. Campos
   não encontrados ficam NULL; valores monetários ambíguos causam erro.
4. Validar integração real dos três agentes com Gemini e suas cotas.
5. Implementar auditoria em lotes para volumes além da janela do modelo, com
   reconciliação global para coincidências entre lotes. Atualmente a sumarização
   automática está desabilitada: exceder contexto pode interromper a análise.
6. Considerar ordenação estável/snapshot na fonte para paginação consistente,
   migrações de banco, identificadores de contrato e proveniência mais rica.
7. Implementar futuramente download e extração de PDFs, LangChain/ChromaDB e
   RAG, além de investigação de empresas e referências comparáveis de preços.

Não há pipeline RAG implementado. Não se comprova sobrepreço sem comparáveis,
nem fracionamento sem datas, modalidades e contexto. Cobertura de índices
valida estrutura, não a correção do raciocínio do modelo.

## Documentação existente

- `README.md`: documentação inicial da Fase 1; contém instruções legadas.
- `FASE2.md`: documentação histórica da Fase 2, anterior à migração completa.
- `FASE3.md`: instruções atuais de configuração, execução e limitações.
- `FASE3_CODIGO.md`: códigos completos reunidos na entrega da Fase 3;
  mudanças futuras devem ser feitas nos arquivos-fonte e refletidas no documento.
- `continuidade.md`: este resumo para retomada do trabalho.

Para continuidade, priorizar o estado atual dos arquivos-fonte e `FASE3.md`
sobre exemplos históricos com OpenAI ou Playwright.
