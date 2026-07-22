from urllib.parse import (
    urldefrag,
    urljoin,
    urlparse,
    urlunparse,
)


PREFIXOS_NAO_HTTP = (
    "#",
    "mailto:",
    "tel:",
    "javascript:",
    "whatsapp:",
    "data:",
)


def normalizar_dominio(
    dominio: str,
) -> str:
    """
    Remove apenas o prefixo WWW.

    Exemplos considerados iguais:

    www.trevisan.com.br
    trevisan.com.br

    Exemplos considerados diferentes:

    trevisan.com.br
    trevisan.edu.br
    """
    dominio_normalizado = (
        dominio
        .strip()
        .casefold()
        .rstrip(".")
    )

    if dominio_normalizado.startswith(
        "www."
    ):
        dominio_normalizado = (
            dominio_normalizado[4:]
        )

    return dominio_normalizado


def obter_dominio_normalizado(
    url: str,
) -> str:
    partes = urlparse(
        url
    )

    hostname = partes.hostname or ""

    return normalizar_dominio(
        hostname
    )


def normalizar_url(
    url: str,
) -> str:
    valor = url.strip()

    if not valor:
        raise ValueError(
            "Digite uma URL para iniciar a auditoria."
        )

    if "://" not in valor:
        valor = f"https://{valor}"

    partes = urlparse(
        valor
    )

    esquema = partes.scheme.casefold()

    if esquema not in {
        "http",
        "https",
    }:
        raise ValueError(
            "A URL deve utilizar HTTP ou HTTPS."
        )

    if not partes.hostname:
        raise ValueError(
            "A URL informada não possui um domínio válido."
        )

    caminho = partes.path or "/"

    url_normalizada = urlunparse(
        (
            esquema,
            partes.netloc.casefold(),
            caminho,
            partes.params,
            partes.query,
            "",
        )
    )

    url_sem_fragmento, _ = urldefrag(
        url_normalizada
    )

    return url_sem_fragmento


def resolver_link_http(
    link: str,
    url_base: str,
) -> str | None:
    valor = link.strip()

    if not valor:
        return None

    if valor.casefold().startswith(
        PREFIXOS_NAO_HTTP
    ):
        return None

    url_absoluta = urljoin(
        url_base,
        valor,
    )

    url_sem_fragmento, _ = urldefrag(
        url_absoluta
    )

    partes = urlparse(
        url_sem_fragmento
    )

    if partes.scheme.casefold() not in {
        "http",
        "https",
    }:
        return None

    if not partes.hostname:
        return None

    return url_sem_fragmento


def eh_url_interna(
    url: str,
    url_principal: str,
) -> bool:
    """
    Faz uma comparação estrita entre os domínios.

    Não utiliza:
    - contains;
    - startswith;
    - endswith.

    Dessa forma, trevisan.edu.br não pode ser
    confundido com trevisan.com.br.
    """
    dominio_url = obter_dominio_normalizado(
        url
    )

    dominio_principal = obter_dominio_normalizado(
        url_principal
    )

    if not dominio_url:
        return False

    if not dominio_principal:
        return False

    return dominio_url == dominio_principal