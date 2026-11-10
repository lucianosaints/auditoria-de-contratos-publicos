# Avaliação humana — 40 casos preparados

Abra `avaliar.html` no navegador. Expanda um caso, confira o registro e as fontes e registre sua avaliação. Existem 40 casos selecionados, sem decisões preenchidas por automação.

- **Há fundamento documental para diligência:** registre responsável, justificativa e fontes conferidas.
- **Não há fundamento para diligência após conferência:** registre os mesmos elementos para sustentar a decisão.
- **Pendente / dados insuficientes:** use quando não houver elementos suficientes para decidir. A falta de documentação não equivale automaticamente a falso positivo ou ausência de problema.

A seção de triagem original começa fechada. Uma primeira impressão pelas fontes pode ajudar a reduzir influência da conclusão do sistema. Fonte publicada ou PDF com hash íntegro não comprova, isoladamente, o mérito do achado.

O rascunho pode ficar neste navegador. Use **Exportar referência preenchida** para baixar e guardar o JSON; o arquivo original não é alterado. A referência exportada pode continuar parcialmente pendente. Os links de PDFs locais dependem de manter a estrutura de pastas do projeto. Este caderno retrata as fontes do instante de preparação e não acompanha alterações futuras.

Para calcular as métricas, na raiz do projeto, use o caminho do arquivo exportado:

```powershell
python -m src.quality_evaluation --execucao data/reports/20261020T015002Z_72b23869 --referencia CAMINHO_DO_JSON_EXPORTADO --saida data/resultado_avaliacao_nova_versao.json
```

Escolha uma saída ainda inexistente. O comando confere os hashes e exige responsável, justificativa e fontes para as decisões concluídas. Métricas descrevem somente a amostra efetivamente avaliada; não devem ser extrapoladas diretamente aos 450 contratos. Os registros de revisão humana do painel têm outra finalidade e não são atualizados automaticamente por esta exportação.
