from abc import ABC, abstractmethod
from typing import Any

from playwright.sync_api import Page


class BaseCheck(ABC):
    nome: str = "Validação sem nome"
    categoria: str = "Geral"

    @abstractmethod
    def executar(
        self,
        page: Page,
        contexto: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Executa uma validação e devolve o resultado padronizado.
        """
        raise NotImplementedError

    def resultado(
        self,
        status: str,
        observacao: str = "",
        dados: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "categoria": self.categoria,
            "status": status,
            "observacao": observacao,
            "dados": dados or {},
        }