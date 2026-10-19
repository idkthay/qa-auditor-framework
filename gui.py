
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TextIO

from config.settings import REPORTS_DIR
from core.auditor import executar_auditoria
from services.http_link_validator import limpar_cache_links
from services.image_size_validator import (
    limpar_cache_imagens,
)
from services.image_validator import (
    limpar_cache_imagens as limpar_cache_validacao_imagens,
)
from services.pagespeed_service import limpar_cache_pagespeed
from services.responsive_service import limpar_cache_responsividade
from services.site_files_validator import limpar_cache_site_files
from utils.url_helper import normalizar_url


class QueueWriter(TextIO):
    """Envia as mensagens da auditoria para a interface."""

    def __init__(self, mensagens: queue.Queue[str]) -> None:
        self.mensagens = mensagens

    def write(self, texto: str) -> int:
        if texto:
            self.mensagens.put(texto)
        return len(texto)

    def flush(self) -> None:
        pass

    @property
    def encoding(self) -> str:
        return "utf-8"


class QAAuditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.mensagens: queue.Queue[str] = queue.Queue()
        self.executando = False

        self.root.title("QA Auditor Framework")
        self.root.geometry("850x650")
        self.root.minsize(700, 520)

        self.criar_interface()
        self.root.after(100, self.processar_mensagens)

    def criar_interface(self) -> None:
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="QA Auditor Framework",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            container,
            text=(
                "Auditoria técnica de sites com Playwright"
            ),
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 18))

        ttk.Label(
            container,
            text="URL do site",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        linha_url = ttk.Frame(container)
        linha_url.pack(fill="x", pady=(6, 12))

        self.campo_url = ttk.Entry(
            linha_url,
            font=("Segoe UI", 11),
        )
        self.campo_url.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=5,
        )
        self.campo_url.bind(
            "<Return>",
            lambda _evento: self.iniciar_auditoria(),
        )

        self.botao_iniciar = ttk.Button(
            linha_url,
            text="Iniciar auditoria",
            command=self.iniciar_auditoria,
        )
        self.botao_iniciar.pack(
            side="left",
            padx=(10, 0),
            ipady=4,
        )

        self.status = tk.StringVar(
            value="Pronto para iniciar."
        )

        ttk.Label(
            container,
            textvariable=self.status,
        ).pack(anchor="w", pady=(0, 8))

        self.progresso = ttk.Progressbar(
            container,
            mode="indeterminate",
        )
        self.progresso.pack(fill="x", pady=(0, 12))

        ttk.Label(
            container,
            text="Execução da auditoria",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        area_log = ttk.Frame(container)
        area_log.pack(
            fill="both",
            expand=True,
            pady=(6, 12),
        )

        self.log = tk.Text(
            area_log,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
            background="#17202A",
            foreground="#ECF0F1",
            insertbackground="#FFFFFF",
        )

        barra = ttk.Scrollbar(
            area_log,
            orient="vertical",
            command=self.log.yview,
        )

        self.log.configure(
            yscrollcommand=barra.set
        )

        self.log.pack(
            side="left",
            fill="both",
            expand=True,
        )
        barra.pack(
            side="right",
            fill="y",
        )

        botoes_relatorio = ttk.Frame(container)
        botoes_relatorio.pack(fill="x")

        ttk.Button(
            botoes_relatorio,
            text="Abrir relatório HTML",
            command=lambda: self.abrir_arquivo(
                "relatorio_qa.html"
            ),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            botoes_relatorio,
            text="Abrir JSON do prontuário",
            command=lambda: self.abrir_arquivo(
                "prontuario_automatico.json"
            ),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            botoes_relatorio,
            text="Abrir pasta de relatórios",
            command=self.abrir_pasta_relatorios,
        ).pack(side="left")

        self.adicionar_log(
            "Aplicativo iniciado.\n"
            "Informe a URL e clique em Iniciar auditoria.\n\n"
        )

    def adicionar_log(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto)
        self.log.see("end")
        self.log.configure(state="disabled")

    def iniciar_auditoria(self) -> None:
        if self.executando:
            return

        url_digitada = self.campo_url.get().strip()

        try:
            url_inicial = normalizar_url(url_digitada)
        except ValueError as erro:
            messagebox.showerror(
                "URL inválida",
                str(erro),
                parent=self.root,
            )
            return

        self.executando = True
        self.botao_iniciar.configure(state="disabled")
        self.campo_url.configure(state="disabled")
        self.progresso.start(10)
        self.status.set("Auditoria em andamento...")
        self.adicionar_log(
            f"\n{'=' * 55}\n"
            f"Iniciando auditoria: {url_inicial}\n"
            f"{'=' * 55}\n\n"
        )

        thread = threading.Thread(
            target=self.executar_em_background,
            args=(url_inicial,),
            daemon=True,
        )
        thread.start()

    def executar_em_background(
        self,
        url_inicial: str,
    ) -> None:
        escritor = QueueWriter(self.mensagens)

        try:
            with redirect_stdout(escritor):
                limpar_cache_links()
                limpar_cache_imagens()
                limpar_cache_validacao_imagens()
                limpar_cache_pagespeed()
                limpar_cache_responsividade()
                limpar_cache_site_files()

                executar_auditoria(url_inicial)

            self.mensagens.put(
                "\n__AUDITORIA_CONCLUIDA__"
            )

        except Exception:
            self.mensagens.put(
                "\n__AUDITORIA_ERRO__\n"
                + traceback.format_exc()
            )

    def processar_mensagens(self) -> None:
        try:
            while True:
                mensagem = self.mensagens.get_nowait()

                if mensagem == "\n__AUDITORIA_CONCLUIDA__":
                    self.finalizar_auditoria(
                        sucesso=True
                    )
                    continue

                if mensagem.startswith(
                    "\n__AUDITORIA_ERRO__\n"
                ):
                    erro = mensagem.replace(
                        "\n__AUDITORIA_ERRO__\n",
                        "",
                        1,
                    )
                    self.adicionar_log(
                        "\nERRO NA AUDITORIA:\n"
                        + erro
                        + "\n"
                    )
                    self.finalizar_auditoria(
                        sucesso=False
                    )
                    continue

                self.adicionar_log(mensagem)

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.processar_mensagens,
        )

    def finalizar_auditoria(
        self,
        sucesso: bool,
    ) -> None:
        self.executando = False
        self.progresso.stop()
        self.botao_iniciar.configure(state="normal")
        self.campo_url.configure(state="normal")

        if sucesso:
            self.status.set(
                "Execução finalizada. Confira os relatórios."
            )
            self.adicionar_log(
                "\nExecução finalizada.\n"
            )
        else:
            self.status.set(
                "A auditoria terminou com erro."
            )

    def abrir_arquivo(self, nome: str) -> None:
        caminho = REPORTS_DIR / nome

        if not caminho.is_file():
            messagebox.showwarning(
                "Arquivo não encontrado",
                (
                    f"O arquivo ainda não existe:\n{caminho}\n\n"
                    "Execute uma auditoria primeiro."
                ),
                parent=self.root,
            )
            return

        try:
            os.startfile(str(caminho.resolve()))
        except OSError as erro:
            messagebox.showerror(
                "Não foi possível abrir",
                str(erro),
                parent=self.root,
            )

    def abrir_pasta_relatorios(self) -> None:
        REPORTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            os.startfile(str(REPORTS_DIR.resolve()))
        except OSError as erro:
            messagebox.showerror(
                "Não foi possível abrir a pasta",
                str(erro),
                parent=self.root,
            )


def main() -> None:
    root = tk.Tk()
    QAAuditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
