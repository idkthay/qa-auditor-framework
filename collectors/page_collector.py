import json
from typing import Any

from playwright.sync_api import Page, Response

from models.page_data import PageData


def obter_meta_description(
    page: Page,
) -> str:
    elemento = page.locator(
        'meta[name="description"]'
    ).first

    if elemento.count() == 0:
        return ""

    conteudo = elemento.get_attribute(
        "content"
    )

    return conteudo.strip() if conteudo else ""


def obter_canonical(
    page: Page,
) -> str:
    elemento = page.locator(
        'link[rel="canonical"]'
    ).first

    if elemento.count() == 0:
        return ""

    href = elemento.get_attribute(
        "href"
    )

    return href.strip() if href else ""


def coletar_headings(
    page: Page,
    seletor: str,
) -> list[str]:
    textos = page.locator(
        seletor
    ).evaluate_all(
        """
        elementos => elementos.map(elemento =>
            (
                elemento.innerText
                || elemento.textContent
                || ""
            ).trim()
        )
        """
    )

    return [
        texto
        for texto in textos
        if isinstance(
            texto,
            str,
        )
    ]


def coletar_imagens(
    page: Page,
) -> list[dict[str, Any]]:
    """
    Coleta informações das tags IMG.

    Também procura o peso transferido por meio da
    Performance API do navegador.
    """
    return page.locator(
        "img"
    ).evaluate_all(
        """
        elementos => {
            const recursos = new Map(
                performance
                    .getEntriesByType("resource")
                    .map(recurso => [
                        recurso.name,
                        recurso
                    ])
            );

            function obterContexto(elemento) {
                const partes = [];
                let atual = elemento;

                for (
                    let nivel = 0;
                    atual && nivel < 5;
                    nivel += 1
                ) {
                    partes.push(
                        [
                            atual.tagName || "",
                            atual.id || "",
                            atual.className || ""
                        ].join(" ")
                    );

                    atual = atual.parentElement;
                }

                return partes.join(" ");
            }

            return elementos.map(imagem => {
                const currentSrc =
                    imagem.currentSrc
                    || imagem.src
                    || "";

                const recurso =
                    recursos.get(currentSrc)
                    || recursos.get(imagem.src)
                    || null;

                const retangulo =
                    imagem.getBoundingClientRect();

                return {
                    tipo: "img",

                    src:
                        imagem.getAttribute("src")
                        || "",

                    current_src: currentSrc,

                    alt_exists:
                        imagem.hasAttribute("alt"),

                    alt:
                        imagem.getAttribute("alt")
                        || "",

                    title_exists:
                        imagem.hasAttribute("title"),

                    title:
                        imagem.getAttribute("title")
                        || "",

                    loading:
                        imagem.getAttribute("loading")
                        || "",

                    id:
                        imagem.getAttribute("id")
                        || "",

                    class_name:
                        imagem.getAttribute("class")
                        || "",

                    ancestor_hint:
                        obterContexto(imagem),

                    width:
                        Math.round(retangulo.width)
                        || imagem.width
                        || 0,

                    height:
                        Math.round(retangulo.height)
                        || imagem.height
                        || 0,

                    natural_width:
                        imagem.naturalWidth
                        || 0,

                    natural_height:
                        imagem.naturalHeight
                        || 0,

                    complete:
                        imagem.complete
                        || false,

                    transfer_size:
                        recurso
                            ? recurso.transferSize || 0
                            : 0,

                    encoded_body_size:
                        recurso
                            ? recurso.encodedBodySize || 0
                            : 0,

                    decoded_body_size:
                        recurso
                            ? recurso.decodedBodySize || 0
                            : 0
                };
            });
        }
        """
    )


def coletar_imagens_de_fundo(
    page: Page,
) -> list[dict[str, Any]]:
    """
    Coleta imagens aplicadas por CSS background-image.

    Isso permite encontrar banners que não utilizam
    diretamente uma tag IMG.
    """
    try:
        return page.locator(
            "body"
        ).evaluate(
            """
            () => {
                const resultados = [];

                const recursos = new Map(
                    performance
                        .getEntriesByType("resource")
                        .map(recurso => [
                            recurso.name,
                            recurso
                        ])
                );

                function obterContexto(elemento) {
                    const partes = [];
                    let atual = elemento;

                    for (
                        let nivel = 0;
                        atual && nivel < 5;
                        nivel += 1
                    ) {
                        partes.push(
                            [
                                atual.tagName || "",
                                atual.id || "",
                                atual.className || ""
                            ].join(" ")
                        );

                        atual = atual.parentElement;
                    }

                    return partes.join(" ");
                }

                const elementos = Array.from(
                    document.querySelectorAll("body *")
                );

                for (const elemento of elementos) {
                    const estilo = getComputedStyle(
                        elemento
                    );

                    const background =
                        estilo.backgroundImage || "";

                    if (
                        !background
                        || background === "none"
                    ) {
                        continue;
                    }

                    const regex =
                        /url\\((['"]?)(.*?)\\1\\)/g;

                    let correspondencia;

                    while (
                        (
                            correspondencia =
                                regex.exec(background)
                        ) !== null
                    ) {
                        const valorOriginal =
                            correspondencia[2] || "";

                        if (
                            !valorOriginal
                            || valorOriginal.startsWith(
                                "data:"
                            )
                        ) {
                            continue;
                        }

                        let urlAbsoluta =
                            valorOriginal;

                        try {
                            urlAbsoluta = new URL(
                                valorOriginal,
                                document.baseURI
                            ).href;

                        } catch (erro) {
                            continue;
                        }

                        const retangulo =
                            elemento
                                .getBoundingClientRect();

                        const recurso =
                            recursos.get(urlAbsoluta)
                            || null;

                        resultados.push({
                            tipo: "background",

                            src: valorOriginal,

                            current_src:
                                urlAbsoluta,

                            id:
                                elemento.getAttribute("id")
                                || "",

                            class_name:
                                elemento.getAttribute(
                                    "class"
                                )
                                || "",

                            ancestor_hint:
                                obterContexto(elemento),

                            width:
                                Math.round(
                                    retangulo.width
                                )
                                || 0,

                            height:
                                Math.round(
                                    retangulo.height
                                )
                                || 0,

                            natural_width: 0,
                            natural_height: 0,

                            complete: true,

                            transfer_size:
                                recurso
                                    ? recurso.transferSize
                                        || 0
                                    : 0,

                            encoded_body_size:
                                recurso
                                    ? recurso.encodedBodySize
                                        || 0
                                    : 0,

                            decoded_body_size:
                                recurso
                                    ? recurso.decodedBodySize
                                        || 0
                                    : 0
                        });
                    }
                }

                return resultados;
            }
            """
        )

    except Exception:
        return []


def coletar_links(
    page: Page,
) -> list[dict[str, Any]]:
    return page.locator(
        "a[href]"
    ).evaluate_all(
        """
        elementos => elementos.map(link => ({
            href: link.href || "",

            href_original:
                link.getAttribute("href")
                || "",

            texto: (
                link.innerText
                || link.textContent
                || ""
            ).trim(),

            title:
                link.getAttribute("title")
                || "",

            target:
                link.getAttribute("target")
                || "",

            rel:
                link.getAttribute("rel")
                || ""
        }))
        """
    )


def coletar_formularios(
    page: Page,
) -> list[dict[str, Any]]:
    """
    Coleta informações estruturais e de acessibilidade
    dos formulários presentes na página.
    """
    return page.locator(
        "form"
    ).evaluate_all(
        """
        formularios => formularios.map(
            (formulario, indice) => {
                const elementos = Array.from(
                    formulario.querySelectorAll(
                        "input, textarea, select, button"
                    )
                );

                const campos = elementos.map(campo => {
                    const tag =
                        campo.tagName.toLowerCase();

                    const type = (
                        campo.getAttribute("type")
                        || ""
                    ).toLowerCase();

                    const id =
                        campo.getAttribute("id")
                        || "";

                    const name =
                        campo.getAttribute("name")
                        || "";

                    let label = "";

                    if (id) {
                        const labelElemento =
                            formulario.querySelector(
                                `label[for="${
                                    CSS.escape(id)
                                }"]`
                            );

                        if (labelElemento) {
                            label = (
                                labelElemento.innerText
                                || labelElemento.textContent
                                || ""
                            ).trim();
                        }
                    }

                    if (!label) {
                        const labelPai =
                            campo.closest("label");

                        if (labelPai) {
                            label = (
                                labelPai.innerText
                                || labelPai.textContent
                                || ""
                            ).trim();
                        }
                    }

                    return {
                        tag: tag,
                        type: type,
                        name: name,
                        id: id,

                        required:
                            campo.required
                            || campo.hasAttribute(
                                "required"
                            ),

                        placeholder:
                            campo.getAttribute(
                                "placeholder"
                            )
                            || "",

                        aria_label:
                            campo.getAttribute(
                                "aria-label"
                            )
                            || "",

                        label: label,

                        disabled:
                            campo.disabled
                            || false,

                        value:
                            campo.getAttribute(
                                "value"
                            )
                            || ""
                    };
                });

                const botoesEnvio =
                    campos.filter(campo => {
                        if (
                            campo.tag === "button"
                        ) {
                            return (
                                campo.type === ""
                                || campo.type
                                    === "submit"
                            );
                        }

                        return (
                            campo.tag === "input"
                            && (
                                campo.type
                                    === "submit"
                                || campo.type
                                    === "image"
                            )
                        );
                    });

                const possuiRecaptchaV2 =
                    formulario.querySelector(
                        ".g-recaptcha, "
                        + "iframe[src*='recaptcha/api2'], "
                        + "[data-sitekey]"
                    ) !== null;

                const htmlFormulario =
                    formulario
                        .innerHTML
                        .toLowerCase();

                const possuiCampoRecaptchaV3 =
                    formulario.querySelector(
                        'input[name="g-recaptcha-response"]'
                    ) !== null;

                const possuiRecaptchaV3 =
                    possuiCampoRecaptchaV3
                    || htmlFormulario.includes(
                        "grecaptcha.execute"
                    )
                    || htmlFormulario.includes(
                        "recaptcha/api.js?render="
                    )
                    || document.documentElement
                        .innerHTML
                        .toLowerCase()
                        .includes(
                            "recaptcha/api.js?render="
                        );

                return {
                    indice: indice,

                    action_original:
                        formulario.getAttribute(
                            "action"
                        )
                        || "",

                    action_absoluta:
                        formulario.action
                        || "",

                    method: (
                        formulario.getAttribute(
                            "method"
                        )
                        || "get"
                    ).toLowerCase(),

                    id:
                        formulario.getAttribute("id")
                        || "",

                    name:
                        formulario.getAttribute(
                            "name"
                        )
                        || "",

                    quantidade_campos:
                        campos.length,

                    quantidade_campos_obrigatorios:
                        campos.filter(
                            campo => campo.required
                        ).length,

                    quantidade_botoes_envio:
                        botoesEnvio.length,

                    possui_botao_envio:
                        botoesEnvio.length > 0,

                    possui_recaptcha:
                        possuiRecaptchaV2
                        || possuiRecaptchaV3,

                    possui_recaptcha_v2:
                        possuiRecaptchaV2,

                    possui_recaptcha_v3:
                        possuiRecaptchaV3,

                    possui_campo_recaptcha_v3:
                        possuiCampoRecaptchaV3,

                    campos: campos
                };
            }
        )
        """
    )


def coletar_scripts(
    page: Page,
) -> list[dict[str, Any]]:
    return page.locator(
        "script"
    ).evaluate_all(
        """
        elementos => elementos.map(script => ({
            src:
                script.getAttribute("src")
                || "",

            type:
                script.getAttribute("type")
                || "",

            async:
                script.async
                || false,

            defer:
                script.defer
                || false,

            inline:
                !script.getAttribute("src"),

            tamanho_inline:
                script.getAttribute("src")
                    ? 0
                    : (
                        script.textContent
                        || ""
                    ).length
        }))
        """
    )


def coletar_recursos(
    page: Page,
) -> list[dict[str, Any]]:
    """
    Coleta recursos capazes de gerar Mixed Content.
    """
    return page.locator(
        "img[src], "
        "script[src], "
        "link[href], "
        "iframe[src], "
        "source[src], "
        "video[src], "
        "audio[src], "
        "object[data], "
        "embed[src]"
    ).evaluate_all(
        """
        elementos => elementos.map(elemento => {
            const tag =
                elemento.tagName.toLowerCase();

            let atributo = "src";

            if (tag === "link") {
                atributo = "href";
            }

            if (tag === "object") {
                atributo = "data";
            }

            const valorOriginal =
                elemento.getAttribute(atributo)
                || "";

            let valorAbsoluto =
                valorOriginal;

            try {
                valorAbsoluto = new URL(
                    valorOriginal,
                    document.baseURI
                ).href;

            } catch (erro) {
                valorAbsoluto =
                    valorOriginal;
            }

            return {
                tag: tag,
                atributo: atributo,
                url_original: valorOriginal,
                url_absoluta: valorAbsoluto
            };
        })
        """
    )


def coletar_schemas(
    page: Page,
) -> list[dict[str, Any]]:
    conteudos = page.locator(
        'script[type="application/ld+json"]'
    ).evaluate_all(
        """
        elementos => elementos.map(
            elemento =>
                elemento.textContent || ""
        )
        """
    )

    schemas: list[dict[str, Any]] = []

    for conteudo in conteudos:
        conteudo_limpo = conteudo.strip()

        if not conteudo_limpo:
            continue

        try:
            schema = json.loads(
                conteudo_limpo
            )

            schemas.append(
                {
                    "valido": True,
                    "conteudo": schema,
                    "erro": "",
                }
            )

        except json.JSONDecodeError as erro:
            schemas.append(
                {
                    "valido": False,
                    "conteudo": conteudo_limpo,
                    "erro": str(
                        erro
                    ),
                }
            )

    return schemas


def coletar_headers(
    response: Response | None,
) -> dict[str, str]:
    if response is None:
        return {}

    try:
        return {
            chave.lower(): valor
            for chave, valor
            in response.headers.items()
        }

    except Exception:
        return {}


def coletar_page_data(
    page: Page,
    response: Response | None,
    url_solicitada: str,
) -> PageData:
    """
    Coleta uma única vez as principais informações da página.
    """
    status_http = (
        response.status
        if response
        else None
    )

    title = page.title().strip()

    lang = (
        page.locator(
            "html"
        ).get_attribute(
            "lang"
        )
        or ""
    ).strip()

    html = page.content()

    return PageData(
        url_solicitada=url_solicitada,
        url_final=page.url,
        status_http=status_http,

        title=title,

        meta_description=obter_meta_description(
            page
        ),

        canonical=obter_canonical(
            page
        ),

        lang=lang,

        h1=coletar_headings(
            page,
            "h1",
        ),

        h2=coletar_headings(
            page,
            "h2",
        ),

        images=coletar_imagens(
            page
        ),

        background_images=(
            coletar_imagens_de_fundo(
                page
            )
        ),

        links=coletar_links(
            page
        ),

        forms=coletar_formularios(
            page
        ),

        scripts=coletar_scripts(
            page
        ),

        schemas=coletar_schemas(
            page
        ),

        resources=coletar_recursos(
            page
        ),

        response_headers=coletar_headers(
            response
        ),

        html=html,
    )