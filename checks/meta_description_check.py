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


class MetaDescriptionMissingCheck(BaseCheck):
    nome = "Meta Descriptions - Missing"
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

        descricao = page_data.meta_description.strip()

        if not descricao:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página não possui Meta Description "
                    "ou o conteúdo está vazio."
                ),
                dados={
                    "meta_description": "",
                    "quantidade_caracteres": 0,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "meta_description": descricao,
                "quantidade_caracteres": len(descricao),
            },
        )


class MetaDescriptionOverCharactersCheck(BaseCheck):
    nome = "Meta Descriptions - Over 160 caracteres"
    categoria = "SEO"

    LIMITE = 160

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

        descricao = page_data.meta_description.strip()
        quantidade = len(descricao)

        if quantidade > self.LIMITE:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"A Meta Description possui {quantidade} caracteres. "
                    f"O limite configurado é {self.LIMITE}."
                ),
                dados={
                    "meta_description": descricao,
                    "quantidade_caracteres": quantidade,
                    "limite": self.LIMITE,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "meta_description": descricao,
                "quantidade_caracteres": quantidade,
                "limite": self.LIMITE,
            },
        )