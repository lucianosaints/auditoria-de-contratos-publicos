import json
from pathlib import Path
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright
from src.config import get_portal_config
from src.tools.portal_details import enrich_contracts, row_details
from src.office_activity import source_request

class ExtratorContratosMarica(BaseTool):
    name: str = "extrator_contratos_marica"
    description: str = "Extrai os contratos do portal de transparência filtrando estritamente pelo ano de 2026 via Playwright."
    output_dir: Path | None = None

    def _run(self, object: str = "", process_number: str = "") -> str:
        portal_cfg = get_portal_config()
        url_base = portal_cfg["url"]
        portal_name = portal_cfg["name"]
        todos_contratos = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                print(f"Acedendo ao Portal da Transparência ({portal_name} - {url_base})...")
                with source_request(url_base, f'Portal da Transparência ({portal_name}) · contratos'):
                    page.goto(url_base, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                
                # 1. Aplica o filtro estrito para o ano de 2026
                try:
                    # Assegura a presença da opção no DOM para permitir o disparo do evento de filtro
                    page.evaluate("""() => {
                        const sel = document.querySelector("select[name='year']");
                        if (sel && !Array.from(sel.options).some(o => o.value === '2026')) {
                            const opt = document.createElement('option');
                            opt.value = '2026';
                            opt.text = '2026';
                            sel.appendChild(opt);
                        }
                    }""")
                    with page.expect_response(lambda response: '/configurar/ano' in response.url and response.request.method == 'PUT') as year_response:
                        page.select_option("select[name='year']", "2026", timeout=5000)
                        page.evaluate("document.querySelector(\"select[name='year']\").dispatchEvent(new Event('change'))")
                    if not year_response.value.ok:
                        raise RuntimeError('O portal não confirmou o filtro de 2026.')
                    page.wait_for_function("document.querySelector('select[name=year]')?.value === '2026' && !document.querySelector('select[name=year]')?.disabled")
                    print("Filtro de ano '2026' aplicado com sucesso.")
                except Exception as exc:
                    raise RuntimeError('Não foi possível confirmar o filtro de 2026.') from exc

                # 2. Cica no botão de pesquisar/filtrar para atualizar a tabela
                try:
                    botao_pesquisar = page.locator("button[type='submit'], input[type='submit'], button:has-text('Pesquisar')")
                    if botao_pesquisar.count() > 0:
                        with page.expect_response(lambda response: '/pesquisar' in response.url and response.request.method == 'POST') as search_response:
                            botao_pesquisar.first.click(timeout=5000)
                        if not search_response.value.ok:
                            raise RuntimeError('Pesquisa de contratos falhou.')
                        page.wait_for_load_state("domcontentloaded")
                        page.wait_for_timeout(3000)
                except Exception as exc:
                    raise RuntimeError('Não foi possível concluir a pesquisa.') from exc

                # Aguarda a tabela carregar
                try:
                    page.wait_for_selector("table", timeout=20000)
                except Exception:
                    print("Tabela não visível imediatamente.")

                pagina = 1
                max_tentativas_paginacao = 50

                while pagina <= max_tentativas_paginacao:
                    print(f"Extraindo dados da página {pagina} (Ano: 2026)...")
                    
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    tabela = soup.find('table')

                    if tabela:
                        headers_tabela = [th.text.strip() for th in tabela.find_all('th')]
                        corpo_tabela = tabela.find('tbody')
                        linhas = corpo_tabela.find_all('tr') if corpo_tabela else tabela.find_all('tr')[1:]
                        
                        contratos_pagina = []
                        for linha in linhas:
                            colunas = linha.find_all('td')
                            if len(colunas) == len(headers_tabela):
                                contrato = {headers_tabela[i]: colunas[i].text.strip().replace('\n', ' ') for i in range(len(colunas))}
                                contrato.update(row_details(linha, url_base))
                                
                                # Garante no código que apenas registos de 2026 (ou sem data explícita se necessário) entram
                                data_vigencia = contrato.get("Período de Vigência", "")
                                data_assinatura = contrato.get("Data Assinatura", "")
                                
                                # Filtro secundário de segurança para reter apenas o ano 2026
                                if "2026" in data_vigencia or "2026" in data_assinatura or not data_vigencia:
                                    contratos_pagina.append(contrato)

                        for c in contratos_pagina:
                            if c not in todos_contratos:
                                todos_contratos.append(c)

                        if not contratos_pagina:
                            break

                    # Navegação para a próxima página
                    proximo_botao = page.locator("ul.pagination li a, div.pagination a").filter(has_text="Próximo")
                    if proximo_botao.count() == 0:
                        proximo_botao = page.locator("a.page-link", has_text="Próximo")

                    if proximo_botao.count() > 0:
                        try:
                            pai_class = proximo_botao.first.locator("xpath=..").get_attribute("class") or ""
                            if "disabled" in pai_class:
                                break
                            
                            proximo_botao.first.click(timeout=5000)
                            page.wait_for_load_state("domcontentloaded")
                            page.wait_for_timeout(2000)
                            pagina += 1
                        except Exception:
                            break
                    else:
                        proxima_pagina_link = page.locator(f"a:text('{pagina + 1}')")
                        if proxima_pagina_link.count() > 0:
                            proxima_pagina_link.first.click()
                            page.wait_for_load_state("domcontentloaded")
                            page.wait_for_timeout(2000)
                            pagina += 1
                        else:
                            break

                    # Limite de segurança razoável para o ano corrente
                    if len(todos_contratos) >= 500:
                        break

                # CSV é evidência separada: não se presume que contenha todas as páginas.
                if self.output_dir is not None:
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    export_status = {'status': 'não encontrado', 'completude': 'não verificada',
                                     'fonte': url_base, 'ano': '2026'}
                    csv_link = page.locator('a').filter(has_text='.csv')
                    if csv_link.count() == 1:
                        try:
                            with page.expect_download(timeout=60000) as download:
                                csv_link.click()
                            download.value.save_as(str(self.output_dir / 'exportacao_portal.csv'))
                            export_status['status'] = 'salvo'
                        except Exception as exc:
                            export_status.update(status='falhou', erro=str(exc))
                    (self.output_dir / 'exportacao.json').write_text(json.dumps(export_status, ensure_ascii=False, indent=2), encoding='utf-8')
                enrich_contracts(browser, todos_contratos, self.output_dir)
                browser.close()
                return json.dumps(todos_contratos, indent=4, ensure_ascii=False)

        except Exception as exc:
            return json.dumps([{"Erro": "Falha na extração via Playwright", "Detalhe": str(exc)}], ensure_ascii=False)
