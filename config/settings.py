
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# =========================================================
# Caminhos do projeto
# =========================================================

if getattr(sys, "frozen", False):
    # Quando executado como aplicativo empacotado,
    # usa a pasta onde o executável está localizado.
    DIRETORIO_RAIZ = Path(sys.executable).resolve().parent
else:
    # Mantém o comportamento normal durante o desenvolvimento.
    DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent

ARQUIVO_ENV = DIRETORIO_RAIZ / ".env"

REPORTS_DIR = DIRETORIO_RAIZ / "reports"

SCREENSHOTS_DIR = DIRETORIO_RAIZ / "screenshots"

RESPONSIVE_SCREENSHOTS_DIR = SCREENSHOTS_DIR / "responsive"


# =========================================================
# Carregamento do arquivo .env
# =========================================================

load_dotenv(
    dotenv_path=ARQUIVO_ENV,
    override=True,
)


# =========================================================
# Leitura de variáveis de ambiente
# =========================================================

def obter_variavel_texto(
    nome: str,
    valor_padrao: str = "",
) -> str:
    valor = os.getenv(nome, valor_padrao)

    if valor is None:
        return valor_padrao

    return str(valor).strip()


def obter_variavel_inteira(
    nome: str,
    valor_padrao: int,
) -> int:
    valor = obter_variavel_texto(
        nome,
        str(valor_padrao),
    )

    try:
        return int(valor)
    except (TypeError, ValueError):
        return valor_padrao


def obter_variavel_booleana(
    nome: str,
    valor_padrao: bool,
) -> bool:
    valor = obter_variavel_texto(
        nome,
        str(valor_padrao),
    ).lower()

    valores_verdadeiros = {
        "true",
        "1",
        "yes",
        "sim",
        "on",
    }

    valores_falsos = {
        "false",
        "0",
        "no",
        "nao",
        "não",
        "off",
    }

    if valor in valores_verdadeiros:
        return True

    if valor in valores_falsos:
        return False

    return valor_padrao


# =========================================================
# Descoberta e seleção de páginas
# =========================================================

LIMITE_DESCOBERTA = obter_variavel_inteira(
    "LIMITE_DESCOBERTA",
    500,
)

LIMITE_MPIS = obter_variavel_inteira(
    "LIMITE_MPIS",
    10,
)

# Mantido para compatibilidade com módulos existentes.
LIMITE_PAGINAS = obter_variavel_inteira(
    "LIMITE_PAGINAS",
    20,
)


# =========================================================
# Configurações gerais
# =========================================================

VIEWPORT_DESKTOP = {
    "width": 1920,
    "height": 1080,
}

VIEWPORT_TABLET = {
    "width": 768,
    "height": 1024,
}

VIEWPORT_MOBILE = {
    "width": 394,
    "height": 852,
}

TIMEOUT_NAVEGACAO = obter_variavel_inteira(
    "TIMEOUT_NAVEGACAO",
    60000,
)

TEMPO_ESPERA_PAGINA = obter_variavel_inteira(
    "TEMPO_ESPERA_PAGINA",
    1000,
)

TEMPO_ESPERA_RESPONSIVIDADE = obter_variavel_inteira(
    "TEMPO_ESPERA_RESPONSIVIDADE",
    800,
)

HEADLESS = obter_variavel_booleana(
    "HEADLESS",
    True,
)


# =========================================================
# PageSpeed Insights
# =========================================================

PAGESPEED_API_URL = (
    "https://www.googleapis.com/"
    "pagespeedonline/v5/runPagespeed"
)

PAGESPEED_API_KEY = obter_variavel_texto(
    "PAGESPEED_API_KEY"
)

PAGESPEED_TIMEOUT_SEGUNDOS = obter_variavel_inteira(
    "PAGESPEED_TIMEOUT_SEGUNDOS",
    120,
)

PAGESPEED_SOMENTE_HOME = obter_variavel_booleana(
    "PAGESPEED_SOMENTE_HOME",
    True,
)

PAGESPEED_ESTRATEGIAS = (
    "mobile",
    "desktop",
)

PAGESPEED_CATEGORIAS = (
    "performance",
    "accessibility",
    "best-practices",
    "seo",
)

PAGESPEED_LIMITES = {
    "performance": 70,
    "accessibility": 90,
    "best-practices": 90,
    "seo": 90,
}


# =========================================================
# Funções auxiliares do PageSpeed
# =========================================================

def pagespeed_esta_configurado() -> bool:
    return bool(PAGESPEED_API_KEY)


def mascarar_chave(
    chave: str,
) -> str:
    chave_limpa = chave.strip()

    if not chave_limpa:
        return "não configurada"

    if len(chave_limpa) <= 8:
        return "*" * len(chave_limpa)

    return (
        f"{chave_limpa[:4]}"
        f"{'*' * 8}"
        f"{chave_limpa[-4:]}"
    )


def obter_status_pagespeed() -> dict[str, str | bool]:
    return {
        "configurado": pagespeed_esta_configurado(),
        "chave_mascarada": mascarar_chave(
            PAGESPEED_API_KEY
        ),
        "arquivo_env": str(ARQUIVO_ENV),
        "arquivo_env_existe": ARQUIVO_ENV.exists(),
    }
