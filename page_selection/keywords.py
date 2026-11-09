from __future__ import annotations


PALAVRAS_CATEGORIAS: dict[
    str,
    tuple[str, ...],
] = {
    "empresa": (
        "empresa",
        "a empresa",
        "sobre",
        "sobre nos",
        "quem somos",
        "institucional",
        "nossa empresa",
        "nossa historia",
        "conheca a empresa",
        "conheca nossa historia",
    ),

    "produtos": (
        "produto",
        "produtos",
        "catalogo",
        "catalogo de produtos",
        "linha de produtos",
        "nossos produtos",
    ),

    "servicos": (
        "servico",
        "servicos",
        "nossos servicos",
        "o que fazemos",
        "solucoes",
        "solucoes oferecidas",
    ),

    "contato": (
        "contato",
        "fale conosco",
        "entre em contato",
        "orcamento",
        "solicite um orcamento",
        "pedir orcamento",
        "atendimento",
    ),

    "trabalhe_conosco": (
        "trabalhe conosco",
        "carreira",
        "carreiras",
        "vaga",
        "vagas",
        "oportunidade",
        "oportunidades",
        "envie seu curriculo",
        "banco de talentos",
    ),
}


ROTULOS_CATEGORIAS: dict[str, str] = {
    "home": "Home",
    "empresa": "Empresa",
    "produtos": "Produtos",
    "servicos": "Serviços",
    "contato": "Contato",
    "trabalhe_conosco": (
        "Trabalhe Conosco"
    ),
    "mpi": "MPI",
    "outra": "Outra página",
}


CATEGORIAS_ESTRUTURAIS: tuple[
    str,
    ...,
] = (
    "home",
    "empresa",
    "produtos",
    "servicos",
    "contato",
    "trabalhe_conosco",
)


TERMOS_EXCLUSAO_MPI: tuple[str, ...] = (
    "blog",
    "noticia",
    "noticias",
    "artigo",
    "artigos",
    "categoria",
    "tag",
    "autor",
    "author",
    "pesquisa",
    "buscar",
    "search",
    "politica de privacidade",
    "privacidade",
    "politica de cookies",
    "cookies",
    "termos de uso",
    "termos e condicoes",
    "mapa do site",
    "sitemap",
    "login",
    "admin",
    "wp admin",
    "wp login",
    "carrinho",
    "checkout",
    "minha conta",
    "obrigado",
    "obrigada",
    "sucesso",
    "erro",
    "404",
    "feed",
)


TERMOS_FORTES_MPI: tuple[str, ...] = (
    "locacao",
    "aluguel",
    "fabricacao",
    "fabricante",
    "fornecedor",
    "distribuidor",
    "distribuidora",
    "empresa de",
    "servico de",
    "produto",
    "equipamento",
    "equipamentos",
    "manutencao",
    "instalacao",
    "assistencia",
    "solucao",
    "solucoes",
    "projeto",
    "projetos",
    "reparo",
    "reformas",
    "consultoria",
)