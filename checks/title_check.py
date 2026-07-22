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


class TitleMissingCheck(BaseCheck):
    nome = "Page Titles - Missing"
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

        title = page_data.title.strip()

        if not title:
            return self.resultado(
                status="rejected",
                observacao="A página não possui Title.",
                dados={
                    "title": "",
                    "quantidade_caracteres": 0,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "title": title,
                "quantidade_caracteres": len(title),
            },
        )


class TitleOverCharactersCheck(BaseCheck):
    nome = "Page Titles - Over 60 caracteres"
    categoria = "SEO"

    LIMITE = 60

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

        title = page_data.title.strip()
        quantidade = len(title)

        if quantidade > self.LIMITE:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"O Title possui {quantidade} caracteres. "
                    f"O limite configurado é {self.LIMITE}."
                ),
                dados={
                    "title": title,
                    "quantidade_caracteres": quantidade,
                    "limite": self.LIMITE,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "title": title,
                "quantidade_caracteres": quantidade,
                "limite": self.LIMITE,
            },
        )