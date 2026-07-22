import re
from typing import Any
from urllib.parse import unquote

from playwright.sync_api import Page

from checks.base_check import BaseCheck


PADRAO_TELEFONE_FORMATADO = re.compile(
    r"(?:\+55\s*)?"
    r"\(\d{2}\)\s?"
    r"(?:9\d{4}|\d{4})-\d{4}"
)

PADRAO_EMAIL = re.compile(
    r"^[A-Z0-9._%+\-]+"
    r"@[A-Z0-9.\-]+"
    r"\.[A-Z]{2,}$",
    re.IGNORECASE,
)

PADRAO_CEP_FORMATADO = re.compile(
    r"^\d{5}-\d{3}$"
)

PADRAO_CPF_FORMATADO = re.compile(
    r"^\d{3}\.\d{3}\.\d{3}-\d{2}$"
)

PADRAO_CNPJ_FORMATADO = re.compile(
    r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"
)


def normalizar_espacos(
    texto: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()


def remover_duplicados(
    valores: list[str],
) -> list[str]:
    return list(
        dict.fromkeys(
            valores
        )
    )


def obter_texto_pagina(
    page: Page,
) -> str:
    try:
        return page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )

    except Exception:
        return ""


def coletar_links(
    page: Page,
    seletor: str,
) -> list[dict[str, str]]:
    elementos: list[dict[str, str]] = []

    locator = page.locator(
        seletor
    )

    quantidade = min(
        locator.count(),
        200,
    )

    for indice in range(
        quantidade
    ):
        elemento = locator.nth(
            indice
        )

        try:
            href = (
                elemento.get_attribute(
                    "href"
                )
                or ""
            ).strip()

            texto = normalizar_espacos(
                elemento.inner_text(
                    timeout=1500
                )
            )

            elementos.append(
                {
                    "href": href,
                    "texto": texto,
                }
            )

        except Exception:
            continue

    return elementos


def normalizar_numero_telefone(
    href: str,
) -> str:
    valor = href

    if ":" in valor:
        valor = valor.split(
            ":",
            1,
        )[1]

    valor = valor.split(
        "?",
        1,
    )[0]

    valor = unquote(
        valor
    )

    digitos = re.sub(
        r"\D",
        "",
        valor,
    )

    if (
        digitos.startswith("55")
        and len(digitos) in {12, 13}
    ):
        digitos = digitos[2:]

    return digitos


def telefone_href_valido(
    href: str,
) -> bool:
    digitos = normalizar_numero_telefone(
        href
    )

    if len(digitos) not in {
        10,
        11,
    }:
        return False

    ddd = digitos[:2]

    if ddd == "00":
        return False

    if (
        len(digitos) == 11
        and digitos[2] != "9"
    ):
        return False

    return True


def coletar_campos_formulario(
    page: Page,
) -> list[dict[str, Any]]:
    try:
        return page.locator(
            "input"
        ).evaluate_all(
            """
            elements => elements.map(element => ({
                type: (
                    element.getAttribute("type")
                    || "text"
                ).toLowerCase(),

                name: (
                    element.getAttribute("name")
                    || ""
                ),

                id: (
                    element.getAttribute("id")
                    || ""
                ),

                placeholder: (
                    element.getAttribute("placeholder")
                    || ""
                ),

                ariaLabel: (
                    element.getAttribute("aria-label")
                    || ""
                ),

                autocomplete: (
                    element.getAttribute("autocomplete")
                    || ""
                ),

                className: (
                    element.getAttribute("class")
                    || ""
                ),

                pattern: (
                    element.getAttribute("pattern")
                    || ""
                ),

                maxlength: (
                    element.getAttribute("maxlength")
                    || ""
                ),

                inputmode: (
                    element.getAttribute("inputmode")
                    || ""
                ),

                dataMask: (
                    element.getAttribute("data-mask")
                    || element.getAttribute("data-inputmask")
                    || element.getAttribute("data-mask-pattern")
                    || ""
                ),

                outerHTML: element.outerHTML
            }))
            """
        )

    except Exception:
        return []


def identificar_tipo_campo(
    campo: dict[str, Any],
) -> str:
    conteudo = " ".join(
        [
            str(campo.get("name", "")),
            str(campo.get("id", "")),
            str(campo.get("placeholder", "")),
            str(campo.get("ariaLabel", "")),
            str(campo.get("autocomplete", "")),
            str(campo.get("className", "")),
        ]
    ).casefold()

    tipo_html = str(
        campo.get(
            "type",
            "",
        )
    ).casefold()

    if (
        tipo_html == "email"
        or "email" in conteudo
        or "e-mail" in conteudo
    ):
        return "email"

    if any(
        termo in conteudo
        for termo in [
            "telefone",
            "phone",
            "celular",
            "whatsapp",
            "fone",
        ]
    ):
        return "telefone"

    if (
        tipo_html == "tel"
        or "tel" in conteudo.split()
    ):
        return "telefone"

    if "cep" in conteudo:
        return "cep"

    if "cnpj" in conteudo:
        return "cnpj"

    if "cpf" in conteudo:
        return "cpf"

    return ""


def descrever_campo(
    campo: dict[str, Any],
) -> str:
    identificador = (
        campo.get("name")
        or campo.get("id")
        or campo.get("placeholder")
        or campo.get("ariaLabel")
        or "campo sem identificação"
    )

    return str(
        identificador
    )


def possui_configuracao_mascara(
    campo: dict[str, Any],
    tipo_campo: str,
) -> bool:
    tipo_html = str(
        campo.get(
            "type",
            "",
        )
    ).casefold()

    placeholder = str(
        campo.get(
            "placeholder",
            "",
        )
    ).strip()

    pattern = str(
        campo.get(
            "pattern",
            "",
        )
    ).strip()

    maxlength = str(
        campo.get(
            "maxlength",
            "",
        )
    ).strip()

    data_mask = str(
        campo.get(
            "dataMask",
            "",
        )
    ).strip()

    class_name = str(
        campo.get(
            "className",
            "",
        )
    ).casefold()

    outer_html = str(
        campo.get(
            "outerHTML",
            "",
        )
    ).casefold()

    if tipo_campo == "email":
        return tipo_html == "email"

    if data_mask:
        return True

    if pattern:
        return True

    if "mask" in class_name:
        return True

    if any(
        termo in outer_html
        for termo in [
            "data-mask",
            "data-inputmask",
            "data-mask-pattern",
            "jquery-mask",
            "imask",
        ]
    ):
        return True

    if tipo_campo == "telefone":
        placeholder_valido = bool(
            re.search(
                r"\(\d{2}\).*\d{4,5}-\d{4}",
                placeholder,
            )
        )

        maxlength_valido = maxlength in {
            "14",
            "15",
            "16",
            "17",
            "18",
            "19",
        }

        return (
            placeholder_valido
            or maxlength_valido
        )

    if tipo_campo == "cep":
        return (
            bool(
                re.search(
                    r"\d{5}-\d{3}",
                    placeholder,
                )
            )
            or maxlength == "9"
        )

    if tipo_campo == "cpf":
        return (
            bool(
                re.search(
                    r"\d{3}\.\d{3}\.\d{3}-\d{2}",
                    placeholder,
                )
            )
            or maxlength == "14"
        )

    if tipo_campo == "cnpj":
        return (
            bool(
                re.search(
                    (
                        r"\d{2}\.\d{3}\.\d{3}"
                        r"/\d{4}-\d{2}"
                    ),
                    placeholder,
                )
            )
            or maxlength == "18"
        )

    return False


class PhoneFormattingCheck(
    BaseCheck
):
    nome = "Phone Numbers - Formatting"
    categoria = "Contato"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        links = coletar_links(
            page=page,
            seletor='a[href^="tel:"]',
        )

        problemas: list[str] = []
        numeros_validos: list[str] = []

        for link in links:
            href = link["href"]
            texto = link["texto"]

            if not telefone_href_valido(
                href
            ):
                problemas.append(
                    f'Link telefônico inválido: "{href}"'
                )

                continue

            numeros_validos.append(
                href
            )

            if (
                texto
                and re.search(
                    r"\d",
                    texto,
                )
                and not PADRAO_TELEFONE_FORMATADO.search(
                    texto
                )
            ):
                problemas.append(
                    (
                        "Número visível sem a formatação "
                        f'brasileira esperada: "{texto}"'
                    )
                )

        problemas = remover_duplicados(
            problemas
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados={
                    "links_analisados": len(
                        links
                    ),
                    "problemas": problemas,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(links)} link(s) telefônico(s) "
                "analisado(s)."
            ),
            dados={
                "links_analisados": len(
                    links
                ),
                "telefones_validos": remover_duplicados(
                    numeros_validos
                ),
            },
        )


class EmailFormattingCheck(
    BaseCheck
):
    nome = "Emails - Formatting"
    categoria = "Contato"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        links = coletar_links(
            page=page,
            seletor='a[href^="mailto:"]',
        )

        problemas: list[str] = []
        emails_validos: list[str] = []

        for link in links:
            href = unquote(
                link["href"]
            )

            texto = link["texto"]

            valor = href.split(
                ":",
                1,
            )[-1].split(
                "?",
                1,
            )[0]

            enderecos = re.split(
                r"[,;]",
                valor,
            )

            for endereco in enderecos:
                email = endereco.strip()

                if not email:
                    continue

                if not PADRAO_EMAIL.fullmatch(
                    email
                ):
                    problemas.append(
                        f'Link de e-mail inválido: "{href}"'
                    )

                else:
                    emails_validos.append(
                        email
                    )

            if (
                "@" in texto
                and not PADRAO_EMAIL.fullmatch(
                    texto
                )
            ):
                problemas.append(
                    (
                        "E-mail visível com formato inválido: "
                        f'"{texto}"'
                    )
                )

        problemas = remover_duplicados(
            problemas
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados={
                    "links_analisados": len(
                        links
                    ),
                    "problemas": problemas,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(links)} link(s) de e-mail "
                "analisado(s)."
            ),
            dados={
                "links_analisados": len(
                    links
                ),
                "emails_validos": remover_duplicados(
                    emails_validos
                ),
            },
        )


class CepFormattingCheck(
    BaseCheck
):
    nome = "CEP - Formatting"
    categoria = "Contato"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        texto = obter_texto_pagina(
            page
        )

        ocorrencias = re.findall(
            (
                r"\bCEP\b\s*[:\-]?\s*"
                r"(\d{5}\s*-?\s*\d{3})\b"
            ),
            texto,
            flags=re.IGNORECASE,
        )

        problemas: list[str] = []
        ceps_validos: list[str] = []

        for ocorrencia in ocorrencias:
            cep = re.sub(
                r"\s+",
                "",
                ocorrencia,
            )

            if not PADRAO_CEP_FORMATADO.fullmatch(
                cep
            ):
                problemas.append(
                    (
                        "CEP sem a formatação esperada "
                        f'00000-000: "{ocorrencia}"'
                    )
                )

            else:
                ceps_validos.append(
                    cep
                )

        problemas = remover_duplicados(
            problemas
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados={
                    "ceps_encontrados": len(
                        ocorrencias
                    ),
                    "problemas": problemas,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(ocorrencias)} CEP(s) "
                "identificado(s)."
            ),
            dados={
                "ceps_encontrados": len(
                    ocorrencias
                ),
                "ceps_validos": remover_duplicados(
                    ceps_validos
                ),
            },
        )


class CpfCnpjFormattingCheck(
    BaseCheck
):
    nome = "CPF/CNPJ - Formatting"
    categoria = "Contato"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        texto = obter_texto_pagina(
            page
        )

        cpfs = re.findall(
            (
                r"\bCPF\b\s*[:\-]?\s*"
                r"(\d{3}\.?\d{3}\.?\d{3}-?\d{2})"
            ),
            texto,
            flags=re.IGNORECASE,
        )

        cnpjs = re.findall(
            (
                r"\bCNPJ\b\s*[:\-]?\s*"
                r"(\d{2}\.?\d{3}\.?\d{3}"
                r"/?\d{4}-?\d{2})"
            ),
            texto,
            flags=re.IGNORECASE,
        )

        problemas: list[str] = []
        documentos_validos: list[str] = []

        for cpf in cpfs:
            cpf_limpo = re.sub(
                r"\s+",
                "",
                cpf,
            )

            if not PADRAO_CPF_FORMATADO.fullmatch(
                cpf_limpo
            ):
                problemas.append(
                    (
                        "CPF sem a formatação esperada "
                        f'000.000.000-00: "{cpf}"'
                    )
                )

            else:
                documentos_validos.append(
                    cpf_limpo
                )

        for cnpj in cnpjs:
            cnpj_limpo = re.sub(
                r"\s+",
                "",
                cnpj,
            )

            if not PADRAO_CNPJ_FORMATADO.fullmatch(
                cnpj_limpo
            ):
                problemas.append(
                    (
                        "CNPJ sem a formatação esperada "
                        f'00.000.000/0000-00: "{cnpj}"'
                    )
                )

            else:
                documentos_validos.append(
                    cnpj_limpo
                )

        problemas = remover_duplicados(
            problemas
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados={
                    "cpfs_encontrados": len(
                        cpfs
                    ),
                    "cnpjs_encontrados": len(
                        cnpjs
                    ),
                    "problemas": problemas,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(cpfs)} CPF(s) e "
                f"{len(cnpjs)} CNPJ(s) identificado(s)."
            ),
            dados={
                "cpfs_encontrados": len(
                    cpfs
                ),
                "cnpjs_encontrados": len(
                    cnpjs
                ),
                "documentos_validos": remover_duplicados(
                    documentos_validos
                ),
            },
        )


class InputMaskCheck(
    BaseCheck
):
    nome = "Input Masks"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        campos = coletar_campos_formulario(
            page
        )

        campos_relevantes: list[
            dict[str, str]
        ] = []

        problemas: list[str] = []

        for campo in campos:
            tipo_campo = identificar_tipo_campo(
                campo
            )

            if not tipo_campo:
                continue

            identificador = descrever_campo(
                campo
            )

            campos_relevantes.append(
                {
                    "campo": identificador,
                    "tipo": tipo_campo,
                }
            )

            if not possui_configuracao_mascara(
                campo=campo,
                tipo_campo=tipo_campo,
            ):
                problemas.append(
                    (
                        f'Campo "{identificador}" '
                        f"identificado como {tipo_campo}, "
                        "mas sem configuração aparente de "
                        "máscara ou validação."
                    )
                )

        problemas = remover_duplicados(
            problemas
        )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(
                    problemas
                ),
                dados={
                    "campos_relevantes": campos_relevantes,
                    "problemas": problemas,
                },
            )

        return self.resultado(
            status="approved",
            observacao=(
                f"{len(campos_relevantes)} campo(s) "
                "de contato ou documento analisado(s)."
            ),
            dados={
                "campos_relevantes": campos_relevantes,
            },
        )