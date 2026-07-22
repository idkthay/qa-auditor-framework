from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


TIPOS_ORGANIZACAO = {
    "organization",
    "localbusiness",
    "corporation",
    "professionalservice",
    "store",
}

TIPOS_CONTEUDO = {
    "article",
    "blogposting",
    "newsarticle",
    "techarticle",
}


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get("page_data")

    if isinstance(page_data, PageData):
        return page_data

    return None


def normalizar_tipo_schema(
    valor: Any,
) -> list[str]:
    """
    Converte o valor de @type em uma lista normalizada.

    O @type pode ser:
    - string;
    - lista de strings;
    - valor ausente.
    """
    if isinstance(valor, str):
        valor_limpo = valor.strip()

        return [valor_limpo] if valor_limpo else []

    if isinstance(valor, list):
        tipos = []

        for item in valor:
            if isinstance(item, str) and item.strip():
                tipos.append(item.strip())

        return tipos

    return []


def percorrer_objetos_schema(
    conteudo: Any,
) -> list[dict[str, Any]]:
    """
    Percorre recursivamente objetos JSON-LD.

    Isso permite encontrar tipos dentro de:
    - @graph;
    - mainEntity;
    - itemListElement;
    - objetos aninhados;
    - listas.
    """
    objetos: list[dict[str, Any]] = []

    if isinstance(conteudo, dict):
        objetos.append(conteudo)

        for valor in conteudo.values():
            objetos.extend(
                percorrer_objetos_schema(valor)
            )

    elif isinstance(conteudo, list):
        for item in conteudo:
            objetos.extend(
                percorrer_objetos_schema(item)
            )

    return objetos


def coletar_tipos_schema(
    page_data: PageData,
) -> list[str]:
    tipos: list[str] = []

    for schema in page_data.schemas:
        if not schema.get("valido", False):
            continue

        conteudo = schema.get("conteudo")

        for objeto in percorrer_objetos_schema(
            conteudo
        ):
            tipos.extend(
                normalizar_tipo_schema(
                    objeto.get("@type")
                )
            )

    return list(dict.fromkeys(tipos))


def possui_tipo_schema(
    tipos_encontrados: list[str],
    tipos_esperados: set[str],
) -> bool:
    tipos_normalizados = {
        tipo.casefold()
        for tipo in tipos_encontrados
    }

    return bool(
        tipos_normalizados.intersection(
            tipos_esperados
        )
    )


class HtmlLangCheck(BaseCheck):
    nome = "HTML - Idioma da página"
    categoria = "AEO/GEO"

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

        idioma = page_data.lang.strip()

        if not idioma:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O elemento HTML não possui o atributo lang."
                ),
                dados={
                    "lang": "",
                },
            )

        idioma_normalizado = idioma.casefold()

        idiomas_portugues = {
            "pt",
            "pt-br",
            "pt_br",
        }

        if idioma_normalizado not in idiomas_portugues:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O idioma da página foi identificado como "
                    f"'{idioma}'. Revise se está correto para "
                    "o conteúdo publicado."
                ),
                dados={
                    "lang": idioma,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "lang": idioma,
                "requer_revisao_manual": False,
            },
        )


class StructuredDataPresenceCheck(BaseCheck):
    nome = "Dados estruturados - Presença"
    categoria = "AEO/GEO"

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

        quantidade = len(page_data.schemas)

        if quantidade == 0:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum bloco JSON-LD foi encontrado na página."
                ),
                dados={
                    "quantidade": 0,
                    "tipos": [],
                },
            )

        tipos = coletar_tipos_schema(
            page_data
        )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": quantidade,
                "tipos": tipos,
            },
        )


class StructuredDataValidityCheck(BaseCheck):
    nome = "Dados estruturados - JSON-LD válido"
    categoria = "AEO/GEO"

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

        schemas_invalidos = []

        for indice, schema in enumerate(
            page_data.schemas
        ):
            if schema.get("valido", False):
                continue

            schemas_invalidos.append(
                {
                    "indice": indice + 1,
                    "erro": schema.get(
                        "erro",
                        "Erro de JSON não identificado.",
                    ),
                    "conteudo": str(
                        schema.get("conteudo", "")
                    )[:500],
                }
            )

        if schemas_invalidos:
            observacoes = []

            for item in schemas_invalidos:
                observacoes.append(
                    (
                        f'Bloco {item["indice"]}: '
                        f'{item["erro"]}'
                    )
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados blocos JSON-LD "
                    "com erro de sintaxe:\n"
                    + "\n".join(observacoes)
                ),
                dados={
                    "quantidade_invalidos": len(
                        schemas_invalidos
                    ),
                    "schemas_invalidos": schemas_invalidos,
                },
            )

        if not page_data.schemas:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não existem blocos JSON-LD para validar."
                ),
                dados={
                    "quantidade_invalidos": 0,
                    "schemas_invalidos": [],
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_invalidos": 0,
                "schemas_invalidos": [],
            },
        )


class OrganizationSchemaCheck(BaseCheck):
    nome = "Schema - Organization ou LocalBusiness"
    categoria = "GEO"

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

        tipos = coletar_tipos_schema(
            page_data
        )

        possui_schema = possui_tipo_schema(
            tipos,
            TIPOS_ORGANIZACAO,
        )

        if not possui_schema:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi encontrado schema Organization, "
                    "LocalBusiness ou tipo equivalente."
                ),
                dados={
                    "tipos_encontrados": tipos,
                    "tipos_esperados": sorted(
                        TIPOS_ORGANIZACAO
                    ),
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "tipos_encontrados": tipos,
                "requer_revisao_manual": False,
            },
        )


class WebsiteSchemaCheck(BaseCheck):
    nome = "Schema - WebSite"
    categoria = "AEO/GEO"

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

        tipos = coletar_tipos_schema(
            page_data
        )

        if not possui_tipo_schema(
            tipos,
            {"website"},
        ):
            return self.resultado(
                status="rejected",
                observacao=(
                    "O schema WebSite não foi encontrado."
                ),
                dados={
                    "tipos_encontrados": tipos,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "tipos_encontrados": tipos,
                "requer_revisao_manual": False,
            },
        )


class BreadcrumbSchemaCheck(BaseCheck):
    nome = "Schema - BreadcrumbList"
    categoria = "SEO/AEO"

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

        tipos = coletar_tipos_schema(
            page_data
        )

        possui_breadcrumb = possui_tipo_schema(
            tipos,
            {"breadcrumblist"},
        )

        if not possui_breadcrumb:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O schema BreadcrumbList não foi encontrado. "
                    "Na página inicial, este item pode não ser "
                    "necessário."
                ),
                dados={
                    "tipos_encontrados": tipos,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "tipos_encontrados": tipos,
                "requer_revisao_manual": False,
            },
        )


class FaqSchemaCheck(BaseCheck):
    nome = "Schema - FAQPage"
    categoria = "AEO"

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

        tipos = coletar_tipos_schema(
            page_data
        )

        possui_faq = possui_tipo_schema(
            tipos,
            {"faqpage"},
        )

        html_normalizado = page_data.html.casefold()

        indicadores_faq = (
            "perguntas frequentes",
            "perguntas e respostas",
            "faq",
            "dúvidas frequentes",
            "duvidas frequentes",
        )

        possui_indicio_faq = any(
            termo in html_normalizado
            for termo in indicadores_faq
        )

        if possui_indicio_faq and not possui_faq:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A página aparenta possuir uma seção de "
                    "perguntas frequentes, mas o schema FAQPage "
                    "não foi encontrado."
                ),
                dados={
                    "possui_indicio_faq": True,
                    "possui_schema_faq": False,
                    "tipos_encontrados": tipos,
                },
            )

        if not possui_faq:
            return self.resultado(
                status="approved",
                observacao=(
                    "Nenhuma seção clara de FAQ foi detectada. "
                    "O schema FAQPage pode não ser necessário "
                    "nesta página."
                ),
                dados={
                    "possui_indicio_faq": False,
                    "possui_schema_faq": False,
                    "tipos_encontrados": tipos,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "possui_indicio_faq": possui_indicio_faq,
                "possui_schema_faq": True,
                "tipos_encontrados": tipos,
                "requer_revisao_manual": False,
            },
        )


class ArticleSchemaCheck(BaseCheck):
    nome = "Schema - Article ou BlogPosting"
    categoria = "AEO/GEO"

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

        tipos = coletar_tipos_schema(
            page_data
        )

        possui_schema_artigo = possui_tipo_schema(
            tipos,
            TIPOS_CONTEUDO,
        )

        url_normalizada = page_data.url_final.casefold()

        indicadores_url_artigo = (
            "/blog/",
            "/noticia/",
            "/noticias/",
            "/artigo/",
            "/artigos/",
        )

        aparenta_ser_artigo = any(
            indicador in url_normalizada
            for indicador in indicadores_url_artigo
        )

        if aparenta_ser_artigo and not possui_schema_artigo:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A URL aparenta ser de artigo ou notícia, "
                    "mas não possui schema Article, BlogPosting "
                    "ou tipo equivalente."
                ),
                dados={
                    "aparenta_ser_artigo": True,
                    "possui_schema_artigo": False,
                    "tipos_encontrados": tipos,
                },
            )

        if not possui_schema_artigo:
            return self.resultado(
                status="approved",
                observacao=(
                    "A página não aparenta ser um artigo. "
                    "O schema Article pode não ser necessário."
                ),
                dados={
                    "aparenta_ser_artigo": aparenta_ser_artigo,
                    "possui_schema_artigo": False,
                    "tipos_encontrados": tipos,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "aparenta_ser_artigo": aparenta_ser_artigo,
                "possui_schema_artigo": True,
                "tipos_encontrados": tipos,
                "requer_revisao_manual": False,
            },
        )