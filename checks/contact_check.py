import re
from typing import Any
from urllib.parse import unquote, urlparse

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


PADRAO_EMAIL = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get("page_data")

    if isinstance(page_data, PageData):
        return page_data

    return None


def obter_href_original(
    link: dict[str, Any],
) -> str:
    return str(
        link.get("href_original", "")
    ).strip()


def obter_href_absoluto(
    link: dict[str, Any],
) -> str:
    return str(
        link.get("href", "")
    ).strip()


def obter_texto_link(
    link: dict[str, Any],
) -> str:
    return str(
        link.get("texto", "")
    ).strip()


def normalizar_texto_pagina(
    texto: str,
) -> str:
    return (
        unquote(texto)
        .casefold()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .replace(".php", " ")
        .replace(".html", " ")
    )


def eh_pagina_contato(
    page_data: PageData,
) -> bool:
    """
    Identifica se a página atual é uma página de contato.

    A identificação considera:
    - caminho da URL;
    - título da página;
    - textos dos H1.
    """
    termos_contato = (
        "contato",
        "contact",
        "fale conosco",
        "fale com a gente",
        "entre em contato",
    )

    url = (
        page_data.url_final
        or page_data.url_solicitada
        or ""
    )

    caminho_url = urlparse(url).path

    caminho_normalizado = normalizar_texto_pagina(
        caminho_url
    )

    if any(
        termo in caminho_normalizado
        for termo in termos_contato
    ):
        return True

    titulo_normalizado = normalizar_texto_pagina(
        page_data.title or ""
    )

    if any(
        termo in titulo_normalizado
        for termo in termos_contato
    ):
        return True

    h1_normalizado = normalizar_texto_pagina(
        " ".join(page_data.h1)
    )

    if any(
        termo in h1_normalizado
        for termo in termos_contato
    ):
        return True

    return False


def identificar_links_whatsapp(
    page_data: PageData,
) -> list[dict[str, str]]:
    resultados = []

    termos_whatsapp = (
        "wa.me/",
        "api.whatsapp.com/",
        "web.whatsapp.com/",
        "whatsapp://",
    )

    for link in page_data.links:
        href = obter_href_absoluto(link)
        href_original = obter_href_original(link)

        url_analisada = (
            href_original or href
        ).casefold()

        if any(
            termo in url_analisada
            for termo in termos_whatsapp
        ):
            resultados.append(
                {
                    "url": href_original or href,
                    "texto": obter_texto_link(link),
                }
            )

    return resultados


class WhatsappButtonCheck(BaseCheck):
    nome = "CTA - Botão WhatsApp"
    categoria = "Contatos"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        links_whatsapp = identificar_links_whatsapp(
            page_data
        )

        if not links_whatsapp:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum link de WhatsApp foi encontrado "
                    "na página."
                ),
                dados={
                    "quantidade": 0,
                    "links": [],
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": len(
                    links_whatsapp
                ),
                "links": links_whatsapp,
                "requer_revisao_manual": False,
            },
        )


class MailtoLinksCheck(BaseCheck):
    nome = "Emails clicáveis e funcionais (mailto:)"
    categoria = "Contatos"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        links_mailto = []
        links_invalidos = []

        for link in page_data.links:
            href = obter_href_original(link)

            if not href.casefold().startswith(
                "mailto:"
            ):
                continue

            email = (
                href[7:]
                .split("?")[0]
                .strip()
            )

            registro = {
                "href": href,
                "email": email,
                "texto": obter_texto_link(
                    link
                ),
            }

            links_mailto.append(
                registro
            )

            if not PADRAO_EMAIL.match(email):
                links_invalidos.append(
                    registro
                )

        if links_invalidos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados links mailto "
                    "inválidos:\n"
                    + "\n".join(
                        item["href"]
                        for item in links_invalidos
                    )
                ),
                dados={
                    "quantidade_mailto": len(
                        links_mailto
                    ),
                    "invalidos": links_invalidos,
                },
            )

        if not links_mailto:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum link de e-mail com mailto: "
                    "foi encontrado."
                ),
                dados={
                    "quantidade_mailto": 0,
                    "invalidos": [],
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_mailto": len(
                    links_mailto
                ),
                "links": links_mailto,
                "invalidos": [],
            },
        )


class TelephoneLinksCheck(BaseCheck):
    nome = "Links de contatos clicáveis e funcionais"
    categoria = "Contatos"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        links_telefone = []
        links_invalidos = []

        for link in page_data.links:
            href = obter_href_original(link)

            if not href.casefold().startswith(
                "tel:"
            ):
                continue

            telefone_original = (
                href[4:].strip()
            )

            telefone_numerico = re.sub(
                r"\D",
                "",
                telefone_original,
            )

            registro = {
                "href": href,
                "telefone": telefone_original,
                "texto": obter_texto_link(
                    link
                ),
                "quantidade_digitos": len(
                    telefone_numerico
                ),
            }

            links_telefone.append(
                registro
            )

            if len(telefone_numerico) < 10:
                links_invalidos.append(
                    registro
                )

        if links_invalidos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados links de telefone "
                    "com poucos dígitos:\n"
                    + "\n".join(
                        item["href"]
                        for item in links_invalidos
                    )
                ),
                dados={
                    "quantidade_tel": len(
                        links_telefone
                    ),
                    "invalidos": links_invalidos,
                },
            )

        if not links_telefone:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum link de telefone com tel: "
                    "foi encontrado."
                ),
                dados={
                    "quantidade_tel": 0,
                    "invalidos": [],
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_tel": len(
                    links_telefone
                ),
                "links": links_telefone,
                "invalidos": [],
            },
        )


class GoogleMapsCheck(BaseCheck):
    nome = "Google Maps carregando e funcional"
    categoria = "Contatos"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        pagina_contato = eh_pagina_contato(
            page_data
        )

        if not pagina_contato:
            return self.resultado(
                status="approved",
                observacao=(
                    "Validação não aplicável. "
                    "O Google Maps é obrigatório somente "
                    "na página de contato."
                ),
                dados={
                    "aplicavel": False,
                    "pagina_contato": False,
                    "quantidade": 0,
                    "referencias": [],
                    "requer_revisao_manual": False,
                },
            )

        referencias_maps: list[
            dict[str, str]
        ] = []

        termos_maps = (
            "google.com/maps",
            "google.com.br/maps",
            "maps.google.",
            "maps.google.com",
            "maps.google.com.br",
            "goo.gl/maps",
            "maps.app.goo.gl",
            "googleusercontent.com/maps",
        )

        for link in page_data.links:
            href = obter_href_absoluto(
                link
            )

            href_normalizado = (
                href.casefold()
            )

            if any(
                termo in href_normalizado
                for termo in termos_maps
            ):
                referencias_maps.append(
                    {
                        "tipo": "link",
                        "url": href,
                        "texto": obter_texto_link(
                            link
                        ),
                    }
                )

        for recurso in page_data.resources:
            tag = str(
                recurso.get(
                    "tag",
                    "",
                )
            ).casefold()

            url = str(
                recurso.get(
                    "url_absoluta",
                    "",
                )
            ).strip()

            url_normalizada = (
                url.casefold()
            )

            if (
                tag == "iframe"
                and any(
                    termo in url_normalizada
                    for termo in termos_maps
                )
            ):
                referencias_maps.append(
                    {
                        "tipo": "iframe",
                        "url": url,
                        "texto": "",
                    }
                )

        referencias_maps = list(
            {
                (
                    item["tipo"],
                    item["url"],
                ): item
                for item in referencias_maps
            }.values()
        )

        if not referencias_maps:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página foi identificada como página "
                    "de contato, mas nenhum link ou iframe "
                    "do Google Maps foi encontrado."
                ),
                dados={
                    "aplicavel": True,
                    "pagina_contato": True,
                    "quantidade": 0,
                    "referencias": [],
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                "Google Maps encontrado na página "
                "de contato."
            ),
            dados={
                "aplicavel": True,
                "pagina_contato": True,
                "quantidade": len(
                    referencias_maps
                ),
                "referencias": referencias_maps,
                "requer_revisao_manual": False,
            },
        )


class InvalidHrefCheck(BaseCheck):
    nome = "Nenhum link ou botão quebrado (404/500)"
    categoria = "Links"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Identifica links claramente inválidos no HTML.

        A validação HTTP completa é realizada por outro check.
        """
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        links_invalidos = []

        valores_invalidos_exatos = {
            "",
            "#",
            "javascript:void(0)",
            "javascript:void(0);",
            "javascript:;",
        }

        for link in page_data.links:
            href = obter_href_original(
                link
            )

            href_normalizado = (
                href.casefold().strip()
            )

            invalido = (
                href_normalizado
                in valores_invalidos_exatos
                or href_normalizado.startswith(
                    "javascript:"
                )
            )

            if not invalido:
                continue

            links_invalidos.append(
                {
                    "href": href,
                    "texto": obter_texto_link(
                        link
                    ),
                }
            )

        if links_invalidos:
            observacoes = []

            for item in links_invalidos:
                texto = (
                    item["texto"]
                    or "Link sem texto"
                )

                observacoes.append(
                    f'{texto}: "{item["href"]}"'
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados links com href "
                    "vazio, # ou JavaScript:\n"
                    + "\n".join(
                        observacoes
                    )
                ),
                dados={
                    "quantidade": len(
                        links_invalidos
                    ),
                    "links": links_invalidos,
                    "validacao_http_completa": False,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "links": [],
                "validacao_http_completa": False,
            },
        )