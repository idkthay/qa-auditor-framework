from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any
from urllib.parse import urldefrag

import requests
from requests import Response
from requests.exceptions import RequestException


TIMEOUT_SEGUNDOS = 10

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0 Safari/537.36 "
    "QA-Auditor-Framework/1.0"
)


@dataclass
class ImageValidationResult:
    url_solicitada: str
    url_final: str
    status_http: int | None
    sucesso: bool
    redirecionado: bool
    erro: str
    metodo: str
    content_type: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


_cache_imagens: dict[
    str,
    ImageValidationResult,
] = {}

_cache_lock = Lock()

_sessao = requests.Session()
_sessao.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "image/avif,image/webp,image/apng,"
            "image/svg+xml,image/*,*/*;q=0.8"
        ),
        "Cache-Control": "no-cache",
    }
)


def normalizar_url_imagem(
    url: str,
) -> str:
    url_sem_fragmento, _ = urldefrag(
        url.strip()
    )

    return url_sem_fragmento


def deve_validar_url(
    url: str,
) -> bool:
    url_normalizada = (
        url.strip().casefold()
    )

    return url_normalizada.startswith(
        (
            "http://",
            "https://",
        )
    )


def resposta_para_resultado(
    url_solicitada: str,
    response: Response,
    metodo: str,
) -> ImageValidationResult:
    status_http = (
        response.status_code
    )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        .split(";")[0]
        .strip()
        .casefold()
    )

    sucesso_http = (
        200 <= status_http < 400
    )

    conteudo_valido = (
        not content_type
        or content_type.startswith(
            "image/"
        )
        or content_type
        in {
            "application/octet-stream",
            "binary/octet-stream",
        }
    )

    sucesso = (
        sucesso_http
        and conteudo_valido
    )

    erro = ""

    if sucesso_http and not conteudo_valido:
        erro = (
            "A URL respondeu, mas o Content-Type "
            f"não parece ser de imagem: {content_type}"
        )

    return ImageValidationResult(
        url_solicitada=url_solicitada,
        url_final=response.url,
        status_http=status_http,
        sucesso=sucesso,
        redirecionado=(
            bool(response.history)
            or response.url
            != url_solicitada
        ),
        erro=erro,
        metodo=metodo,
        content_type=content_type,
    )


def executar_head(
    url: str,
) -> Response:
    return _sessao.head(
        url,
        allow_redirects=True,
        timeout=TIMEOUT_SEGUNDOS,
    )


def executar_get(
    url: str,
) -> Response:
    return _sessao.get(
        url,
        allow_redirects=True,
        timeout=TIMEOUT_SEGUNDOS,
        stream=True,
    )


def validar_imagem_sem_cache(
    url: str,
) -> ImageValidationResult:
    """
    Primeiro tenta HEAD.

    Quando HEAD é bloqueado, inconclusivo ou retorna
    um Content-Type inesperado, faz GET como fallback.
    """
    try:
        response_head = executar_head(
            url
        )

        resultado_head = (
            resposta_para_resultado(
                url_solicitada=url,
                response=response_head,
                metodo="HEAD",
            )
        )

        precisa_fallback_get = (
            not resultado_head.sucesso
            or resultado_head.status_http
            in {
                400,
                401,
                403,
                405,
                406,
                429,
                500,
                501,
                502,
                503,
                504,
            }
        )

        if not precisa_fallback_get:
            return resultado_head

    except RequestException:
        pass

    try:
        response_get = executar_get(
            url
        )

        return resposta_para_resultado(
            url_solicitada=url,
            response=response_get,
            metodo="GET",
        )

    except RequestException as erro:
        return ImageValidationResult(
            url_solicitada=url,
            url_final=url,
            status_http=None,
            sucesso=False,
            redirecionado=False,
            erro=str(
                erro
            ),
            metodo="GET",
            content_type="",
        )


def validar_imagem(
    url: str,
) -> ImageValidationResult:
    url_normalizada = (
        normalizar_url_imagem(
            url
        )
    )

    if not deve_validar_url(
        url_normalizada
    ):
        return ImageValidationResult(
            url_solicitada=url,
            url_final=url,
            status_http=None,
            sucesso=False,
            redirecionado=False,
            erro=(
                "URL de imagem inválida ou "
                "não suportada."
            ),
            metodo="IGNORADO",
            content_type="",
        )

    with _cache_lock:
        resultado_cache = (
            _cache_imagens.get(
                url_normalizada
            )
        )

    if resultado_cache is not None:
        return resultado_cache

    resultado = validar_imagem_sem_cache(
        url_normalizada
    )

    with _cache_lock:
        _cache_imagens[
            url_normalizada
        ] = resultado

    return resultado


def limpar_cache_imagens(
) -> None:
    with _cache_lock:
        _cache_imagens.clear()


def quantidade_imagens_validadas_em_cache(
) -> int:
    with _cache_lock:
        return len(
            _cache_imagens
        )