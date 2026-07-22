from core.auditor import executar_auditoria
from services.http_link_validator import (
    limpar_cache_links,
)
from services.image_size_validator import (
    limpar_cache_imagens,
)
from services.image_validator import (
    limpar_cache_imagens as limpar_cache_validacao_imagens,
)
from services.pagespeed_service import (
    limpar_cache_pagespeed,
)
from services.responsive_service import (
    limpar_cache_responsividade,
)
from services.site_files_validator import (
    limpar_cache_site_files,
)
from utils.url_helper import normalizar_url


def main() -> None:
    print("=" * 55)
    print("QA AUDITOR FRAMEWORK")
    print("=" * 55)

    url_digitada = input(
        "\nDigite a URL do site: "
    )

    try:
        url_inicial = normalizar_url(
            url_digitada
        )

    except ValueError as erro:
        print(
            f"\n❌ {erro}"
        )
        return

    try:
        limpar_cache_links()
        limpar_cache_imagens()
        limpar_cache_validacao_imagens()
        limpar_cache_pagespeed()
        limpar_cache_responsividade()
        limpar_cache_site_files()

        executar_auditoria(
            url_inicial
        )

    except KeyboardInterrupt:
        print(
            "\n⚠️ Auditoria interrompida "
            "pelo usuário."
        )

    except Exception as erro:
        print(
            "\n❌ Ocorreu um erro durante a auditoria."
        )

        print(
            erro
        )


if __name__ == "__main__":
    main()