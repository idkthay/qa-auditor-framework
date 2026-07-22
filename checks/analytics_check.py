from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from playwright.sync_api import Page
from requests.exceptions import RequestException

from checks.base_check import BaseCheck
from models.page_data import PageData


TIMEOUT_VERIFICACAO = 8

PADRAO_GA4 = re.compile(
    r"\bG-[A-Z0-9]{6,15}\b",
    re.IGNORECASE,
)

PADRAO_GOOGLE_HTML = re.compile(
    r"^google[a-zA-Z0-9_-]+\.html$",
    re.IGNORECASE,
)

_ARQUIVO_SEARCH_CONSOLE = ""


def configurar_arquivo_search_console(
    arquivo: str,
) -> None:
    """
    Define o nome do arquivo HTML do Google Search Console
    informado no início da auditoria.
    """
    global _ARQUIVO_SEARCH_CONSOLE

    arquivo_limpo = (
        arquivo.strip()
        .replace("\\", "/")
        .split("/")[-1]
    )

    if not arquivo_limpo:
        _ARQUIVO_SEARCH_CONSOLE = ""
        return

    if not PADRAO_GOOGLE_HTML.fullmatch(
        arquivo_limpo
    ):
        raise ValueError(
            "O arquivo do Search Console deve seguir "
            "o padrão google*.html. Exemplo: "
            "google363a45d212dc8769.html"
        )

    _ARQUIVO_SEARCH_CONSOLE = (
        arquivo_limpo
    )


def obter_arquivo_search_console() -> str:
    return _ARQUIVO_SEARCH_CONSOLE


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


def obter_html_completo(
    page_data: PageData,
) -> str:
    return page_data.html or ""


def obter_scripts_completos(
    page_data: PageData,
) -> str:
    partes: list[str] = []

    for script in page_data.scripts:
        src = str(
            script.get(
                "src",
                "",
            )
        ).strip()

        if src:
            partes.append(
                src
            )

    partes.append(
        obter_html_completo(
            page_data
        )
    )

    return "\n".join(
        partes
    )


def encontrar_ids_ga4(
    page_data: PageData,
) -> list[str]:
    conteudo = obter_scripts_completos(
        page_data
    )

    ids = PADRAO_GA4.findall(
        conteudo
    )

    ids_normalizados = [
        identificador.upper()
        for identificador in ids
        if identificador.upper()
        != "G-RECAPTCHA"
    ]

    return remover_duplicados(
        ids_normalizados
    )


def normalizar_origem(
    url: str,
) -> str:
    partes = urlparse(
        url
    )

    return (
        f"{partes.scheme}://"
        f"{partes.netloc}/"
    )


def eh_home(
    page_data: PageData,
    contexto: dict[str, Any],
) -> bool:
    url_principal = str(
        contexto.get(
            "url_principal",
            "",
        )
    ).strip()

    if not url_principal:
        return False

    origem_principal = normalizar_origem(
        url_principal
    )

    origem_pagina = normalizar_origem(
        page_data.url_final
        or page_data.url_solicitada
    )

    caminho = urlparse(
        page_data.url_final
        or page_data.url_solicitada
    ).path.rstrip("/")

    return (
        origem_pagina == origem_principal
        and caminho == ""
    )


def validar_arquivo_google(
    arquivo: str,
    url_base: str,
) -> dict[str, Any]:
    url = urljoin(
        normalizar_origem(
            url_base
        ),
        arquivo,
    )

    try:
        resposta = requests.get(
            url,
            timeout=TIMEOUT_VERIFICACAO,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "QA-Auditor-Framework/1.0"
                ),
            },
        )

        conteudo = resposta.text[
            :2000
        ]

        assinatura_esperada = (
            f"google-site-verification: "
            f"{arquivo}"
        )

        valido = (
            resposta.status_code == 200
            and assinatura_esperada.casefold()
            in conteudo.casefold()
        )

        erro = ""

        if (
            resposta.status_code == 200
            and not valido
        ):
            erro = (
                "O arquivo respondeu com HTTP 200, "
                "mas não contém a assinatura esperada."
            )

        return {
            "arquivo": arquivo,
            "url": url,
            "url_final": resposta.url,
            "status_http": resposta.status_code,
            "valido": valido,
            "erro": erro,
        }

    except RequestException as erro:
        return {
            "arquivo": arquivo,
            "url": url,
            "url_final": "",
            "status_http": None,
            "valido": False,
            "erro": str(
                erro
            ),
        }


class GoogleAnalyticsGa4Check(
    BaseCheck
):
    nome = "Google Analytics 4 - GA4"
    categoria = "Best Practices"

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

        ids_ga4 = encontrar_ids_ga4(
            page_data
        )

        html = obter_html_completo(
            page_data
        ).casefold()

        possui_gtag = (
            "googletagmanager.com/gtag/js"
            in html
            or "gtag(" in html
        )

        possui_google_analytics = (
            "google-analytics.com"
            in html
            or "googletagmanager.com/gtag/js"
            in html
        )

        detectado = bool(
            ids_ga4
            or (
                possui_gtag
                and possui_google_analytics
            )
        )

        dados = {
            "detectado": detectado,
            "ids_ga4": ids_ga4,
            "possui_gtag": possui_gtag,
            "possui_google_analytics": (
                possui_google_analytics
            ),
        }

        if not detectado:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi encontrada uma configuração "
                    "do Google Analytics 4 na página."
                ),
                dados=dados,
            )

        observacao = (
            "Google Analytics 4 encontrado."
        )

        if ids_ga4:
            observacao += (
                " IDs identificados: "
                + ", ".join(
                    ids_ga4
                )
            )

        return self.resultado(
            status="approved",
            observacao=observacao,
            dados=dados,
        )


class SearchConsoleHtmlFileCheck(
    BaseCheck
):
    nome = "Search Console - Arquivo HTML"
    categoria = "Best Practices"

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

        if not eh_home(
            page_data=page_data,
            contexto=contexto,
        ):
            return self.resultado(
                status="approved",
                observacao=(
                    "Validação não aplicável nesta página. "
                    "O arquivo do Search Console é verificado "
                    "somente na Home."
                ),
                dados={
                    "aplicavel": False,
                    "arquivo": "",
                    "resultado": {},
                    "requer_revisao_manual": False,
                },
            )

        arquivo = (
            obter_arquivo_search_console()
        )

        if not arquivo:
            return self.resultado(
                status="approved",
                observacao=(
                    "O nome do arquivo HTML do Search Console "
                    "não foi informado no início da auditoria. "
                    "Confirme este item manualmente."
                ),
                dados={
                    "aplicavel": True,
                    "arquivo": "",
                    "resultado": {},
                    "requer_revisao_manual": True,
                },
            )

        resultado = validar_arquivo_google(
            arquivo=arquivo,
            url_base=page_data.url_final,
        )

        if resultado["valido"]:
            return self.resultado(
                status="approved",
                observacao=(
                    "Arquivo HTML válido do Google "
                    "Search Console encontrado na raiz "
                    "do site."
                ),
                dados={
                    "aplicavel": True,
                    "arquivo": arquivo,
                    "resultado": resultado,
                    "requer_revisao_manual": False,
                },
            )

        status_http = resultado.get(
            "status_http"
        )

        if status_http is None:
            status_texto = (
                "sem resposta HTTP"
            )
        else:
            status_texto = (
                f"HTTP {status_http}"
            )

        erro = str(
            resultado.get(
                "erro",
                "",
            )
        ).strip()

        observacao = (
            "O arquivo HTML informado para o "
            "Google Search Console não foi validado. "
            f"Resultado: {status_texto}."
        )

        if erro:
            observacao += (
                f" Detalhe: {erro}"
            )

        return self.resultado(
            status="rejected",
            observacao=observacao,
            dados={
                "aplicavel": True,
                "arquivo": arquivo,
                "resultado": resultado,
                "requer_revisao_manual": True,
            },
        )