from typing import Any

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


class ResponseSuccessCheck(BaseCheck):
    nome = "Response Codes - Success"
    categoria = "Response Codes"

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

        status_http = page_data.status_http

        if status_http is None:
            return self.resultado(
                status="error",
                observacao="Não foi possível identificar o status HTTP.",
            )

        if 200 <= status_http < 300:
            return self.resultado(
                status="approved",
                dados={"status_http": status_http},
            )

        return self.resultado(
            status="rejected",
            observacao=(
                "A página não retornou um código de sucesso. "
                f"Status identificado: {status_http}."
            ),
            dados={"status_http": status_http},
        )


class ResponseRedirectionCheck(BaseCheck):
    nome = "Response Codes - Redirection"
    categoria = "Response Codes"

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

        url_solicitada = page_data.url_solicitada
        url_final = page_data.url_final

        if not url_solicitada or not url_final:
            return self.resultado(
                status="error",
                observacao=(
                    "Não foi possível comparar a URL solicitada "
                    "com a URL final."
                ),
            )

        if url_solicitada != url_final:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A URL foi redirecionada.\n"
                    f"Origem: {url_solicitada}\n"
                    f"Destino: {url_final}"
                ),
                dados={
                    "url_origem": url_solicitada,
                    "url_destino": url_final,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url_origem": url_solicitada,
                "url_destino": url_final,
            },
        )


class ResponseClientErrorCheck(BaseCheck):
    nome = "Response Codes - Client Error"
    categoria = "Response Codes"

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

        status_http = page_data.status_http

        if status_http is None:
            return self.resultado(
                status="error",
                observacao="Não foi possível identificar o status HTTP.",
            )

        if 400 <= status_http < 500:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"A página retornou erro de cliente HTTP {status_http}."
                ),
                dados={"status_http": status_http},
            )

        return self.resultado(
            status="approved",
            dados={"status_http": status_http},
        )


class ResponseServerErrorCheck(BaseCheck):
    nome = "Response Codes - Server Error"
    categoria = "Response Codes"

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

        status_http = page_data.status_http

        if status_http is None:
            return self.resultado(
                status="error",
                observacao="Não foi possível identificar o status HTTP.",
            )

        if 500 <= status_http < 600:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"A página retornou erro de servidor HTTP {status_http}."
                ),
                dados={"status_http": status_http},
            )

        return self.resultado(
            status="approved",
            dados={"status_http": status_http},
        )