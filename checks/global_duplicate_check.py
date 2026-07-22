import re
from collections import defaultdict
from typing import Any


def normalizar_texto(texto: str) -> str:
    """
    Normaliza o texto utilizado nas comparações globais.

    Ignora:
    - Diferenças entre letras maiúsculas e minúsculas;
    - Espaços repetidos;
    - Espaços no início e no final.
    """
    texto_normalizado = re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()

    return texto_normalizado.casefold()


def obter_url_pagina(
    pagina: dict[str, Any],
) -> str:
    return (
        pagina.get("url_final")
        or pagina.get("url_solicitada")
        or "URL não identificada"
    )


def obter_screenshot_pagina(
    pagina: dict[str, Any],
) -> str:
    return pagina.get(
        "screenshot",
        "",
    )


def criar_resultado_global(
    nome: str,
    categoria: str,
    rotulo: str,
    grupos_duplicados: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Cria o resultado padronizado de um check global.
    """
    if not grupos_duplicados:
        return {
            "nome": nome,
            "categoria": categoria,
            "status": "approved",
            "observacao": "",
            "dados": {
                "quantidade_grupos": 0,
                "grupos_duplicados": [],
            },
            "imgs": [],
        }

    blocos_observacao: list[str] = []
    imagens: list[str] = []

    for grupo in grupos_duplicados:
        valor = grupo.get(
            "valor",
            "",
        )

        urls = grupo.get(
            "urls",
            [],
        )

        imgs = grupo.get(
            "imgs",
            [],
        )

        bloco = (
            f'{rotulo} duplicado: "{valor}"\n'
            + "\n".join(urls)
        )

        blocos_observacao.append(
            bloco
        )

        imagens.extend(
            imgs
        )

    return {
        "nome": nome,
        "categoria": categoria,
        "status": "rejected",
        "observacao": "\n\n".join(
            blocos_observacao
        ),
        "dados": {
            "quantidade_grupos": len(
                grupos_duplicados
            ),
            "grupos_duplicados": grupos_duplicados,
        },
        "imgs": list(
            dict.fromkeys(
                imagens
            )
        ),
    }


def detectar_campo_texto_duplicado(
    paginas: list[dict[str, Any]],
    campo: str,
    nome: str,
    rotulo: str,
) -> dict[str, Any]:
    """
    Detecta valores de texto repetidos entre URLs diferentes.

    Pode validar:
    - Page Title;
    - Meta Description;
    - Outros campos simples do PageData.
    """
    valores: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "valor_original": "",
            "urls": [],
            "imgs": [],
        }
    )

    for pagina in paginas:
        if pagina.get("erro_navegacao"):
            continue

        page_data = pagina.get(
            "page_data",
            {},
        )

        valor = page_data.get(
            campo,
            "",
        )

        if not isinstance(
            valor,
            str,
        ):
            continue

        valor_limpo = re.sub(
            r"\s+",
            " ",
            valor,
        ).strip()

        if not valor_limpo:
            continue

        chave = normalizar_texto(
            valor_limpo
        )

        url = obter_url_pagina(
            pagina
        )

        screenshot = obter_screenshot_pagina(
            pagina
        )

        if not valores[chave]["valor_original"]:
            valores[chave][
                "valor_original"
            ] = valor_limpo

        valores[chave]["urls"].append(
            url
        )

        if screenshot:
            valores[chave]["imgs"].append(
                screenshot
            )

    grupos_duplicados: list[dict[str, Any]] = []

    for dados in valores.values():
        urls_unicas = list(
            dict.fromkeys(
                dados["urls"]
            )
        )

        if len(urls_unicas) <= 1:
            continue

        grupos_duplicados.append(
            {
                "valor": dados[
                    "valor_original"
                ],
                "urls": urls_unicas,
                "imgs": list(
                    dict.fromkeys(
                        dados["imgs"]
                    )
                ),
            }
        )

    grupos_duplicados.sort(
        key=lambda grupo: (
            -len(grupo["urls"]),
            grupo["valor"].casefold(),
        )
    )

    return criar_resultado_global(
        nome=nome,
        categoria="SEO",
        rotulo=rotulo,
        grupos_duplicados=grupos_duplicados,
    )


def detectar_h1_duplicado(
    paginas: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Detecta textos de H1 utilizados em URLs diferentes.
    """
    valores: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "valor_original": "",
            "urls": [],
            "imgs": [],
        }
    )

    for pagina in paginas:
        if pagina.get("erro_navegacao"):
            continue

        page_data = pagina.get(
            "page_data",
            {},
        )

        lista_h1 = page_data.get(
            "h1",
            [],
        )

        if not isinstance(
            lista_h1,
            list,
        ):
            continue

        url = obter_url_pagina(
            pagina
        )

        screenshot = obter_screenshot_pagina(
            pagina
        )

        h1_encontrados_na_pagina: set[str] = set()

        for texto_h1 in lista_h1:
            if not isinstance(
                texto_h1,
                str,
            ):
                continue

            texto_limpo = re.sub(
                r"\s+",
                " ",
                texto_h1,
            ).strip()

            if not texto_limpo:
                continue

            chave = normalizar_texto(
                texto_limpo
            )

            # Evita considerar o mesmo H1 duas vezes
            # dentro da mesma URL.
            if chave in h1_encontrados_na_pagina:
                continue

            h1_encontrados_na_pagina.add(
                chave
            )

            if not valores[chave]["valor_original"]:
                valores[chave][
                    "valor_original"
                ] = texto_limpo

            valores[chave]["urls"].append(
                url
            )

            if screenshot:
                valores[chave]["imgs"].append(
                    screenshot
                )

    grupos_duplicados: list[dict[str, Any]] = []

    for dados in valores.values():
        urls_unicas = list(
            dict.fromkeys(
                dados["urls"]
            )
        )

        if len(urls_unicas) <= 1:
            continue

        grupos_duplicados.append(
            {
                "valor": dados[
                    "valor_original"
                ],
                "urls": urls_unicas,
                "imgs": list(
                    dict.fromkeys(
                        dados["imgs"]
                    )
                ),
            }
        )

    grupos_duplicados.sort(
        key=lambda grupo: (
            -len(grupo["urls"]),
            grupo["valor"].casefold(),
        )
    )

    return criar_resultado_global(
        nome="H1 Duplicate",
        categoria="Semântica",
        rotulo="H1",
        grupos_duplicados=grupos_duplicados,
    )


def executar_checks_globais(
    paginas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Executa checks que dependem da comparação entre
    várias páginas do site.
    """
    return [
        detectar_campo_texto_duplicado(
            paginas=paginas,
            campo="title",
            nome="Page Titles - Duplicate",
            rotulo="Title",
        ),
        detectar_campo_texto_duplicado(
            paginas=paginas,
            campo="meta_description",
            nome="Meta Descriptions - Duplicate",
            rotulo="Meta Description",
        ),
        detectar_h1_duplicado(
            paginas=paginas,
        ),
    ]