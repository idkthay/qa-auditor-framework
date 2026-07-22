from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from config.settings import (
    PAGESPEED_LIMITES,
    PAGESPEED_SOMENTE_HOME,
)
from models.page_data import PageData
from services.pagespeed_service import (
    executar_pagespeed,
)


NOMES_CATEGORIAS = {
    "performance": "Performance",
    "accessibility": "Accessibility",
    "best-practices": "Best Practices",
    "seo": "SEO",
}


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


def eh_home(
    url: str,
) -> bool:
    partes = urlparse(
        url
    )

    caminho = partes.path.strip(
        "/"
    )

    return not caminho


def obter_scores_categoria(
    resultado_pagespeed: dict[str, Any],
    categoria: str,
) -> dict[str, int | None]:
    scores: dict[
        str,
        int | None,
    ] = {}

    estrategias = resultado_pagespeed.get(
        "estrategias",
        {},
    )

    for estrategia, resultado in estrategias.items():
        if not isinstance(
            resultado,
            dict,
        ):
            continue

        scores_estrategia = resultado.get(
            "scores",
            {},
        )

        if not isinstance(
            scores_estrategia,
            dict,
        ):
            continue

        scores[
            estrategia
        ] = scores_estrategia.get(
            categoria
        )

    return scores


def obter_metricas(
    resultado_pagespeed: dict[str, Any],
) -> dict[str, Any]:
    metricas: dict[
        str,
        Any,
    ] = {}

    estrategias = resultado_pagespeed.get(
        "estrategias",
        {},
    )

    for estrategia, resultado in estrategias.items():
        if not isinstance(
            resultado,
            dict,
        ):
            continue

        metricas[
            estrategia
        ] = resultado.get(
            "metricas",
            {},
        )

    return metricas


def obter_oportunidades(
    resultado_pagespeed: dict[str, Any],
) -> dict[str, Any]:
    oportunidades: dict[
        str,
        Any,
    ] = {}

    estrategias = resultado_pagespeed.get(
        "estrategias",
        {},
    )

    for estrategia, resultado in estrategias.items():
        if not isinstance(
            resultado,
            dict,
        ):
            continue

        oportunidades[
            estrategia
        ] = resultado.get(
            "oportunidades",
            [],
        )

    return oportunidades


def formatar_scores(
    scores: dict[str, int | None],
) -> str:
    partes: list[str] = []

    for estrategia in (
        "mobile",
        "desktop",
    ):
        score = scores.get(
            estrategia
        )

        nome = (
            "Mobile"
            if estrategia == "mobile"
            else "Desktop"
        )

        if score is None:
            partes.append(
                f"{nome}: indisponível"
            )

        else:
            partes.append(
                f"{nome}: {score}"
            )

    return " | ".join(
        partes
    )


class PageSpeedCategoryCheck(
    BaseCheck
):
    categoria_pagespeed = ""

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

        url = (
            page_data.url_final
            or page_data.url_solicitada
        )

        if (
            PAGESPEED_SOMENTE_HOME
            and not eh_home(
                url
            )
        ):
            return self.resultado(
                status="approved",
                observacao=(
                    "Check ignorado nesta página. "
                    "O PageSpeed é executado somente "
                    "na página inicial."
                ),
                dados={
                    "ignorado": True,
                    "motivo": (
                        "PageSpeed configurado "
                        "somente para a home."
                    ),
                    "url": url,
                },
            )

        resultado_pagespeed = executar_pagespeed(
            url
        )

        if not resultado_pagespeed.get(
            "sucesso",
            False,
        ):
            return self.resultado(
                status="error",
                observacao=(
                    "Não foi possível executar "
                    "o PageSpeed Insights: "
                    + str(
                        resultado_pagespeed.get(
                            "erro",
                            "Erro não identificado.",
                        )
                    )
                ),
                dados={
                    "ignorado": False,
                    "url": url,
                    "resultado_pagespeed": (
                        resultado_pagespeed
                    ),
                },
            )

        categoria = self.categoria_pagespeed

        limite = int(
            PAGESPEED_LIMITES.get(
                categoria,
                90,
            )
        )

        scores = obter_scores_categoria(
            resultado_pagespeed=resultado_pagespeed,
            categoria=categoria,
        )

        scores_validos = {
            estrategia: score
            for estrategia, score
            in scores.items()
            if isinstance(
                score,
                int,
            )
        }

        abaixo_limite = {
            estrategia: score
            for estrategia, score
            in scores_validos.items()
            if score < limite
        }

        nome_categoria = NOMES_CATEGORIAS.get(
            categoria,
            categoria,
        )

        observacao_scores = formatar_scores(
            scores
        )

        dados = {
            "ignorado": False,
            "url": url,
            "categoria_pagespeed": categoria,
            "nome_categoria": nome_categoria,
            "limite_aprovacao": limite,
            "scores": scores,
            "abaixo_limite": abaixo_limite,
            "metricas": obter_metricas(
                resultado_pagespeed
            ),
            "oportunidades": obter_oportunidades(
                resultado_pagespeed
            ),
            "resultado_completo": (
                resultado_pagespeed
            ),
        }

        if not scores_validos:
            return self.resultado(
                status="error",
                observacao=(
                    f"O PageSpeed não retornou uma nota "
                    f"válida para {nome_categoria}."
                ),
                dados=dados,
            )

        if abaixo_limite:
            detalhes = ", ".join(
                (
                    f"{estrategia}: {score}"
                )
                for estrategia, score
                in abaixo_limite.items()
            )

            return self.resultado(
                status="rejected",
                observacao=(
                    f"PageSpeed {nome_categoria} abaixo "
                    f"do limite mínimo de {limite}. "
                    f"{observacao_scores}. "
                    f"Abaixo do limite: {detalhes}."
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"PageSpeed {nome_categoria} aprovado. "
                f"Limite mínimo: {limite}. "
                f"{observacao_scores}."
            ),
            dados=dados,
        )


class PageSpeedPerformanceCheck(
    PageSpeedCategoryCheck
):
    nome = "PageSpeed - Performance"
    categoria = "PageSpeed"
    categoria_pagespeed = "performance"


class PageSpeedAccessibilityCheck(
    PageSpeedCategoryCheck
):
    nome = "PageSpeed - Accessibility"
    categoria = "PageSpeed"
    categoria_pagespeed = "accessibility"


class PageSpeedBestPracticesCheck(
    PageSpeedCategoryCheck
):
    nome = "PageSpeed - Best Practices"
    categoria = "PageSpeed"
    categoria_pagespeed = "best-practices"


class PageSpeedSeoCheck(
    PageSpeedCategoryCheck
):
    nome = "PageSpeed - SEO"
    categoria = "PageSpeed"
    categoria_pagespeed = "seo"