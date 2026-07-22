from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

import requests
from requests.exceptions import RequestException

from config.settings import (
    PAGESPEED_API_KEY,
    PAGESPEED_API_URL,
    PAGESPEED_CATEGORIAS,
    PAGESPEED_ESTRATEGIAS,
    PAGESPEED_TIMEOUT_SEGUNDOS,
)


_cache_pagespeed: dict[
    str,
    dict[str, Any],
] = {}

_cache_lock = Lock()


def limpar_cache_pagespeed() -> None:
    with _cache_lock:
        _cache_pagespeed.clear()


def criar_chave_cache(
    url: str,
) -> str:
    return url.strip()


def criar_parametros(
    url: str,
    estrategia: str,
) -> list[tuple[str, str]]:
    parametros: list[tuple[str, str]] = [
        (
            "url",
            url,
        ),
        (
            "strategy",
            estrategia,
        ),
        (
            "locale",
            "pt-BR",
        ),
    ]

    for categoria in PAGESPEED_CATEGORIAS:
        parametros.append(
            (
                "category",
                categoria,
            )
        )

    if PAGESPEED_API_KEY:
        parametros.append(
            (
                "key",
                PAGESPEED_API_KEY,
            )
        )

    return parametros


def converter_score(
    valor: Any,
) -> int | None:
    if not isinstance(
        valor,
        (int, float),
    ):
        return None

    return round(
        float(valor) * 100
    )


def extrair_metricas_lighthouse(
    resposta_json: dict[str, Any],
) -> dict[str, Any]:
    lighthouse = resposta_json.get(
        "lighthouseResult",
        {},
    )

    audits = lighthouse.get(
        "audits",
        {},
    )

    metricas_desejadas = {
        "first-contentful-paint": "FCP",
        "largest-contentful-paint": "LCP",
        "total-blocking-time": "TBT",
        "cumulative-layout-shift": "CLS",
        "speed-index": "Speed Index",
        "interactive": "Time to Interactive",
    }

    metricas: dict[str, Any] = {}

    for codigo, nome in metricas_desejadas.items():
        auditoria = audits.get(
            codigo,
            {},
        )

        if not isinstance(
            auditoria,
            dict,
        ):
            continue

        metricas[codigo] = {
            "nome": nome,
            "valor_exibido": auditoria.get(
                "displayValue",
                "",
            ),
            "valor_numerico": auditoria.get(
                "numericValue",
            ),
            "unidade": auditoria.get(
                "numericUnit",
                "",
            ),
            "score": auditoria.get(
                "score",
            ),
        }

    return metricas


def extrair_oportunidades(
    resposta_json: dict[str, Any],
) -> list[dict[str, Any]]:
    lighthouse = resposta_json.get(
        "lighthouseResult",
        {},
    )

    audits = lighthouse.get(
        "audits",
        {},
    )

    oportunidades: list[
        dict[str, Any]
    ] = []

    for codigo, auditoria in audits.items():
        if not isinstance(
            auditoria,
            dict,
        ):
            continue

        detalhes = auditoria.get(
            "details",
            {},
        )

        tipo_detalhe = ""

        if isinstance(
            detalhes,
            dict,
        ):
            tipo_detalhe = str(
                detalhes.get(
                    "type",
                    "",
                )
            )

        score = auditoria.get(
            "score"
        )

        economia_ms = auditoria.get(
            "numericValue",
            0,
        )

        eh_oportunidade = (
            tipo_detalhe == "opportunity"
        )

        if not eh_oportunidade:
            continue

        oportunidades.append(
            {
                "codigo": codigo,
                "titulo": auditoria.get(
                    "title",
                    codigo,
                ),
                "descricao": auditoria.get(
                    "description",
                    "",
                ),
                "valor_exibido": auditoria.get(
                    "displayValue",
                    "",
                ),
                "score": score,
                "economia_estimada_ms": (
                    economia_ms
                ),
            }
        )

    oportunidades.sort(
        key=lambda item: (
            item.get(
                "economia_estimada_ms",
                0,
            )
            or 0
        ),
        reverse=True,
    )

    return oportunidades[:10]


def extrair_scores(
    resposta_json: dict[str, Any],
) -> dict[str, int | None]:
    lighthouse = resposta_json.get(
        "lighthouseResult",
        {},
    )

    categorias = lighthouse.get(
        "categories",
        {},
    )

    scores: dict[
        str,
        int | None,
    ] = {}

    for categoria in PAGESPEED_CATEGORIAS:
        dados_categoria = categorias.get(
            categoria,
            {},
        )

        score = None

        if isinstance(
            dados_categoria,
            dict,
        ):
            score = converter_score(
                dados_categoria.get(
                    "score"
                )
            )

        scores[categoria] = score

    return scores


def extrair_erro_api(
    resposta_json: dict[str, Any],
    status_http: int,
) -> str:
    erro_api = resposta_json.get(
        "error",
        {},
    )

    if isinstance(
        erro_api,
        dict,
    ):
        mensagem = str(
            erro_api.get(
                "message",
                "",
            )
        ).strip()

        if mensagem:
            return mensagem

    lighthouse = resposta_json.get(
        "lighthouseResult",
        {},
    )

    runtime_error = {}

    if isinstance(
        lighthouse,
        dict,
    ):
        runtime_error = lighthouse.get(
            "runtimeError",
            {},
        )

    if isinstance(
        runtime_error,
        dict,
    ):
        mensagem = str(
            runtime_error.get(
                "message",
                "",
            )
        ).strip()

        if mensagem:
            return mensagem

    return (
        "A API do PageSpeed retornou "
        f"HTTP {status_http}."
    )


def consultar_estrategia(
    url: str,
    estrategia: str,
) -> dict[str, Any]:
    try:
        resposta = requests.get(
            PAGESPEED_API_URL,
            params=criar_parametros(
                url=url,
                estrategia=estrategia,
            ),
            timeout=PAGESPEED_TIMEOUT_SEGUNDOS,
            headers={
                "User-Agent": (
                    "QA-Auditor-Framework/1.0"
                ),
                "Accept": "application/json",
            },
        )

    except RequestException as erro:
        return {
            "sucesso": False,
            "estrategia": estrategia,
            "status_http": None,
            "erro": str(
                erro
            ),
            "scores": {},
            "metricas": {},
            "oportunidades": [],
        }

    try:
        resposta_json = resposta.json()

    except ValueError:
        return {
            "sucesso": False,
            "estrategia": estrategia,
            "status_http": resposta.status_code,
            "erro": (
                "A API do PageSpeed não retornou "
                "um JSON válido."
            ),
            "scores": {},
            "metricas": {},
            "oportunidades": [],
        }

    if (
        resposta.status_code >= 400
        or "error" in resposta_json
    ):
        return {
            "sucesso": False,
            "estrategia": estrategia,
            "status_http": resposta.status_code,
            "erro": extrair_erro_api(
                resposta_json=resposta_json,
                status_http=resposta.status_code,
            ),
            "scores": {},
            "metricas": {},
            "oportunidades": [],
        }

    lighthouse = resposta_json.get(
        "lighthouseResult",
        {},
    )

    if not lighthouse:
        return {
            "sucesso": False,
            "estrategia": estrategia,
            "status_http": resposta.status_code,
            "erro": (
                "A resposta não possui "
                "lighthouseResult."
            ),
            "scores": {},
            "metricas": {},
            "oportunidades": [],
        }

    runtime_error = lighthouse.get(
        "runtimeError"
    )

    if runtime_error:
        return {
            "sucesso": False,
            "estrategia": estrategia,
            "status_http": resposta.status_code,
            "erro": extrair_erro_api(
                resposta_json=resposta_json,
                status_http=resposta.status_code,
            ),
            "scores": extrair_scores(
                resposta_json
            ),
            "metricas": extrair_metricas_lighthouse(
                resposta_json
            ),
            "oportunidades": extrair_oportunidades(
                resposta_json
            ),
        }

    return {
        "sucesso": True,
        "estrategia": estrategia,
        "status_http": resposta.status_code,
        "erro": "",
        "id": resposta_json.get(
            "id",
            url,
        ),
        "data_analise": lighthouse.get(
            "fetchTime",
            "",
        ),
        "versao_lighthouse": lighthouse.get(
            "lighthouseVersion",
            "",
        ),
        "scores": extrair_scores(
            resposta_json
        ),
        "metricas": extrair_metricas_lighthouse(
            resposta_json
        ),
        "oportunidades": extrair_oportunidades(
            resposta_json
        ),
    }


def executar_pagespeed(
    url: str,
) -> dict[str, Any]:
    url_normalizada = url.strip()

    if not url_normalizada:
        return {
            "sucesso": False,
            "url": url,
            "erro": "URL não informada.",
            "estrategias": {},
        }

    if not PAGESPEED_API_KEY:
        return {
            "sucesso": False,
            "url": url_normalizada,
            "erro": (
                "A variável de ambiente "
                "PAGESPEED_API_KEY não foi configurada."
            ),
            "estrategias": {},
        }

    chave_cache = criar_chave_cache(
        url_normalizada
    )

    with _cache_lock:
        resultado_cache = _cache_pagespeed.get(
            chave_cache
        )

    if resultado_cache is not None:
        return deepcopy(
            resultado_cache
        )

    estrategias: dict[
        str,
        dict[str, Any],
    ] = {}

    for estrategia in PAGESPEED_ESTRATEGIAS:
        estrategias[
            estrategia
        ] = consultar_estrategia(
            url=url_normalizada,
            estrategia=estrategia,
        )

    sucessos = [
        resultado
        for resultado in estrategias.values()
        if resultado.get(
            "sucesso",
            False,
        )
    ]

    erros = [
        (
            f"{estrategia}: "
            f"{resultado.get('erro', '')}"
        )
        for estrategia, resultado
        in estrategias.items()
        if not resultado.get(
            "sucesso",
            False,
        )
    ]

    resultado_final = {
        "sucesso": bool(
            sucessos
        ),
        "sucesso_completo": (
            len(sucessos)
            == len(PAGESPEED_ESTRATEGIAS)
        ),
        "url": url_normalizada,
        "erro": " | ".join(
            erros
        ),
        "estrategias": estrategias,
    }

    with _cache_lock:
        _cache_pagespeed[
            chave_cache
        ] = deepcopy(
            resultado_final
        )

    return resultado_final