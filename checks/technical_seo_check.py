from __future__ import annotations

from typing import Any
from urllib.parse import urldefrag, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get("page_data")

    if isinstance(page_data, PageData):
        return page_data

    return None


def criar_soup(
    page_data: PageData,
) -> BeautifulSoup:
    return BeautifulSoup(
        page_data.html,
        "html.parser",
    )


def normalizar_url_comparacao(
    url: str,
) -> str:
    """
    Normaliza a URL para comparação:

    - remove fragmento;
    - transforma domínio em minúsculas;
    - remove barra final, exceto na raiz;
    - remove portas padrão;
    - mantém query string.
    """
    if not url:
        return ""

    url_sem_fragmento, _ = urldefrag(
        url.strip()
    )

    partes = urlsplit(
        url_sem_fragmento
    )

    esquema = partes.scheme.casefold()
    host = partes.hostname.casefold() if partes.hostname else ""
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
        host = f"{host}:{porta}"

    caminho = partes.path or "/"

    if caminho != "/":
        caminho = caminho.rstrip("/")

    return urlunsplit(
        (
            esquema,
            host,
            caminho,
            partes.query,
            "",
        )
    )


def encontrar_meta_por_nome(
    soup: BeautifulSoup,
    nome: str,
) -> list[str]:
    valores: list[str] = []

    for tag in soup.find_all(
        "meta",
        attrs={"name": True},
    ):
        nome_encontrado = str(
            tag.get("name", "")
        ).strip().casefold()

        if nome_encontrado != nome.casefold():
            continue

        conteudo = str(
            tag.get("content", "")
        ).strip()

        valores.append(conteudo)

    return valores


def encontrar_meta_por_property(
    soup: BeautifulSoup,
    propriedade: str,
) -> list[str]:
    valores: list[str] = []

    for tag in soup.find_all(
        "meta",
        attrs={"property": True},
    ):
        propriedade_encontrada = str(
            tag.get("property", "")
        ).strip().casefold()

        if (
            propriedade_encontrada
            != propriedade.casefold()
        ):
            continue

        conteudo = str(
            tag.get("content", "")
        ).strip()

        valores.append(conteudo)

    return valores


def encontrar_canonicals(
    soup: BeautifulSoup,
) -> list[str]:
    canonicals: list[str] = []

    for tag in soup.find_all(
        "link",
        attrs={"rel": True},
    ):
        rel = tag.get("rel", [])

        if isinstance(rel, str):
            valores_rel = rel.casefold().split()

        else:
            valores_rel = [
                str(item).casefold()
                for item in rel
            ]

        if "canonical" not in valores_rel:
            continue

        href = str(
            tag.get("href", "")
        ).strip()

        canonicals.append(href)

    return canonicals


class MetaRobotsIndexabilityCheck(BaseCheck):
    nome = "Meta Robots - Indexação"
    categoria = "SEO Técnico"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)

        valores_robots = encontrar_meta_por_nome(
            soup,
            "robots",
        )

        valores_googlebot = encontrar_meta_por_nome(
            soup,
            "googlebot",
        )

        valores = (
            valores_robots
            + valores_googlebot
        )

        diretivas: list[str] = []

        for valor in valores:
            diretivas.extend(
                [
                    item.strip().casefold()
                    for item in valor.split(",")
                    if item.strip()
                ]
            )

        diretivas = list(
            dict.fromkeys(diretivas)
        )

        diretivas_bloqueadoras = [
            diretiva
            for diretiva in diretivas
            if diretiva in {
                "noindex",
                "none",
            }
        ]

        if diretivas_bloqueadoras:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página possui diretiva que impede "
                    "a indexação: "
                    + ", ".join(
                        diretivas_bloqueadoras
                    )
                ),
                dados={
                    "meta_robots": valores_robots,
                    "meta_googlebot": valores_googlebot,
                    "diretivas": diretivas,
                    "bloqueadores": diretivas_bloqueadoras,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                "Nenhuma diretiva noindex foi encontrada."
            ),
            dados={
                "meta_robots": valores_robots,
                "meta_googlebot": valores_googlebot,
                "diretivas": diretivas,
                "bloqueadores": [],
            },
        )


class MetaRobotsFollowCheck(BaseCheck):
    nome = "Meta Robots - Seguimento de links"
    categoria = "SEO Técnico"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)

        valores = (
            encontrar_meta_por_nome(
                soup,
                "robots",
            )
            + encontrar_meta_por_nome(
                soup,
                "googlebot",
            )
        )

        diretivas: list[str] = []

        for valor in valores:
            diretivas.extend(
                [
                    item.strip().casefold()
                    for item in valor.split(",")
                    if item.strip()
                ]
            )

        diretivas = list(
            dict.fromkeys(diretivas)
        )

        bloqueadores = [
            diretiva
            for diretiva in diretivas
            if diretiva in {
                "nofollow",
                "none",
            }
        ]

        if bloqueadores:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página possui diretiva que impede "
                    "o seguimento de links: "
                    + ", ".join(bloqueadores)
                ),
                dados={
                    "diretivas": diretivas,
                    "bloqueadores": bloqueadores,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "diretivas": diretivas,
                "bloqueadores": [],
                "requer_revisao_manual": False,
            },
        )


class ViewportCheck(BaseCheck):
    nome = "Meta Viewport"
    categoria = "Responsividade"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)

        valores = encontrar_meta_por_nome(
            soup,
            "viewport",
        )

        if not valores:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página não possui a meta tag viewport."
                ),
                dados={
                    "quantidade": 0,
                    "valores": [],
                },
            )

        valores_validos = [
            valor
            for valor in valores
            if (
                "width=device-width"
                in valor.casefold().replace(" ", "")
            )
        ]

        if not valores_validos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A meta viewport existe, mas não contém "
                    "width=device-width."
                ),
                dados={
                    "quantidade": len(valores),
                    "valores": valores,
                },
            )

        if len(valores) > 1:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontradas múltiplas meta tags "
                    "viewport."
                ),
                dados={
                    "quantidade": len(valores),
                    "valores": valores,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 1,
                "valores": valores,
            },
        )


class FaviconCheck(BaseCheck):
    nome = "Favicon"
    categoria = "SEO Técnico"

    RELS_FAVICON = {
        "icon",
        "shortcut icon",
        "apple-touch-icon",
        "apple-touch-icon-precomposed",
        "mask-icon",
    }

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)
        favicons: list[dict[str, str]] = []

        for tag in soup.find_all(
            "link",
            attrs={"rel": True},
        ):
            rel = tag.get("rel", [])

            if isinstance(rel, str):
                rel_normalizado = rel.casefold().strip()

            else:
                rel_normalizado = " ".join(
                    str(item).casefold().strip()
                    for item in rel
                )

            eh_favicon = any(
                valor in rel_normalizado
                for valor in self.RELS_FAVICON
            )

            if not eh_favicon:
                continue

            favicons.append(
                {
                    "rel": rel_normalizado,
                    "href": str(
                        tag.get("href", "")
                    ).strip(),
                    "type": str(
                        tag.get("type", "")
                    ).strip(),
                    "sizes": str(
                        tag.get("sizes", "")
                    ).strip(),
                }
            )

        favicons_validos = [
            favicon
            for favicon in favicons
            if favicon["href"]
        ]

        if not favicons_validos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum favicon configurado foi encontrado."
                ),
                dados={
                    "quantidade": 0,
                    "favicons": favicons,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": len(
                    favicons_validos
                ),
                "favicons": favicons_validos,
            },
        )


class OpenGraphCheck(BaseCheck):
    nome = "Open Graph"
    categoria = "SEO Social"

    CAMPOS_OBRIGATORIOS = {
        "og:title",
        "og:description",
        "og:image",
        "og:url",
        "og:type",
    }

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)

        valores: dict[str, list[str]] = {
            campo: encontrar_meta_por_property(
                soup,
                campo,
            )
            for campo in self.CAMPOS_OBRIGATORIOS
        }

        ausentes = [
            campo
            for campo, conteudos in valores.items()
            if not any(
                conteudo.strip()
                for conteudo in conteudos
            )
        ]

        if ausentes:
            return self.resultado(
                status="rejected",
                observacao=(
                    "As seguintes propriedades Open Graph "
                    "estão ausentes ou vazias: "
                    + ", ".join(sorted(ausentes))
                ),
                dados={
                    "campos_ausentes": sorted(ausentes),
                    "valores": valores,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "campos_ausentes": [],
                "valores": valores,
            },
        )


class TwitterCardCheck(BaseCheck):
    nome = "Twitter Cards"
    categoria = "SEO Social"

    CAMPOS_RECOMENDADOS = {
        "twitter:card",
        "twitter:title",
        "twitter:description",
        "twitter:image",
    }

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)

        valores: dict[str, list[str]] = {
            campo: encontrar_meta_por_nome(
                soup,
                campo,
            )
            for campo in self.CAMPOS_RECOMENDADOS
        }

        ausentes = [
            campo
            for campo, conteudos in valores.items()
            if not any(
                conteudo.strip()
                for conteudo in conteudos
            )
        ]

        if len(ausentes) == len(
            self.CAMPOS_RECOMENDADOS
        ):
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhuma Twitter Card foi encontrada."
                ),
                dados={
                    "campos_ausentes": sorted(ausentes),
                    "valores": valores,
                    "requer_revisao_manual": True,
                },
            )

        if ausentes:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A Twitter Card está incompleta. "
                    "Campos ausentes: "
                    + ", ".join(sorted(ausentes))
                ),
                dados={
                    "campos_ausentes": sorted(ausentes),
                    "valores": valores,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "campos_ausentes": [],
                "valores": valores,
                "requer_revisao_manual": False,
            },
        )


class MultipleCanonicalCheck(BaseCheck):
    nome = "Canonical - Múltiplas tags"
    categoria = "SEO Técnico"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        soup = criar_soup(page_data)

        canonicals = encontrar_canonicals(
            soup
        )

        if len(canonicals) > 1:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontradas múltiplas tags "
                    "canonical na página."
                ),
                dados={
                    "quantidade": len(canonicals),
                    "canonicals": canonicals,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": len(canonicals),
                "canonicals": canonicals,
            },
        )


class CanonicalProtocolCheck(BaseCheck):
    nome = "Canonical - Protocolo HTTPS"
    categoria = "SEO Técnico"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        canonical = page_data.canonical.strip()

        if not canonical:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página não possui canonical para "
                    "verificação do protocolo."
                ),
                dados={
                    "canonical": "",
                },
            )

        pagina_https = (
            page_data.url_final.casefold()
            .startswith("https://")
        )

        canonical_http = (
            canonical.casefold()
            .startswith("http://")
        )

        if pagina_https and canonical_http:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página utiliza HTTPS, mas o canonical "
                    "aponta para uma URL HTTP."
                ),
                dados={
                    "url_pagina": page_data.url_final,
                    "canonical": canonical,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url_pagina": page_data.url_final,
                "canonical": canonical,
            },
        )


class SelfCanonicalCheck(BaseCheck):
    nome = "Canonical - URL autorreferente"
    categoria = "SEO Técnico"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        canonical = normalizar_url_comparacao(
            page_data.canonical
        )

        url_final = normalizar_url_comparacao(
            page_data.url_final
        )

        if not canonical:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página não possui canonical."
                ),
                dados={
                    "url_final": url_final,
                    "canonical": "",
                },
            )

        if canonical != url_final:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O canonical aponta para uma URL diferente "
                    "da página auditada. Revise se isso é "
                    "intencional."
                ),
                dados={
                    "url_final": url_final,
                    "canonical": canonical,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url_final": url_final,
                "canonical": canonical,
                "requer_revisao_manual": False,
            },
        )