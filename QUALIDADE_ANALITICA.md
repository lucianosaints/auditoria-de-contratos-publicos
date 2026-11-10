# Qualidade analítica e evolução do projeto

Atualizado em 23/10/2026.

## Piloto supervisionado preparado — avaliação pelo usuário

O usuário informou que fará a avaliação. Abra `iniciar_piloto.bat` ou
[avaliar.html](data/piloto_supervisionado_20261023/avaliar.html). O roteiro
completo está em [PILOTO_SUPERVISIONADO.md](PILOTO_SUPERVISIONADO.md).

São os mesmos 40 casos, todos ainda pendentes, em uma versão nova do caderno.
Primeiro registra-se a conferência independente pelas fontes, com cronômetro,
identificação, justificativa e fontes. Só após encerrá-la a interface mostra a
triagem original. A opinião posterior fica separada e não altera a primeira
avaliação. Casos com exposição prévia declarada ou etapa independente não
encerrada ficam pendentes de validação nas métricas. Falta de documentação
continua sem ser convertida em decisão negativa.

Exportação/importação permitem retomar o progresso. Cronômetros pausam ao
fechar/recarregar e continuam ao abrir PDFs em outra aba; interrupções devem
ser pausadas manualmente. Tempos são declarados, incluindo etapas parciais.
Consulta posterior dos mesmos casos não mede economia de tempo: esse valor
permanece null, exigindo desenho comparativo independente para estimá-lo.

Precisão/sensibilidade/F1 descrevem as decisões independentes elegíveis da
amostra, com cobertura desigual e sem extrapolação populacional. Contagem de
mudanças após consulta não demonstra acerto. Ocultação da triagem na interface
não é cegamento formal; identificação é autodeclarada. Não foi realizada
validação profissional ou institucional pelo simples preparo do caderno.

Avaliação via `src.quality_evaluation` aceita o JSON exportado e apresenta
protocolo, exclusões, tempos e métricas. Estado inicial em
`data/piloto_supervisionado_20261023/avaliacao_inicial.json`: zero avaliados,
40 pendentes, precisão/sensibilidade/F1 e tempos null. Caderno anterior e
referência inicial preservados. QA de decisões/tempos somente em fixtures;
provas em `frontend/qa/quality-pilot-verificacao.json`.

## Cobertura documental ampliada — 23/10/2026

Resolvidos os dois downloads PNCP anteriormente bloqueados por tamanho:
linhas 60 e 280, 33 páginas extraídas. Retomada seletiva preservou os outros
214 documentos. RAG/MCP atualizados e indicadores regenerados com histórico:
22 linhas com PDF publicado extraído (antes 20), 72 com ficha/tipo não
validado, 356 não processadas. Amostra visual de seis páginas conferida;
não significa validação integral dos instrumentos ou dos erros de OCR.
Detalhes, limites e provas em PNCP.md. A referência humana e seu caderno
anterior permanecem como retratos preservados, sem decisões inventadas.

## Diagnóstico rastreável e análise de erros — 23/10/2026

A avaliação agora inclui os casos individuais, as decisões e fontes humanas,
a cobertura separada dos grupos com e sem alerta e as linhas divergentes para
segunda conferência independente. Essa fila não afirma que a segunda conferência
já ocorreu. Pendências permanecem fora da matriz de confusão.

Para gerar também um resumo legível, acrescente
`--relatorio data/diagnostico_qualidade.md` ao comando de avaliação. O JSON
contém as justificativas e fontes; o Markdown apresenta cobertura, métricas,
linhas divergentes e hashes. Os dois destinos devem ser diferentes e inéditos.

Diagnóstico real salvo em `data/qualidade_diagnostico_20261023.json` e
`data/qualidade_diagnostico_20261023.md`: 40 selecionados, zero avaliados,
40 pendentes (20 em cada grupo). Precisão, sensibilidade e F1 continuam null.
Não foram atribuídas decisões ou nota ao projeto.

## Caderno de conferência humana disponível

Abra [avaliar.html](data/avaliacao_humana_caderno_20261021/avaliar.html) no navegador. São os mesmos 40 casos da referência inicial: **zero decisões preenchidas, 40 pendentes e métricas ainda não calculáveis**. O caderno foi preparado sem IA ou rede, com dados originais, links oficiais e 50 PDFs locais distintos cujo hash foi conferido. Conferir o hash não valida o conteúdo do PDF.

Cada caso tem campos para decisão, responsável, justificativa e fontes efetivamente conferidas. O botão **Exportar referência preenchida** produz JSON compatível com `src.quality_evaluation`; decisões sem responsável, justificativa ou fontes são bloqueadas na exportação. Casos sem documentos suficientes devem permanecer pendentes, inclusive os inicialmente sem alerta. A cobertura documental é desigual entre os grupos e não pode ser tratada como evidência de acerto.

A triagem original fica em uma seção inicialmente fechada para permitir primeira impressão pelas fontes. O navegador pode preservar um rascunho local, mas a cópia exportada é necessária para guardar e versionar o trabalho. A exportação não altera a referência inicial nem os registros de revisão humana do painel. Não há envio de decisões a serviço externo ou sincronização entre navegadores.

Depois de exportar, informe o caminho do JSON baixado ao comando de avaliação documentado abaixo. Mantenha a pasta do projeto disponível para os links de PDFs locais. O caderno é um retrato das fontes; alterações posteriores exigem conferir os hashes e preparar nova versão.

Para gerar outro caderno, sem sobrescrever uma pasta existente:

```powershell
python -m src.quality_packet --execucao data/reports/20261020T015002Z_72b23869 --referencia data/avaliacao_humana_20261021.json --saida data/avaliacao_humana_caderno_nova_versao
```

Validação: 166 testes Python e 44 frontend/Node, build e QA Playwright desktop/mobile. Formulário, rascunho e exportação preenchida foram testados em casos fictícios; a exportação dos 40 casos reais foi conferida mantendo todas as decisões pendentes. Zero requisições externas ou erros JS no caderno. Provas em `frontend/qa/quality-packet-*.png` e `quality-packet-verificacao.json`.

## O que será medido

Uma nota informal não certifica o sistema. O objetivo é sustentar a evolução com evidências de cobertura, correção das associações, precisão dos alertas, casos perdidos, desempenho e utilidade para a análise humana.

A primeira entrega é `src/quality_evaluation.py`: avaliação da triagem original contra decisões humanas sobre **necessidade de diligência**. Não mede comprovação de ilegalidade nem a qualidade de cada frase dos agentes. A decisão humana também pode conter erros; recomenda-se segunda conferência independente dos casos divergentes.

## Amostra real preparada

Arquivo: `data/avaliacao_humana_20261021.json`.

Execução: `20261020T015002Z_72b23869`. Seleção aleatória reproduzível com semente 42: até 20 contratos com alerta e até 20 sem alerta. São 40 decisões inicialmente pendentes. Coleta e parecer originais não foram alterados. Não houve chamadas à IA, ao portal ou ao banco.

Para cada linha, consultar o registro original e as fontes oficiais. Preencher:

- `exige_diligencia`: `true` quando há fundamento documental para diligência; `false` quando a triagem não se sustenta após a conferência; manter `null` se os dados não permitem decidir.
- `responsavel`: pessoa que realizou a avaliação.
- `justificativa`: raciocínio e limites da decisão.
- `fontes`: lista de referências conferidas, incluindo documento e página quando aplicável.

Falta de documentação, isoladamente, não deve ser convertida automaticamente em falso positivo ou decisão negativa. Não alterar linhas nem hashes. Salvar uma cópia versionada do arquivo preenchido e conservar a referência inicial. Os registros existentes de revisão humana no painel têm outra finalidade e não são convertidos automaticamente em referência de avaliação.

Gerar uma nova amostra, na raiz do projeto:

```powershell
python -m src.quality_evaluation --execucao data/reports/20261020T015002Z_72b23869 --por-grupo 20 --saida data/nova_amostra.json
```

Avaliar a amostra preenchida:

```powershell
python -m src.quality_evaluation --execucao data/reports/20261020T015002Z_72b23869 --referencia data/avaliacao_humana_preenchida.json --saida data/resultado_avaliacao.json
```

O comando recusa sobrescrever uma saída existente. Aceita avaliação parcial e publica o número de pendências. Exige correspondência dos hashes da coleta, parecer e registros; rejeita linhas repetidas, decisões sem justificativa/fontes e tipos inválidos.

Precisão = VP / (VP + FP). Sensibilidade = VP / (VP + FN). F1 = 2VP / (2VP + FP + FN). Denominadores zero produzem `null`. Os valores descrevem apenas os casos efetivamente avaliados. A seleção estratificada e eventuais pendências impedem extrapolar esses valores diretamente aos 450 contratos. Não há estimativa populacional ponderada ou intervalo de confiança nesta versão.

## Entregas e critérios de aceite

| Frente | Entrega necessária | Evidência de aceite |
| --- | --- | --- |
| Qualidade dos alertas | Referência humana, decisões rastreáveis e conjunto reservado para avaliação | Matriz de confusão, pendências explícitas, análise dos erros e revisão independente das divergências |
| Documentação | Instrumentos integrais, anexos e aditivos vinculados ao contrato certo | Original, fonte, hash, páginas e vínculo conferido; ficha cadastral continua identificada como ficha |
| Reconciliação PNCP | Consulta oficial com paginação e vínculos candidatos/confirmados/conflitantes | Cobertura municipal verificada; amostra de associações conferida, inclusive homônimos e contratos ausentes |
| Execução financeira | Empenhos, liquidações, pagamentos, estornos e medições relacionados | Reconciliação dos valores e períodos sem equiparar reconhecimento de dívida a pagamento |
| Preços | Itens, unidades, quantidades e referências comparáveis | Critérios de inclusão/exclusão, cálculos reproduzíveis e ausência de conclusão quando não há comparáveis |
| Resultados públicos | Entregas contratadas, realizadas e indicadores de resultado | Evidências de execução e avaliação humana do benefício esperado |
| Operação | Tempos, chamadas, consumo informado pelo provedor, falhas e recuperação | Medições reais por etapa e testes de recuperação; custo não estimado como zero na falta de informação |

Prioridade escolhida pelo usuário: documentos integrais e reconciliação PNCP.
A primeira integração foi implementada e testada com dados reais em 21/10/2026:
22 vínculos confirmados por regras, 19 PDFs extraídos (um parcial) e dois
downloads pendentes por tamanho. Consulte PNCP.md para cobertura, contagens,
validação e limitações. A ampliação da cobertura documental e as demais
frentes continuam pendentes; esta entrega não conclui a evolução inteira.

Também foi entregue a camada descritiva pandas: cobertura por linha,
distribuição de valores contratuais por CNPJ e tratamento de identidades
repetidas, com resultado real e consulta no painel/MCP. Consulte
INDICADORES.md. Essa camada não mede execução financeira nem substitui
a referência humana necessária para medir acertos e erros dos alertas.

Não existe nota 10 atribuída automaticamente, meta universal de precisão nem certificação institucional. Critérios de desempenho devem ser definidos após a primeira rodada humana e conforme o uso pretendido.
