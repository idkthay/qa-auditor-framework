from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import unquote, urlparse

from selectors.keywords import (
    PALAVRAS_CATEGORIAS,
    TERMOS_EXCLUSAO_MPI,
    TERMOS_FORTES_MPI,
)


def normalizar_texto(
    valor: Any,
) -> str:
    if valor is None:
        return ""

    texto = str(
        valor
    ).strip().casefold()

    texto = unquote(
        texto
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    texto = re.sub(
        r"[_/|–—]+",
        " ",
        texto,
    )

    texto = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        texto,
    )

    texto = texto.replace(
        "-",
        " ",
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def obter_valor(
    pagina: str | dict[str, Any],
    nome: str,
    valor_padrao: Any = "",
) -> Any:
    if isinstance(
        pagina,
        str,
    ):
        if nome == "url":
            return pagina

        return valor_padrao

    return pagina.get(
        nome,
        valor_padrao,
    )


def obter_url(
    pagina: str | dict[str, Any],
) -> str:
    return str(
        obter_valor(
            pagina,
            "url",
            "",
        )
    ).strip()


def caminho_eh_home(
    url: str,
) -> bool:
    partes = urlparse(
        url
    )

    caminho = partes.path.strip(
        "/"
    )

    return caminho == ""


def montar_evidencias(
    pagina: str | dict[str, Any],
) -> dict[str, str]:
    url = obter_url(
        pagina
    )

    partes = urlparse(
        url
    )

    caminho = normalizar_texto(
        partes.path
    )

    titulo = normalizar_texto(
        obter_valor(
            pagina,
            "titulo",
            "",
        )
    )

    h1 = normalizar_texto(
        obter_valor(
            pagina,
            "h1",
            "",
        )
    )

    breadcrumb = normalizar_texto(
        obter_valor(
            pagina,
            "breadcrumb",
            "",
        )
    )

    textos_links = obter_valor(
        pagina,
        "textos_links",
        [],
    )

    if isinstance(
        textos_links,
        str,
    ):
        textos_links = [
            textos_links
        ]

    texto_links = normalizar_texto(
        " ".join(
            str(texto)
            for texto in textos_links
        )
    )

    return {
        "url": normalizar_texto(
            url
        ),
        "caminho": caminho,
        "titulo": titulo,
        "h1": h1,
        "breadcrumb": breadcrumb,
        "textos_links": texto_links,
    }


def pontuar_termo(
    termo: str,
    evidencias: dict[str, str],
) -> int:
    termo_normalizado = normalizar_texto(
        termo
    )

    if not termo_normalizado:
        return 0

    pontuacao = 0

    pesos = {
        "caminho": 8,
        "textos_links": 6,
        "breadcrumb": 5,
        "h1": 4,
        "titulo": 3,
        "url": 1,
    }

    for campo, peso in pesos.items():
        valor = evidencias.get(
            campo,
            "",
        )

        if not valor:
            continue

        if valor == termo_normalizado:
            pontuacao += peso * 2

        elif termo_normalizado in valor:
            pontuacao += peso

    return pontuacao


def pontuar_categoria(
    categoria: str,
    evidencias: dict[str, str],
) -> int:
    termos = PALAVRAS_CATEGORIAS.get(
        categoria,
        (),
    )

    return sum(
        pontuar_termo(
            termo=termo,
            evidencias=evidencias,
        )
        for termo in termos
    )


def contem_termo_excluido(
    texto: str,
) -> bool:
    return any(
        normalizar_texto(
            termo
        ) in texto
        for termo in TERMOS_EXCLUSAO_MPI
    )


def calcular_pontuacao_mpi(
    pagina: str | dict[str, Any],
    evidencias: dict[str, str],
) -> int:
    url = obter_url(
        pagina
    )

    partes = urlparse(
        url
    )

    caminho = normalizar_texto(
        partes.path
    )

    if not caminho:
        return 0

    texto_completo = " ".join(
        evidencias.values()
    )

    if contem_termo_excluido(
        texto_completo
    ):
        return 0

    segmentos = [
        segmento
        for segmento in partes.path.split(
            "/"
        )
        if segmento
    ]

    if len(segmentos) > 4:
        return 0

    pontuacao = 1

    quantidade_palavras = len(
        caminho.split()
    )

    if quantidade_palavras >= 2:
        pontuacao += 3

    if quantidade_palavras >= 3:
        pontuacao += 2

    for termo in TERMOS_FORTES_MPI:
        termo_normalizado = (
            normalizar_texto(
                termo
            )
        )

        if termo_normalizado in texto_completo:
            pontuacao += 3

    no_menu = bool(
        obter_valor(
            pagina,
            "no_menu",
            False,
        )
    )

    na_home = bool(
        obter_valor(
            pagina,
            "na_home",
            False,
        )
    )

    if no_menu:
        pontuacao += 4

    if na_home:
        pontuacao += 3

    profundidade = obter_valor(
        pagina,
        "profundidade",
        99,
    )

    try:
        profundidade = int(
            profundidade
        )

    except (TypeError, ValueError):
        profundidade = 99

    if profundidade == 1:
        pontuacao += 3

    elif profundidade == 2:
        pontuacao += 2

    elif profundidade == 3:
        pontuacao += 1

    return pontuacao


def classificar_pagina(
    pagina: str | dict[str, Any],
) -> dict[str, Any]:
    url = obter_url(
        pagina
    )

    evidencias = montar_evidencias(
        pagina
    )

    if caminho_eh_home(
        url
    ):
        return {
            "url": url,
            "categoria": "home",
            "pontuacao": 1000,
            "pontuacoes": {
                "home": 1000,
            },
            "evidencias": evidencias,
        }

    pontuacoes = {
        categoria: pontuar_categoria(
            categoria=categoria,
            evidencias=evidencias,
        )
        for categoria
        in PALAVRAS_CATEGORIAS
    }

    categoria_principal = max(
        pontuacoes,
        key=pontuacoes.get,
    )

    maior_pontuacao = pontuacoes[
        categoria_principal
    ]

    if maior_pontuacao > 0:
        categoria = categoria_principal
        pontuacao = maior_pontuacao

    else:
        pontuacao_mpi = (
            calcular_pontuacao_mpi(
                pagina=pagina,
                evidencias=evidencias,
            )
        )

        pontuacoes[
            "mpi"
        ] = pontuacao_mpi

        if pontuacao_mpi > 0:
            categoria = "mpi"
            pontuacao = pontuacao_mpi

        else:
            categoria = "outra"
            pontuacao = 0

    return {
        "url": url,
        "categoria": categoria,
        "pontuacao": pontuacao,
        "pontuacoes": pontuacoes,
        "evidencias": evidencias,
    }