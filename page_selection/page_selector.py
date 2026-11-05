from __future__ import annotations

from typing import Any

from page_selection.keywords import (
    CATEGORIAS_ESTRUTURAIS,
    ROTULOS_CATEGORIAS,
)
from page_selection.page_classifier import (
    classificar_pagina,
    obter_url,
)


def normalizar_registro(
    pagina: str | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(
        pagina,
        str,
    ):
        return {
            "url": pagina,
            "titulo": "",
            "h1": "",
            "breadcrumb": "",
            "textos_links": [],
            "no_menu": False,
            "na_home": False,
            "profundidade": 99,
        }

    registro = dict(
        pagina
    )

    registro.setdefault(
        "titulo",
        "",
    )

    registro.setdefault(
        "h1",
        "",
    )

    registro.setdefault(
        "breadcrumb",
        "",
    )

    registro.setdefault(
        "textos_links",
        [],
    )

    registro.setdefault(
        "no_menu",
        False,
    )

    registro.setdefault(
        "na_home",
        False,
    )

    registro.setdefault(
        "profundidade",
        99,
    )

    return registro


def calcular_prioridade(
    registro: dict[str, Any],
    classificacao: dict[str, Any],
) -> tuple[int, int, int, int]:
    no_menu = int(
        bool(
            registro.get(
                "no_menu",
                False,
            )
        )
    )

    na_home = int(
        bool(
            registro.get(
                "na_home",
                False,
            )
        )
    )

    try:
        profundidade = int(
            registro.get(
                "profundidade",
                99,
            )
        )

    except (TypeError, ValueError):
        profundidade = 99

    pontuacao = int(
        classificacao.get(
            "pontuacao",
            0,
        )
    )

    return (
        pontuacao,
        no_menu,
        na_home,
        -profundidade,
    )


def selecionar_melhor_categoria(
    candidatos: list[
        dict[str, Any]
    ],
) -> dict[str, Any] | None:
    if not candidatos:
        return None

    return max(
        candidatos,
        key=lambda item: (
            item["prioridade"]
        ),
    )


def selecionar_paginas(
    paginas_descobertas: list[
        str | dict[str, Any]
    ],
    limite_mpis: int = 10,
) -> dict[str, Any]:
    registros: list[
        dict[str, Any]
    ] = []

    urls_processadas: set[str] = set()

    for pagina in paginas_descobertas:
        registro = normalizar_registro(
            pagina
        )

        url = obter_url(
            registro
        )

        if (
            not url
            or url in urls_processadas
        ):
            continue

        urls_processadas.add(
            url
        )

        classificacao = (
            classificar_pagina(
                registro
            )
        )

        registro[
            "classificacao"
        ] = classificacao

        registro[
            "prioridade"
        ] = calcular_prioridade(
            registro=registro,
            classificacao=classificacao,
        )

        registros.append(
            registro
        )

    selecionadas: list[
        dict[str, Any]
    ] = []

    urls_selecionadas: set[str] = set()

    categorias_encontradas: dict[
        str,
        dict[str, Any] | None
    ] = {}

    for categoria in CATEGORIAS_ESTRUTURAIS:
        candidatos = [
            registro
            for registro in registros
            if (
                registro[
                    "classificacao"
                ][
                    "categoria"
                ]
                == categoria
            )
        ]

        melhor = selecionar_melhor_categoria(
            candidatos
        )

        categorias_encontradas[
            categoria
        ] = melhor

        if melhor is None:
            continue

        url = obter_url(
            melhor
        )

        if url in urls_selecionadas:
            continue

        urls_selecionadas.add(
            url
        )

        selecionadas.append(
            melhor
        )

    candidatos_mpi = [
        registro
        for registro in registros
        if (
            registro[
                "classificacao"
            ][
                "categoria"
            ]
            == "mpi"
            and obter_url(
                registro
            )
            not in urls_selecionadas
        )
    ]

    candidatos_mpi.sort(
        key=lambda item: (
            item["prioridade"]
        ),
        reverse=True,
    )

    mpis_selecionadas = (
        candidatos_mpi[
            :max(
                0,
                limite_mpis,
            )
        ]
    )

    for registro in mpis_selecionadas:
        url = obter_url(
            registro
        )

        urls_selecionadas.add(
            url
        )

        selecionadas.append(
            registro
        )

    categorias_nao_encontradas = [
        categoria
        for categoria, registro
        in categorias_encontradas.items()
        if registro is None
    ]

    resumo_categorias = {
        categoria: (
            obter_url(
                registro
            )
            if registro
            else None
        )
        for categoria, registro
        in categorias_encontradas.items()
    }

    return {
        "urls": [
            obter_url(
                registro
            )
            for registro in selecionadas
        ],

        "paginas": selecionadas,

        "quantidade_descobertas": len(
            registros
        ),

        "quantidade_selecionadas": len(
            selecionadas
        ),

        "quantidade_mpis": len(
            mpis_selecionadas
        ),

        "categorias": (
            resumo_categorias
        ),

        "categorias_nao_encontradas": (
            categorias_nao_encontradas
        ),

        "rotulos_categorias": (
            ROTULOS_CATEGORIAS
        ),
    }


def imprimir_resumo_selecao(
    resultado: dict[str, Any],
) -> None:
    print(
        "\n" + "=" * 55
    )

    print(
        "SELEÇÃO INTELIGENTE DE PÁGINAS"
    )

    print(
        "=" * 55
    )

    print(
        "URLs descobertas: "
        f"{resultado.get(
            'quantidade_descobertas',
            0,
        )}"
    )

    categorias = resultado.get(
        "categorias",
        {},
    )

    rotulos = resultado.get(
        "rotulos_categorias",
        {},
    )

    for categoria in CATEGORIAS_ESTRUTURAIS:
        rotulo = rotulos.get(
            categoria,
            categoria,
        )

        url = categorias.get(
            categoria
        )

        if url:
            print(
                f"✅ {rotulo}: {url}"
            )

        else:
            print(
                f"⚠️ {rotulo}: "
                "não encontrada"
            )

    print(
        "✅ MPIs selecionadas: "
        f"{resultado.get(
            'quantidade_mpis',
            0,
        )}"
    )

    print(
        "✅ Total selecionado: "
        f"{resultado.get(
            'quantidade_selecionadas',
            0,
        )}"
    )