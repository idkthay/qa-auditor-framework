from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData
from services.http_link_validator import (
    quantidade_links_em_cache,
    validar_link,
)
from utils.url_helper import (
    eh_url_interna,
    resolver_link_http,
)


LIMITE_LINKS_HTTP_POR_PAGINA = 40


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


def remover_duplicados(
    valores: list[str],
) -> list[str]:
    return list(
        dict.fromkeys(
            valores
        )
    )


def coletar_links_http_internos(
    page_data: PageData,
    url_principal: str,
) -> tuple[list[str], list[str]]:
    """
    Resolve os links usando a URL da página atual,
    mas sempre compara o domínio com a URL inicial
    da auditoria.
    """
    url_base = (
        page_data.url_final
        or page_data.url_solicitada
    )

    links_internos: list[str] = []
    links_externos: list[str] = []

    for link in page_data.links:
        href = str(
            link.get(
                "href_original",
                "",
            )
            or link.get(
                "href",
                "",
            )
        ).strip()

        if not href:
            continue

        url_absoluta = resolver_link_http(
            link=href,
            url_base=url_base,
        )

        if not url_absoluta:
            continue

        if not eh_url_interna(
            url=url_absoluta,
            url_principal=url_principal,
        ):
            links_externos.append(
                url_absoluta
            )

            continue

        links_internos.append(
            url_absoluta
        )

    return (
        remover_duplicados(
            links_internos
        ),
        remover_duplicados(
            links_externos
        ),
    )


class HttpBrokenLinksCheck(
    BaseCheck
):
    nome = "Links HTTP - Erros 4xx/5xx"
    categoria = "Links"

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

        url_principal = str(
            contexto.get(
                "url_principal",
                page_data.url_solicitada,
            )
        )

        (
            links_internos,
            links_externos,
        ) = coletar_links_http_internos(
            page_data=page_data,
            url_principal=url_principal,
        )

        links_testados = links_internos[
            :LIMITE_LINKS_HTTP_POR_PAGINA
        ]

        links_ignorados_por_limite = max(
            0,
            len(links_internos)
            - len(links_testados),
        )

        erros_http: list[dict[str, Any]] = []
        erros_conexao: list[dict[str, Any]] = []
        redirecionamentos: list[dict[str, Any]] = []
        resultados: list[dict[str, Any]] = []

        for url in links_testados:
            resultado = validar_link(
                url
            )

            resultado_dict = resultado.to_dict()

            resultados.append(
                resultado_dict
            )

            if resultado.erro:
                erros_conexao.append(
                    resultado_dict
                )

                continue

            if (
                resultado.status_http is not None
                and resultado.status_http >= 400
            ):
                erros_http.append(
                    resultado_dict
                )

            if resultado.redirecionado:
                redirecionamentos.append(
                    resultado_dict
                )

        total_problemas = (
            len(erros_http)
            + len(erros_conexao)
        )

        dados = {
            "dominio_auditado": url_principal,
            "quantidade_links_internos_encontrados": (
                len(links_internos)
            ),
            "quantidade_links_internos_testados": (
                len(links_testados)
            ),
            "quantidade_links_externos_ignorados": (
                len(links_externos)
            ),
            "links_externos_ignorados": links_externos,
            "quantidade_links_ignorados_por_limite": (
                links_ignorados_por_limite
            ),
            "quantidade_erros_http": len(
                erros_http
            ),
            "quantidade_erros_conexao": len(
                erros_conexao
            ),
            "quantidade_redirecionamentos": len(
                redirecionamentos
            ),
            "erros_http": erros_http,
            "erros_conexao": erros_conexao,
            "redirecionamentos": redirecionamentos,
            "resultados": resultados,
            "links_em_cache_global": (
                quantidade_links_em_cache()
            ),
        }

        if total_problemas > 0:
            observacoes: list[str] = []

            for item in erros_http:
                observacoes.append(
                    (
                        f'HTTP {item["status_http"]}: '
                        f'{item["url_solicitada"]}'
                    )
                )

            for item in erros_conexao:
                observacoes.append(
                    (
                        "Falha de conexão: "
                        f'{item["url_solicitada"]} — '
                        f'{item["erro"]}'
                    )
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados "
                    f"{total_problemas} links internos "
                    "com problemas:\n"
                    + "\n".join(
                        observacoes
                    )
                ),
                dados=dados,
            )

        mensagens: list[str] = []

        if links_externos:
            mensagens.append(
                (
                    f"{len(links_externos)} link(s) "
                    "externo(s) ignorado(s)."
                )
            )

        if links_ignorados_por_limite:
            mensagens.append(
                (
                    f"{links_ignorados_por_limite} "
                    "link(s) interno(s) não foram "
                    "testados devido ao limite."
                )
            )

        return self.resultado(
            status="approved",
            observacao=" ".join(
                mensagens
            ),
            dados=dados,
        )


class HttpRedirectLinksCheck(
    BaseCheck
):
    nome = "Links HTTP - Redirecionamentos"
    categoria = "Links"

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

        url_principal = str(
            contexto.get(
                "url_principal",
                page_data.url_solicitada,
            )
        )

        (
            links_internos,
            links_externos,
        ) = coletar_links_http_internos(
            page_data=page_data,
            url_principal=url_principal,
        )

        links_testados = links_internos[
            :LIMITE_LINKS_HTTP_POR_PAGINA
        ]

        redirecionamentos: list[
            dict[str, Any]
        ] = []

        for url in links_testados:
            resultado = validar_link(
                url
            )

            if not resultado.redirecionado:
                continue

            redirecionamentos.append(
                resultado.to_dict()
            )

        if redirecionamentos:
            observacoes: list[str] = []

            for item in redirecionamentos:
                observacoes.append(
                    (
                        f'{item["url_solicitada"]} → '
                        f'{item["url_final"]}'
                    )
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados "
                    f"{len(redirecionamentos)} links "
                    "internos com redirecionamento:\n"
                    + "\n".join(
                        observacoes
                    )
                ),
                dados={
                    "quantidade": len(
                        redirecionamentos
                    ),
                    "quantidade_links_internos": len(
                        links_internos
                    ),
                    "quantidade_links_externos_ignorados": (
                        len(links_externos)
                    ),
                    "links_externos_ignorados": (
                        links_externos
                    ),
                    "redirecionamentos": (
                        redirecionamentos
                    ),
                },
            )

        observacao = ""

        if links_externos:
            observacao = (
                f"{len(links_externos)} link(s) "
                "externo(s) ignorado(s)."
            )

        return self.resultado(
            status="approved",
            observacao=observacao,
            dados={
                "quantidade": 0,
                "quantidade_links_internos": len(
                    links_internos
                ),
                "quantidade_links_externos_ignorados": (
                    len(links_externos)
                ),
                "links_externos_ignorados": (
                    links_externos
                ),
                "redirecionamentos": [],
            },
        )