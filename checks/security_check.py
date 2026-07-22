from typing import Any
from urllib.parse import urlparse

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


def obter_header(
    page_data: PageData,
    nome: str,
) -> str:
    return page_data.response_headers.get(
        nome.lower(),
        "",
    ).strip()


class MixedContentCheck(BaseCheck):
    nome = "Mixed Content HTTP/HTTPS"
    categoria = "Segurança"

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

        protocolo_pagina = urlparse(
            page_data.url_final
        ).scheme.lower()

        if protocolo_pagina != "https":
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página principal não utiliza HTTPS."
                ),
                dados={
                    "url": page_data.url_final,
                    "recursos_http": [],
                },
            )

        recursos_http = []

        for recurso in page_data.resources:
            url_recurso = str(
                recurso.get("url_absoluta", "")
            ).strip()

            if url_recurso.lower().startswith("http://"):
                recursos_http.append(
                    {
                        "tag": recurso.get("tag", ""),
                        "url": url_recurso,
                    }
                )

        if recursos_http:
            urls = [
                recurso["url"]
                for recurso in recursos_http
            ]

            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados {len(recursos_http)} "
                    "recursos carregados por HTTP:\n"
                    + "\n".join(urls)
                ),
                dados={
                    "quantidade": len(recursos_http),
                    "recursos_http": recursos_http,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "recursos_http": [],
            },
        )


class HttpsUrlsCheck(BaseCheck):
    nome = "HTTPS URL’s (100% das URLs)"
    categoria = "Segurança"

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

        protocolo = urlparse(
            page_data.url_final
        ).scheme.lower()

        if protocolo != "https":
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página não está sendo carregada por HTTPS."
                ),
                dados={
                    "url": page_data.url_final,
                    "protocolo": protocolo,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url": page_data.url_final,
                "protocolo": protocolo,
            },
        )


class MissingHstsCheck(BaseCheck):
    nome = "Missing HSTS"
    categoria = "Segurança"

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

        valor = obter_header(
            page_data,
            "strict-transport-security",
        )

        if not valor:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O header Strict-Transport-Security "
                    "não foi encontrado."
                ),
                dados={"header": ""},
            )

        return self.resultado(
            status="approved",
            dados={"header": valor},
        )


class MissingXFrameOptionsCheck(BaseCheck):
    nome = "Missing X Frame Options"
    categoria = "Segurança"

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

        x_frame = obter_header(
            page_data,
            "x-frame-options",
        )

        csp = obter_header(
            page_data,
            "content-security-policy",
        )

        possui_frame_ancestors = (
            "frame-ancestors" in csp.lower()
        )

        if not x_frame and not possui_frame_ancestors:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi encontrado X-Frame-Options "
                    "nem a diretiva frame-ancestors no CSP."
                ),
                dados={
                    "x_frame_options": "",
                    "frame_ancestors_csp": False,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "x_frame_options": x_frame,
                "frame_ancestors_csp": possui_frame_ancestors,
            },
        )


class MissingReferrerPolicyCheck(BaseCheck):
    nome = "Missing Secure Referrer Policy"
    categoria = "Segurança"

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

        valor = obter_header(
            page_data,
            "referrer-policy",
        )

        if not valor:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O header Referrer-Policy "
                    "não foi encontrado."
                ),
                dados={"header": ""},
            )

        return self.resultado(
            status="approved",
            dados={"header": valor},
        )


class MissingContentSecurityPolicyCheck(BaseCheck):
    nome = "Missing Content Security Policy"
    categoria = "Segurança"

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

        valor = obter_header(
            page_data,
            "content-security-policy",
        )

        if not valor:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O header Content-Security-Policy "
                    "não foi encontrado."
                ),
                dados={"header": ""},
            )

        return self.resultado(
            status="approved",
            dados={"header": valor},
        )


class MissingXContentTypeOptionsCheck(BaseCheck):
    nome = "Missing X Content Type Options"
    categoria = "Segurança"

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

        valor = obter_header(
            page_data,
            "x-content-type-options",
        )

        if not valor:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O header X-Content-Type-Options "
                    "não foi encontrado."
                ),
                dados={"header": ""},
            )

        if valor.casefold() != "nosniff":
            return self.resultado(
                status="rejected",
                observacao=(
                    "O header X-Content-Type-Options existe, "
                    f"mas possui o valor '{valor}' em vez de "
                    "'nosniff'."
                ),
                dados={"header": valor},
            )

        return self.resultado(
            status="approved",
            dados={"header": valor},
        )