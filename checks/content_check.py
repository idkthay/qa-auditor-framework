from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


class LoremIpsumCheck(BaseCheck):
    nome = "Lorem Ipsum"
    categoria = "Conteúdo"

    TERMOS = (
        "lorem ipsum",
        "dolor sit amet",
        "consectetur adipiscing elit",
    )

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = contexto.get("page_data")

        if not isinstance(page_data, PageData):
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        html_normalizado = page_data.html.casefold()

        termos_encontrados = [
            termo
            for termo in self.TERMOS
            if termo in html_normalizado
        ]

        if termos_encontrados:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foi encontrado conteúdo de preenchimento: "
                    + ", ".join(termos_encontrados)
                ),
                dados={
                    "termos_encontrados": termos_encontrados,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "termos_encontrados": [],
            },
        )