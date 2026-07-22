from typing import Any
from urllib.parse import unquote, urlparse

from playwright.sync_api import Page

from checks.base_check import BaseCheck


LIMITE_CARACTERES_URL = 115


def obter_url(contexto: dict[str, Any]) -> str:
    return (
        contexto.get("url_solicitada")
        or contexto.get("url_final")
        or ""
    )


class UrlContainsSpaceCheck(BaseCheck):
    nome = "URLs - Contains Space"
    categoria = "URLs"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        url = obter_url(contexto)
        url_decodificada = unquote(url)

        if " " in url_decodificada:
            return self.resultado(
                status="rejected",
                observacao="A URL possui espaço.",
                dados={"url": url},
            )

        return self.resultado(
            status="approved",
            dados={"url": url},
        )


class UrlMultipleSlashesCheck(BaseCheck):
    nome = "URLs - Multiple Slashes"
    categoria = "URLs"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        url = obter_url(contexto)
        caminho = urlparse(url).path

        if "//" in caminho:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A URL possui múltiplas barras consecutivas "
                    "em seu caminho."
                ),
                dados={
                    "url": url,
                    "caminho": caminho,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url": url,
                "caminho": caminho,
            },
        )


class UrlNonAsciiCheck(BaseCheck):
    nome = "URLs - Non ASCII Characters URL"
    categoria = "URLs"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        url = obter_url(contexto)
        url_decodificada = unquote(url)

        caracteres_nao_ascii = sorted(
            {
                caractere
                for caractere in url_decodificada
                if ord(caractere) > 127
            }
        )

        if caracteres_nao_ascii:
            return self.resultado(
                status="rejected",
                observacao=(
                    "A URL possui caracteres não ASCII: "
                    + ", ".join(caracteres_nao_ascii)
                ),
                dados={
                    "url": url,
                    "caracteres_nao_ascii": caracteres_nao_ascii,
                },
            )

        return self.resultado(
            status="approved",
            dados={"url": url},
        )


class UrlOverCharactersCheck(BaseCheck):
    nome = "URLs - Over Characters"
    categoria = "URLs"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        url = obter_url(contexto)
        quantidade = len(url)

        if quantidade > LIMITE_CARACTERES_URL:
            return self.resultado(
                status="rejected",
                observacao=(
                    f"A URL possui {quantidade} caracteres. "
                    f"O limite configurado é "
                    f"{LIMITE_CARACTERES_URL}."
                ),
                dados={
                    "url": url,
                    "quantidade_caracteres": quantidade,
                    "limite": LIMITE_CARACTERES_URL,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url": url,
                "quantidade_caracteres": quantidade,
                "limite": LIMITE_CARACTERES_URL,
            },
        )


class UrlUppercaseCheck(BaseCheck):
    nome = "URLs - Uppercase"
    categoria = "URLs"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        url = obter_url(contexto)
        partes = urlparse(url)

        caminho_decodificado = unquote(partes.path)

        letras_maiusculas = sorted(
            {
                caractere
                for caractere in caminho_decodificado
                if caractere.isupper()
            }
        )

        if letras_maiusculas:
            return self.resultado(
                status="rejected",
                observacao=(
                    "O caminho da URL possui letras maiúsculas."
                ),
                dados={
                    "url": url,
                    "caminho": caminho_decodificado,
                    "letras_maiusculas": letras_maiusculas,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "url": url,
                "caminho": caminho_decodificado,
            },
        )