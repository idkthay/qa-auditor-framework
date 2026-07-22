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


class H1MissingCheck(BaseCheck):
    nome = "H1 Missing"
    categoria = "SEO"

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

        h1 = [
            texto.strip()
            for texto in page_data.h1
            if texto.strip()
        ]

        if not h1:
            return self.resultado(
                status="rejected",
                observacao="Nenhum H1 foi encontrado na página.",
                dados={
                    "quantidade_h1": 0,
                    "h1": [],
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_h1": len(h1),
                "h1": h1,
            },
        )


class H1MultipleCheck(BaseCheck):
    nome = "H1 Multiple"
    categoria = "SEO"

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

        h1 = [
            texto.strip()
            for texto in page_data.h1
            if texto.strip()
        ]

        quantidade = len(h1)

        if quantidade > 1:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados {quantidade} elementos H1 "
                    "na página."
                ),
                dados={
                    "quantidade_h1": quantidade,
                    "h1": h1,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_h1": quantidade,
                "h1": h1,
            },
        )