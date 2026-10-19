from __future__ import annotations

import json
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    sync_playwright,
)

from checks.global_duplicate_check import (
    executar_checks_globais,
)
from checks.registry import obter_checks
from collectors.page_collector import coletar_page_data
from config.settings import (
    HEADLESS,
    LIMITE_DESCOBERTA,
    LIMITE_MPIS,
    REPORTS_DIR,
    TEMPO_ESPERA_PAGINA,
    TIMEOUT_NAVEGACAO,
    VIEWPORT_DESKTOP,
)
from crawler.internal_crawler import executar_crawler
from exporters.html_exporter import exportar_relatorio_html
from models.page_data import PageData
from reporters.prontuario_reporter import (
    gerar_itens_prontuario,
)
from selectors.page_selector import (
    imprimir_resumo_selecao,
    selecionar_paginas,
)
from utils.url_helper import eh_url_interna


def preparar_pastas() -> None:
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def executar_checks(
    page: Page,
    contexto: dict[str, Any],
) -> list[dict[str, Any]]:
    resultados: list[
        dict[str, Any]
    ] = []

    for check in obter_checks():
        try:
            resultado = check.executar(
                page=page,
                contexto=contexto,
            )

        except Exception as erro:
            resultado = check.resultado(
                status="error",
                observacao=(
                    "Erro ao executar "
                    f"a validação: {erro}"
                ),
            )

        resultados.append(
            resultado
        )

    return resultados


def criar_contexto(
    page_data: PageData,
    url_principal: str,
) -> dict[str, Any]:
    return {
        "status_http": (
            page_data.status_http
        ),
        "url_solicitada": (
            page_data.url_solicitada
        ),
        "url_final": (
            page_data.url_final
        ),
        "url_principal": (
            url_principal
        ),
        "page_data": (
            page_data
        ),
    }


def criar_resultado_pagina(
    url: str,
) -> dict[str, Any]:
    return {
        "url_solicitada": url,
        "url_final": None,
        "status_http": None,
        "erro_navegacao": "",
        "ignorada": False,
        "motivo_ignorada": "",
        "page_data": {},
        "checks": [],
    }


def auditar_pagina(
    page: Page,
    url: str,
    numero: int,
    total: int,
    url_principal: str,
) -> dict[str, Any]:
    print(
        f"\n🌐 Auditando "
        f"({numero}/{total}): "
        f"{url}"
    )

    resultado_pagina = (
        criar_resultado_pagina(
            url
        )
    )

    if not eh_url_interna(
        url=url,
        url_principal=url_principal,
    ):
        resultado_pagina.update(
            {
                "url_final": url,
                "ignorada": True,
                "motivo_ignorada": (
                    "URL externa ignorada "
                    "antes da navegação."
                ),
            }
        )

        print(
            "   ⚠️ URL externa ignorada:"
        )

        print(
            f"   {url}"
        )

        return resultado_pagina

    try:
        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=TIMEOUT_NAVEGACAO,
        )

        page.wait_for_timeout(
            TEMPO_ESPERA_PAGINA
        )

        url_final_navegacao = (
            page.url
        )

        status_http = (
            response.status
            if response
            else None
        )

        if not eh_url_interna(
            url=url_final_navegacao,
            url_principal=url_principal,
        ):
            resultado_pagina.update(
                {
                    "url_final": (
                        url_final_navegacao
                    ),
                    "status_http": (
                        status_http
                    ),
                    "ignorada": True,
                    "motivo_ignorada": (
                        "A URL interna "
                        "redirecionou para "
                        "um domínio externo."
                    ),
                }
            )

            print(
                "   ⚠️ Redirecionamento "
                "externo ignorado:"
            )

            print(
                f"   {url_final_navegacao}"
            )

            return resultado_pagina

        page_data = coletar_page_data(
            page=page,
            response=response,
            url_solicitada=url,
        )

        contexto = criar_contexto(
            page_data=page_data,
            url_principal=url_principal,
        )

        resultados = executar_checks(
            page=page,
            contexto=contexto,
        )

        resultado_pagina.update(
            {
                "url_final": (
                    page_data.url_final
                ),
                "status_http": (
                    page_data.status_http
                ),
                "page_data": (
                    page_data.to_dict(
                        include_html=False
                    )
                ),
                "checks": resultados,
            }
        )

    except PlaywrightError as erro:
        resultado_pagina[
            "erro_navegacao"
        ] = str(
            erro
        )

        print(
            "   ❌ Falha ao acessar "
            "a página."
        )

        print(
            f"   {erro}"
        )

    except Exception as erro:
        resultado_pagina[
            "erro_navegacao"
        ] = str(
            erro
        )

        print(
            "   ❌ Erro inesperado "
            "durante a auditoria."
        )

        print(
            f"   {erro}"
        )

    return resultado_pagina


def auditar_urls(
    context: BrowserContext,
    urls: list[str],
    url_principal: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    paginas_auditadas: list[
        dict[str, Any]
    ] = []

    urls_ignoradas: list[
        dict[str, Any]
    ] = []

    page = context.new_page()

    try:
        for indice, url in enumerate(
            urls,
            start=1,
        ):
            resultado = auditar_pagina(
                page=page,
                url=url,
                numero=indice,
                total=len(urls),
                url_principal=url_principal,
            )

            if resultado.get(
                "ignorada",
                False,
            ):
                urls_ignoradas.append(
                    resultado
                )

                continue

            paginas_auditadas.append(
                resultado
            )

    finally:
        page.close()

    return (
        paginas_auditadas,
        urls_ignoradas,
    )


def mostrar_resumo(
    paginas: list[dict[str, Any]],
    checks_globais: list[
        dict[str, Any]
    ],
    urls_ignoradas: list[
        dict[str, Any]
    ],
    selecao_paginas: dict[str, Any],
) -> None:
    aprovados = 0
    rejeitados = 0
    erros = 0

    for pagina in paginas:
        if pagina.get(
            "erro_navegacao"
        ):
            erros += 1

        for check in pagina.get(
            "checks",
            [],
        ):
            status = check.get(
                "status"
            )

            if status == "approved":
                aprovados += 1

            elif status == "rejected":
                rejeitados += 1

            else:
                erros += 1

    for check in checks_globais:
        status = check.get(
            "status",
            "error",
        )

        if status == "approved":
            aprovados += 1

        elif status == "rejected":
            rejeitados += 1

        else:
            erros += 1

    print(
        "\n" + "=" * 55
    )

    print(
        "RESUMO DA AUDITORIA"
    )

    print(
        "=" * 55
    )

    print(
        "URLs descobertas: "
        f"{selecao_paginas.get(
            'quantidade_descobertas',
            0,
        )}"
    )

    print(
        "URLs selecionadas: "
        f"{selecao_paginas.get(
            'quantidade_selecionadas',
            0,
        )}"
    )

    print(
        "MPIs selecionadas: "
        f"{selecao_paginas.get(
            'quantidade_mpis',
            0,
        )}"
    )

    print(
        "URLs internas auditadas: "
        f"{len(paginas)}"
    )

    print(
        "URLs externas ignoradas: "
        f"{len(urls_ignoradas)}"
    )

    print(
        "Checks globais: "
        f"{len(checks_globais)}"
    )

    print(
        f"Checks aprovados: {aprovados}"
    )

    print(
        f"Checks rejeitados: {rejeitados}"
    )

    print(
        f"Erros de execução: {erros}"
    )


def salvar_relatorio_tecnico(
    url_inicial: str,
    paginas: list[dict[str, Any]],
    checks_globais: list[
        dict[str, Any]
    ],
    urls_ignoradas: list[
        dict[str, Any]
    ],
    selecao_paginas: dict[str, Any],
) -> Path:
    relatorio = {
        "info": {
            "url_inicial": url_inicial,
            "dominio_principal": (
                urlparse(
                    url_inicial
                ).netloc
            ),
            "data_execucao": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
            "quantidade_paginas": len(
                paginas
            ),
            "quantidade_urls_descobertas": (
                selecao_paginas.get(
                    "quantidade_descobertas",
                    0,
                )
            ),
            "quantidade_urls_selecionadas": (
                selecao_paginas.get(
                    "quantidade_selecionadas",
                    0,
                )
            ),
            "quantidade_mpis_selecionadas": (
                selecao_paginas.get(
                    "quantidade_mpis",
                    0,
                )
            ),
            "quantidade_urls_externas_ignoradas": (
                len(
                    urls_ignoradas
                )
            ),
            "quantidade_checks_globais": (
                len(
                    checks_globais
                )
            ),
            "limite_descoberta": (
                LIMITE_DESCOBERTA
            ),
            "limite_mpis": (
                LIMITE_MPIS
            ),
        },
        "selecao_paginas": {
            "categorias": (
                selecao_paginas.get(
                    "categorias",
                    {},
                )
            ),
            "categorias_nao_encontradas": (
                selecao_paginas.get(
                    "categorias_nao_encontradas",
                    [],
                )
            ),
            "paginas": (
                selecao_paginas.get(
                    "paginas",
                    [],
                )
            ),
        },
        "checks_globais": (
            checks_globais
        ),
        "urls_externas_ignoradas": (
            urls_ignoradas
        ),
        "paginas": paginas,
    }

    caminho = (
        REPORTS_DIR
        / "auditoria_completa.json"
    )

    with caminho.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            relatorio,
            arquivo,
            indent=4,
            ensure_ascii=False,
        )

    return caminho


MAPEAMENTO_DIRETO_PRONTUARIO = {
    "Google Analytics 4 - GA4": (
        "Tag Google Analytics (GA4)"
    ),
    "Menu Ativo": (
        "Botão - Active Menu"
    ),
    "Images - Broken": (
        "Imagem quebrada"
    ),
    "Images - Over 200 KB": (
        "Imagens - Over 200kb"
    ),
    "Banners - Over 500 KB": (
        "Imagens - Banner Over 500kb"
    ),
    "Favicon": (
        "Favicon funcional (32x32)"
    ),
    "Input Masks": (
        "Máscaras ativas nos campos de entrada "
        "(telefone, CPF, etc.)"
    ),
    "Links de contatos clicáveis e funcionais": (
        "Links de números clicáveis e funcionais"
    ),
    "Phone Numbers - Formatting": (
        "Texto Formatação - Números de Telefone "
        "(Ex: 11 99999-9999/11 5555-5555)"
    ),
    "Emails - Formatting": (
        "Texto Formatação - Emails (Ex: email@dominio.com)"
    ),
    "Robots.txt - Existência": (
        "Configuração do arquivo robots.txt"
    ),
    "Sitemap XML - Validade": (
        "Sitemap.xml"
    ),
}


ITENS_DIRETOS_PRONTUARIO = {
    "CTA - Botão WhatsApp",
    "Links de números clicáveis e funcionais",
    "Emails clicáveis e funcionais (mailto:)",
    "Google Maps carregando e funcional",
    "Nenhum link ou botão quebrado (404/500)",
    "Lorem Ipsum",
    "H1 Missing",
    "H1 Multiple",
    "H1 Duplicate",
    "H2 Missing",
    "URLs - Contains Space",
    "URLs - Multiple Slashes",
    "URLs - Non ASCII Characters URL",
    "URLs - Over Characters",
    "URLs - Uppercase",
    "Response Codes - Client Error",
    "Response Codes - Redirection",
    "Response Codes - Server Error",
    "Response Codes - Success",
    "Meta Descriptions - Duplicate",
    "Meta Descriptions - Missing",
    "Meta Descriptions - Over 160 caracteres",
    "Page Titles - Missing",
    "Page Titles - Duplicate",
    "Page Titles - Over 100 caracteres",
    "Mixed Content HTTP/HTTPS",
    "Missing HSTS",
    "HTTPS URL’s (100% das URLs)",
    "Missing X Frame Options",
    "Missing Secure Referrer Policy",
    "Missing Content Security Policy",
    "Missing X Content Type Options",
}


GRUPOS_PRONTUARIO = {
    (
        "Todos formulários com validação "
        "e reCAPTCHA ativo (v2 ou v3)"
    ): [
        "Formulário presente",
        "Formulário - Método POST",
        "Formulário - Botão de envio",
        "Formulário - Campos identificados",
        "Formulário - reCAPTCHA presente",
        "Formulário - Apenas um tipo de reCAPTCHA",
    ],
    "Menu Header = Menu Footer + Mapa do Site": [
        "Menu Header x Footer",
        "Mapa do Site no Footer",
    ],
    "Mapa do Site": [
        "Mapa do Site no Footer",
    ],
    "Scroll lateral": [
        "Responsividade - Desktop 1920px",
        "Responsividade - Mobile 394px",
        "Responsividade - Tablet 768px",
    ],
}


def normalizar_status_prontuario(
    status: str,
) -> str:
    if status == "approved":
        return "approved"

    if status == "rejected":
        return "rejected"

    return "warning"


def combinar_itens_prontuario(
    nomes_checks: list[str],
    itens: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    resultados = [
        (
            nome,
            itens[nome],
        )
        for nome in nomes_checks
        if nome in itens
    ]

    if not resultados:
        return None

    checks_ausentes = [
        nome
        for nome in nomes_checks
        if nome not in itens
    ]

    statuses = [
        normalizar_status_prontuario(
            str(
                resultado.get(
                    "status",
                    "",
                )
            )
        )
        for _, resultado in resultados
    ]

    if "rejected" in statuses:
        status_final = "rejected"

    elif (
        "warning" in statuses
        or checks_ausentes
    ):
        status_final = "warning"

    else:
        status_final = "approved"

    observacoes: list[str] = []

    for nome, resultado in resultados:
        observacao = str(
            resultado.get(
                "obs",
                "",
            )
        ).strip()

        if observacao:
            observacoes.append(
                f"{nome}:\n{observacao}"
            )

    if checks_ausentes:
        observacoes.append(
            "Validação automática parcial. "
            "Checks não encontrados: "
            + ", ".join(
                checks_ausentes
            )
            + "."
        )

    return {
        "status": status_final,
        "obs": "\n\n".join(
            observacoes
        ),
        "imgs": [],
    }


def gerar_itens_importacao_prontuario(
    itens: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    itens_importacao: dict[
        str,
        dict[str, Any],
    ] = {}

    for nome, resultado in itens.items():
        nome_prontuario = (
            MAPEAMENTO_DIRETO_PRONTUARIO.get(
                nome,
                nome,
            )
        )

        nome_valido = (
            nome in ITENS_DIRETOS_PRONTUARIO
            or nome
            in MAPEAMENTO_DIRETO_PRONTUARIO
        )

        if not nome_valido:
            continue

        itens_importacao[
            nome_prontuario
        ] = {
            "status": (
                normalizar_status_prontuario(
                    str(
                        resultado.get(
                            "status",
                            "",
                        )
                    )
                )
            ),
            "obs": str(
                resultado.get(
                    "obs",
                    "",
                )
            ),
            "imgs": [],
        }

    for (
        nome_prontuario,
        nomes_checks,
    ) in GRUPOS_PRONTUARIO.items():
        resultado_combinado = (
            combinar_itens_prontuario(
                nomes_checks=nomes_checks,
                itens=itens,
            )
        )

        if resultado_combinado is None:
            continue

        itens_importacao[
            nome_prontuario
        ] = resultado_combinado

    return itens_importacao


def salvar_prontuario_automatico(
    url_inicial: str,
    paginas: list[dict[str, Any]],
    itens: dict[
        str,
        dict[str, Any],
    ],
    urls_ignoradas: list[
        dict[str, Any]
    ],
    selecao_paginas: dict[str, Any],
) -> Path:
    itens_importacao = (
        gerar_itens_importacao_prontuario(
            itens
        )
    )

    prontuario = {
        "info": {
            "dominio": (
                urlparse(
                    url_inicial
                ).netloc
            ),
            "data_validacao": (
                datetime.now()
                .date()
                .isoformat()
            ),
            "tipo": "AUTOMATICO",
            "quantidade_paginas": len(
                paginas
            ),
            "quantidade_urls_descobertas": (
                selecao_paginas.get(
                    "quantidade_descobertas",
                    0,
                )
            ),
            "quantidade_urls_selecionadas": (
                selecao_paginas.get(
                    "quantidade_selecionadas",
                    0,
                )
            ),
            "quantidade_mpis_selecionadas": (
                selecao_paginas.get(
                    "quantidade_mpis",
                    0,
                )
            ),
            "quantidade_urls_externas_ignoradas": (
                len(
                    urls_ignoradas
                )
            ),
        },
        "selecao_paginas": {
            "categorias": (
                selecao_paginas.get(
                    "categorias",
                    {},
                )
            ),
            "categorias_nao_encontradas": (
                selecao_paginas.get(
                    "categorias_nao_encontradas",
                    [],
                )
            ),
        },
        "items": itens_importacao,
        "groupBy": "tool",
        "generalComments": (
            "Relatório gerado automaticamente "
            "pelo QA Auditor. A auditoria utilizou "
            "seleção inteligente de páginas. "
            "URLs externas não foram auditadas."
        ),
    }

    caminho = (
        REPORTS_DIR
        / "prontuario_automatico.json"
    )

    with caminho.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            prontuario,
            arquivo,
            indent=4,
            ensure_ascii=False,
        )

    return caminho


def executar_auditoria(
    url_inicial: str,
) -> None:
    preparar_pastas()

    with sync_playwright() as playwright:
        browser = (
            playwright.chromium.launch(
                headless=HEADLESS,
            )
        )

        context = browser.new_context(
            viewport=VIEWPORT_DESKTOP,
            ignore_https_errors=True,
        )

        try:
            print(
                "\nIniciando descoberta "
                "de URLs internas...\n"
            )

            paginas_descobertas = (
                executar_crawler(
                    context=context,
                    url_inicial=url_inicial,
                    limite_paginas=(
                        LIMITE_DESCOBERTA
                    ),
                )
            )

            if not paginas_descobertas:
                print(
                    "❌ Nenhuma URL interna "
                    "foi encontrada."
                )

                return

            print(
                "\n🧠 Selecionando páginas "
                "relevantes para auditoria..."
            )

            selecao_paginas = (
                selecionar_paginas(
                    paginas_descobertas=(
                        paginas_descobertas
                    ),
                    limite_mpis=LIMITE_MPIS,
                )
            )

            imprimir_resumo_selecao(
                selecao_paginas
            )

            urls_auditoria = (
                selecao_paginas.get(
                    "urls",
                    [],
                )
            )

            if not urls_auditoria:
                print(
                    "\n❌ Nenhuma página foi "
                    "selecionada para auditoria."
                )

                return

            print(
                "\n🚀 Iniciando auditoria "
                "das páginas selecionadas..."
            )

            (
                paginas_auditadas,
                urls_ignoradas,
            ) = auditar_urls(
                context=context,
                urls=urls_auditoria,
                url_principal=url_inicial,
            )

            if not paginas_auditadas:
                print(
                    "\n❌ Nenhuma página "
                    "interna pôde ser "
                    "auditada."
                )

                return

            print(
                "\n🔎 Executando checks "
                "globais..."
            )

            checks_globais = (
                executar_checks_globais(
                    paginas=paginas_auditadas,
                )
            )

            itens_prontuario = (
                gerar_itens_prontuario(
                    paginas=paginas_auditadas,
                    checks_globais=checks_globais,
                )
            )

            caminho_tecnico = (
                salvar_relatorio_tecnico(
                    url_inicial=url_inicial,
                    paginas=paginas_auditadas,
                    checks_globais=checks_globais,
                    urls_ignoradas=urls_ignoradas,
                    selecao_paginas=selecao_paginas,
                )
            )

            caminho_prontuario = (
                salvar_prontuario_automatico(
                    url_inicial=url_inicial,
                    paginas=paginas_auditadas,
                    itens=itens_prontuario,
                    urls_ignoradas=urls_ignoradas,
                    selecao_paginas=selecao_paginas,
                )
            )

            caminho_html = (
                exportar_relatorio_html(
                    url_inicial=url_inicial,
                    paginas=paginas_auditadas,
                    itens_prontuario=itens_prontuario,
                    caminho_saida=(
                        REPORTS_DIR
                        / "relatorio_qa.html"
                    ),
                )
            )

            mostrar_resumo(
                paginas=paginas_auditadas,
                checks_globais=checks_globais,
                urls_ignoradas=urls_ignoradas,
                selecao_paginas=selecao_paginas,
            )

            print(
                f"\n📄 Relatório técnico: "
                f"{caminho_tecnico}"
            )

            print(
                f"📋 Prontuário automático: "
                f"{caminho_prontuario}"
            )

            print(
                f"🌐 Dashboard HTML: "
                f"{caminho_html}"
            )

            try:
                webbrowser.open(
                    caminho_html
                    .resolve()
                    .as_uri()
                )

            except Exception:
                pass

        finally:
            context.close()
            browser.close()