from __future__ import annotations

import re
from typing import Any
from urllib.parse import (
    urldefrag,
    urljoin,
    urlparse,
    urlunparse,
)

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData
from utils.url_helper import eh_url_interna


TERMOS_SOCIAIS = {
    "facebook",
    "instagram",
    "linkedin",
    "youtube",
    "tiktok",
    "twitter",
    "x.com",
    "whatsapp",
}

TERMOS_AUXILIARES_FOOTER = {
    "política de privacidade",
    "politica de privacidade",
    "termos de uso",
    "cookies",
    "lgpd",
    "trabalhe conosco",
}

TERMOS_MAPA_SITE = {
    "mapa do site",
    "mapa de site",
    "sitemap",
}

SELETORES_VOLTAR_TOPO = (
    ".scrollup",
    ".scroll-up",
    ".scroll_up",
    ".scroll-top",
    ".scroll_top",
    ".scrolltotop",
    ".scroll-to-top",
    ".scrollToTop",
    ".backtotop",
    ".back-to-top",
    ".back_to_top",
    ".back-toTop",
    ".go-top",
    ".go_top",
    ".gotop",
    ".goTop",
    ".btn-top",
    ".btn_top",
    ".top-button",
    ".top_button",
    ".to-top",
    ".to_top",
    ".page-up",
    ".page_up",
    "#scrollup",
    "#scrollUp",
    "#scroll-up",
    "#scroll_top",
    "#scroll-top",
    "#scrollToTop",
    "#scroll-to-top",
    "#backtotop",
    "#back-to-top",
    "#back_to_top",
    "#go-top",
    "#go_top",
    "#gotop",
    "#goTop",
    "#btn-top",
    "#btn_top",
    "#to-top",
    "#to_top",
    "[data-scroll-top]",
    "[data-scrolltop]",
    "[data-back-to-top]",
    "[data-backtotop]",
    "[aria-label*='topo' i]",
    "[title*='topo' i]",
    "[aria-label*='back to top' i]",
    "[title*='back to top' i]",
)


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get(
        "page_data"
    )

    if isinstance(
        page_data,
        PageData,
    ):
        return page_data

    return None


def normalizar_texto(
    texto: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def normalizar_url_menu(
    url: str,
) -> str:
    if not url:
        return ""

    url_sem_fragmento, _ = urldefrag(
        url.strip()
    )

    partes = urlparse(
        url_sem_fragmento
    )

    esquema = partes.scheme.casefold()

    hostname = (
        partes.hostname.casefold()
        if partes.hostname
        else ""
    )

    if hostname.startswith(
        "www."
    ):
        hostname = hostname[4:]

    porta = partes.port

    if (
        porta
        and not (
            esquema == "http"
            and porta == 80
        )
        and not (
            esquema == "https"
            and porta == 443
        )
    ):
        hostname = (
            f"{hostname}:{porta}"
        )

    caminho = partes.path or "/"

    if caminho != "/":
        caminho = caminho.rstrip(
            "/"
        )

    return urlunparse(
        (
            esquema,
            hostname,
            caminho,
            "",
            partes.query,
            "",
        )
    )


def obter_url_principal(
    contexto: dict[str, Any],
    page_data: PageData,
) -> str:
    return str(
        contexto.get(
            "url_principal",
            page_data.url_solicitada,
        )
    )


def coletar_links_regiao(
    page: Page,
    seletor: str,
) -> list[dict[str, Any]]:
    try:
        return page.locator(
            seletor
        ).evaluate_all(
            """
            regioes => {
                const resultados = [];

                function estaVisivel(elemento) {
                    const estilo = getComputedStyle(
                        elemento
                    );

                    const retangulo =
                        elemento.getBoundingClientRect();

                    return (
                        estilo.display !== "none"
                        && estilo.visibility !== "hidden"
                        && Number(estilo.opacity) !== 0
                        && retangulo.width > 0
                        && retangulo.height > 0
                    );
                }

                for (const regiao of regioes) {
                    const links = Array.from(
                        regiao.querySelectorAll(
                            "a[href]"
                        )
                    );

                    for (const link of links) {
                        if (!estaVisivel(link)) {
                            continue;
                        }

                        resultados.push({
                            href:
                                link.href || "",

                            href_original:
                                link.getAttribute("href")
                                || "",

                            texto: (
                                link.innerText
                                || link.textContent
                                || link.getAttribute(
                                    "aria-label"
                                )
                                || link.getAttribute(
                                    "title"
                                )
                                || ""
                            )
                                .replace(/\\s+/g, " ")
                                .trim(),

                            class_name:
                                link.getAttribute("class")
                                || "",

                            aria_current:
                                link.getAttribute(
                                    "aria-current"
                                )
                                || "",

                            id:
                                link.getAttribute("id")
                                || ""
                        });
                    }
                }

                return resultados;
            }
            """
        )

    except Exception:
        return []


def link_deve_ser_ignorado(
    link: dict[str, Any],
) -> bool:
    href_original = str(
        link.get(
            "href_original",
            "",
        )
    ).strip().casefold()

    texto = normalizar_texto(
        str(
            link.get(
                "texto",
                "",
            )
        )
    ).casefold()

    if not href_original:
        return True

    if href_original.startswith(
        (
            "#",
            "mailto:",
            "tel:",
            "javascript:",
            "whatsapp:",
        )
    ):
        return True

    conteudo = (
        f"{href_original} {texto}"
    )

    if any(
        termo in conteudo
        for termo in TERMOS_SOCIAIS
    ):
        return True

    if texto in TERMOS_AUXILIARES_FOOTER:
        return True

    return False


def preparar_links_menu(
    links: list[dict[str, Any]],
    url_base: str,
    url_principal: str,
) -> list[dict[str, str]]:
    resultados: dict[
        str,
        dict[str, str],
    ] = {}

    for link in links:
        if link_deve_ser_ignorado(
            link
        ):
            continue

        href = str(
            link.get(
                "href",
                "",
            )
            or link.get(
                "href_original",
                "",
            )
        ).strip()

        texto = normalizar_texto(
            str(
                link.get(
                    "texto",
                    "",
                )
            )
        )

        if not href:
            continue

        url_absoluta = urljoin(
            url_base,
            href,
        )

        if not eh_url_interna(
            url=url_absoluta,
            url_principal=url_principal,
        ):
            continue

        url_normalizada = (
            normalizar_url_menu(
                url_absoluta
            )
        )

        if not url_normalizada:
            continue

        if not texto:
            continue

        if url_normalizada not in resultados:
            resultados[url_normalizada] = {
                "url": url_normalizada,
                "texto": texto,
            }

    return list(
        resultados.values()
    )


def coletar_menu_header(
    page: Page,
    url_principal: str,
) -> list[dict[str, str]]:
    seletores = (
        "header nav, "
        "header [role='navigation'], "
        "header .menu, "
        "header [class*='menu'], "
        "nav.main-menu, "
        "nav.primary-menu, "
        "#menu-principal, "
        ".menu-principal"
    )

    links = coletar_links_regiao(
        page=page,
        seletor=seletores,
    )

    if not links:
        links = coletar_links_regiao(
            page=page,
            seletor="header",
        )

    return preparar_links_menu(
        links=links,
        url_base=page.url,
        url_principal=url_principal,
    )


def coletar_menu_footer(
    page: Page,
    url_principal: str,
) -> list[dict[str, str]]:
    seletores = (
        "footer nav, "
        "footer [role='navigation'], "
        "footer .menu, "
        "footer [class*='menu'], "
        "#footer nav, "
        ".footer nav"
    )

    links = coletar_links_regiao(
        page=page,
        seletor=seletores,
    )

    if not links:
        links = coletar_links_regiao(
            page=page,
            seletor=(
                "footer, "
                "#footer, "
                ".footer, "
                "[role='contentinfo']"
            ),
        )

    return preparar_links_menu(
        links=links,
        url_base=page.url,
        url_principal=url_principal,
    )


def identificar_menu_ativo(
    page: Page,
    url_principal: str,
) -> list[dict[str, Any]]:
    try:
        candidatos = page.locator(
            (
                "header nav a[href], "
                "header [role='navigation'] a[href], "
                "nav.main-menu a[href], "
                "nav.primary-menu a[href], "
                "#menu-principal a[href], "
                ".menu-principal a[href]"
            )
        ).evaluate_all(
            """
            links => links.map(link => {
                const pai =
                    link.closest(
                        "li, .menu-item, .nav-item"
                    );

                const classesLink =
                    link.getAttribute("class")
                    || "";

                const classesPai =
                    pai
                        ? (
                            pai.getAttribute("class")
                            || ""
                        )
                        : "";

                const ariaCurrent =
                    link.getAttribute(
                        "aria-current"
                    )
                    || "";

                const classeCompleta = (
                    classesLink
                    + " "
                    + classesPai
                ).toLowerCase();

                const ativoPorClasse =
                    /(^|\\s|[-_])(active|current|selected)(\\s|[-_]|$)/
                        .test(classeCompleta)
                    || classeCompleta.includes(
                        "current-menu-item"
                    )
                    || classeCompleta.includes(
                        "current_page_item"
                    );

                return {
                    href:
                        link.href || "",

                    href_original:
                        link.getAttribute("href")
                        || "",

                    texto: (
                        link.innerText
                        || link.textContent
                        || link.getAttribute(
                            "aria-label"
                        )
                        || ""
                    )
                        .replace(/\\s+/g, " ")
                        .trim(),

                    aria_current:
                        ariaCurrent,

                    classes_link:
                        classesLink,

                    classes_pai:
                        classesPai,

                    ativo:
                        Boolean(
                            ariaCurrent
                            || ativoPorClasse
                        )
                };
            })
            """
        )

    except Exception:
        return []

    resultados: list[
        dict[str, Any]
    ] = []

    for candidato in candidatos:
        if not candidato.get(
            "ativo",
            False,
        ):
            continue

        href = str(
            candidato.get(
                "href",
                "",
            )
        ).strip()

        if (
            href
            and eh_url_interna(
                url=href,
                url_principal=url_principal,
            )
        ):
            resultados.append(
                candidato
            )

    return resultados


def identificar_botoes_voltar_topo(
    page: Page,
) -> list[dict[str, Any]]:
    """
    Identifica possíveis botões de voltar ao topo.

    Reconhece:
    - scrollup;
    - scrollUp;
    - scroll-top;
    - scrollToTop;
    - back-to-top;
    - go-top;
    - btn-top;
    - href #top, #topo, #header etc.;
    - onclick com window.scrollTo;
    - onclick com scrollIntoView;
    - onclick com animação para scrollTop 0.
    """
    seletor = ", ".join(
        SELETORES_VOLTAR_TOPO
    )

    seletor_geral = (
        f"{seletor}, "
        "a[href^='#'], "
        "button[onclick], "
        "[role='button'][onclick]"
    )

    try:
        return page.locator(
            seletor_geral
        ).evaluate_all(
            """
            elementos => {
                const seletoresConhecidos = [
                    "scrollup",
                    "scroll-up",
                    "scroll_up",
                    "scrolltop",
                    "scroll-top",
                    "scroll_top",
                    "scrolltotop",
                    "scroll-to-top",
                    "backtotop",
                    "back-to-top",
                    "back_to_top",
                    "gotop",
                    "go-top",
                    "go_top",
                    "btn-top",
                    "btn_top",
                    "top-button",
                    "top_button",
                    "to-top",
                    "to_top",
                    "page-up",
                    "page_up"
                ];

                const hrefsTopo = [
                    "#top",
                    "#topo",
                    "#page-top",
                    "#page_top",
                    "#header",
                    "#cabecalho",
                    "#inicio"
                ];

                function estaVisivel(elemento) {
                    const estilo = getComputedStyle(
                        elemento
                    );

                    const retangulo =
                        elemento.getBoundingClientRect();

                    return (
                        estilo.display !== "none"
                        && estilo.visibility !== "hidden"
                        && Number(estilo.opacity) > 0
                        && retangulo.width > 0
                        && retangulo.height > 0
                    );
                }

                function criarSeletor(elemento) {
                    const tag =
                        elemento.tagName
                            .toLowerCase();

                    if (elemento.id) {
                        return (
                            tag
                            + "#"
                            + CSS.escape(
                                elemento.id
                            )
                        );
                    }

                    const classes = Array.from(
                        elemento.classList || []
                    );

                    if (classes.length) {
                        return (
                            tag
                            + "."
                            + classes
                                .slice(0, 4)
                                .map(classe =>
                                    CSS.escape(classe)
                                )
                                .join(".")
                        );
                    }

                    return "";
                }

                const resultados = [];

                for (
                    const elemento
                    of elementos
                ) {
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
                    )
                        .replace(/\\s+/g, " ")
                        .trim();

                    const href = (
                        elemento.getAttribute(
                            "href"
                        )
                        || ""
                    ).trim();

                    const id = (
                        elemento.getAttribute(
                            "id"
                        )
                        || ""
                    ).trim();

                    const classes = (
                        elemento.getAttribute(
                            "class"
                        )
                        || ""
                    ).trim();

                    const onclick = (
                        elemento.getAttribute(
                            "onclick"
                        )
                        || ""
                    ).trim();

                    const ariaLabel = (
                        elemento.getAttribute(
                            "aria-label"
                        )
                        || ""
                    ).trim();

                    const title = (
                        elemento.getAttribute(
                            "title"
                        )
                        || ""
                    ).trim();

                    const dataScrollTop = (
                        elemento.getAttribute(
                            "data-scroll-top"
                        )
                        || elemento.getAttribute(
                            "data-scrolltop"
                        )
                        || elemento.getAttribute(
                            "data-back-to-top"
                        )
                        || elemento.getAttribute(
                            "data-backtotop"
                        )
                        || ""
                    ).trim();

                    const conteudo = (
                        texto
                        + " "
                        + href
                        + " "
                        + id
                        + " "
                        + classes
                        + " "
                        + onclick
                        + " "
                        + ariaLabel
                        + " "
                        + title
                        + " "
                        + dataScrollTop
                    ).toLowerCase();

                    const conteudoCompacto =
                        conteudo.replace(
                            /[^a-z0-9]+/g,
                            ""
                        );

                    const padraoConhecido =
                        seletoresConhecidos.some(
                            termo => {
                                const termoCompacto =
                                    termo.replace(
                                        /[^a-z0-9]+/g,
                                        ""
                                    );

                                return (
                                    conteudoCompacto
                                        .includes(
                                            termoCompacto
                                        )
                                );
                            }
                        );

                    const hrefTopo =
                        hrefsTopo.includes(
                            href.toLowerCase()
                        );

                    const possuiComportamentoJS =
                        conteudo.includes(
                            "window.scrollto"
                        )
                        || conteudo.includes(
                            "scrollintoview"
                        )
                        || conteudo.includes(
                            "scrolltop(0"
                        )
                        || conteudo.includes(
                            "scrolltop: 0"
                        )
                        || conteudo.includes(
                            "scrolltop:0"
                        )
                        || conteudo.includes(
                            "scrolltop = 0"
                        )
                        || conteudo.includes(
                            "scrolltop=0"
                        )
                        || (
                            conteudo.includes(
                                "animate"
                            )
                            && conteudo.includes(
                                "scrolltop"
                            )
                        );

                    const textoTopo =
                        conteudo.includes(
                            "voltar ao topo"
                        )
                        || conteudo.includes(
                            "voltar para o topo"
                        )
                        || conteudo.includes(
                            "ir ao topo"
                        )
                        || conteudo.includes(
                            "back to top"
                        );

                    if (
                        !padraoConhecido
                        && !hrefTopo
                        && !possuiComportamentoJS
                        && !textoTopo
                    ) {
                        continue;
                    }

                    const estilo = getComputedStyle(
                        elemento
                    );

                    const retangulo =
                        elemento.getBoundingClientRect();

                    resultados.push({
                        seletor:
                            criarSeletor(elemento),

                        tag:
                            elemento.tagName
                                .toLowerCase(),

                        texto: texto,
                        href: href,
                        id: id,
                        class_name: classes,
                        onclick: onclick,
                        aria_label: ariaLabel,
                        title: title,

                        visivel:
                            estaVisivel(elemento),

                        position:
                            estilo.position,

                        bottom:
                            estilo.bottom,

                        right:
                            estilo.right,

                        largura:
                            Math.round(
                                retangulo.width
                            ),

                        altura:
                            Math.round(
                                retangulo.height
                            ),

                        padrao_conhecido:
                            padraoConhecido,

                        href_topo:
                            hrefTopo,

                        comportamento_js:
                            possuiComportamentoJS,

                        texto_topo:
                            textoTopo
                    });
                }

                const unicos = new Map();

                for (
                    const resultado
                    of resultados
                ) {
                    const chave = [
                        resultado.seletor,
                        resultado.href,
                        resultado.id,
                        resultado.class_name
                    ].join("|");

                    if (!unicos.has(chave)) {
                        unicos.set(
                            chave,
                            resultado
                        );
                    }
                }

                return Array.from(
                    unicos.values()
                );
            }
            """
        )

    except Exception:
        return []


def testar_botao_voltar_topo(
    page: Page,
    candidatos: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Testa se algum candidato realmente faz a página
    voltar para o topo.
    """
    resultado = {
        "testado": False,
        "funcional": False,
        "scroll_antes": 0,
        "scroll_depois": 0,
        "candidato_funcional": {},
        "erro": "",
    }

    if not candidatos:
        return resultado

    try:
        altura_documento = page.evaluate(
            """
            () => Math.max(
                document.documentElement.scrollHeight,
                document.body
                    ? document.body.scrollHeight
                    : 0
            )
            """
        )

        altura_viewport = page.evaluate(
            "() => window.innerHeight"
        )

        if (
            not isinstance(
                altura_documento,
                (int, float),
            )
            or altura_documento
            <= altura_viewport + 100
        ):
            resultado["erro"] = (
                "A página não possui altura suficiente "
                "para testar a rolagem."
            )

            return resultado

        page.evaluate(
            """
            () => {
                window.scrollTo({
                    top: Math.max(
                        document.documentElement.scrollHeight,
                        document.body
                            ? document.body.scrollHeight
                            : 0
                    ),
                    behavior: "instant"
                });
            }
            """
        )

        page.wait_for_timeout(
            600
        )

        scroll_antes = page.evaluate(
            "() => Math.round(window.scrollY)"
        )

        resultado[
            "scroll_antes"
        ] = scroll_antes

        for candidato in candidatos:
            seletor = str(
                candidato.get(
                    "seletor",
                    "",
                )
            ).strip()

            if not seletor:
                continue

            locator = page.locator(
                seletor
            ).first

            if locator.count() == 0:
                continue

            try:
                locator.scroll_into_view_if_needed(
                    timeout=1500
                )

            except Exception:
                pass

            try:
                visivel = locator.is_visible(
                    timeout=1500
                )

            except Exception:
                visivel = False

            if not visivel:
                continue

            resultado["testado"] = True

            try:
                locator.click(
                    timeout=2500,
                    force=True,
                )

            except Exception:
                continue

            page.wait_for_timeout(
                900
            )

            scroll_depois = page.evaluate(
                "() => Math.round(window.scrollY)"
            )

            resultado[
                "scroll_depois"
            ] = scroll_depois

            if scroll_depois <= 150:
                resultado[
                    "funcional"
                ] = True

                resultado[
                    "candidato_funcional"
                ] = candidato

                return resultado

            page.evaluate(
                """
                () => {
                    window.scrollTo({
                        top: Math.max(
                            document.documentElement
                                .scrollHeight,
                            document.body
                                ? document.body.scrollHeight
                                : 0
                        ),
                        behavior: "instant"
                    });
                }
                """
            )

            page.wait_for_timeout(
                400
            )

        return resultado

    except Exception as erro:
        resultado["erro"] = str(
            erro
        )

        return resultado

    finally:
        try:
            page.evaluate(
                """
                () => window.scrollTo({
                    top: 0,
                    behavior: "instant"
                })
                """
            )

            page.wait_for_timeout(
                200
            )

        except Exception:
            pass


def identificar_mapa_site_footer(
    page: Page,
) -> list[dict[str, str]]:
    links = coletar_links_regiao(
        page=page,
        seletor=(
            "footer, "
            "#footer, "
            ".footer, "
            "[role='contentinfo']"
        ),
    )

    resultados: list[
        dict[str, str]
    ] = []

    for link in links:
        texto = normalizar_texto(
            str(
                link.get(
                    "texto",
                    "",
                )
            )
        ).casefold()

        href = str(
            link.get(
                "href",
                "",
            )
            or link.get(
                "href_original",
                "",
            )
        ).strip()

        conteudo = (
            f"{texto} {href.casefold()}"
        )

        if any(
            termo in conteudo
            for termo in TERMOS_MAPA_SITE
        ):
            resultados.append(
                {
                    "texto": texto,
                    "url": href,
                }
            )

    return resultados


class HeaderFooterMenuCheck(
    BaseCheck
):
    nome = "Menu Header x Footer"
    categoria = "Navegação"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        url_principal = obter_url_principal(
            contexto=contexto,
            page_data=page_data,
        )

        menu_header = coletar_menu_header(
            page=page,
            url_principal=url_principal,
        )

        menu_footer = coletar_menu_footer(
            page=page,
            url_principal=url_principal,
        )

        urls_header = {
            item["url"]
            for item in menu_header
        }

        urls_footer = {
            item["url"]
            for item in menu_footer
        }

        ausentes_footer = sorted(
            urls_header
            - urls_footer
        )

        extras_footer = sorted(
            urls_footer
            - urls_header
        )

        dados = {
            "quantidade_header": len(
                menu_header
            ),
            "quantidade_footer": len(
                menu_footer
            ),
            "menu_header": menu_header,
            "menu_footer": menu_footer,
            "ausentes_no_footer": (
                ausentes_footer
            ),
            "extras_no_footer": (
                extras_footer
            ),
            "requer_revisao_manual": True,
        }

        if not menu_header:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi possível identificar "
                    "o menu principal no header."
                ),
                dados=dados,
            )

        if not menu_footer:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi possível identificar "
                    "um menu no footer."
                ),
                dados=dados,
            )

        if ausentes_footer:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Existem links do menu principal "
                    "que não foram encontrados no footer:\n"
                    + "\n".join(
                        ausentes_footer
                    )
                ),
                dados=dados,
            )

        observacao = (
            "Todos os links internos identificados "
            "no menu principal também foram encontrados "
            "no footer."
        )

        if extras_footer:
            observacao += (
                f" O footer possui {len(extras_footer)} "
                "link(s) interno(s) adicional(is)."
            )

        return self.resultado(
            status="approved",
            observacao=observacao,
            dados=dados,
        )


class ActiveMenuCheck(
    BaseCheck
):
    nome = "Menu Ativo"
    categoria = "Navegação"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        url_principal = obter_url_principal(
            contexto=contexto,
            page_data=page_data,
        )

        itens_ativos = identificar_menu_ativo(
            page=page,
            url_principal=url_principal,
        )

        if not itens_ativos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum item ativo foi identificado "
                    "no menu principal por aria-current, "
                    "active, current ou selected."
                ),
                dados={
                    "quantidade": 0,
                    "itens_ativos": [],
                    "requer_revisao_manual": True,
                },
            )

        if len(
            itens_ativos
        ) > 1:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados {len(itens_ativos)} "
                    "itens marcados como ativos no menu."
                ),
                dados={
                    "quantidade": len(
                        itens_ativos
                    ),
                    "itens_ativos": itens_ativos,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                "Um item ativo foi identificado "
                "no menu principal."
            ),
            dados={
                "quantidade": 1,
                "itens_ativos": itens_ativos,
                "requer_revisao_manual": False,
            },
        )


class BackToTopButtonCheck(
    BaseCheck
):
    nome = "Botão Voltar ao Topo"
    categoria = "Navegação"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        candidatos = identificar_botoes_voltar_topo(
            page
        )

        if not candidatos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum botão de voltar ao topo foi "
                    "encontrado. Foram verificados padrões "
                    "como scrollup, scroll-top, back-to-top, "
                    "go-top e btn-top."
                ),
                dados={
                    "quantidade": 0,
                    "candidatos": [],
                    "teste_funcional": {},
                    "requer_revisao_manual": True,
                },
            )

        teste_funcional = (
            testar_botao_voltar_topo(
                page=page,
                candidatos=candidatos,
            )
        )

        dados = {
            "quantidade": len(
                candidatos
            ),
            "candidatos": candidatos,
            "teste_funcional": teste_funcional,
            "requer_revisao_manual": (
                not teste_funcional.get(
                    "funcional",
                    False,
                )
            ),
        }

        if teste_funcional.get(
            "funcional",
            False,
        ):
            candidato = teste_funcional.get(
                "candidato_funcional",
                {},
            )

            identificacao = (
                candidato.get(
                    "seletor"
                )
                or candidato.get(
                    "id"
                )
                or candidato.get(
                    "class_name"
                )
                or "elemento não identificado"
            )

            return self.resultado(
                status="approved",
                observacao=(
                    "O botão de voltar ao topo foi "
                    "encontrado e o funcionamento foi "
                    f"confirmado. Elemento: {identificacao}."
                ),
                dados=dados,
            )

        if teste_funcional.get(
            "testado",
            False,
        ):
            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados {len(candidatos)} "
                    "candidato(s) a botão de voltar ao topo, "
                    "mas o clique não levou a página para "
                    "o início."
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"Foram encontrados {len(candidatos)} "
                "candidato(s) a botão de voltar ao topo, "
                "incluindo padrões como scrollup. "
                "O teste funcional automático não pôde "
                "ser concluído; recomenda-se revisão manual."
            ),
            dados=dados,
        )


class SitemapFooterCheck(
    BaseCheck
):
    nome = "Mapa do Site no Footer"
    categoria = "Navegação"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        referencias = identificar_mapa_site_footer(
            page
        )

        if not referencias:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum link para Mapa do Site "
                    "foi encontrado no footer."
                ),
                dados={
                    "quantidade": 0,
                    "referencias": [],
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                "Foi encontrada referência ao "
                "Mapa do Site no footer."
            ),
            dados={
                "quantidade": len(
                    referencias
                ),
                "referencias": referencias,
                "requer_revisao_manual": False,
            },
        )