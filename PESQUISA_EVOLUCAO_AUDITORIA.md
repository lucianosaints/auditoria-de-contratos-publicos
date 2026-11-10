# Pesquisa para evolução da Auditoria Cidadã

Data da consulta: 20/10/2026. Pesquisa documental em fontes primárias; não houve teste de integração das APIs nem avaliação comparativa de desempenho dos produtos.

## Conclusão para o projeto

A prioridade proposta é ampliar a evidência disponível: documentos completos, identificação confiável de contratos entre fontes e cruzamentos verificáveis. Depois, acrescentar procedimentos especializados e indicadores reproduzíveis. Acrescentar prompts sem esses dados manteria as principais limitações atuais.

Estado local conferido em continuidade.md, FASE3.md e busca nos fontes: auditoria por lotes, coincidências globais, consulta DOM/JOM, investigador/revisor, citações validadas e painel com controles. Ainda faltam leitura automática de anexos, OCR, PNCP, consulta de sanções e comparação estruturada de preços. O procedimento de preços existente orienta análise e diligências; não fornece uma base de preços comparáveis.

As prioridades e desenhos abaixo são propostas para este projeto, inferidas a partir das referências. Não são funcionalidades já implementadas nem promessas de equivalência com ferramentas institucionais.

## Referências pesquisadas

| Referência | Capacidade documentada | Aplicação proposta |
| --- | --- | --- |
| Alice/CGU | Monitoramento diário, análise de documentos e cruzamento de bases para alertas preventivos | Monitorar mudanças, analisar editais e encaminhar casos para revisão |
| Ecossistema TCU | MONICA reúne aquisições; ADELE apresenta dinâmica de lances; MARINA avalia riscos; SAO avalia riscos de orçamentos de obras | Separar procedimentos por tipo de análise e dados necessários |
| Open Contracting Partnership | Guia com 73 indicadores, definições e fórmulas associados ao OCDS | Catálogo de regras mensuráveis com cobertura explícita |
| PNCP | API documenta consulta de contratações, contratos e atas, inclusive por atualização | Reconciliação com portal municipal e acompanhamento incremental |
| Compras.gov.br | API documenta CATMAT/CATSER, preços praticados, atas e itens de contratos | Comparação de itens equivalentes e investigação de atas |
| Portal da Transparência/CGU | API de CEIS e CNEP | Verificação documental de sanções por identificador |
| Querido Diário/OKBR | Extração e indexação de diários, com API pública | Referência de arquitetura e fonte complementar, se houver cobertura municipal |

Fontes: [Alice](https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao/alice), [soluções TCU, descrição publicada em 2024](https://portal.tcu.gov.br/imprensa/noticias/uso-de-inteligencia-artificial-aprimora-processos-internos-no-tribunal-de-contas-da-uniao), [guia OCP](https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/), [API PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html), [API Compras](https://dadosabertos.compras.gov.br/swagger-ui/index.html), [API Transparência](https://api.portaldatransparencia.gov.br/), [arquitetura Querido Diário](https://docs.queridodiario.ok.org.br/pt-br/latest/entendendo/arquitetura.html).

A Alice institucional não é uma API pública de auditoria disponível à sociedade. A página de adesão restringe o acesso a unidades de controle. Podemos aplicar os princípios publicados e utilizar bases públicas independentemente dela. [Condições de acesso](https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao/alice/alice-para-estados-e-municipios).

## Habilidades propostas, em ordem de dependência

### 1. Formação de dossiê documental — prioridade muito alta

Baixar anexos oficiais, identificar tipo documental, extrair texto e tabelas e executar OCR somente quando necessário. Guardar original, URL, data de coleta, hash, página, método e qualidade da extração. Documentos que falham devem constar como não lidos.

O investigador receberia os trechos pertinentes do contrato, edital, termo de referência, ata e aditivos. Cada citação deve abrir a página de origem no painel. Texto extraído por OCR precisa ficar identificado, com revisão da imagem para números ou datas decisivos.

Aceite: amostras com PDF textual, digitalização, tabela e documento com duas colunas; conferir valores e páginas contra o original. Uma URL encontrada nunca deve contar como documento lido. Conteúdo de documentos deve ser tratado como dados, sem poder alterar instruções dos agentes.

### 2. Reconciliação Portal–PNCP–Diário — prioridade muito alta

Localizar candidatos por órgão, número/ano, processo e fornecedor; conservar o identificador PNCP quando houver correspondência confirmada. Classificar vínculos como confirmado, candidato, conflitante ou não localizado. Não juntar contratos apenas por número ou semelhança textual.

Comparar valor, objeto, fornecedor e datas, exibindo as duas fontes em divergências. Uma ausência no PNCP será resultado da busca e de sua cobertura, sem conclusão automática de falta de publicação. Usar as rotas de atualização para novas consultas incrementais.

Aceite: casos com mesmo número em órgãos diferentes, processo de ano anterior, retificação e contrato não encontrado. Validar antes a cobertura real de Maricá e os endpoints aplicáveis. [Documentação de consulta de contrato](https://pncp.gov.br/manual/pt-br/latest/contrato_empenho/consultar_contrato_ou_empenho.html).

### 3. Consulta de sanções — prioridade alta

Consultar CEIS/CNEP por CNPJ e guardar resposta, data e fonte. Confrontar período, tipo e alcance do registro com a data do evento contratual. O sistema deve mostrar a sanção e seus limites para análise, sem equiparar todo registro do CNEP a impedimento de contratar.

Aceite: CNPJ exato, sanção encerrada, registro sem datas completas e indisponibilidade. Separar não consultado, consulta falhou, registro não localizado e registro localizado. Confirmar requisitos de chave e limites da API antes da integração.

### 4. Linha do tempo e aditivos — prioridade alta

Organizar assinatura, publicação, vigência, período de prestação, prorrogações, alterações e reconhecimento de dívida. Calcular mudanças de prazo e valor de forma reproduzível. Apontar divergências entre fontes e períodos que exigem documentos adicionais.

Não aplicar um percentual ou prazo jurídico universal: regras precisam identificar regime, instrumento e exceções pertinentes. Uma vigência vencida, sozinha, não demonstra execução sem cobertura. O caso da linha 109 pode integrar a amostra de validação documental, com o resultado esperado revisado por pessoa.

### 5. Preços e quantitativos — prioridade alta após obter itens

Extrair código, especificação, unidade, quantidade e preço unitário. Buscar referências no Compras.gov.br e calcular distribuição e diferença em relação a uma amostra comparável. Exibir quais referências foram aceitas ou descartadas e por quê.

Comparabilidade exige considerar época, local, quantidade, frete, instalação, manutenção, duração e especificação. Para escolas modulares, decompor fornecimento/locação, área, fundação, instalações, transporte e prazo antes de comparar alternativas. Diferença entre valores globais não basta para concluir sobrepreço.

Aceite: rejeitar unidades incompatíveis, duplicatas e objetos apenas semelhantes. Sem amostra suficiente, informar não avaliável. Obras exigem uma etapa própria de composições e metodologia; qualquer uso de tabela referencial deve verificar a disponibilidade e validade dos preços na referência escolhida.

### 6. Competição, concentração e vínculos — prioridade posterior

Calcular participação por fornecedor em recortes de órgão, período e categoria; detectar recorrência e agrupar objetos semelhantes para revisão. Evoluir para licitante único, padrões de participação e lances somente quando houver dados dos participantes e das disputas.

Dados cadastrais e quadro societário podem apoiar relações entre fornecedores, mas a fonte, atualização e acesso precisam ser validados. Nome de sócio isolado ou endereço compartilhado não confirma vínculo indevido; um cadastro atual não prova a composição histórica. [Consulta oficial CNPJ/QSA](https://www.gov.br/pt-br/servicos/consultar-cadastro-nacional-de-pessoas-juridicas).

Fracionamento e conluio devem permanecer hipóteses de diligência dependentes do contexto, das modalidades, datas, participantes e demais evidências.

### 7. Execução financeira e entrega — prioridade posterior

Associar empenhos, liquidações, pagamentos, notas fiscais, medições e atestos ao contrato correto. Procurar divergências de quantidade, repetição de documento financeiro e incompatibilidades de período. A disponibilidade desses dados em Maricá ainda precisa ser verificada; não presumir que a base federal cubra pagamentos municipais.

Aceite: distinguir parcela, estorno, cancelamento, aditivo e duplicata. Reconhecimento de dívida deve continuar separado de pagamento, e pagamento de entrega comprovada.

### 8. Revisão humana, priorização e monitoramento — começar junto das primeiras etapas

Criar uma fila com prioridade explicável, considerando materialidade, sinais e qualidade da evidência separadamente. Registrar análise humana, justificativa, documentos pedidos, respostas e alterações de classificação. Prioridade não é probabilidade estatística de fraude.

Nas novas coletas, destacar documentos, valores e prazos alterados. Reprocessar somente os módulos afetados, preservando versões anteriores. Alertas no próprio painel podem vir primeiro; notificações externas e agendamento ficam para uma etapa específica.

## Modelo mínimo de uma regra

Cada regra deve declarar: identificador/versão, objetivo, fontes, campos obrigatórios, cálculo, âmbito temporal, critério de disparo, limitações, diligência e evidência citada. Saídas: sinal identificado, sinal não identificado, dados insuficientes, falha na consulta ou não aplicável.

Falta de dados não deve produzir nota de risco zero. Guardar o resultado do cálculo separado da explicação do LLM. A interpretação gerada precisa ser rastreável aos mesmos documentos e valores usados pela regra.

## Sequência de entrega sugerida

1. Dossiês de anexos + OCR seletivo + visualização das fontes e registro de revisão humana.
2. PNCP + sanções + linha do tempo, inicialmente com uma pequena amostra conferida.
3. Itens, preços e atas, começando por uma categoria de objetos comparáveis.
4. Competição, relações entre fornecedores, execução financeira e monitoramento incremental, conforme cobertura comprovada.

Integrar ao executor existente com planejamento, progresso, interrupção, cache e checkpoints próprios. Novas evidências devem invalidar somente módulos dependentes. Preservar pareceres e checkpoints da auditoria original; resultados novos podem ser artefatos adicionais por contrato e execução.

Não é necessário criar um agente por fonte. Python pode coletar, relacionar identificadores e calcular indicadores; procedimentos especializados orientam o investigador e o revisor. Novos agentes só se justificam por responsabilidades distintas e ganho medido.

## Como verificar se houve melhora

Montar uma amostra humana com casos sinalizados e não sinalizados, diferentes objetos e documentos incompletos. Medir precisão dos alertas, perda de casos conhecidos, erros de associação, correção de números extraídos, cobertura documental, tempo e custo. Registrar falsos positivos e ajustar regras com exemplos versionados.

O manual da Alice reforça que alertas apoiam a seleção de trabalhos e dependem da qualidade dos dados e da análise humana. Ausência de alerta não demonstra regularidade. [Manual prático Alice](https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao/alice/arquivos/sfc-manual-pratico-alice.pdf).

## Limites desta pesquisa

Foram consultadas páginas e documentações públicas. Não foram testadas autenticação, estabilidade, paginação ou cobertura municipal das APIs; não foi confirmada cobertura de Maricá no Querido Diário. A descrição do TCU é uma referência publicada em 2024, não um inventário validado de seu ambiente interno atual. Nenhum serviço de IA recebeu contratos nesta pesquisa; nenhuma auditoria, revisão em lote ou mudança no banco foi executada. Este documento registra uma proposta, sem alteração funcional do aplicativo.
