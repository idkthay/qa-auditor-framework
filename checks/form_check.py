from typing import Any

from playwright.sync_api import Page

from checks.base_check import BaseCheck
from models.page_data import PageData


TIPOS_IGNORADOS_ACESSIBILIDADE = {
    "hidden",
    "submit",
    "button",
    "reset",
    "image",
}


def obter_page_data(
    contexto: dict[str, Any],
) -> PageData | None:
    page_data = contexto.get("page_data")

    if isinstance(page_data, PageData):
        return page_data

    return None


def identificar_formulario(
    formulario: dict[str, Any],
    indice: int,
) -> str:
    form_id = str(
        formulario.get("id", "")
    ).strip()

    form_name = str(
        formulario.get("name", "")
    ).strip()

    if form_id:
        return f"Formulário #{form_id}"

    if form_name:
        return f"Formulário {form_name}"

    return f"Formulário {indice + 1}"


class FormPresenceCheck(BaseCheck):
    nome = "Formulário presente"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        quantidade = len(page_data.forms)

        if quantidade == 0:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Nenhum formulário foi encontrado na página. "
                    "Revise se esta página deveria possuir formulário."
                ),
                dados={
                    "quantidade": 0,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": quantidade,
                "requer_revisao_manual": False,
            },
        )


class FormActionCheck(BaseCheck):
    nome = "Formulário - Action configurado"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        formularios_invalidos = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            action = str(
                formulario.get(
                    "action_original",
                    "",
                )
            ).strip()

            if action:
                continue

            formularios_invalidos.append(
                identificar_formulario(
                    formulario,
                    indice,
                )
            )

        if formularios_invalidos:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados formulários sem "
                    "atributo action explícito:\n"
                    + "\n".join(formularios_invalidos)
                ),
                dados={
                    "quantidade": len(
                        formularios_invalidos
                    ),
                    "formularios": formularios_invalidos,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "formularios": [],
            },
        )


class FormMethodCheck(BaseCheck):
    nome = "Formulário - Método POST"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        formularios_get = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            metodo = str(
                formulario.get("method", "get")
            ).casefold()

            if metodo == "post":
                continue

            formularios_get.append(
                {
                    "formulario": identificar_formulario(
                        formulario,
                        indice,
                    ),
                    "metodo": metodo,
                }
            )

        if formularios_get:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados formulários que não "
                    "utilizam POST:\n"
                    + "\n".join(
                        (
                            f'{item["formulario"]}: '
                            f'{item["metodo"].upper()}'
                        )
                        for item in formularios_get
                    )
                ),
                dados={
                    "quantidade": len(formularios_get),
                    "formularios": formularios_get,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "formularios": [],
            },
        )


class FormSubmitButtonCheck(BaseCheck):
    nome = "Formulário - Botão de envio"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        formularios_sem_botao = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            possui_botao = bool(
                formulario.get(
                    "possui_botao_envio",
                    False,
                )
            )

            if possui_botao:
                continue

            formularios_sem_botao.append(
                identificar_formulario(
                    formulario,
                    indice,
                )
            )

        if formularios_sem_botao:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados formulários sem "
                    "botão de envio:\n"
                    + "\n".join(
                        formularios_sem_botao
                    )
                ),
                dados={
                    "quantidade": len(
                        formularios_sem_botao
                    ),
                    "formularios": formularios_sem_botao,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "formularios": [],
            },
        )


class FormRequiredFieldsCheck(BaseCheck):
    nome = "Formulário - Campos obrigatórios"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        sem_campos_obrigatorios = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            quantidade = int(
                formulario.get(
                    "quantidade_campos_obrigatorios",
                    0,
                )
                or 0
            )

            if quantidade > 0:
                continue

            sem_campos_obrigatorios.append(
                identificar_formulario(
                    formulario,
                    indice,
                )
            )

        if sem_campos_obrigatorios:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Os seguintes formulários não possuem "
                    "nenhum campo obrigatório:\n"
                    + "\n".join(
                        sem_campos_obrigatorios
                    )
                ),
                dados={
                    "quantidade": len(
                        sem_campos_obrigatorios
                    ),
                    "formularios": sem_campos_obrigatorios,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "formularios": [],
                "requer_revisao_manual": False,
            },
        )


class FormFieldIdentificationCheck(BaseCheck):
    nome = "Formulário - Campos identificados"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        campos_sem_identificacao = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            nome_formulario = identificar_formulario(
                formulario,
                indice,
            )

            for campo in formulario.get(
                "campos",
                [],
            ):
                tipo = str(
                    campo.get("type", "")
                ).casefold()

                if tipo in TIPOS_IGNORADOS_ACESSIBILIDADE:
                    continue

                tag = str(
                    campo.get("tag", "")
                ).casefold()

                if tag == "button":
                    continue

                possui_identificacao = any(
                    str(
                        campo.get(chave, "")
                    ).strip()
                    for chave in (
                        "label",
                        "aria_label",
                        "placeholder",
                    )
                )

                if possui_identificacao:
                    continue

                campos_sem_identificacao.append(
                    {
                        "formulario": nome_formulario,
                        "tag": tag,
                        "type": tipo,
                        "name": campo.get(
                            "name",
                            "",
                        ),
                        "id": campo.get(
                            "id",
                            "",
                        ),
                    }
                )

        if campos_sem_identificacao:
            observacoes = []

            for item in campos_sem_identificacao:
                identificador = (
                    item["name"]
                    or item["id"]
                    or "sem nome ou ID"
                )

                observacoes.append(
                    (
                        f'{item["formulario"]}: '
                        f'{item["tag"]} '
                        f'{item["type"]} '
                        f'({identificador})'
                    )
                )

            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados campos sem label, "
                    "aria-label ou placeholder:\n"
                    + "\n".join(observacoes)
                ),
                dados={
                    "quantidade": len(
                        campos_sem_identificacao
                    ),
                    "campos": campos_sem_identificacao,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "campos": [],
            },
        )


class RecaptchaPresenceCheck(BaseCheck):
    nome = "Formulário - reCAPTCHA presente"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        formularios_sem_recaptcha = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            possui_recaptcha = bool(
                formulario.get(
                    "possui_recaptcha",
                    False,
                )
            )

            if possui_recaptcha:
                continue

            formularios_sem_recaptcha.append(
                identificar_formulario(
                    formulario,
                    indice,
                )
            )

        if formularios_sem_recaptcha:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram encontrados formulários sem "
                    "reCAPTCHA detectável:\n"
                    + "\n".join(
                        formularios_sem_recaptcha
                    )
                ),
                dados={
                    "quantidade": len(
                        formularios_sem_recaptcha
                    ),
                    "formularios": formularios_sem_recaptcha,
                    "requer_revisao_manual": True,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "formularios": [],
                "requer_revisao_manual": False,
            },
        )


class RecaptchaConflictCheck(BaseCheck):
    nome = "Formulário - Apenas um tipo de reCAPTCHA"
    categoria = "Formulários"

    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        page_data = obter_page_data(contexto)

        if page_data is None:
            return self.resultado(
                status="error",
                observacao="PageData não está disponível.",
            )

        formularios_com_conflito = []

        for indice, formulario in enumerate(
            page_data.forms
        ):
            possui_v2 = bool(
                formulario.get(
                    "possui_recaptcha_v2",
                    False,
                )
            )

            possui_v3 = bool(
                formulario.get(
                    "possui_recaptcha_v3",
                    False,
                )
            )

            if not (
                possui_v2
                and possui_v3
            ):
                continue

            formularios_com_conflito.append(
                identificar_formulario(
                    formulario,
                    indice,
                )
            )

        if formularios_com_conflito:
            return self.resultado(
                status="rejected",
                observacao=(
                    "Foram detectados reCAPTCHA v2 e v3 "
                    "no mesmo formulário:\n"
                    + "\n".join(
                        formularios_com_conflito
                    )
                ),
                dados={
                    "quantidade": len(
                        formularios_com_conflito
                    ),
                    "formularios": formularios_com_conflito,
                },
            )

        return self.resultado(
            status="approved",
            dados={
                "quantidade": 0,
                "formularios": [],
            },
        )