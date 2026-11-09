
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


def obter_url_pagina(pagina: dict[str, Any]) -> str:
    return (
        pagina.get("url_final")
        or pagina.get("url_solicitada")
        or "URL não identificada"
    )


def obter_screenshot_pagina(pagina: dict[str, Any]) -> str:
    screenshot = pagina.get("screenshot", "")
    return screenshot if isinstance(screenshot, str) else ""


def obter_evidencias_check(check: dict[str, Any]) -> list[str]:
    dados = check.get("dados", {})

    if not isinstance(dados, dict):
        return []

    evidencias = dados.get("evidencias", [])

    if not isinstance(evidencias, list):
        return []

    return [
        str(evidencia)
        for evidencia in evidencias
        if evidencia
    ]


def deduplicar_textos(valores: list[Any]) -> list[str]:
    """Remove valores vazios e duplicados preservando a ordem."""
    resultado = []
    vistos = set()

    for valor in valores:
        if not isinstance(valor, str):
            continue

        texto = valor.strip()
        if not texto or texto in vistos:
            continue

        vistos.add(texto)
        resultado.append(texto)

    return resultado


def combinar_itens(
    item_existente: dict[str, Any],
    item_novo: dict[str, Any],
) -> dict[str, Any]:
    """Combina dois itens sem perder status, observações ou evidências."""
    status_existente = normalizar_status(
        item_existente.get("status")
    )
    status_novo = normalizar_status(
        item_novo.get("status")
    )

    if (
        STATUS_PRIORIDADE[status_novo]
        > STATUS_PRIORIDADE[status_existente]
    ):
        status_final = status_novo
    else:
        status_final = status_existente

    observacoes = deduplicar_textos(
        normalizar_observacao(item_existente.get("obs", "")).splitlines()
        + normalizar_observacao(item_novo.get("obs", "")).splitlines()
    )

    imagens_existentes = item_existente.get("imgs", [])
    imagens_novas = item_novo.get("imgs", [])

    if not isinstance(imagens_existentes, list):
        imagens_existentes = []

    if not isinstance(imagens_novas, list):
        imagens_novas = []

    return {
        "categoria": (
            item_existente.get("categoria")
            or item_novo.get("categoria")
            or "Geral"
        ),
        "status": status_final,
        "obs": "\n".join(observacoes),
        "imgs": deduplicar_textos(
            imagens_existentes + imagens_novas
        ),
    }


def consolidar_checks(
    paginas: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    agrupados: dict[str, dict[str, Any]] = {}

    for pagina in paginas:
        url = obter_url_pagina(pagina)
        screenshot_pagina = obter_screenshot_pagina(pagina)

        checks = pagina.get("checks", [])
        if not isinstance(checks, list):
            continue

        for check in checks:
            if not isinstance(check, dict):
                continue

            nome = check.get("nome") or "Validação sem nome"
            categoria = check.get("categoria") or "Geral"

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

            if (
                STATUS_PRIORIDADE[status]
                > STATUS_PRIORIDADE[item_atual["status"]]
            ):
                item_atual["status"] = status

            if status in {"warning", "rejected", "error"}:
                texto_ocorrencia = url

                if observacao:
                    texto_ocorrencia = f"{url} — {observacao}"

                item_atual["ocorrencias"].append(texto_ocorrencia)

            if status in {"rejected", "error"}:
                if evidencias_check:
                    item_atual["imgs"].extend(evidencias_check)
                elif screenshot_pagina:
                    item_atual["imgs"].append(screenshot_pagina)

    resultado: dict[str, dict[str, Any]] = {}

    for nome, dados in agrupados.items():
        resultado[nome] = {
            "categoria": dados["categoria"],
            "status": normalizar_status(dados["status"]),
            "obs": "\n".join(
                deduplicar_textos(dados["ocorrencias"])
            ),
            "imgs": deduplicar_textos(dados["imgs"]),
        }

    return resultado


def consolidar_checks_globais(
    checks_globais: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    resultado: dict[str, dict[str, Any]] = {}

    for check in checks_globais:
        if not isinstance(check, dict):
            continue

        nome = check.get("nome") or "Validação global sem nome"
        categoria = check.get("categoria") or "Geral"

        status = normalizar_status(
            check.get("status", "error")
        )
        observacao = normalizar_observacao(
            check.get("observacao", "")
        )

        imagens = check.get("imgs", [])
        if not isinstance(imagens, list):
            imagens = []

        item_novo = {
            "categoria": categoria,
            "status": status,
            "obs": observacao,
            "imgs": deduplicar_textos(imagens),
        }

        if nome in resultado:
            resultado[nome] = combinar_itens(
                resultado[nome],
                item_novo,
            )
        else:
            resultado[nome] = item_novo

    return resultado


def gerar_itens_prontuario(
    paginas: list[dict[str, Any]],
    checks_globais: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    itens = consolidar_checks(paginas)

    itens_globais = consolidar_checks_globais(
        checks_globais or []
    )

    for nome, item_global in itens_globais.items():
        if nome in itens:
            itens[nome] = combinar_itens(
                itens[nome],
                item_global,
            )
        else:
            itens[nome] = item_global

    # Mantém exatamente as quatro chaves esperadas pelo prontuário.
    return {
        nome: {
            "categoria": item["categoria"],
            "status": item["status"],
            "obs": item["obs"],
            "imgs": item["imgs"],
        }
        for nome, item in itens.items()
    }
