from __future__ import annotations

from collections import deque
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
)

from utils.url_helper import (
    obter_dominio_normalizado,
    resolver_link_http,
)


EXTENSOES_IGNORADAS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}


def possui_extensao_ignorada(
    url: str,
) -> bool:
    caminho = urlparse(
        url
    ).path.casefold()

    return any(
        caminho.endswith(
            extensao
        )
        for extensao in EXTENSOES_IGNORADAS
    )


def normalizar_link(
    link: str,
    url_base: str,
    dominio_principal: str,
) -> str | None:
    url_absoluta = resolver_link_http(
        link=link,
        url_base=url_base,
    )

    if not url_absoluta:
        return None

    dominio_link = obter_dominio_normalizado(
        url_absoluta
    )

    if dominio_link != dominio_principal:
        return None

    if possui_extensao_ignorada(
        url_absoluta
    ):
        return None

    partes = urlparse(
        url_absoluta
    )

    caminho = partes.path

    if (
        caminho != "/"
        and url_absoluta.endswith("/")
    ):
        url_absoluta = url_absoluta.rstrip(
            "/"
        )

    return url_absoluta


def criar_registro_pagina(
    url: str,
    profundidade: int,
    origem: str = "",
) -> dict[str, Any]:
    return {
        "url": url,
        "titulo": "",
        "h1": "",
        "breadcrumb": "",
        "textos_links": [],
        "no_menu": False,
        "na_home": False,
        "profundidade": profundidade,
        "origem": origem,
    }


def adicionar_texto_link(
    registro: dict[str, Any],
    texto: str,
) -> None:
    texto_limpo = texto.strip()

    if not texto_limpo:
        return

    textos_links = registro.setdefault(
        "textos_links",
        [],
    )

    if texto_limpo not in textos_links:
        textos_links.append(
            texto_limpo
        )


def coletar_dados_da_pagina(
    context: BrowserContext,
    url: str,
    dominio_principal: str,
    timeout: int = 30000,
) -> dict[str, Any]:
    page = context.new_page()

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout,
        )

        titulo = page.title().strip()

        h1 = ""

        localizador_h1 = page.locator(
            "h1"
        ).first

        if localizador_h1.count() > 0:
            try:
                h1 = (
                    localizador_h1
                    .inner_text()
                    .strip()
                )

            except Exception:
                h1 = ""

        breadcrumb = ""

        seletores_breadcrumb = (
            "[aria-label*='breadcrumb' i], "
            ".breadcrumb, "
            "#breadcrumb, "
            ".breadcrumbs, "
            "#breadcrumbs"
        )

        localizador_breadcrumb = (
            page.locator(
                seletores_breadcrumb
            ).first
        )

        if localizador_breadcrumb.count() > 0:
            try:
                breadcrumb = (
                    localizador_breadcrumb
                    .inner_text()
                    .strip()
                )

            except Exception:
                breadcrumb = ""

        links_brutos = page.locator(
            "a[href]"
        ).evaluate_all(
            """
            elementos => elementos.map(
                elemento => {
                    const texto = (
                        elemento.innerText
                        || elemento.textContent
                        || elemento.getAttribute(
                            "aria-label"
                        )
                        || elemento.getAttribute(
                            "title"
                        )
                        || ""
                    ).trim();

                    const estaNoMenu = Boolean(
                        elemento.closest(
                            [
                                "header",
                                "nav",
                                "[role='navigation']",
                                ".menu",
                                "#menu",
                                ".navbar",
                                ".nav",
                                ".menu-principal",
                                "#menu-principal",
                                ".main-menu",
                                "#main-menu"
                            ].join(",")
                        )
                    );

                    return {
                        href:
                            elemento.getAttribute(
                                "href"
                            )
                            || "",

                        texto: texto,

                        no_menu: estaNoMenu
                    };
                }
            )
            """
        )

        links_validos: list[
            dict[str, Any]
        ] = []

        urls_processadas: set[str] = set()

        for link in links_brutos:
            if not isinstance(
                link,
                dict,
            ):
                continue

            href = link.get(
                "href",
                "",
            )

            if not isinstance(
                href,
                str,
            ):
                continue

            link_normalizado = normalizar_link(
                link=href,
                url_base=page.url,
                dominio_principal=dominio_principal,
            )

            if not link_normalizado:
                continue

            texto = str(
                link.get(
                    "texto",
                    "",
                )
            ).strip()

            no_menu = bool(
                link.get(
                    "no_menu",
                    False,
                )
            )

            chave = (
                f"{link_normalizado}|"
                f"{texto}|"
                f"{no_menu}"
            )

            if chave in urls_processadas:
                continue

            urls_processadas.add(
                chave
            )

            links_validos.append(
                {
                    "url": link_normalizado,
                    "texto": texto,
                    "no_menu": no_menu,
                }
            )

        return {
            "url_final": page.url,
            "titulo": titulo,
            "h1": h1,
            "breadcrumb": breadcrumb,
            "links": links_validos,
            "erro": "",
        }

    except PlaywrightError as erro:
        print(
            "⚠️ Não foi possível coletar "
            f"links de {url}"
        )

        print(
            f"   {erro}"
        )

        return {
            "url_final": url,
            "titulo": "",
            "h1": "",
            "breadcrumb": "",
            "links": [],
            "erro": str(
                erro
            ),
        }

    except Exception as erro:
        print(
            "⚠️ Erro inesperado ao "
            f"coletar links de {url}"
        )

        print(
            f"   {erro}"
        )

        return {
            "url_final": url,
            "titulo": "",
            "h1": "",
            "breadcrumb": "",
            "links": [],
            "erro": str(
                erro
            ),
        }

    finally:
        page.close()


def executar_crawler(
    context: BrowserContext,
    url_inicial: str,
    limite_paginas: int = 500,
) -> list[dict[str, Any]]:
    dominio_principal = obter_dominio_normalizado(
        url_inicial
    )

    if not dominio_principal:
        return []

    fila: deque[
        tuple[str, int, str]
    ] = deque(
        [
            (
                url_inicial,
                0,
                "",
            )
        ]
    )

    registros: dict[
        str,
        dict[str, Any]
    ] = {
        url_inicial: criar_registro_pagina(
            url=url_inicial,
            profundidade=0,
        )
    }

    urls_visitadas: set[str] = set()

    while (
        fila
        and len(urls_visitadas)
        < limite_paginas
    ):
        (
            url_atual,
            profundidade_atual,
            origem_atual,
        ) = fila.popleft()

        if url_atual in urls_visitadas:
            continue

        print(
            "🔎 Descobrindo páginas "
            f"({len(urls_visitadas) + 1}/"
            f"{limite_paginas}): "
            f"{url_atual}"
        )

        urls_visitadas.add(
            url_atual
        )

        registro_atual = registros.setdefault(
            url_atual,
            criar_registro_pagina(
                url=url_atual,
                profundidade=profundidade_atual,
                origem=origem_atual,
            ),
        )

        dados = coletar_dados_da_pagina(
            context=context,
            url=url_atual,
            dominio_principal=dominio_principal,
        )

        registro_atual[
            "titulo"
        ] = dados.get(
            "titulo",
            "",
        )

        registro_atual[
            "h1"
        ] = dados.get(
            "h1",
            "",
        )

        registro_atual[
            "breadcrumb"
        ] = dados.get(
            "breadcrumb",
            "",
        )

        registro_atual[
            "erro_descoberta"
        ] = dados.get(
            "erro",
            "",
        )

        links = dados.get(
            "links",
            [],
        )

        for link in links:
            url_link = str(
                link.get(
                    "url",
                    "",
                )
            ).strip()

            if not url_link:
                continue

            texto_link = str(
                link.get(
                    "texto",
                    "",
                )
            ).strip()

            no_menu = bool(
                link.get(
                    "no_menu",
                    False,
                )
            )

            profundidade_link = (
                profundidade_atual + 1
            )

            registro_link = registros.get(
                url_link
            )

            if registro_link is None:
                registro_link = (
                    criar_registro_pagina(
                        url=url_link,
                        profundidade=(
                            profundidade_link
                        ),
                        origem=url_atual,
                    )
                )

                registros[
                    url_link
                ] = registro_link

            else:
                profundidade_existente = (
                    registro_link.get(
                        "profundidade",
                        profundidade_link,
                    )
                )

                try:
                    profundidade_existente = int(
                        profundidade_existente
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    profundidade_existente = (
                        profundidade_link
                    )

                registro_link[
                    "profundidade"
                ] = min(
                    profundidade_existente,
                    profundidade_link,
                )

            adicionar_texto_link(
                registro=registro_link,
                texto=texto_link,
            )

            if no_menu:
                registro_link[
                    "no_menu"
                ] = True

            if profundidade_atual == 0:
                registro_link[
                    "na_home"
                ] = True

            if (
                url_link not in urls_visitadas
                and len(registros)
                <= limite_paginas
            ):
                fila.append(
                    (
                        url_link,
                        profundidade_link,
                        url_atual,
                    )
                )

    registros_ordenados = sorted(
        registros.values(),
        key=lambda registro: (
            int(
                registro.get(
                    "profundidade",
                    99,
                )
            ),
            registro.get(
                "url",
                "",
            ),
        ),
    )

    return registros_ordenados