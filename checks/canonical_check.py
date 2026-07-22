from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


class CanonicalMissingCheck(BaseCheck):
    nome = "Canonical - Missing"
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

        canonical = page_data.canonical.strip()

        if not canonical:
            return self.resultado(
                status="rejected",
                observacao="A página não possui Canonical.",
                dados={
                    "canonical": "",
                },
            )

        canonical_absoluto = urljoin(
            page_data.url_final,
            canonical,
        )

        return self.resultado(
            status="approved",
            dados={
                "canonical": canonical_absoluto,
            },
        )