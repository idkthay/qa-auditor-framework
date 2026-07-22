from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import requests
from requests.exceptions import RequestException


TIMEOUT_SEGUNDOS = 10

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0 Safari/537.36 "
    "QA-Auditor-Framework/1.0"
)


@dataclass
class SiteFileResult:
    url: str
    url_final: str
    status_http: int | None
    acessivel: bool
    conteudo: str
    content_type: str
    erro: str
    redirecionado: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_cache: dict[str, SiteFileResult] = {}
_cache_lock = Lock()

_sessao = requests.Session()
_sessao.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/plain,application/xml,text/xml,"
            "text/html;q=0.9,*/*;q=0.8"
        ),
    }
)


def obter_origem(url: str) -> str:
    partes = urlsplit(url)

    return f"{partes.scheme}://{partes.netloc}"


def criar_url_arquivo(
    url_pagina: str,
    caminho: str,
) -> str:
    origem = obter_origem(url_pagina)

    return urljoin(
        f"{origem}/",
        caminho.lstrip("/"),
    )


def buscar_arquivo(
    url: str,
) -> SiteFileResult:
    with _cache_lock:
        resultado_cache = _cache.get(url)

    if resultado_cache is not None:
        return resultado_cache

    try:
        resposta = _sessao.get(
            url,
            allow_redirects=True,
            timeout=TIMEOUT_SEGUNDOS,
        )

        status_http = resposta.status_code

        resultado = SiteFileResult(
            url=url,
            url_final=resposta.url,
            status_http=status_http,
            acessivel=200 <= status_http < 400,
            conteudo=resposta.text,
            content_type=resposta.headers.get(
                "Content-Type",
                "",
            ),
            erro="",
            redirecionado=(
                bool(resposta.history)
                or resposta.url != url
            ),
        )

    except RequestException as erro:
        resultado = SiteFileResult(
            url=url,
            url_final="",
            status_http=None,
            acessivel=False,
            conteudo="",
            content_type="",
            erro=str(erro),
            redirecionado=False,
        )

    with _cache_lock:
        _cache[url] = resultado

    return resultado


def buscar_robots(
    url_pagina: str,
) -> SiteFileResult:
    return buscar_arquivo(
        criar_url_arquivo(
            url_pagina,
            "/robots.txt",
        )
    )


def extrair_sitemaps_robots(
    conteudo: str,
) -> list[str]:
    sitemaps: list[str] = []

    for linha in conteudo.splitlines():
        linha_limpa = linha.strip()

        if not linha_limpa:
            continue

        if linha_limpa.startswith("#"):
            continue

        if ":" not in linha_limpa:
            continue

        chave, valor = linha_limpa.split(
            ":",
            1,
        )

        if chave.strip().casefold() != "sitemap":
            continue

        url_sitemap = valor.strip()

        if url_sitemap:
            sitemaps.append(url_sitemap)

    return list(dict.fromkeys(sitemaps))


def possui_bloqueio_global(
    conteudo: str,
) -> bool:
    """
    Detecta o seguinte bloco:

    User-agent: *
    Disallow: /

    A análise respeita os grupos do robots.txt.
    """
    agente_atual: list[str] = []

    for linha in conteudo.splitlines():
        linha = linha.split(
            "#",
            1,
        )[0].strip()

        if not linha or ":" not in linha:
            continue

        chave, valor = linha.split(
            ":",
            1,
        )

        chave = chave.strip().casefold()
        valor = valor.strip()

        if chave == "user-agent":
            agente_atual = [
                valor.casefold()
            ]
            continue

        if (
            chave == "disallow"
            and "*" in agente_atual
            and valor == "/"
        ):
            return True

    return False


def buscar_sitemap_padrao(
    url_pagina: str,
) -> SiteFileResult:
    return buscar_arquivo(
        criar_url_arquivo(
            url_pagina,
            "/sitemap.xml",
        )
    )


def validar_xml_sitemap(
    conteudo: str,
) -> dict[str, Any]:
    if not conteudo.strip():
        return {
            "valido": False,
            "tipo": "",
            "quantidade_urls": 0,
            "erro": "O sitemap está vazio.",
        }

    try:
        raiz = ElementTree.fromstring(
            conteudo
        )

    except ElementTree.ParseError as erro:
        return {
            "valido": False,
            "tipo": "",
            "quantidade_urls": 0,
            "erro": str(erro),
        }

    tag_raiz = raiz.tag.split(
        "}",
        1,
    )[-1].casefold()

    if tag_raiz not in {
        "urlset",
        "sitemapindex",
    }:
        return {
            "valido": False,
            "tipo": tag_raiz,
            "quantidade_urls": 0,
            "erro": (
                "O elemento raiz não é urlset "
                "nem sitemapindex."
            ),
        }

    elementos_loc = [
        elemento
        for elemento in raiz.iter()
        if (
            elemento.tag.split(
                "}",
                1,
            )[-1].casefold()
            == "loc"
            and elemento.text
            and elemento.text.strip()
        )
    ]

    return {
        "valido": True,
        "tipo": tag_raiz,
        "quantidade_urls": len(
            elementos_loc
        ),
        "erro": "",
    }


def limpar_cache_site_files() -> None:
    with _cache_lock:
        _cache.clear()