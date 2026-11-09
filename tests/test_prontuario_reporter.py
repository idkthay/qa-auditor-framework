
import unittest

from reporters.prontuario_reporter import (
    consolidar_checks,
    consolidar_checks_globais,
    gerar_itens_prontuario,
)


def pagina(url, status, observacao=""):
    return {
        "url_final": url,
        "checks": [
            {
                "nome": "Formulário presente",
                "categoria": "Formulários",
                "status": status,
                "observacao": observacao,
            }
        ],
    }


class TestConsolidarChecks(unittest.TestCase):
    def test_warning_nao_pode_virar_approved(self):
        resultado = consolidar_checks([
            pagina("https://exemplo.com/", "approved"),
            pagina(
                "https://exemplo.com/contato",
                "warning",
                "Teste manual necessário",
            ),
        ])

        item = resultado["Formulário presente"]
        self.assertEqual(item["status"], "warning")
        self.assertIn("https://exemplo.com/contato", item["obs"])
        self.assertIn("Teste manual necessário", item["obs"])

    def test_rejected_tem_prioridade_sobre_error_e_warning(self):
        resultado = consolidar_checks([
            pagina("https://exemplo.com/", "warning", "Atenção"),
            pagina(
                "https://exemplo.com/contato",
                "error",
                "Falha técnica",
            ),
            pagina(
                "https://exemplo.com/form",
                "rejected",
                "Não encontrado",
            ),
        ])

        self.assertEqual(
            resultado["Formulário presente"]["status"],
            "rejected",
        )

    def test_status_desconhecido_vira_error(self):
        resultado = consolidar_checks([
            pagina(
                "https://exemplo.com/",
                "unexpected-status",
                "Status inválido",
            ),
        ])

        item = resultado["Formulário presente"]
        self.assertEqual(item["status"], "error")
        self.assertIn("Status inválido", item["obs"])

    def test_ocorrencias_repetidas_sao_deduplicadas(self):
        resultado = consolidar_checks([
            pagina("https://exemplo.com/", "warning", "Revisar"),
            pagina("https://exemplo.com/", "warning", "Revisar"),
        ])

        self.assertEqual(
            resultado["Formulário presente"]["obs"].count("Revisar"),
            1,
        )

    def test_observacoes_sao_separadas_por_quebra_de_linha(self):
        resultado = consolidar_checks([
            pagina(
                "https://exemplo.com/contato",
                "warning",
                "Primeiro aviso",
            ),
            pagina(
                "https://exemplo.com/form",
                "error",
                "Segunda falha",
            ),
        ])

        observacoes = resultado["Formulário presente"]["obs"]
        self.assertIn("\n", observacoes)
        self.assertNotIn("\\n", observacoes)

    def test_observacao_none_nao_interrompe_consolidacao(self):
        resultado = consolidar_checks([
            pagina("https://exemplo.com/", "warning", None),
        ])

        self.assertEqual(
            resultado["Formulário presente"]["status"],
            "warning",
        )


class TestChecksGlobais(unittest.TestCase):
    def test_status_global_desconhecido_vira_error(self):
        resultado = consolidar_checks_globais([
            {
                "nome": "Sitemap.xml",
                "categoria": "SEO técnico",
                "status": "not-sure",
                "observacao": "Resultado inesperado",
            }
        ])

        self.assertEqual(resultado["Sitemap.xml"]["status"], "error")

    def test_json_preserva_formato_esperado(self):
        resultado = gerar_itens_prontuario(
            [pagina("https://exemplo.com/", "warning", "Revisar")],
            [],
        )

        item = resultado["Formulário presente"]
        self.assertEqual(
            set(item),
            {"categoria", "status", "obs", "imgs"},
        )

    def test_global_aprovado_nao_sobrescreve_rejeicao_da_pagina(self):
        resultado = gerar_itens_prontuario(
            [
                pagina(
                    "https://exemplo.com/contato",
                    "rejected",
                    "Formulário inválido",
                )
            ],
            [
                {
                    "nome": "Formulário presente",
                    "categoria": "Formulários",
                    "status": "approved",
                    "observacao": "",
                    "imgs": [],
                }
            ],
        )

        item = resultado["Formulário presente"]
        self.assertEqual(item["status"], "rejected")
        self.assertIn("Formulário inválido", item["obs"])
        self.assertIn("https://exemplo.com/contato", item["obs"])

    def test_observacoes_global_e_por_pagina_sao_preservadas(self):
        resultado = gerar_itens_prontuario(
            [
                pagina(
                    "https://exemplo.com/contato",
                    "warning",
                    "Validar manualmente",
                )
            ],
            [
                {
                    "nome": "Formulário presente",
                    "categoria": "Formulários",
                    "status": "rejected",
                    "observacao": "Falha na validação global",
                    "imgs": [],
                }
            ],
        )

        item = resultado["Formulário presente"]
        self.assertEqual(item["status"], "rejected")
        self.assertIn("Validar manualmente", item["obs"])
        self.assertIn("Falha na validação global", item["obs"])

    def test_check_global_exclusivo_e_preservado(self):
        resultado = gerar_itens_prontuario(
            [],
            [
                {
                    "nome": "Sitemap.xml",
                    "categoria": "SEO técnico",
                    "status": "approved",
                    "observacao": "",
                    "imgs": [],
                }
            ],
        )

        self.assertEqual(resultado["Sitemap.xml"]["status"], "approved")

    def test_imagens_duplicadas_sao_removidas_ao_combinar(self):
        resultado = gerar_itens_prontuario(
            [
                {
                    "url_final": "https://exemplo.com/",
                    "screenshot": "evidencia.png",
                    "checks": [
                        {
                            "nome": "Formulário presente",
                            "categoria": "Formulários",
                            "status": "rejected",
                            "observacao": "Falha",
                        }
                    ],
                }
            ],
            [
                {
                    "nome": "Formulário presente",
                    "categoria": "Formulários",
                    "status": "approved",
                    "observacao": "",
                    "imgs": ["evidencia.png"],
                }
            ],
        )

        self.assertEqual(
            resultado["Formulário presente"]["imgs"],
            ["evidencia.png"],
        )


if __name__ == "__main__":
    unittest.main()
