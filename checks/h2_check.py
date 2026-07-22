from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


class H2MissingCheck(BaseCheck):
    nome = "H2 Missing"
    categoria = "SEO"

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

        h2 = [
            texto.strip()
            for texto in page_data.h2
            if texto.strip()
        ]

        if not h2:
            return self.resultado(
                status="rejected",
                observacao="Nenhum H2 foi encontrado na página.",
                dados={
                    "quantidade_h2": 0,
                    "h2": [],
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_h2": len(h2),
                "h2": h2,
            },
        )