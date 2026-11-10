# RAG local e ligação dos agentes por MCP

Implementado em 20/10/2026. O fluxo é:

`PDF baixado → texto/OCR → índice SQLite FTS5 → MCP stdio → dossiê → investigador → revisor → conferência humana`

No painel, selecione a execução e use **Ler documentos → Preparar RAG → Verificar MCP → Revisar com agentes**. A seção **Consultar evidências locais** permite pesquisar termos por linha do contrato e abrir o PDF na página correspondente. Feche e reabra o painel após a atualização para carregar as novas rotas do executor.

Preparar RAG usa apenas textos já extraídos; não baixa arquivos, não chama IA e não altera o banco PostgreSQL. O índice fica em `data/reports/<execucao>/rag/indice.sqlite3`. Um índice sem texto não é publicado como pronto. A ação acompanha o executor e pode ser interrompida; a versão anterior do índice é preservada se a reconstrução falhar.

A busca usa BM25 textual, ignora acentos e seleciona até cinco trechos de até 700 caracteres, com sobreposição de 100. Não há embeddings, banco vetorial, sinônimos automáticos ou busca semântica nesta versão. A consulta dos agentes combina os motivos dos alertas com o objeto publicado. O filtro de execução e linha é obrigatório. Uma sessão MCP atende todas as consultas da revisão, evitando abrir um subprocesso para cada contrato; os textos carregados são reutilizados enquanto os arquivos não mudarem.

O servidor MCP é real, usa o SDK oficial Python 1.x e transporte stdio, somente sob demanda. Não abre porta de rede. Ferramentas disponíveis:

- `estado_indice(execucao)`: cobertura, versão e atualização.
- `buscar_evidencias(execucao, linha, consulta, limite=5)`: trechos literais com URL, página, posições na extração, hash do PDF, tipo documental e qualidade do OCR.
- `consultar_indicadores(execucao, linha=None, limite_fornecedores=10)`: indicadores de gestão salvos e compatíveis com as fontes atuais. Somente leitura, sem IA ou cálculo automático. Uso e critérios em [INDICADORES.md](INDICADORES.md).

Os agentes recebem o resultado das consultas MCP antes das chamadas ao Gemini. A aplicação determina o contrato e o escopo; o modelo seleciona citações do catálogo validado. O revisor só usa as citações aprovadas pelo investigador. Os dados documentais continuam sendo conteúdo não confiável, não instruções para executar ferramentas. Não foram conectados servidores MCP externos.

Sem índice, a revisão mantém o comportamento anterior de trechos iniciais. Havendo índice inválido/desatualizado, ela pede reconstrução antes de prosseguir. Mudanças na coleta ou no manifesto invalidam o índice; cada trecho recuperado é novamente comparado à extração e o PDF é conferido por SHA-256. Resultados RAG e consultas integram a assinatura dos dossiês; checkpoints de contexto diferente não são reaproveitados. A auditoria base e o recibo de arquivamento continuam independentes.

O índice só cobre páginas já extraídas, inclusive seus limites de OCR, downloads e tamanho. Uma ficha cadastral continua identificada como ficha, sem ser apresentada como instrumento contratual completo. Ausência de correspondências não comprova ausência de cláusulas. A busca pode reduzir o contexto enviado, mas não elimina pausas de cota nem garante menor duração da IA ou acerto na interpretação.

## Clientes MCP externos

A integração interna já funciona sem configurar outro programa. Para um cliente externo que aceite `mcpServers`, há o exemplo `mcp.auditoria.example.json`, com os caminhos deste computador. A entrada `mcp_auditoria.py` prepara as dependências locais sem carregar `.env`. O exemplo não foi instalado nas configurações pessoais de nenhum cliente. Ajuste os caminhos ao mover o projeto. A integração segue o [SDK oficial MCP](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x).

Dependências: `requirements.txt` inclui `mcp>=1.28,<2`; `requirements-rag.txt` passa a apontar para essas mesmas dependências, sem instalar LangChain/Chroma/OpenAI. SQLite FTS5 foi verificado no Python local.

## Verificação realizada

Testes cobrem filtro por contrato, recuperação da página 9 em vez da primeira, acentos, consulta com sintaxe FTS hostil, fontes alteradas, PDF alterado, atualização do índice, publicação atômica e citações do dossiê. O teste de integração inicializa um servidor MCP subprocesso real e recupera evidências para os agentes, sem IA.

`frontend/scripts/verify_rag_sample.py` testa uma cópia temporária do PDF real já baixado da linha 109, preservando os arquivos da auditoria principal; prova em `data/raw/rag_verificacao/verificacao.json`. Nenhuma nova chamada ao Gemini, portal ou banco foi feita. A execução principal ainda precisa passar por Ler documentos e Preparar RAG para ter seu próprio índice; o teste isolado não foi publicado nela.

`frontend/scripts/verify_rag_ui.py` confere botões, pesquisa, referência à página, execução selecionada e layout mobile com dados fictícios. Artefatos em `frontend/qa/rag-*`.

Validação final: 115 testes Python, 34 testes Node/frontend e build aprovados. Retomada em cópia dos checkpoints reais anteriores também aprovada: duas etapas recuperadas/migradas, cinco contratos, zero chamadas de IA e originais preservados.
