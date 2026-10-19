from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

from playwright.sync_api import Page

from checks.base_check import BaseCheck


EMAIL_RE = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)
DIGITS_RE = re.compile(r"\D+")
PHONE_RE = re.compile(r"^\+?\d[\d\s().-]{7,}\d$")
CEP_RE = re.compile(r"^\d{5}-?\d{3}$")
CPF_RE = re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
CNPJ_RE = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")

BUSINESS_WORDS = {
    "empresa", "company", "organization", "organizacao",
    "razao", "social", "fantasia", "business",
}
EMAIL_WORDS = {"email", "mail"}
PHONE_WORDS = {"telefone", "phone", "celular", "whatsapp", "fone", "tel"}
MASK_LIBRARY_HINTS = (
    "inputmask", "data-inputmask", "jquery.mask", "jquery-mask",
    "imask", "cleave", "data-mask", "data-mask-pattern",
)


def normalizar_espacos(valor: Any) -> str:
    return re.sub(r"\s+", " ", str(valor or "")).strip()


def remover_duplicados(valores: list[str]) -> list[str]:
    resultado: list[str] = []
    vistos: set[str] = set()
    for valor in valores:
        chave = normalizar_espacos(valor).casefold()
        if chave and chave not in vistos:
            vistos.add(chave)
            resultado.append(normalizar_espacos(valor))
    return resultado


def obter_texto_pagina(page: Page) -> str:
    try:
        return normalizar_espacos(page.locator("body").inner_text(timeout=3000))
    except Exception:
        return ""


def coletar_links(page: Page) -> list[dict[str, str]]:
    try:
        return page.locator("a[href]").evaluate_all(
            """els => els.map(a => ({
                href: a.getAttribute('href') || '',
                texto: (a.innerText || a.getAttribute('aria-label') || '').trim()
            }))"""
        )
    except Exception:
        return []


def coletar_campos_formulario(page: Page) -> list[dict[str, Any]]:
    """Coleta atributos relevantes sem preencher nem enviar formulários."""
    try:
        return page.locator(
            "input:not([type='hidden']), textarea, select"
        ).evaluate_all(
            """els => els.map(el => {
                const get = name => el.getAttribute(name) || '';
                return {
                    type: (el.getAttribute('type') || (el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName.toLowerCase())),
                    name: get('name'),
                    id: get('id'),
                    placeholder: get('placeholder'),
                    ariaLabel: get('aria-label'),
                    autocomplete: get('autocomplete'),
                    className: typeof el.className === 'string' ? el.className : '',
                    pattern: get('pattern'),
                    maxlength: get('maxlength'),
                    inputmode: get('inputmode'),
                    dataMask: get('data-mask') || get('data-inputmask') || get('data-mask-pattern'),
                    outerHTML: (el.outerHTML || '').slice(0, 1800),
                    required: !!el.required,
                    visible: !!(el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' && getComputedStyle(el).display !== 'none'),
                    disabled: !!el.disabled,
                    value: el.value || ''
                };
            })"""
        )
    except Exception:
        return []


def identificar_tipo_campo(campo: dict[str, Any]) -> str:
    tipo_html = str(campo.get("type", "")).strip().casefold()
    autocomplete = str(campo.get("autocomplete", "")).strip().casefold()
    identificadores = [
        str(campo.get("name", "")),
        str(campo.get("id", "")),
        str(campo.get("placeholder", "")),
        str(campo.get("ariaLabel", "")),
    ]
    texto_identificadores = " ".join(identificadores).casefold()
    palavras_identificadores = set(
        re.sub(r"[^a-z0-9]+", " ", texto_identificadores).split()
    )

    # O significado do campo prevalece sobre um type/autocomplete HTML incorreto.
    # "empresa" isolado não é um campo de e-mail, telefone ou documento.
    tem_identificador_empresa = bool(palavras_identificadores & BUSINESS_WORDS)
    tem_identificador_email = bool(palavras_identificadores & EMAIL_WORDS)
    if tem_identificador_empresa and not tem_identificador_email:
        return ""

    if tipo_html == "email" or autocomplete == "email":
        return "email"
    if tipo_html == "tel" or autocomplete in {"tel", "tel-national", "tel-local"}:
        return "telefone"
    if tem_identificador_email:
        return "email"

    texto = " ".join(identificadores + [str(campo.get("className", ""))]).casefold()
    palavras = set(re.sub(r"[^a-z0-9]+", " ", texto).split())
    if palavras & PHONE_WORDS:
        return "telefone"
    if "cep" in palavras:
        return "cep"
    if "cnpj" in palavras:
        return "cnpj"
    if "cpf" in palavras:
        return "cpf"
    return ""


def descrever_campo(campo: dict[str, Any]) -> str:
    identificador = (
        campo.get("name")
        or campo.get("id")
        or campo.get("placeholder")
        or campo.get("ariaLabel")
        or "campo sem identificação"
    )
    return str(identificador)


def _digitos(valor: Any) -> str:
    return DIGITS_RE.sub("", str(valor or ""))


def normalizar_numero_telefone(valor: Any) -> str:
    digitos = _digitos(valor)
    if len(digitos) in {12, 13} and digitos.startswith("55"):
        digitos = digitos[2:]
    return digitos


def telefone_href_valido(href: Any) -> bool:
    valor = unquote(str(href or "")).strip()
    if not valor.casefold().startswith("tel:"):
        return False
    numero = normalizar_numero_telefone(valor[4:].split("?")[0])
    if len(numero) not in {10, 11}:
        return False
    # Celular brasileiro com DDD deve ter 9 como primeiro dígito local.
    if len(numero) == 11 and numero[2] != "9":
        return False
    return True


def _tem_indicio_mascara(campo: dict[str, Any]) -> bool:
    data_mask = str(campo.get("dataMask", "")).strip()
    pattern = str(campo.get("pattern", "")).strip()
    class_name = str(campo.get("className", "")).casefold()
    outer_html = str(campo.get("outerHTML", "")).casefold()
    placeholder = str(campo.get("placeholder", "")).strip()

    if data_mask or pattern:
        return True
    if any(hint in class_name or hint in outer_html for hint in MASK_LIBRARY_HINTS):
        return True
    # Placeholders formatados são evidência de formato esperado, não prova absoluta.
    if any(char in placeholder for char in "()-/ .") and any(ch.isdigit() for ch in placeholder):
        return True
    return False


def _biblioteca_mascara_carregada(page: Page) -> bool:
    """Indício complementar; não reprova campo apenas por falta de atributos."""
    try:
        return bool(
            page.evaluate(
                """() => !!(
                    window.Inputmask ||
                    window.IMask ||
                    window.Cleave ||
                    (window.jQuery && window.jQuery.fn && window.jQuery.fn.mask)
                )"""
            )
        )
    except Exception:
        return False



def possui_configuracao_mascara(
    campo: dict[str, Any],
    tipo_campo: str,
    biblioteca_mascara_carregada: bool = False,
) -> bool:
    tipo_html = str(campo.get("type", "")).strip().casefold()

    if tipo_campo == "email":
        return tipo_html == "email" or _tem_indicio_mascara(campo)

    # Só considera evidências encontradas no próprio campo.
    # Uma biblioteca carregada na página não comprova que o campo
    # esteja efetivamente utilizando uma máscara.
    if _tem_indicio_mascara(campo):
        return True

    return False

class PhoneFormattingCheck(BaseCheck):
    nome = "Texto Formatação - Números de Telefone"
    categoria = "Contatos"

    def executar(self, page: Page, contexto: dict[str, Any]) -> dict[str, Any]:
        links = coletar_links(page)
        problemas: list[str] = []
        encontrados: list[dict[str, str]] = []
        for link in links:
            href = link.get("href", "").strip()
            if href.casefold().startswith("tel:"):
                numero = normalizar_numero_telefone(href[4:].split("?")[0])
                item = {"href": href, "numero": numero, "texto": link.get("texto", "")}
                encontrados.append(item)
                if not telefone_href_valido(href):
                    problemas.append(
                        f"Link telefônico possivelmente inválido ou sem DDD: {href}"
                    )
        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(remover_duplicados(problemas)),
                dados={"telefones": encontrados, "problemas": remover_duplicados(problemas)},
            )
        if encontrados:
            return self.resultado(
                status="approved",
                observacao=f"{len(encontrados)} link(s) telefônico(s) com formato válido.",
                dados={"telefones": encontrados},
            )
        return self.resultado(
            status="warning",
            observacao="Nenhum link tel: encontrado nesta página; confirmar se há telefone que deveria ser clicável.",
            dados={"telefones": []},
        )


class EmailFormattingCheck(BaseCheck):
    nome = "Texto Formatação - E-mails"
    categoria = "Contatos"

    def executar(self, page: Page, contexto: dict[str, Any]) -> dict[str, Any]:
        links = coletar_links(page)
        encontrados: list[dict[str, str]] = []
        problemas: list[str] = []
        for link in links:
            href = link.get("href", "").strip()
            if href.casefold().startswith("mailto:"):
                email = unquote(href[7:].split("?")[0]).strip()
                encontrados.append({"href": href, "email": email})
                if not EMAIL_RE.match(email):
                    problemas.append(f"Link de e-mail possivelmente inválido: {href}")
        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(remover_duplicados(problemas)),
                dados={"emails": encontrados, "problemas": remover_duplicados(problemas)},
            )
        return self.resultado(
            status="approved" if encontrados else "warning",
            observacao=(
                f"{len(encontrados)} link(s) mailto: com formato válido."
                if encontrados
                else "Nenhum link mailto: encontrado nesta página."
            ),
            dados={"emails": encontrados},
        )


class CepFormattingCheck(BaseCheck):
    nome = "Texto Formatação - CEP"
    categoria = "Formulários"

    def executar(self, page: Page, contexto: dict[str, Any]) -> dict[str, Any]:
        return _executar_check_formato_documento(page, self, {"cep"})


class CpfCnpjFormattingCheck(BaseCheck):
    nome = "Texto Formatação - CPF/CNPJ"
    categoria = "Formulários"

    def executar(self, page: Page, contexto: dict[str, Any]) -> dict[str, Any]:
        return _executar_check_formato_documento(page, self, {"cpf", "cnpj"})


def _executar_check_formato_documento(
    page: Page,
    check: BaseCheck,
    tipos_permitidos: set[str],
) -> dict[str, Any]:
    campos = coletar_campos_formulario(page)
    relevantes: list[dict[str, str]] = []
    problemas: list[str] = []
    biblioteca = _biblioteca_mascara_carregada(page)
    for campo in campos:
        tipo = identificar_tipo_campo(campo)
        if tipo not in tipos_permitidos:
            continue
        registro = {"campo": descrever_campo(campo), "tipo": tipo}
        relevantes.append(registro)
        if not possui_configuracao_mascara(campo, tipo, biblioteca):
            problemas.append(
                f"Campo '{registro['campo']}' identificado como {tipo.upper()} sem evidência de máscara/formato."
            )
    if problemas:
        return check.resultado(
            status="rejected",
            observacao="\n".join(remover_duplicados(problemas)),
            dados={"campos_relevantes": relevantes, "problemas": remover_duplicados(problemas)},
        )
    return check.resultado(
        status="approved" if relevantes else "warning",
        observacao=(
            f"{len(relevantes)} campo(s) de documento analisado(s)."
            if relevantes
            else "Nenhum campo de documento aplicável encontrado."
        ),
        dados={"campos_relevantes": relevantes},
    )


class InputMaskCheck(BaseCheck):
    nome = "Input Masks"
    categoria = "Formulários"

    def executar(self, page: Page, contexto: dict[str, Any]) -> dict[str, Any]:
        campos = coletar_campos_formulario(page)
        relevantes: list[dict[str, str]] = []
        problemas: list[str] = []
        biblioteca = _biblioteca_mascara_carregada(page)

        for campo in campos:
            if campo.get("disabled") or not campo.get("visible", True):
                continue
            tipo = identificar_tipo_campo(campo)
            if tipo not in {"telefone", "email", "cep", "cpf", "cnpj"}:
                continue

            identificador = descrever_campo(campo)
            relevantes.append({"campo": identificador, "tipo": tipo})
            if not possui_configuracao_mascara(campo, tipo, biblioteca):
                problemas.append(
                    f"Campo '{identificador}' identificado como {tipo.upper()} sem evidência de máscara ou validação de formato."
                )

        if problemas:
            return self.resultado(
                status="rejected",
                observacao="\n".join(remover_duplicados(problemas)),
                dados={
                    "campos_relevantes": relevantes,
                    "problemas": remover_duplicados(problemas),
                },
            )

        return self.resultado(
            status="approved" if relevantes else "warning",
            observacao=(
                f"{len(relevantes)} campo(s) de contato/documento analisado(s)."
                if relevantes
                else "Nenhum campo de contato/documento aplicável encontrado."
            ),
            dados={"campos_relevantes": relevantes},
        )
