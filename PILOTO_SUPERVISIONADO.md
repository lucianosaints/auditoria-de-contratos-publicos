# Piloto supervisionado — avaliação feita pelo usuário

Preparado em 23/10/2026. Ainda não há avaliações reais ou tempos de trabalho
registrados. O usuário informou que fará a avaliação; sua identificação e
função serão preenchidas por ele. Qualificação profissional não foi verificada.

Abra `iniciar_piloto.bat` com dois cliques ou o arquivo
[avaliar.html](data/piloto_supervisionado_20261023/avaliar.html).

## Como começar

1. Preencha sua identificação. A função/experiência é opcional e autodeclarada.
2. Abra o primeiro caso e inicie o cronômetro da conferência independente.
3. Confira registro e fontes. Registre decisão, justificativa e documentos/páginas
   efetivamente conferidos. Se as fontes não permitirem decidir, deixe pendente
   e explique a insuficiência; não converta falta de documentos em decisão negativa.
4. Marque se já conhecia a triagem daquele caso, mesmo que a tenha visto fora
   deste caderno. Esses casos ficam fora das métricas da referência independente.
5. Encerre a primeira etapa. Você pode reabri-la antes de consultar a triagem.
6. Consulte a triagem quando quiser comparar. Depois disso, sua primeira avaliação
   fica bloqueada na interface. Uma opinião posterior é registrada separadamente,
   com justificativa, e não substitui a referência independente.
7. Exporte o progresso ao terminar cada sessão. Use Importar progresso salvo para
   retomar o JSON no mesmo caderno. O navegador pode manter um rascunho, mas a
   exportação é a cópia que você pode guardar. Use uma aba por vez.

Comece com poucos casos para conhecer o formulário, exporte e retome. Você não
precisa concluir os 40 em uma sessão. Casos com documentação insuficiente podem
continuar pendentes mesmo após encerrar a primeira etapa.

Na conferência, verifique número/ano do contrato, processo, órgão e CNPJ do
fornecedor. Diferencie ficha cadastral, instrumento contratual e documento de
execução. Compare campos equivalentes de datas e valores. Registre o fundamento
específico da diligência e seus limites; valor contratual não demonstra pagamento.

## O que o cronômetro mede

Há uma medição por caso para a conferência independente e outra para a consulta
posterior ao sistema. Só uma medição fica ativa por vez. O tempo continua ao ler
PDFs em outra aba. Pause nas interrupções. Fechar/recarregar pausa a medição,
salva o tempo no rascunho quando disponível e exige retomada manual.

São tempos de cronômetro declarados, incluindo etapas parciais, sujeitos a
interrupções esquecidas e à disponibilidade do armazenamento do navegador.
Não há monitoramento de atividade nem certificação do tempo efetivamente trabalhado.

**O tempo adicional de consultar o sistema nos mesmos casos não mede economia
de tempo.** Para estimá-la, será necessário um desenho comparativo independente,
com casos/grupos comparáveis e controle da experiência prévia. O avaliador publica
`tempo_economizado_segundos: null` neste piloto.

## Como os resultados serão avaliados

- Amostra preservada: mesmos 40 casos, 20 originalmente com alerta e 20 sem.
  A seleção é estratificada; métricas não são extrapoladas aos 450 contratos.
- A triagem original só aparece após encerrar a conferência independente. É uma
  ocultação da interface; o arquivo local contém a triagem e não implementa
  cegamento formal de pesquisa. O avaliador deve respeitar a ordem do protocolo.
- Precisão, sensibilidade, F1 e divergências usam apenas decisões independentes
  encerradas, fundamentadas e sem exposição prévia declarada. Os demais casos
  ficam pendentes de validação nas métricas, mesmo quando houver uma opinião salva.
- A cobertura documental é desigual. Os casos sem alerta frequentemente não têm
  dossiê local processado. Os links oficiais podem ser usados para obter fontes;
  a ausência de material no caderno não constitui evidência de regularidade.
- Reavaliações após consultar a triagem mostram mudanças de opinião e comentários
  de utilidade; mudança de opinião não demonstra acerto do sistema.
- As divergências devem passar por nova conferência independente antes de ajustar
  regras/prompts. A amostra atual já foi usada para preparar o piloto; não deve
  ser apresentada depois como conjunto reservado de avaliação final.
- A referência humana também pode conter erros. Um piloto de um avaliador não
  constitui validação institucional, jurídica ou certificação da qualidade.

Depois de exportar, informe o caminho de `avaliacao_piloto_preenchida.json` para
calcular as métricas. Também é possível usar o comando, na raiz do projeto:

```powershell
python -m src.quality_evaluation --execucao data/reports/20261020T015002Z_72b23869 --referencia CAMINHO_DO_JSON_EXPORTADO --saida data/resultado_piloto_v1.json --relatorio data/resultado_piloto_v1.md
```

Escolha destinos novos em cada avaliação. O avaliador aceita progresso parcial,
confere identidade das fontes, linha/registro, ordem das etapas, campos obrigatórios,
tempos e preservação da primeira avaliação. Não mede a qualidade de toda frase
da IA, detecção de fraude ou execução financeira reconciliada.

## Preservação e operação

O caderno é independente do painel: não inicia auditoria, Gemini ou banco.
PDFs locais foram conferidos por hash e dependem das pastas originais. Fontes
oficiais só são acessadas quando você abre os respectivos links. Nenhuma decisão
é sincronizada com outros navegadores ou gravada automaticamente na auditoria.

A referência original e o caderno de 21/10 permanecem preservados. O novo retrato
usa o manifesto documental atual, sem transformar candidatos PNCP conflitantes
em vínculos confirmados. A função `src.quality_packet.build_packet(..., pilot=True)`
e a opção CLI `--piloto` permitem gerar novas versões; uma referência preenchida
não é convertida silenciosamente em uma referência independente nova.
