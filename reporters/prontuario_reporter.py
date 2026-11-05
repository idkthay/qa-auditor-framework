from typing import Any


STATUS_PRIORIDADE = {
    "approved": 1,
    "warning": 2,
    "error": 3,
    "rejected": 4,
}
STATUS_VALIDOS = frozenset(STATUS_PRIORIDADE)


def normalizar_status(status: Any) -> str:
    """Impede que status ausentes ou desconhecidos sejam tratados como aprovação."""
    if not isinstance(status, str):
        return "error"

    status_normalizado = status.strip().lower()
    if status_normalizado not in STATUS_VALIDOS:
        return "error"

    return status_normalizado


def normalizar_observacao(observacao: Any) -> str:
    if observacao is None:
        return ""
    return str(observacao).strip()


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
        url = obter_url_pagina(pagina)
        screenshot_pagina = obter_screenshot_pagina(pagina)

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

            status = normalizar_status(
                check.get("status", "error")
            )

            observacao = normalizar_observacao(
                check.get("observacao", "")
            )

            evidencias_check = obter_evidencias_check(check)

            if nome not in agrupados:
                agrupados[nome] = {
                    "categoria": categoria,
                    "status": "approved",
                    "ocorrencias": [],
                    "imgs": [],
                }

            item_atual = agrupados[nome]
            prioridade_nova = STATUS_PRIORIDADE[status]
            prioridade_atual = STATUS_PRIORIDADE[
                item_atual["status"]
            ]

            if prioridade_nova > prioridade_atual:
                item_atual["status"] = status

            # Avisos também precisam aparecer no prontuário: não podem
            # elevar o status para warning e deixar a observação vazia.
            if status in {
                "warning",
                "rejected",
                "error",
            }:
                texto_ocorrencia = url

                if observacao:
                    texto_ocorrencia = f"{url} — {observacao}"

                item_atual["ocorrencias"].append(
                    texto_ocorrencia
                )

            # Mantém evidências visuais somente para falhas efetivas,
            # preservando o comportamento anterior para error/rejected.
            if status in {"rejected", "error"}:
                if evidencias_check:
                    item_atual["imgs"].extend(
                        evidencias_check
                    )
                elif screenshot_pagina:
                    item_atual["imgs"].append(
                        screenshot_pagina
                    )

    resultado: dict[str, dict[str, Any]] = {}

    for nome, dados in agrupados.items():
        ocorrencias_unicas = list(
            dict.fromkeys(dados["ocorrencias"])
        )

        imagens_unicas = list(
            dict.fromkeys(dados["imgs"])
        )

        resultado[nome] = {
            "categoria": dados["categoria"],
            "status": dados["status"],
            "obs": "\n".join(ocorrencias_unicas),
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
        dict[str, Any]
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

        status = normalizar_status(
            check.get("status", "error")
        )

        observacao = normalizar_observacao(
            check.get("observacao", "")
        )

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
                    imagem
                    for imagem in imagens
                    if isinstance(imagem, str) and imagem
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
    itens = consolidar_checks(paginas)

    itens_globais = consolidar_checks_globais(
        checks_globais or []
    )

    itens.update(itens_globais)

    return itens
