from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException


TIMEOUT_SEGUNDOS = 10

# Impede o download ilimitado de imagens muito grandes.
LIMITE_DOWNLOAD_BYTES = 10 * 1024 * 1024

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0 Safari/537.36 "
    "QA-Auditor-Framework/1.0"
)


@dataclass
class ImageSizeResult:
    url: str
    tamanho_bytes: int
    tamanho_kb: float
    tamanho_exato: bool
    sucesso: bool
    status_http: int | None
    content_type: str
    origem_tamanho: str
    erro: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


_cache_imagens: dict[
    str,
    ImageSizeResult,
] = {}

_cache_lock = Lock()

_sessao = requests.Session()

_sessao.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "image/avif,"
            "image/webp,"
            "image/apng,"
            "image/svg+xml,"
            "image/*,"
            "*/*;q=0.8"
        ),
    }
)


def converter_kb(
    tamanho_bytes: int,
) -> float:
    return round(
        tamanho_bytes / 1024,
        2,
    )


def obter_content_length(
    response: Response,
) -> int:
    valor = response.headers.get(
        "Content-Length",
        "",
    ).strip()

    if not valor:
        return 0

    try:
        tamanho = int(
            valor
        )

    except ValueError:
        return 0

    return max(
        tamanho,
        0,
    )


def criar_resultado(
    url: str,
    tamanho_bytes: int,
    tamanho_exato: bool,
    sucesso: bool,
    status_http: int | None,
    content_type: str,
    origem_tamanho: str,
    erro: str = "",
) -> ImageSizeResult:
    return ImageSizeResult(
        url=url,
        tamanho_bytes=tamanho_bytes,
        tamanho_kb=converter_kb(
            tamanho_bytes
        ),
        tamanho_exato=tamanho_exato,
        sucesso=sucesso,
        status_http=status_http,
        content_type=content_type,
        origem_tamanho=origem_tamanho,
        erro=erro,
    )


def consultar_por_head(
    url: str,
) -> ImageSizeResult | None:
    try:
        response = _sessao.head(
            url,
            allow_redirects=True,
            timeout=TIMEOUT_SEGUNDOS,
        )

    except RequestException:
        return None

    status_http = response.status_code

    if status_http >= 400:
        return None

    tamanho = obter_content_length(
        response
    )

    if tamanho <= 0:
        return None

    return criar_resultado(
        url=url,
        tamanho_bytes=tamanho,
        tamanho_exato=True,
        sucesso=True,
        status_http=status_http,
        content_type=response.headers.get(
            "Content-Type",
            "",
        ),
        origem_tamanho="http_head",
    )


def consultar_por_get(
    url: str,
) -> ImageSizeResult:
    try:
        with _sessao.get(
            url,
            allow_redirects=True,
            timeout=TIMEOUT_SEGUNDOS,
            stream=True,
        ) as response:
            status_http = response.status_code

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            if status_http >= 400:
                return criar_resultado(
                    url=url,
                    tamanho_bytes=0,
                    tamanho_exato=False,
                    sucesso=False,
                    status_http=status_http,
                    content_type=content_type,
                    origem_tamanho="http_get",
                    erro=(
                        "A imagem retornou HTTP "
                        f"{status_http}."
                    ),
                )

            tamanho_cabecalho = obter_content_length(
                response
            )

            if tamanho_cabecalho > 0:
                return criar_resultado(
                    url=url,
                    tamanho_bytes=tamanho_cabecalho,
                    tamanho_exato=True,
                    sucesso=True,
                    status_http=status_http,
                    content_type=content_type,
                    origem_tamanho=(
                        "http_get_content_length"
                    ),
                )

            tamanho_total = 0
            tamanho_exato = True

            for bloco in response.iter_content(
                chunk_size=64 * 1024,
            ):
                if not bloco:
                    continue

                tamanho_total += len(
                    bloco
                )

                if (
                    tamanho_total
                    >= LIMITE_DOWNLOAD_BYTES
                ):
                    tamanho_exato = False
                    break

            if tamanho_total <= 0:
                return criar_resultado(
                    url=url,
                    tamanho_bytes=0,
                    tamanho_exato=False,
                    sucesso=False,
                    status_http=status_http,
                    content_type=content_type,
                    origem_tamanho=(
                        "http_get_stream"
                    ),
                    erro=(
                        "Não foi possível identificar "
                        "o tamanho da imagem."
                    ),
                )

            return criar_resultado(
                url=url,
                tamanho_bytes=tamanho_total,
                tamanho_exato=tamanho_exato,
                sucesso=True,
                status_http=status_http,
                content_type=content_type,
                origem_tamanho=(
                    "http_get_stream"
                ),
            )

    except RequestException as erro:
        return criar_resultado(
            url=url,
            tamanho_bytes=0,
            tamanho_exato=False,
            sucesso=False,
            status_http=None,
            content_type="",
            origem_tamanho="http_get",
            erro=str(
                erro
            ),
        )


def validar_tamanho_imagem(
    url: str,
    tamanho_navegador: int = 0,
) -> ImageSizeResult:
    """
    Identifica o peso da imagem utilizando:

    1. Performance API do navegador;
    2. requisição HTTP HEAD;
    3. requisição HTTP GET.
    """
    url_normalizada = url.strip()

    if not url_normalizada:
        return criar_resultado(
            url=url,
            tamanho_bytes=0,
            tamanho_exato=False,
            sucesso=False,
            status_http=None,
            content_type="",
            origem_tamanho="",
            erro="Imagem sem URL.",
        )

    if url_normalizada.casefold().startswith(
        (
            "data:",
            "blob:",
        )
    ):
        return criar_resultado(
            url=url_normalizada,
            tamanho_bytes=0,
            tamanho_exato=False,
            sucesso=False,
            status_http=None,
            content_type="",
            origem_tamanho="",
            erro=(
                "Imagem incorporada por "
                "data URI ou blob."
            ),
        )

    if tamanho_navegador > 0:
        resultado_navegador = criar_resultado(
            url=url_normalizada,
            tamanho_bytes=tamanho_navegador,
            tamanho_exato=True,
            sucesso=True,
            status_http=None,
            content_type="",
            origem_tamanho="performance_api",
        )

        with _cache_lock:
            _cache_imagens[
                url_normalizada
            ] = resultado_navegador

        return resultado_navegador

    with _cache_lock:
        resultado_cache = _cache_imagens.get(
            url_normalizada
        )

    if resultado_cache is not None:
        return resultado_cache

    resultado = consultar_por_head(
        url_normalizada
    )

    if resultado is None:
        resultado = consultar_por_get(
            url_normalizada
        )

    with _cache_lock:
        _cache_imagens[
            url_normalizada
        ] = resultado

    return resultado


def quantidade_imagens_em_cache(
) -> int:
    with _cache_lock:
        return len(
            _cache_imagens
        )


def limpar_cache_imagens(
) -> None:
    with _cache_lock:
        _cache_imagens.clear()