import unittest
from unittest.mock import patch

from services import responsive_service


class FakePage:
    def __init__(self):
        self.url = "https://exemplo.com/"
        self.viewport_size = {"width": 1920, "height": 1080}
        self.viewport_changes = []

    def set_viewport_size(self, viewport):
        self.viewport_size = dict(viewport)
        self.viewport_changes.append(dict(viewport))


class TestValidacaoResponsiva(unittest.TestCase):
    def setUp(self):
        responsive_service.limpar_cache_responsividade()

    def test_aguarda_apos_alterar_viewport_mas_nao_apos_restaurar(self):
        page = FakePage()
        analise = {
            "possui_overflow_horizontal": False,
            "elementos_overflow": [],
        }

        with (
            patch.object(responsive_service, "aguardar_estabilizacao") as aguardar,
            patch.object(responsive_service, "analisar_layout", return_value=analise),
        ):
            resultado = responsive_service.executar_validacao_responsiva(
                page=page,
                nome_viewport="mobile",
                largura=394,
                altura=852,
            )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(aguardar.call_count, 1)
        self.assertEqual(
            page.viewport_size,
            {"width": 1920, "height": 1080},
        )
        self.assertEqual(
            page.viewport_changes,
            [
                {"width": 394, "height": 852},
                {"width": 1920, "height": 1080},
            ],
        )

    def test_retorna_cache_sem_repetir_analise(self):
        page = FakePage()
        analise = {
            "possui_overflow_horizontal": False,
            "elementos_overflow": [],
        }

        with (
            patch.object(responsive_service, "aguardar_estabilizacao"),
            patch.object(responsive_service, "analisar_layout", return_value=analise) as analisar,
        ):
            primeiro = responsive_service.executar_validacao_responsiva(
                page=page,
                nome_viewport="mobile",
                largura=394,
                altura=852,
            )
            segundo = responsive_service.executar_validacao_responsiva(
                page=page,
                nome_viewport="mobile",
                largura=394,
                altura=852,
            )

        self.assertEqual(analisar.call_count, 1)
        self.assertEqual(primeiro, segundo)


if __name__ == "__main__":
    unittest.main()
