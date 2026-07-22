from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any
from urllib.parse import urldefrag

import requests
from requests import Response
from requests.exceptions import RequestException


TIMEOUT_SEGUNDOS = 8

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0 Safari/537.36 "
    "QA-Auditor-Framework/1.0"
)


@dataclass
class LinkHttpResult:
    url_solicitada: str
    url_final: str
    status_http: int | None
    sucesso: bool
    redirecionado: bool
    erro: str
    metodo: str
    content_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_cache_links: dict[str, LinkHttpResult] = {}
_cache_lock = Lock()

_sessao = requests.Session()
_sessao.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8"
        ),
    }
)


def normalizar_url_link(url: str) -> str:
    """
    Remove fragmentos da URL.

    Exemplo:
    https://site.com/pagina#contato
    vira:
    https://site.com/pagina
    """
    url_sem_fragmento, _ = urldefrag(url.strip())

    return url_sem_fragmento


def deve_validar_url(url: str) -> bool:
    url_normalizada = url.strip().casefold()

    return (
        url_normalizada.startswith("http://")
        or url_normalizada.startswith("https://")
    )


def resposta_para_resultado(
    url_solicitada: str,
    response: Response,
    metodo: str,
) -> LinkHttpResult:
    status_http = response.status_code

    return LinkHttpResult(
        url_solicitada=url_solicitada,
        url_final=response.url,
        status_http=status_http,
        sucesso=status_http < 400,
        redirecionado=(
            bool(response.history)
            or response.url != url_solicitada
        ),
        erro="",
        metodo=metodo,
        content_type=response.headers.get(
            "Content-Type",
            "",
        ),
    )


def executar_head(url: str) -> Response:
    return _sessao.head(
        url,
        allow_redirects=True,
        timeout=TIMEOUT_SEGUNDOS,
    )


def executar_get(url: str) -> Response:
    return _sessao.get(
        url,
        allow_redirects=True,
        timeout=TIMEOUT_SEGUNDOS,
        stream=True,
    )


def validar_link_sem_cache(
    url: str,
) -> LinkHttpResult:
    """
    Primeiro tenta HEAD.

    Alguns servidores bloqueiam HEAD. Nesses casos,
    realiza GET como alternativa.
    """
    try:
        response_head = executar_head(url)

        status_head = response_head.status_code

        precisa_fallback_get = status_head in {
            400,
            403,
            405,
            501,
        }

        if not precisa_fallback_get:
            return resposta_para_resultado(
                url_solicitada=url,
                response=response_head,
                metodo="HEAD",
            )

    except RequestException:
        pass

    try:
        response_get = executar_get(url)

        return resposta_para_resultado(
            url_solicitada=url,
            response=response_get,
            metodo="GET",
        )

    except RequestException as erro:
        return LinkHttpResult(
            url_solicitada=url,
            url_final="",
            status_http=None,
            sucesso=False,
            redirecionado=False,
            erro=str(erro),
            metodo="GET",
            content_type="",
        )


def validar_link(
    url: str,
) -> LinkHttpResult:
    url_normalizada = normalizar_url_link(url)

    if not deve_validar_url(url_normalizada):
        return LinkHttpResult(
            url_solicitada=url,
            url_final="",
            status_http=None,
            sucesso=False,
            redirecionado=False,
            erro="Protocolo não suportado.",
            metodo="",
            content_type="",
        )

    with _cache_lock:
        resultado_cache = _cache_links.get(
            url_normalizada
        )

    if resultado_cache is not None:
        return resultado_cache

    resultado = validar_link_sem_cache(
        url_normalizada
    )

    with _cache_lock:
        _cache_links[url_normalizada] = resultado

    return resultado


def quantidade_links_em_cache() -> int:
    with _cache_lock:
        return len(_cache_links)


def limpar_cache_links() -> None:
    with _cache_lock:
        _cache_links.clear()