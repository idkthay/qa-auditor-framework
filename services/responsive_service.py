from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

from playwright.sync_api import Page

from config.settings import (
    TEMPO_ESPERA_RESPONSIVIDADE,
    VIEWPORT_DESKTOP,
)


TOLERANCIA_OVERFLOW_PX = 3

LIMITE_ELEMENTOS_PROBLEMATICOS = 30


_cache_responsividade: dict[
    str,
    dict[str, Any],
] = {}

_cache_lock = Lock()


def limpar_cache_responsividade() -> None:
    with _cache_lock:
        _cache_responsividade.clear()


def criar_chave_cache(
    url: str,
    largura: int,
    altura: int,
) -> str:
    return (
        f"{url}|"
        f"{largura}x{altura}"
    )


def obter_viewport_atual(
    page: Page,
) -> dict[str, int]:
    viewport = page.viewport_size

    if viewport:
        return {
            "width": int(
                viewport.get(
                    "width",
                    VIEWPORT_DESKTOP["width"],
                )
            ),
            "height": int(
                viewport.get(
                    "height",
                    VIEWPORT_DESKTOP["height"],
                )
            ),
        }

    return {
        "width": VIEWPORT_DESKTOP["width"],
        "height": VIEWPORT_DESKTOP["height"],
    }


def aguardar_estabilizacao(
    page: Page,
) -> None:
    page.wait_for_timeout(
        TEMPO_ESPERA_RESPONSIVIDADE
    )

    try:
        page.evaluate(
            """
            async () => {
                if (
                    document.fonts
                    && document.fonts.ready
                ) {
                    await document.fonts.ready;
                }
            }
            """
        )

    except Exception:
        pass

    page.wait_for_timeout(
        200
    )


def analisar_layout(
    page: Page,
    largura_viewport: int,
) -> dict[str, Any]:
    """
    Analisa visualmente o DOM após a alteração
    da largura da viewport.
    """
    return page.evaluate(
        """
        ({ larguraViewport, tolerancia, limite }) => {
            const html = document.documentElement;
            const body = document.body;

            const larguraDocumento = Math.max(
                html ? html.scrollWidth : 0,
                body ? body.scrollWidth : 0,
                html ? html.clientWidth : 0,
                body ? body.clientWidth : 0
            );

            const alturaDocumento = Math.max(
                html ? html.scrollHeight : 0,
                body ? body.scrollHeight : 0,
                html ? html.clientHeight : 0,
                body ? body.clientHeight : 0
            );

            function estaVisivel(elemento) {
                const estilo = getComputedStyle(
                    elemento
                );

                if (
                    estilo.display === "none"
                    || estilo.visibility === "hidden"
                    || Number(estilo.opacity) === 0
                ) {
                    return false;
                }

                const retangulo =
                    elemento.getBoundingClientRect();

                return (
                    retangulo.width > 0
                    && retangulo.height > 0
                );
            }

            function criarSeletor(elemento) {
                if (!elemento) {
                    return "";
                }

                const tag =
                    elemento.tagName
                        ? elemento.tagName.toLowerCase()
                        : "";

                if (elemento.id) {
                    return `${tag}#${elemento.id}`;
                }

                const classes = Array.from(
                    elemento.classList || []
                )
                    .slice(0, 3)
                    .join(".");

                if (classes) {
                    return `${tag}.${classes}`;
                }

                return tag;
            }

            function descreverElemento(elemento) {
                const retangulo =
                    elemento.getBoundingClientRect();

                return {
                    seletor:
                        criarSeletor(elemento),

                    tag:
                        elemento.tagName
                            ? elemento.tagName.toLowerCase()
                            : "",

                    id:
                        elemento.id || "",

                    class_name:
                        elemento.getAttribute("class")
                        || "",

                    largura:
                        Math.round(
                            retangulo.width
                        ),

                    altura:
                        Math.round(
                            retangulo.height
                        ),

                    esquerda:
                        Math.round(
                            retangulo.left
                        ),

                    direita:
                        Math.round(
                            retangulo.right
                        ),

                    texto:
                        (
                            elemento.innerText
                            || elemento.textContent
                            || ""
                        )
                            .replace(/\\s+/g, " ")
                            .trim()
                            .slice(0, 120)
                };
            }

            const todosElementos = Array.from(
                document.querySelectorAll(
                    "body *"
                )
            );

            const elementosOverflow = [];

            for (
                const elemento
                of todosElementos
            ) {
                if (!estaVisivel(elemento)) {
                    continue;
                }

                const estilo = getComputedStyle(
                    elemento
                );

                const retangulo =
                    elemento.getBoundingClientRect();

                const posicaoFixa =
                    estilo.position === "fixed"
                    || estilo.position === "sticky";

                const ultrapassaDireita =
                    retangulo.right
                    > larguraViewport + tolerancia;

                const ultrapassaEsquerda =
                    retangulo.left
                    < -tolerancia;

                const larguraExcessiva =
                    retangulo.width
                    > larguraViewport + tolerancia;

                if (
                    ultrapassaDireita
                    || ultrapassaEsquerda
                    || larguraExcessiva
                ) {
                    elementosOverflow.push({
                        ...descreverElemento(
                            elemento
                        ),

                        ultrapassa_direita:
                            ultrapassaDireita,

                        ultrapassa_esquerda:
                            ultrapassaEsquerda,

                        largura_excessiva:
                            larguraExcessiva,

                        posicao_fixa:
                            posicaoFixa
                    });
                }

                if (
                    elementosOverflow.length
                    >= limite
                ) {
                    break;
                }
            }

            function analisarGrupo(seletor) {
                const elementos = Array.from(
                    document.querySelectorAll(
                        seletor
                    )
                );

                const encontrados = [];
                const problematicos = [];

                for (
                    const elemento
                    of elementos
                ) {
                    if (!estaVisivel(elemento)) {
                        continue;
                    }

                    const item =
                        descreverElemento(
                            elemento
                        );

                    const problema =
                        item.direita
                            > larguraViewport
                                + tolerancia
                        || item.esquerda
                            < -tolerancia
                        || item.largura
                            > larguraViewport
                                + tolerancia;

                    encontrados.push(
                        item
                    );

                    if (problema) {
                        problematicos.push(
                            item
                        );
                    }
                }

                return {
                    quantidade:
                        encontrados.length,

                    quantidade_problematicos:
                        problematicos.length,

                    problematicos:
                        problematicos.slice(
                            0,
                            limite
                        )
                };
            }

            const imagens = analisarGrupo(
                "img, picture, svg"
            );

            const formularios = analisarGrupo(
                "form"
            );

            const iframes = analisarGrupo(
                "iframe"
            );

            const mapas = analisarGrupo(
                [
                    "iframe[src*='google.com/maps']",
                    "iframe[src*='google.com.br/maps']",
                    "iframe[src*='maps.google']",
                    "[class*='map']",
                    "[id*='map']",
                    "[class*='mapa']",
                    "[id*='mapa']"
                ].join(",")
            );

            const footers = analisarGrupo(
                [
                    "footer",
                    "#footer",
                    ".footer",
                    "[role='contentinfo']"
                ].join(",")
            );

            const tabelas = analisarGrupo(
                "table"
            );

            const videos = analisarGrupo(
                "video"
            );

            const overflowHorizontal =
                larguraDocumento
                > larguraViewport + tolerancia;

            return {
                viewport: {
                    largura:
                        larguraViewport,

                    altura:
                        window.innerHeight
                },

                documento: {
                    largura:
                        larguraDocumento,

                    altura:
                        alturaDocumento,

                    diferenca_horizontal:
                        Math.max(
                            0,
                            larguraDocumento
                                - larguraViewport
                        )
                },

                possui_overflow_horizontal:
                    overflowHorizontal,

                quantidade_elementos_overflow:
                    elementosOverflow.length,

                elementos_overflow:
                    elementosOverflow,

                imagens:
                    imagens,

                formularios:
                    formularios,

                iframes:
                    iframes,

                mapas:
                    mapas,

                footers:
                    footers,

                tabelas:
                    tabelas,

                videos:
                    videos,

                footer_encontrado:
                    footers.quantidade > 0
            };
        }
        """,
        {
            "larguraViewport": largura_viewport,
            "tolerancia": TOLERANCIA_OVERFLOW_PX,
            "limite": LIMITE_ELEMENTOS_PROBLEMATICOS,
        },
    )


def executar_validacao_responsiva(
    page: Page,
    nome_viewport: str,
    largura: int,
    altura: int,
) -> dict[str, Any]:
    """
    Altera temporariamente a viewport, analisa o
    layout e restaura a viewport.
    """
    url = page.url

    chave_cache = criar_chave_cache(
        url=url,
        largura=largura,
        altura=altura,
    )

    with _cache_lock:
        resultado_cache = (
            _cache_responsividade.get(
                chave_cache
            )
        )

    if resultado_cache is not None:
        return deepcopy(
            resultado_cache
        )

    viewport_original = obter_viewport_atual(
        page
    )

    resultado: dict[str, Any] = {
        "nome_viewport": nome_viewport,
        "largura": largura,
        "altura": altura,
        "url": url,
        "sucesso": False,
        "erro": "",
        "analise": {},
    }

    try:
        page.set_viewport_size(
            {
                "width": largura,
                "height": altura,
            }
        )

        aguardar_estabilizacao(
            page
        )

        analise = analisar_layout(
            page=page,
            largura_viewport=largura,
        )

        resultado.update(
            {
                "sucesso": True,
                "analise": analise,
            }
        )

    except Exception as erro:
        resultado[
            "erro"
        ] = str(
            erro
        )

    finally:
        try:
            # A próxima validação responsiva aguarda a estabilização
            # depois de definir sua própria viewport. Aguardar novamente
            # aqui duplicava até 1 segundo por viewport sem contribuir
            # para a medição já concluída.
            page.set_viewport_size(
                viewport_original
            )

        except Exception:
            pass

    with _cache_lock:
        _cache_responsividade[
            chave_cache
        ] = deepcopy(
            resultado
        )

    return resultado
