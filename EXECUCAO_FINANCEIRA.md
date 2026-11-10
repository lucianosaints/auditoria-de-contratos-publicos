# Disponibilidade de execução financeira — Maricá

## Duas fontes citam a nota 4003/2026; diligência pronta — 23/10/2026

Inspeção da página 5, coluna esquerda, do Diário Oficial Extraordinário 09
(10/09/2026) encontrou o extrato do contrato 341/2026, processo 12242/2026,
CS BRASIL FROTAS S.A., com citação expressa à nota 4003/2026. O PDF do candidato
PNCP 413/2026, obtido para inspeção isolada, apresenta a identificação na página
1 e cita a mesma nota na página 10. Programa 68.01.06.181.0018.2076, elemento
3.3.3.9.0.39.00.00.00 e origem de recurso 1704 coincidem nas duas fontes.

São referências documentais, não a nota de empenho original nem comprovação
de pagamento. O vínculo financeiro 4003/2026 → 776/2024 permanece rejeitado.
O candidato PNCP permanece conflitante: assinatura no portal em 18/08/2026,
extrato e metadado PNCP em 01/09/2026. Página 11 do PDF apresenta espaços de
assinatura sem assinaturas visíveis; não foi validada assinatura digital.
Não houve importação desse candidato ao manifesto principal ou ao RAG.

Três consultas públicas adicionais (nome CS BRASIL, número 4003/2026 e unidade
1102/número 4003) vieram vazias, com todos os filtros devolvidos conferidos.
Controle positivo de fornecedor presente na listagem atual encontrou três
registros, incluindo o empenho de controle 5617/2026. Isso verifica a consulta
de controle; não certifica cobertura ou ausência de despesa na linha 175.

`src/financial_diligence.py` valida identificadores no escopo documental
selecionado e prepara pacote com referências, hashes, pendências e minuta.
Rejeita nota ausente/divergente/ambígua, ano malformado, contrato/processo ou
fornecedor incompatíveis e dotação ambígua. Preserva revisão humana pendente;
não confirma vínculos financeiros ou atribui valores ao contrato.

Entrega em `data/diligencia_financeira_175_20261023/`: `relatorio.md`,
`diligencia.json`, `solicitacao.md` e `verificacao.json`. Minuta preparada
localmente, não enviada. Script offline reproduzível:
`frontend/scripts/prepare_financial_diligence175.py --saida NOVA_PASTA`.
Fontes e provas em `data/raw/financial_alternative175_20261023/`.
Nove artefatos principais preservados. Nenhuma nova auditoria, IA ou banco.

## Linha 175 reconsultada e vínculo rejeitado — 23/10/2026

A relação antes pendente do contrato 341/2026 (processo 12242/2026) aponta
para 4003/2026, mas o mesmo URL retornou **776/2024** na conferência atual,
em duas sessões independentes. Não foi determinada a causa da mudança em
relação à resposta de 21/10. Saldos dessa relação agora estão rejeitados.

Pesquisas limitadas por número 4003, pela pista 140921 do histórico antigo e
por CNPJ 27.595.780/0001-16/exercício 2026 retornaram vazias, com filtros
devolvidos conferidos. Isso não comprova ausência de despesa. O detalhamento
e as evidências estão em `data/raw/financial_case175_20261023/relatorio.md`.

Implementado `recheck_saved_detail`: reavalia uma relação publicada com HTML
cujo hash/origem/data são conferidos, valida coleta/parecer/HTML contratual,
mantém histórico e cache e substitui atomicamente o resultado. Não chama rede,
IA ou banco. O chamador deve adquirir a trava de execução; o script
`frontend/scripts/verify_financial_case175.py --publicar` faz isso.

Somente a linha 175 foi atualizada na principal. As outras 93 linhas e oito
artefatos principais permaneceram intactos; a cobertura/datas antigas não são
apresentadas como uma rodada nova. Resultado: **30 relações rejeitadas em 20
contratos, zero confirmadas**. O painel mostra a data de cada fonte e informa
que houve reconsulta pontual. Não foram calculados pagamentos por contrato.

Validação: 177 testes Python, 45 frontend/Node e build aprovados. QA com dados
reais de leitura em desktop/mobile conferiu 4003/2026 versus 776/2024, data,
ausência dos saldos rejeitados, zero erros JS e ausência de overflow. Capturas
`frontend/qa/financial-recheck-175-*.png` conferidas visualmente.

## Conferência de processo, contrato e fornecedor — atualização de 21/10/2026

A política de identidade 2 passou a comparar referências explicitamente rotuladas no resumo do empenho, além do número/ano. Também compara o fornecedor/CNPJ e o processo da consulta filtrada quando houver registro correspondente. Referências ausentes permanecem não comparáveis; múltiplas referências ficam ambíguas. Anos malformados não são corrigidos nem truncados. Qualquer campo comparável divergente rejeita os saldos da relação.

Conferência pública isolada das duas amostras, em `data/raw/financial_two_cases_20261021/verificacao.json`:

- **Linha 96:** contrato 376/2026, processo 17900/2025; empenho 5342/2026 cita P.A 7501/2026 e referência malformada `374/20260`. O processo diverge; associação rejeitada mesmo com número/ano do empenho coincidente. Não se corrigiu `374/20260` para adivinhar outro contrato.
- **Linha 175:** empenho 4003/2026 e processo 12242/2026 coincidem, mas não houve registro correspondente na consulta CNPJ/exercício e o detalhe não fornece CNPJ para confronto. Continua pendente; a consulta vazia não prova ausência de despesa ou erro cadastral.

O resultado principal foi reprocessado com as respostas em cache: job `20261021T195425Z_74b46b7e`, concluído às 16h54min40s locais. Mesmo recorte de 94 linhas, 10 consultas e 30 detalhes: **29 relações conflitantes em 19 contratos e uma pendente**, sem vínculo financeiro confirmado. As datas de todas as respostas reutilizadas antecedem o job; não foi necessário obter novas respostas nessa reavaliação. Artefato anterior arquivado, oito fontes principais preservadas.

O painel agora exibe comparações e referências inválidas nos detalhes; resultados da política anterior ficam desatualizados até a reavaliação. A execução principal já foi atualizada. A amostra não resolve instituição, fornecedor, documentos financeiros e reconciliação de eventos. Nenhum total por contrato foi calculado.

166 testes Python, 44 frontend/Node, build e QA Playwright passaram; a interface real verificou linha 96 sem os saldos rejeitados e linha 175 ainda pendente, em desktop/mobile. Capturas `frontend/qa/financial-identity-*.png` conferidas visualmente.

## Integração entregue em 21/10/2026

Reabra `iniciar_painel.bat` e use **Consultar financeiro** na execução selecionada. O botão pesquisa contratos com alertas, sem Gemini ou banco. A execução principal já recebeu a consulta limitada descrita abaixo; não é necessário repetir a auditoria.

`src/financial.py` pesquisa CNPJ/exercício e exige confirmação dos filtros no HTML e nas linhas retornadas. Limites: **10 combinações CNPJ/exercício e 30 URLs de detalhe** por ação. Os vínculos publicados nos HTMLs locais só são lidos após conferir a identidade do contrato de origem. Destinos e redirecionamentos ficam restritos às rotas municipais previstas, com timeout e limite de 8 MB por resposta.

Número/ano é extraído do campo específico do detalhe. Divergência produz `conflito_identidade`, sem saldos na relação publicada. Coincidência produz `vinculo_pendente`: saldos do empenho são exibidos com essa ressalva. Não há confirmação automática do contrato, soma de pagamentos, interpretação de estornos ou comprovação de entrega. Movimentações ficam preservadas literalmente em seção expansível.

O painel mostra cobertura, limites, falhas e atalhos aos conflitos. Nos detalhes do contrato, compare número esperado e observado. Resultado incompatível com coleta, parecer ou HTML de origem é ocultado. Importação de `financeiro.json` não está disponível nesta versão.

O executor mantém trava e interrupção. `financeiro.json` é publicado atomicamente durante a consulta, com assinatura, fontes e hashes. Cache por CNPJ/exercício ou URL dura até 24 horas; versões anteriores ficam em `financeiro/historico`. Repetir a ação com os mesmos limites revisita o mesmo recorte, aproveitando respostas válidas; não amplia automaticamente a cobertura. Em CLI: `python -m src.financial --execucao ID`.

### Primeira rodada real na execução principal — histórico anterior à política 2

Job `20261021T194049Z_26e8a1ca`, concluído em 21/10/2026 às 16h41min09s (America/Sao_Paulo). Das 94 linhas com alertas: 11 cobertas por 10 consultas CNPJ/exercício compartilhadas, 69 fora desse limite e 14 sem CNPJ/exercício suficiente. Os links locais podem fornecer detalhes também para linhas não cobertas pela pesquisa filtrada.

30 URLs consultadas: **28 relações com identidade divergente em 19 contratos**, rejeitadas, e duas com número/ano compatível, ainda pendentes de vínculo contratual (linhas 96 e 175). Outras 72 relações foram omitidas pelo limite de detalhes. Zero falhas de consulta de fornecedor ou incompatibilidades dos HTMLs de origem nesta rodada. Os conflitos são problemas de associação observados, sem conclusão de irregularidade contratual ou causa determinada no portal.

Nenhum vínculo financeiro foi confirmado ou total por contrato calculado. Oito artefatos originais preservados por SHA-256, inclusive revisão, documentos, PNCP e indicadores. Sem IA, banco, alteração de `.env` ou modelo. Dados financeiros não foram enviados aos agentes/RAG.

### Validação

159 testes Python e 44 frontend/Node passaram, além do build. Cobertura inclui regressão 5512/2026 → 3832/2021, filtros não aplicados, identidades duplicadas, limites, cache corrompido/expirado, redirecionamentos, interrupção e integração da ação. QA Playwright desktop/mobile verificou botão e execução selecionada com POST simulado, conflitos sem saldos, fonte obsoleta, ausência de overflow e zero erros JS. API e exibição da execução principal conferidas com dados reais; capturas inspecionadas visualmente.

Amostra real isolada testou um CNPJ/exercício e dois detalhes; um controle positivo por CNPJ já presente na tabela retornou os dois empenhos esperados. Provas em `data/raw/financial_integration_20261021/`, logs em `data/ui_jobs`, capturas `frontend/qa/financial-*.png`. Os scripts `frontend/scripts/verify_financial_*.py` indicam quais executam rede e qual publica na execução principal.

Próximas etapas: ampliar cobertura com limites explícitos, investigar uma rota de detalhe com identidade correta, reconciliar fornecedor/instituição/processo e eventos, obter notas/medições/atestos municipais. Execução financeira dos contratos continua **não avaliável**.

## Inspeção inicial que fundamentou a integração

Verificação limitada em 21/10/2026. **Há dados municipais de empenhos e movimentações, mas a associação financeira aos contratos ainda não foi validada.** A primeira amostra de link publicado no contrato abriu um empenho de outro número e exercício. Nenhum pagamento foi atribuído a contrato nesta etapa.

## Fontes verificadas

- [Consulta municipal de empenhos](https://transparencia.marica.rj.gov.br/e-cidade/consulta-empenhos): tabela com número/ano, emissão, beneficiário, CPF/CNPJ, unidade, procedimento, número do procedimento, objeto, empenhado, liquidado e pago. Detalhes incluem instituição, anulado, dotação, itens e movimentações com data, tipo, valor e histórico.
- [Dados abertos](https://transparencia.marica.rj.gov.br/governo-digital/dados-abertos/links-e-arquivos): publica links de demonstrativos por projeto, programa, instituição/órgão e elemento de despesa. Os arquivos agregados não foram baixados ou reconciliados nesta inspeção.
- [Notas Fiscais Eletrônicas](https://transparencia.marica.rj.gov.br/receitas-e-despesas/notas-fiscais-eletronicas/links-e-arquivos): os quatro atalhos observados apontam ao portal federal. A página não demonstrou cobertura das notas municipais.

## Evidência obtida

A sessão inicial seleciona exercício 2026 e todos os meses/unidades disponíveis. O formulário observado usa POST `/e-cidade/consulta-empenhos/pesquisar`, com campos `year`, `month`, `unit`, `beneficiary`, `document` e `encumbrance_number`. O JavaScript descreve paginação no navegador. Filtros POST, outros exercícios e completude municipal ainda não foram testados.

O CSV público `/e-cidade/consulta-empenhos/exportar?download=csv` foi baixado na mesma sessão: 44.663 bytes, 118 registros. Todos os campos coincidiram com as 118 linhas HTML, com conversão monetária exata usando Decimal. Não houve repetição de número/ano nesse recorte. Isso verifica consistência entre duas apresentações da mesma consulta; não certifica cobertura municipal ou de outras entidades.

Totais desse recorte: empenhado R$ 109.347.372,47; liquidado R$ 56.339.881,14; pago R$ 56.331.081,14. **São totais da consulta recebida, sem vínculo financeiro validado aos 450 contratos.** Não devem substituir os indicadores contratuais ou ser apresentados como execução desses contratos.

Um detalhe aberto pela consulta de empenhos mostrou 5546/2026, com empenhado e liquidado de R$ 1.760,00 e pago R$ 0,00, além de eventos datados. É uma amostra de suprimento de fundos, sem associação a um contrato da auditoria.

## Vínculos publicados exigem validação

Inspeção local dos 450 HTMLs já salvos identificou 348 linhas contratuais com tabela de empenhos e 102 com a mensagem de nenhum empenho encontrado. Foram inventariadas **550 URLs distintas**, em 550 relações publicadas. A ausência da tabela não comprova ausência de despesa.

**Falha observada na amostra da linha contratual 5:** o HTML apresenta empenho 5512/2026, sobre fornecimento de livros, mas o link `/e-cidade/contratos/padrao/26417/empenho` retornou o campo Número **3832 - 2021**, resumo de rescisão e movimentações de 2021. A identidade diverge e a associação foi rejeitada. A causa não foi determinada e não se extrapola a falha para todos os links.

O cruzamento exploratório do CSV por CNPJ formal e processo explicitamente rotulado no objeto produziu 31 pares candidatos em 27 linhas contratuais. Nenhum foi confirmado: processo e fornecedor podem compartilhar vários contratos. A coluna “Nº do Procedimento” pode representar ata ou licitação e não foi presumida como processo administrativo. CPFs mascarados não viraram CNPJ.

## Próxima implementação

1. Coletor próprio de consulta financeira com filtros conferidos, limites, cache, progresso e cobertura explícita. Validar a consulta filtrada antes de baixar grandes volumes.
2. Ler número/ano no campo específico do detalhe; rejeitar divergência do vínculo publicado. Conferir instituição, beneficiário/CNPJ, processo e identidade contratual quando disponíveis. Número isolado ou URL não bastam.
3. Preservar saldos e eventos separadamente. Modelar estornos, anulações, parcelas, restos a pagar e encerramento sem somar indiscriminadamente todas as movimentações. Validar regras contra amostras de cada tipo antes de calcular indicadores.
4. Mostrar candidatos, conflitos e dados insuficientes no painel. Só publicar totais por contrato após reconciliação. Pagamento publicado não comprova entrega; notas, medições e atestos exigem fontes próprias.

## Artefatos e conferência

Em `data/raw/financeiro_verificacao_20261021/`: HTMLs públicos, CSV original, `inspecao.json`, `verificacao.json`, `amostra_vinculada.json` e scripts reproduzíveis. Metadados guardam URLs, instante UTC e SHA-256. Os HTMLs contêm tokens efêmeros de sessão pública; evidência local, não destinada a publicação como está.

`inspecionar.py` consulta três páginas, um detalhe e CSV, sem IA/banco. `conferir.py` roda offline, verifica hashes, compara todas as células, inventaria vínculos e registra hashes antes/depois de oito artefatos principais da execução `20261020T015002Z_72b23869`. `validar_link.py` consulta somente a primeira relação publicada e rejeita número/ano incompatível. Scripts de inspeção não integram o executor do painel e não são coletores de produção.

A conferência da inspeção inicial passou e os oito artefatos originais foram preservados. Nessa inspeção não houve mudança funcional do painel. A integração posterior e seus testes estão descritos no início deste documento.
