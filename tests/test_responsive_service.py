import unittest

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
        chamadas_aguardar = []
        original_aguardar = responsive_service.aguardar_estabilizacao
        original_analisar = responsive_service.analisar_layout

        def aguardar(_page):
            chamadas_aguardar.append(_page)

        try:
            responsive_service.aguardar_estabilizacao = aguardar
            responsive_service.analisar_layout = lambda **_kwargs: analise
            resultado = responsive_service.executar_validacao_responsiva(
                page=page,
                nome_viewport="mobile",
                largura=394,
                altura=852,
            )
        finally:
            responsive_service.aguardar_estabilizacao = original_aguardar
            responsive_service.analisar_layout = original_analisar

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(len(chamadas_aguardar), 1)
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
        chamadas_analise = []
        original_aguardar = responsive_service.aguardar_estabilizacao
        original_analisar = responsive_service.analisar_layout

        def analisar(**_kwargs):
            chamadas_analise.append(True)
            return analise

        try:
            responsive_service.aguardar_estabilizacao = lambda _page: None
            responsive_service.analisar_layout = analisar
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
        finally:
            responsive_service.aguardar_estabilizacao = original_aguardar
            responsive_service.analisar_layout = original_analisar

        self.assertEqual(len(chamadas_analise), 1)
        self.assertEqual(primeiro, segundo)


if __name__ == "__main__":
    unittest.main()
