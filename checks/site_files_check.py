from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData
from services.site_files_validator import (
    buscar_arquivo,
    buscar_robots,
    buscar_sitemap_padrao,
    extrair_sitemaps_robots,
    possui_bloqueio_global,
    validar_xml_sitemap,
)


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get("page_data")

    if isinstance(page_data, PageData):
        return page_data

    return None


class RobotsTxtCheck(BaseCheck):
    nome = "Robots.txt - Existência"
    categoria = "SEO Técnico"

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

        resultado = buscar_robots(
            page_data.url_final
        )

        dados = resultado.to_dict()

        dados["conteudo"] = (
            resultado.conteudo[:2000]
        )

        if not resultado.acessivel:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O arquivo robots.txt não está acessível. "
                    f"Status: {resultado.status_http}. "
                    f"Erro: {resultado.erro or 'nenhum'}"
                ),
                dados=dados,
            )

        conteudo_normalizado = (
            resultado.conteudo.casefold()
        )

        if "<html" in conteudo_normalizado:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A URL robots.txt retornou conteúdo HTML. "
                    "Pode ser uma página de erro personalizada."
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            dados=dados,
        )


class RobotsGlobalBlockCheck(BaseCheck):
    nome = "Robots.txt - Bloqueio global"
    categoria = "SEO Técnico"

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

        resultado = buscar_robots(
            page_data.url_final
        )

        if not resultado.acessivel:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi possível verificar o bloqueio "
                    "porque o robots.txt não está acessível."
                ),
                dados=resultado.to_dict(),
            )

        bloqueio_global = possui_bloqueio_global(
            resultado.conteudo
        )

        if bloqueio_global:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foi encontrado User-agent: * com "
                    "Disallow: /. O site pode estar bloqueado "
                    "para mecanismos de busca."
                ),
                dados={
                    "bloqueio_global": True,
                    "url_robots": resultado.url_final,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "bloqueio_global": False,
                "url_robots": resultado.url_final,
            },
        )


class RobotsSitemapDeclarationCheck(BaseCheck):
    nome = "Robots.txt - Sitemap declarado"
    categoria = "SEO Técnico"

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

        resultado = buscar_robots(
            page_data.url_final
        )

        if not resultado.acessivel:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Não foi possível procurar o sitemap "
                    "porque o robots.txt não está acessível."
                ),
                dados=resultado.to_dict(),
            )

        sitemaps = extrair_sitemaps_robots(
            resultado.conteudo
        )

        if not sitemaps:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhuma diretiva Sitemap foi encontrada "
                    "no robots.txt."
                ),
                dados={
                    "quantidade": 0,
                    "sitemaps": [],
                },
            )

        sitemaps_invalidos = []

        for sitemap in sitemaps:
            resultado_sitemap = buscar_arquivo(
                sitemap
            )

            if not resultado_sitemap.acessivel:
                sitemaps_invalidos.append(
                    {
                        "url": sitemap,
                        "status_http": (
                            resultado_sitemap.status_http
                        ),
                        "erro": (
                            resultado_sitemap.erro
                        ),
                    }
                )

        if sitemaps_invalidos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O robots.txt declara sitemap, mas um ou "
                    "mais arquivos não estão acessíveis."
                ),
                dados={
                    "quantidade": len(sitemaps),
                    "sitemaps": sitemaps,
                    "sitemaps_invalidos": (
                        sitemaps_invalidos
                    ),
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": len(sitemaps),
                "sitemaps": sitemaps,
                "sitemaps_invalidos": [],
            },
        )


class SitemapXmlCheck(BaseCheck):
    nome = "Sitemap XML - Validade"
    categoria = "SEO Técnico"

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

        robots = buscar_robots(
            page_data.url_final
        )

        sitemaps_declarados = []

        if robots.acessivel:
            sitemaps_declarados = (
                extrair_sitemaps_robots(
                    robots.conteudo
                )
            )

        if sitemaps_declarados:
            urls_sitemap = sitemaps_declarados

        else:
            sitemap_padrao = buscar_sitemap_padrao(
                page_data.url_final
            )

            urls_sitemap = [
                sitemap_padrao.url
            ]

        resultados = []
        sitemaps_invalidos = []

        for url_sitemap in urls_sitemap:
            arquivo = buscar_arquivo(
                url_sitemap
            )

            validacao = validar_xml_sitemap(
                arquivo.conteudo
            )

            registro = {
                "url": url_sitemap,
                "url_final": arquivo.url_final,
                "status_http": arquivo.status_http,
                "acessivel": arquivo.acessivel,
                "content_type": arquivo.content_type,
                "xml_valido": validacao["valido"],
                "tipo": validacao["tipo"],
                "quantidade_urls": (
                    validacao["quantidade_urls"]
                ),
                "erro": (
                    arquivo.erro
                    or validacao["erro"]
                ),
            }

            resultados.append(registro)

            if (
                not arquivo.acessivel
                or not validacao["valido"]
                or validacao["quantidade_urls"] == 0
            ):
                sitemaps_invalidos.append(
                    registro
                )

        if sitemaps_invalidos:
            observacoes = []

            for item in sitemaps_invalidos:
                observacoes.append(
                    (
                        f'{item["url"]} — '
                        f'status {item["status_http"]}, '
                        f'URLs: {item["quantidade_urls"]}, '
                        f'erro: {item["erro"] or "nenhum"}'
                    )
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados problemas no sitemap:\n"
                    + "\n".join(observacoes)
                ),
                dados={
                    "quantidade_sitemaps": len(
                        resultados
                    ),
                    "resultados": resultados,
                    "invalidos": sitemaps_invalidos,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_sitemaps": len(
                    resultados
                ),
                "resultados": resultados,
                "invalidos": [],
            },
        )