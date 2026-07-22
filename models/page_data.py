from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PageData:
    """
    Representa os dados coletados de uma página.

    Centraliza informações utilizadas pelos checks de SEO,
    segurança, formulários, conteúdo, imagens e layout.
    """

    url_solicitada: str
    url_final: str
    status_http: int | None

    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    lang: str = ""

    h1: list[str] = field(
        default_factory=list
    )

    h2: list[str] = field(
        default_factory=list
    )

    images: list[dict[str, Any]] = field(
        default_factory=list
    )

    background_images: list[
        dict[str, Any]
    ] = field(
        default_factory=list
    )

    links: list[dict[str, Any]] = field(
        default_factory=list
    )

    forms: list[dict[str, Any]] = field(
        default_factory=list
    )

    scripts: list[dict[str, Any]] = field(
        default_factory=list
    )

    schemas: list[dict[str, Any]] = field(
        default_factory=list
    )

    resources: list[dict[str, Any]] = field(
        default_factory=list
    )

    response_headers: dict[str, str] = field(
        default_factory=dict
    )

    html: str = ""

    def to_dict(
        self,
        include_html: bool = False,
    ) -> dict[str, Any]:
        """
        Converte o PageData em dicionário.

        Por padrão, não inclui o HTML completo para evitar
        que o relatório JSON fique excessivamente grande.
        """
        dados = asdict(
            self
        )

        dados["html_length"] = len(
            self.html
        )

        if not include_html:
            dados.pop(
                "html",
                None,
            )

        return dados