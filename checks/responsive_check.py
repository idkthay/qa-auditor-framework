from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from config.settings import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MOBILE,
    VIEWPORT_TABLET,
)
from services.responsive_service import (
    executar_validacao_responsiva,
)


def obter_problemas_responsivos(
    resultado: dict[str, Any],
) -> list[str]:
    problemas: list[str] = []

    analise = resultado.get(
        "analise",
        {},
    )

    if not resultado.get(
        "sucesso",
        False,
    ):
        erro = resultado.get(
            "erro",
            "Erro não identificado.",
        )

        return [
            (
                "Não foi possível executar "
                f"a validação responsiva: {erro}"
            )
        ]

    if analise.get(
        "possui_overflow_horizontal",
        False,
    ):
        documento = analise.get(
            "documento",
            {},
        )

        diferenca = documento.get(
            "diferenca_horizontal",
            0,
        )

        problemas.append(
            (
                "A página possui rolagem horizontal. "
                f"O conteúdo ultrapassa a viewport "
                f"em aproximadamente {diferenca}px."
            )
        )

    elementos_overflow = analise.get(
        "elementos_overflow",
        [],
    )

    if elementos_overflow:
        problemas.append(
            (
                f"{len(elementos_overflow)} elemento(s) "
                "ultrapassam os limites da tela."
            )
        )

    imagens = analise.get(
        "imagens",
        {},
    )

    quantidade_imagens = imagens.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_imagens:
        problemas.append(
            (
                f"{quantidade_imagens} imagem(ns) "
                "ultrapassam a largura da viewport."
            )
        )

    formularios = analise.get(
        "formularios",
        {},
    )

    quantidade_formularios = formularios.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_formularios:
        problemas.append(
            (
                f"{quantidade_formularios} formulário(s) "
                "ultrapassam a largura da viewport."
            )
        )

    mapas = analise.get(
        "mapas",
        {},
    )

    quantidade_mapas = mapas.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_mapas:
        problemas.append(
            (
                f"{quantidade_mapas} mapa(s) ou "
                "elemento(s) relacionado(s) ao mapa "
                "ultrapassam a largura da viewport."
            )
        )

    iframes = analise.get(
        "iframes",
        {},
    )

    quantidade_iframes = iframes.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_iframes:
        problemas.append(
            (
                f"{quantidade_iframes} iframe(s) "
                "ultrapassam a largura da viewport."
            )
        )

    footers = analise.get(
        "footers",
        {},
    )

    if not analise.get(
        "footer_encontrado",
        False,
    ):
        problemas.append(
            "Não foi encontrado um footer na página."
        )

    quantidade_footers = footers.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_footers:
        problemas.append(
            (
                f"{quantidade_footers} elemento(s) "
                "do footer ultrapassam a largura "
                "da viewport."
            )
        )

    tabelas = analise.get(
        "tabelas",
        {},
    )

    quantidade_tabelas = tabelas.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_tabelas:
        problemas.append(
            (
                f"{quantidade_tabelas} tabela(s) "
                "ultrapassam a largura da viewport."
            )
        )

    videos = analise.get(
        "videos",
        {},
    )

    quantidade_videos = videos.get(
        "quantidade_problematicos",
        0,
    )

    if quantidade_videos:
        problemas.append(
            (
                f"{quantidade_videos} vídeo(s) "
                "ultrapassam a largura da viewport."
            )
        )

    return problemas


def criar_dados_resultado(
    resultado: dict[str, Any],
    problemas: list[str],
) -> dict[str, Any]:
    screenshot = resultado.get(
        "screenshot",
        "",
    )

    evidencias = []

    if screenshot:
        evidencias.append(
            screenshot
        )

    return {
        "viewport": {
            "nome": resultado.get(
                "nome_viewport",
                "",
            ),
            "largura": resultado.get(
                "largura",
                0,
            ),
            "altura": resultado.get(
                "altura",
                0,
            ),
        },
        "problemas": problemas,
        "analise": resultado.get(
            "analise",
            {},
        ),
        "screenshot": screenshot,
        "evidencias": evidencias,
    }


class ResponsiveDesktopCheck(
    BaseCheck
):
    nome = "Responsividade - Desktop 1920px"
    categoria = "Layout e Usabilidade"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        resultado = executar_validacao_responsiva(
            page=page,
            nome_viewport="desktop",
            largura=VIEWPORT_DESKTOP[
                "width"
            ],
            altura=VIEWPORT_DESKTOP[
                "height"
            ],
        )

        problemas = obter_problemas_responsivos(
            resultado
        )

        dados = criar_dados_resultado(
            resultado=resultado,
            problemas=problemas,
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                "A página não apresentou problemas "
                "automáticos de responsividade em "
                "1920px."
            ),
            dados=dados,
        )


class ResponsiveMobile394Check(
    BaseCheck
):
    nome = "Responsividade - Mobile 394px"
    categoria = "Layout e Usabilidade"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        resultado = executar_validacao_responsiva(
            page=page,
            nome_viewport="mobile",
            largura=VIEWPORT_MOBILE[
                "width"
            ],
            altura=VIEWPORT_MOBILE[
                "height"
            ],
        )

        problemas = obter_problemas_responsivos(
            resultado
        )

        dados = criar_dados_resultado(
            resultado=resultado,
            problemas=problemas,
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                "A página não apresentou problemas "
                "automáticos de responsividade em "
                "394px."
            ),
            dados=dados,
        )


class ResponsiveTablet768Check(
    BaseCheck
):
    nome = "Responsividade - Tablet 768px"
    categoria = "Layout e Usabilidade"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        resultado = executar_validacao_responsiva(
            page=page,
            nome_viewport="tablet",
            largura=VIEWPORT_TABLET[
                "width"
            ],
            altura=VIEWPORT_TABLET[
                "height"
            ],
        )

        problemas = obter_problemas_responsivos(
            resultado
        )

        dados = criar_dados_resultado(
            resultado=resultado,
            problemas=problemas,
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                "A página não apresentou problemas "
                "automáticos de responsividade em "
                "768px."
            ),
            dados=dados,
        )