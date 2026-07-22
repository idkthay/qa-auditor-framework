from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData
from services.image_size_validator import (
    quantidade_imagens_em_cache,
    validar_tamanho_imagem,
)
from services.image_validator import (
    quantidade_imagens_validadas_em_cache,
    validar_imagem,
)


LIMITE_IMAGEM_BYTES = 200 * 1024
LIMITE_BANNER_BYTES = 500 * 1024

LIMITE_IMAGENS_POR_PAGINA = 100

TERMOS_BANNER = (
    "banner",
    "hero",
    "slider",
    "slide",
    "carousel",
    "destaque",
    "featured",
    "cover",
    "topo",
)


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get(
        "page_data"
    )

    if isinstance(
        page_data,
        PageData,
    ):
        return page_data

    return None


def obter_url_imagem(
    imagem: dict[str, Any],
) -> str:
    return str(
        imagem.get(
            "current_src"
        )
        or imagem.get(
            "src"
        )
        or "Imagem sem URL identificada"
    ).strip()


def obter_tamanho_performance(
    imagem: dict[str, Any],
) -> int:
    encoded = int(
        imagem.get(
            "encoded_body_size",
            0,
        )
        or 0
    )

    if encoded > 0:
        return encoded

    return int(
        imagem.get(
            "transfer_size",
            0,
        )
        or 0
    )


def calcular_proporcao(
    largura: int,
    altura: int,
) -> float:
    if altura <= 0:
        return 0

    return largura / altura


def eh_banner(
    imagem: dict[str, Any],
) -> bool:
    contexto = " ".join(
        [
            obter_url_imagem(
                imagem
            ),
            str(
                imagem.get(
                    "id",
                    "",
                )
            ),
            str(
                imagem.get(
                    "class_name",
                    "",
                )
            ),
            str(
                imagem.get(
                    "ancestor_hint",
                    "",
                )
            ),
        ]
    ).casefold()

    possui_termo_banner = any(
        termo in contexto
        for termo in TERMOS_BANNER
    )

    largura = int(
        imagem.get(
            "width",
            0,
        )
        or 0
    )

    altura = int(
        imagem.get(
            "height",
            0,
        )
        or 0
    )

    largura_natural = int(
        imagem.get(
            "natural_width",
            0,
        )
        or 0
    )

    altura_natural = int(
        imagem.get(
            "natural_height",
            0,
        )
        or 0
    )

    proporcao = calcular_proporcao(
        largura,
        altura,
    )

    proporcao_natural = calcular_proporcao(
        largura_natural,
        altura_natural,
    )

    if (
        possui_termo_banner
        and max(
            largura,
            largura_natural,
        ) >= 500
    ):
        return True

    if (
        largura >= 700
        and proporcao >= 2.1
    ):
        return True

    if (
        largura >= 600
        and largura_natural >= 1200
        and proporcao_natural >= 2.5
    ):
        return True

    return False


def coletar_imagens_para_peso(
    page_data: PageData,
) -> tuple[list[dict[str, Any]], int]:
    imagens = [
        *page_data.images,
        *page_data.background_images,
    ]

    imagens_unicas: dict[
        str,
        dict[str, Any],
    ] = {}

    for imagem in imagens:
        url = obter_url_imagem(
            imagem
        )

        if not url:
            continue

        if url == "Imagem sem URL identificada":
            continue

        if url.casefold().startswith(
            (
                "data:",
                "blob:",
            )
        ):
            continue

        tamanho_performance = (
            obter_tamanho_performance(
                imagem
            )
        )

        banner = eh_banner(
            imagem
        )

        registro_existente = (
            imagens_unicas.get(
                url
            )
        )

        if registro_existente is None:
            imagens_unicas[url] = {
                "url": url,
                "tipo": imagem.get(
                    "tipo",
                    "img",
                ),
                "banner": banner,
                "tamanho_performance": (
                    tamanho_performance
                ),
            }

            continue

        registro_existente["banner"] = (
            registro_existente["banner"]
            or banner
        )

        registro_existente[
            "tamanho_performance"
        ] = max(
            registro_existente[
                "tamanho_performance"
            ],
            tamanho_performance,
        )

    registros = list(
        imagens_unicas.values()
    )

    registros_testados = registros[
        :LIMITE_IMAGENS_POR_PAGINA
    ]

    ignoradas = max(
        0,
        len(registros)
        - len(registros_testados),
    )

    resultados: list[
        dict[str, Any]
    ] = []

    for registro in registros_testados:
        resultado = validar_tamanho_imagem(
            url=registro["url"],
            tamanho_navegador=registro[
                "tamanho_performance"
            ],
        )

        resultados.append(
            {
                **registro,
                **resultado.to_dict(),
            }
        )

    return (
        resultados,
        ignoradas,
    )


def formatar_tamanho(
    tamanho_kb: float,
    tamanho_exato: bool,
) -> str:
    prefixo = (
        ""
        if tamanho_exato
        else "pelo menos "
    )

    return (
        f"{prefixo}{tamanho_kb:.2f} KB"
    )


def eh_imagem_tecnica_ou_decorativa(
    imagem: dict[str, Any],
) -> bool:
    """
    Identifica imagens técnicas ou decorativas que não
    devem gerar reprovação automática por ALT ausente.
    """
    contexto = " ".join(
        [
            obter_url_imagem(
                imagem
            ),
            str(
                imagem.get(
                    "id",
                    "",
                )
            ),
            str(
                imagem.get(
                    "class_name",
                    "",
                )
            ),
            str(
                imagem.get(
                    "ancestor_hint",
                    "",
                )
            ),
        ]
    ).casefold()

    termos_tecnicos = (
        "icon",
        "icone",
        "ícone",
        "arrow",
        "seta",
        "whatsapp",
        "facebook",
        "instagram",
        "linkedin",
        "youtube",
        "menu",
        "hamburger",
        "close",
        "search",
        "lupa",
        "loading",
        "spinner",
        "pixel",
        "tracker",
        "analytics",
        "recaptcha",
        "badge",
        "selo",
    )

    if any(
        termo in contexto
        for termo in termos_tecnicos
    ):
        return True

    largura = int(
        imagem.get(
            "width",
            0,
        )
        or 0
    )

    altura = int(
        imagem.get(
            "height",
            0,
        )
        or 0
    )

    if (
        largura > 0
        and altura > 0
        and largura <= 64
        and altura <= 64
    ):
        return True

    return False


class ImagesMissingAltCheck(
    BaseCheck
):
    nome = "Images - Missing ALT"
    categoria = "Imagens"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        imagens_sem_alt: list[str] = []
        imagens_ignoradas: list[str] = []

        for imagem in page_data.images:
            possui_alt = bool(
                imagem.get(
                    "alt_exists",
                    False,
                )
            )

            if possui_alt:
                continue

            url = obter_url_imagem(
                imagem
            )

            if eh_imagem_tecnica_ou_decorativa(
                imagem
            ):
                imagens_ignoradas.append(
                    url
                )

                continue

            imagens_sem_alt.append(
                url
            )

        imagens_sem_alt = list(
            dict.fromkeys(
                imagens_sem_alt
            )
        )

        imagens_ignoradas = list(
            dict.fromkeys(
                imagens_ignoradas
            )
        )

        dados = {
            "quantidade": len(
                imagens_sem_alt
            ),
            "imagens": imagens_sem_alt,
            "quantidade_ignorada": len(
                imagens_ignoradas
            ),
            "imagens_ignoradas": (
                imagens_ignoradas
            ),
        }

        if imagens_sem_alt:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontradas "
                    f"{len(imagens_sem_alt)} imagens "
                    "sem o atributo ALT:\n"
                    + "\n".join(
                        imagens_sem_alt
                    )
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(imagens_ignoradas)} imagem(ns) "
                "técnica(s) ou decorativa(s) foram "
                "ignoradas."
            ),
            dados=dados,
        )



class ImagesEmptyAltCheck(
    BaseCheck
):
    nome = "Images - Empty ALT"
    categoria = "Imagens"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        imagens_alt_vazio: list[str] = []
        imagens_ignoradas: list[str] = []

        for imagem in page_data.images:
            possui_alt = bool(
                imagem.get(
                    "alt_exists",
                    False,
                )
            )

            if not possui_alt:
                continue

            alt = str(
                imagem.get(
                    "alt",
                    "",
                )
            ).strip()

            if alt:
                continue

            url = obter_url_imagem(
                imagem
            )

            if eh_imagem_tecnica_ou_decorativa(
                imagem
            ):
                imagens_ignoradas.append(
                    url
                )

                continue

            imagens_alt_vazio.append(
                url
            )

        imagens_alt_vazio = list(
            dict.fromkeys(
                imagens_alt_vazio
            )
        )

        imagens_ignoradas = list(
            dict.fromkeys(
                imagens_ignoradas
            )
        )

        dados = {
            "quantidade": len(
                imagens_alt_vazio
            ),
            "imagens": imagens_alt_vazio,
            "quantidade_ignorada": len(
                imagens_ignoradas
            ),
            "imagens_ignoradas": (
                imagens_ignoradas
            ),
        }

        if imagens_alt_vazio:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontradas "
                    f"{len(imagens_alt_vazio)} imagens "
                    "com ALT vazio:\n"
                    + "\n".join(
                        imagens_alt_vazio
                    )
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(imagens_ignoradas)} imagem(ns) "
                "técnica(s) ou decorativa(s) foram "
                "ignoradas."
            ),
            dados=dados,
        )



class ImagesBrokenCheck(
    BaseCheck
):
    nome = "Images - Broken"
    categoria = "Imagens"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        imagens_unicas: dict[
            str,
            dict[str, Any],
        ] = {}

        for imagem in page_data.images:
            url = obter_url_imagem(
                imagem
            )

            if (
                not url
                or url
                == "Imagem sem URL identificada"
            ):
                continue

            url_normalizada = url.casefold()

            if url_normalizada.startswith(
                (
                    "data:",
                    "blob:",
                )
            ):
                continue

            if url in imagens_unicas:
                continue

            imagens_unicas[url] = imagem

        resultados: list[
            dict[str, Any]
        ] = []

        imagens_quebradas: list[
            dict[str, Any]
        ] = []

        for url, imagem in imagens_unicas.items():
            complete = bool(
                imagem.get(
                    "complete",
                    False,
                )
            )

            natural_width = int(
                imagem.get(
                    "natural_width",
                    0,
                )
                or 0
            )

            carregou_no_navegador = (
                complete
                and natural_width > 0
            )

            resultado_http = validar_imagem(
                url
            )

            registro = {
                **resultado_http.to_dict(),
                "complete": complete,
                "natural_width": natural_width,
                "carregou_no_navegador": (
                    carregou_no_navegador
                ),
            }

            resultados.append(
                registro
            )

            if not resultado_http.sucesso:
                imagens_quebradas.append(
                    registro
                )

        dados = {
            "quantidade_analisada": len(
                resultados
            ),
            "quantidade_quebrada": len(
                imagens_quebradas
            ),
            "imagens_quebradas": (
                imagens_quebradas
            ),
            "resultados": resultados,
            "imagens_validadas_em_cache": (
                quantidade_imagens_validadas_em_cache()
            ),
        }

        if imagens_quebradas:
            observacoes = []

            for item in imagens_quebradas:
                status_http = item.get(
                    "status_http"
                )

                status_texto = (
                    str(status_http)
                    if status_http is not None
                    else "sem resposta"
                )

                erro = str(
                    item.get(
                        "erro",
                        "",
                    )
                ).strip()

                detalhe = (
                    f"HTTP {status_texto}"
                )

                if erro:
                    detalhe += f" — {erro}"

                observacoes.append(
                    f"{detalhe} — "
                    f"{item['url_solicitada']}"
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontradas "
                    f"{len(imagens_quebradas)} imagens "
                    "indisponíveis após validação HTTP:\n"
                    + "\n".join(
                        observacoes
                    )
                ),
                dados=dados,
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(resultados)} imagem(ns) "
                "validada(s) por HTTP."
            ),
            dados=dados,
        )


class ImagesOver200KbCheck(
    BaseCheck
):
    nome = "Images - Over 200 KB"
    categoria = "Imagens"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        resultados, ignoradas = (
            coletar_imagens_para_peso(
                page_data
            )
        )

        imagens_comuns = [
            item
            for item in resultados
            if not item["banner"]
        ]

        imagens_pesadas = [
            item
            for item in imagens_comuns
            if (
                item["sucesso"]
                and item["tamanho_bytes"]
                > LIMITE_IMAGEM_BYTES
            )
        ]

        indisponiveis = [
            item
            for item in imagens_comuns
            if not item["sucesso"]
        ]

        dados = {
            "limite_kb": 200,

            "quantidade_analisada": len(
                imagens_comuns
            ),

            "quantidade_acima_limite": len(
                imagens_pesadas
            ),

            "quantidade_tamanho_indisponivel": len(
                indisponiveis
            ),

            "quantidade_ignorada_por_limite": (
                ignoradas
            ),

            "imagens_acima_limite": (
                imagens_pesadas
            ),

            "tamanhos_indisponiveis": (
                indisponiveis
            ),

            "imagens_em_cache": (
                quantidade_imagens_em_cache()
            ),
        }

        if imagens_pesadas:
            observacoes: list[str] = []

            for item in imagens_pesadas:
                tamanho = formatar_tamanho(
                    item["tamanho_kb"],
                    item["tamanho_exato"],
                )

                observacoes.append(
                    f"{tamanho} — {item['url']}"
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontradas "
                    f"{len(imagens_pesadas)} imagens "
                    "com mais de 200 KB:\n"
                    + "\n".join(
                        observacoes
                    )
                ),
                dados=dados,
            )

        mensagens: list[str] = []

        if indisponiveis:
            mensagens.append(
                (
                    "Não foi possível identificar "
                    f"o peso de {len(indisponiveis)} "
                    "imagem(ns)."
                )
            )

        if ignoradas:
            mensagens.append(
                (
                    f"{ignoradas} imagem(ns) não foram "
                    "analisadas devido ao limite "
                    "por página."
                )
            )

        return self.resultado(
            status="approved",
            observacao=" ".join(
                mensagens
            ),
            dados=dados,
        )


class BannersOver500KbCheck(
    BaseCheck
):
    nome = "Banners - Over 500 KB"
    categoria = "Imagens"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        resultados, ignoradas = (
            coletar_imagens_para_peso(
                page_data
            )
        )

        banners = [
            item
            for item in resultados
            if item["banner"]
        ]

        banners_pesados = [
            item
            for item in banners
            if (
                item["sucesso"]
                and item["tamanho_bytes"]
                > LIMITE_BANNER_BYTES
            )
        ]

        indisponiveis = [
            item
            for item in banners
            if not item["sucesso"]
        ]

        dados = {
            "limite_kb": 500,

            "quantidade_banners_analisados": len(
                banners
            ),

            "quantidade_acima_limite": len(
                banners_pesados
            ),

            "quantidade_tamanho_indisponivel": len(
                indisponiveis
            ),

            "quantidade_ignorada_por_limite": (
                ignoradas
            ),

            "banners_acima_limite": (
                banners_pesados
            ),

            "tamanhos_indisponiveis": (
                indisponiveis
            ),

            "banners_analisados": banners,
        }

        if banners_pesados:
            observacoes: list[str] = []

            for item in banners_pesados:
                tamanho = formatar_tamanho(
                    item["tamanho_kb"],
                    item["tamanho_exato"],
                )

                observacoes.append(
                    f"{tamanho} — {item['url']}"
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    f"Foram encontrados "
                    f"{len(banners_pesados)} banners "
                    "com mais de 500 KB:\n"
                    + "\n".join(
                        observacoes
                    )
                ),
                dados=dados,
            )

        mensagens = [
            f"{len(banners)} banner(s) analisado(s)."
        ]

        if indisponiveis:
            mensagens.append(
                (
                    "Não foi possível identificar "
                    f"o peso de {len(indisponiveis)} "
                    "banner(s)."
                )
            )

        if ignoradas:
            mensagens.append(
                (
                    f"{ignoradas} imagem(ns) não foram "
                    "analisadas devido ao limite "
                    "por página."
                )
            )

        return self.resultado(
            status="approved",
            observacao=" ".join(
                mensagens
            ),
            dados=dados,
        )


class ImagesSummaryCheck(
    BaseCheck
):
    nome = "Images - Summary"
    categoria = "Imagens"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(
            contexto
        )

        if page_data is None:
            return self.resultado(
                status="error",
                observacao=(
                    "PageData não está disponível."
                ),
            )

        quantidade_img = len(
            page_data.images
        )

        quantidade_background = len(
            page_data.background_images
        )

        quantidade_total = (
            quantidade_img
            + quantidade_background
        )

        return self.resultado(
            status="approved",
            dados={
                "quantidade_total_imagens": (
                    quantidade_total
                ),
                "quantidade_tags_img": (
                    quantidade_img
                ),
                "quantidade_background_images": (
                    quantidade_background
                ),
            },
        )