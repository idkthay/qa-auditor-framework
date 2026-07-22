from typing import Any


STATUS_PRIORIDADE = {
    "approved": 1,
    "error": 2,
    "rejected": 3,
}


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


def obter_evidencias_check(
    check: dict[str, Any],
) -> list[str]:
    dados = check.get(
        "dados",
        {},
    )

    if not isinstance(
        dados,
        dict,
    ):
        return []

    evidencias = dados.get(
        "evidencias",
        [],
    )

    if not isinstance(
        evidencias,
        list,
    ):
        return []

    return [
        str(evidencia)
        for evidencia in evidencias
        if evidencia
    ]


def consolidar_checks(
    paginas: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    agrupados: dict[str, dict[str, Any]] = {}

    for pagina in paginas:
        url = obter_url_pagina(
            pagina
        )

        screenshot_pagina = (
            obter_screenshot_pagina(
                pagina
            )
        )

        for check in pagina.get(
            "checks",
            [],
        ):
            nome = check.get(
                "nome",
                "Validação sem nome",
            )

            categoria = check.get(
                "categoria",
                "Geral",
            )

            status = check.get(
                "status",
                "error",
            )

            observacao = check.get(
                "observacao",
                "",
            ).strip()

            evidencias_check = (
                obter_evidencias_check(
                    check
                )
            )

            if nome not in agrupados:
                agrupados[nome] = {
                    "categoria": categoria,
                    "status": "approved",
                    "ocorrencias": [],
                    "imgs": [],
                }

            item_atual = agrupados[
                nome
            ]

            prioridade_nova = (
                STATUS_PRIORIDADE.get(
                    status,
                    0,
                )
            )

            prioridade_atual = (
                STATUS_PRIORIDADE.get(
                    item_atual["status"],
                    0,
                )
            )

            if (
                prioridade_nova
                > prioridade_atual
            ):
                item_atual[
                    "status"
                ] = status

            if status in {
                "rejected",
                "error",
            }:
                texto_ocorrencia = url

                if observacao:
                    texto_ocorrencia = (
                        f"{url} — {observacao}"
                    )

                item_atual[
                    "ocorrencias"
                ].append(
                    texto_ocorrencia
                )

                if evidencias_check:
                    item_atual[
                        "imgs"
                    ].extend(
                        evidencias_check
                    )

                elif screenshot_pagina:
                    item_atual[
                        "imgs"
                    ].append(
                        screenshot_pagina
                    )

    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for nome, dados in agrupados.items():
        ocorrencias_unicas = list(
            dict.fromkeys(
                dados["ocorrencias"]
            )
        )

        imagens_unicas = list(
            dict.fromkeys(
                dados["imgs"]
            )
        )

        resultado[nome] = {
            "categoria": dados[
                "categoria"
            ],
            "status": dados[
                "status"
            ],
            "obs": "\n".join(
                ocorrencias_unicas
            ),
            "imgs": imagens_unicas,
        }

    return resultado


def consolidar_checks_globais(
    checks_globais: list[
        dict[str, Any]
    ],
) -> dict[str, dict[str, Any]]:
    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for check in checks_globais:
        nome = check.get(
            "nome",
            "Validação global sem nome",
        )

        categoria = check.get(
            "categoria",
            "Geral",
        )

        status = check.get(
            "status",
            "error",
        )

        observacao = check.get(
            "observacao",
            "",
        ).strip()

        imagens = check.get(
            "imgs",
            [],
        )

        if not isinstance(
            imagens,
            list,
        ):
            imagens = []

        resultado[nome] = {
            "categoria": categoria,
            "status": status,
            "obs": observacao,
            "imgs": list(
                dict.fromkeys(
                    imagens
                )
            ),
        }

    return resultado


def gerar_itens_prontuario(
    paginas: list[dict[str, Any]],
    checks_globais: list[
        dict[str, Any]
    ] | None = None,
) -> dict[str, dict[str, Any]]:
    itens = consolidar_checks(
        paginas
    )

    itens_globais = (
        consolidar_checks_globais(
            checks_globais or []
        )
    )

    itens.update(
        itens_globais
    )

    return itens