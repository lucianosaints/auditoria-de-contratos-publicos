# Indicadores de gestão com pandas

Primeira entrega em 21/10/2026. Os cálculos usam somente arquivos locais; não consultam rede, IA ou banco.

Atualização real em 23/10/2026 após leitura dos dois PDFs grandes PNCP:
22 linhas com PDF publicado extraído, 72 com fichas/tipo não validado e 356
não processadas. Indicadores regenerados, versão anterior arquivada; valores
contratuais não se transformam em pagamentos. Provas em
`data/raw/large_pncp_20261023/verificacao_mcp_indicadores.json`.

## Uso

Reabra `iniciar_painel.bat`, selecione a execução local e clique **Gerar indicadores**. O painel apresenta valores contratuais elegíveis, exclusões, distribuição por CNPJ e cobertura documental/PNCP. A tabela dos dez maiores valores permite abrir as linhas de origem. Os detalhes do contrato explicam a inclusão ou exclusão do cálculo.

Na execução principal `20261020T015002Z_72b23869`, os indicadores já foram gerados. Nenhuma auditoria ou revisão Gemini precisa ser repetida para consultá-los.

A ferramenta MCP `consultar_indicadores(execucao, linha=None, limite_fornecedores=10)` lê os resultados salvos. Aceita limite de 1 a 50 fornecedores e linha positiva existente. Não gera arquivos nem executa análises automaticamente. Retorna `nao_preparado`, `desatualizado` ou `pronto`. O servidor importa pandas somente quando há cálculo, mantendo a leitura dos indicadores sem a inicialização da biblioteca numérica.

## Critérios e fórmulas

O cálculo cobre **linhas da coleta**, não um universo municipal certificado de contratos únicos. A fonte monetária preferencial é `Detalhe - Valor Global`, seguida de `Valor do Contrato` e `Valor`. A prioridade evita misturar o valor inicial com o global vigente. Valores ausentes ou com formato ambíguo não viram zero nem são substituídos silenciosamente por outro valor.

Conversão aceita os formatos brasileiros e decimais com ponto já usados no projeto. Os valores são convertidos diretamente de texto para **centavos inteiros Python**, com colunas `object` no DataFrame. As somas não usam `float` nem inteiros NumPy de 64 bits. Os valores publicados no JSON são strings decimais com duas casas; a apresentação no painel também preserva a precisão dessas strings. Identificadores e CNPJ permanecem texto, com zeros iniciais.

Uma linha só participa da distribuição financeira quando tem:

- Número/ano do contrato, processo/ano e CNPJ com 14 dígitos no formato esperado.
- Identidade contratual não repetida nessa combinação.
- Valor monetário válido e não negativo.

O formato do CNPJ não constitui validação cadastral. CPF não é convertido em CNPJ. Nomes iguais não unem entidades diferentes. Para um mesmo CNPJ, os nomes publicados são preservados.

**Todas** as linhas com a mesma identidade repetida são excluídas da distribuição, mesmo quando seus valores coincidem. Isso evita escolher arbitrariamente entre duplicata e versão histórica. As linhas continuam na cobertura e podem ser abertas para conferência.

Denominador = soma dos valores das linhas elegíveis. Participação por CNPJ = soma elegível desse CNPJ / denominador × 100. Participação dos cinco maiores = soma dos cinco maiores agregados por CNPJ / denominador × 100. Denominador zero produz `null`, mostrado como não calculável. Percentuais têm duas casas decimais e podem apresentar diferenças de soma por arredondamento.

O recorte pode conter contratados, beneficiários, convênios e ajustes de naturezas diferentes. Não é uma definição de mercado nem uma análise de competição. Os percentuais não são probabilidade de fraude ou diagnóstico de irregularidade.

## Cobertura das fontes

O pandas combina o quadro normalizado e a cobertura pela linha, com `merge(validate='one_to_one')`. Linhas duplicadas ou fora da coleta nos manifestos são rejeitadas, evitando multiplicação de valores. As distribuições de cobertura preservam todas as linhas; não descartam ausências.

Documento só é contado para um registro cujo hash coincide com o da coleta. Sem manifesto compatível, o estado é não processado ou fonte desatualizada. As categorias diferenciam PDF publicado extraído, ficha cadastral/tipo não validado e ausência de texto. Cobertura é declarada no manifesto, sem nova leitura ou certificação dos PDFs.

O estado PNCP é incorporado somente quando a reconciliação corresponde à coleta e ao conjunto de linhas com alertas atuais, com assinatura íntegra. Não se faz uma nova associação entre contratos pelo pandas. Candidatos e diferenças continuam sujeitos aos critérios conservadores descritos em PNCP.md.

**Execução financeira permanece não avaliável**: valores contratuais não são pagamentos, liquidações ou comprovação de entrega. A próxima etapa financeira depende de obter e relacionar dados estruturados de empenhos, liquidações, pagamentos, estornos e medições. Não há estimativa automática desses dados a partir dos textos do objeto.

## Artefatos e atualização

`src/management_analytics.py` publica `indicadores.json` atomicamente. Antes de substituir uma versão, preserva a anterior em `indicadores/historico/<hash>.json`. Guarda versão da metodologia, pandas utilizado, data UTC, fontes e hashes, critérios, cobertura e cálculos por linha.

O painel e o MCP verificam os hashes dos arquivos `contratos.json`, `parecer.json`, `documentos.json` e `pncp.json`, além da assinatura do resultado. Fonte ausente tem hash `null`; sua inclusão posterior exige novo cálculo. Mudanças nos arquivos, inclusive de serialização, invalidam os indicadores. O painel oculta resultados obsoletos e orienta gerar novamente. A versão da metodologia deve ser incrementada quando as regras de cálculo mudarem.

Coleta, parecer, revisão, recibo, PDFs, manifesto documental e índice RAG não são modificados pela análise. O cálculo não altera notas ou classificações dos agentes.

## Resultado real e validação

Execução principal: 450 linhas; 94 com alertas. Para distribuição: 384 elegíveis e 66 excluídas, sendo 58 com identidade incompleta e oito com identidade repetida. Quarenta e cinco das 58 não têm CNPJ no formato esperado; isso pode incluir registros de pessoas físicas, sem conclusão de erro cadastral. Os grupos se sobrepõem e não devem ser somados como exclusões adicionais.

Total contratual elegível: **R$ 1.127.925.080,43**. Foram identificados 321 CNPJs nesse recorte; 23 linhas elegíveis têm valor zero. Os cinco maiores agregados representam **50,86%** do denominador elegível. Esses números não medem gasto executado nem o total de contratações do Município.

Cobertura dos 450 registros: 20 linhas com PDF publicado extraído, 74 somente com fichas/tipo não validado e 356 sem processamento documental. São contagens de linhas, não de PDFs físicos; um mesmo PDF pode apoiar mais de uma linha. Para PNCP: 22 confirmados por regras, três candidatos, 62 com diferenças entre candidatos, sete não localizados no recorte e 356 não consultados.

Validação: 149 testes Python, 41 frontend, build, QA Playwright desktop/mobile com leitura real e POST simulado, e consulta MCP real da linha 31. Inclui soma exata de centavos e valor superior a 64 bits, zeros iniciais, homônimos, duplicatas, ausências, dados obsoletos e coleção vazia. Prova em `data/raw/analytics_verificacao_20261021/verificacao.json`; imagens em `frontend/qa/analytics-*.png`. Hashes da auditoria, documentos e índice originais foram preservados. Pandas instalado: 2.3.3, somente no ambiente do projeto.

Referências da implementação: [agrupamentos no pandas](https://pandas.pydata.org/pandas-docs/version/2.3/user_guide/groupby.html) e [validação de associações entre tabelas](https://pandas.pydata.org/docs/user_guide/merging.html).
