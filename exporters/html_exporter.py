from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def calcular_score(
    aprovados: int,
    total: int,
) -> int:
    if total == 0:
        return 0

    return round((aprovados / total) * 100)


def calcular_estatisticas(
    itens: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    aprovados = 0
    rejeitados = 0
    erros = 0

    categorias: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "approved": 0,
            "rejected": 0,
            "error": 0,
        }
    )

    for dados in itens.values():
        status = dados.get(
            "status",
            "error",
        )

        categoria = dados.get(
            "categoria",
            "Geral",
        )

        if status == "approved":
            aprovados += 1

        elif status == "rejected":
            rejeitados += 1

        else:
            erros += 1
            status = "error"

        categorias[categoria][status] += 1

    total = (
        aprovados
        + rejeitados
        + erros
    )

    scores_categorias = {}

    for categoria, dados in categorias.items():
        total_categoria = (
            dados["approved"]
            + dados["rejected"]
            + dados["error"]
        )

        scores_categorias[categoria] = {
            **dados,
            "total": total_categoria,
            "score": calcular_score(
                dados["approved"],
                total_categoria,
            ),
        }

    return {
        "aprovados": aprovados,
        "rejeitados": rejeitados,
        "erros": erros,
        "total": total,
        "score_geral": calcular_score(
            aprovados,
            total,
        ),
        "categorias": scores_categorias,
    }


def classe_status(status: str) -> str:
    return {
        "approved": "status-approved",
        "rejected": "status-rejected",
        "error": "status-error",
    }.get(status, "status-error")


def texto_status(status: str) -> str:
    return {
        "approved": "Aprovado",
        "rejected": "Reprovado",
        "error": "Erro",
    }.get(status, "Erro")


def caminho_evidencia_html(caminho: str) -> str:
    if not caminho:
        return ""

    caminho_normalizado = caminho.replace("\\", "/")

    if caminho_normalizado.startswith("screenshots/"):
        return f"../{caminho_normalizado}"

    return caminho_normalizado


def criar_cards_categorias(
    categorias: dict[str, dict[str, int]],
) -> str:
    if not categorias:
        return """
        <div class="empty-state">
            Nenhuma categoria foi encontrada.
        </div>
        """

    cards = []

    for categoria, dados in sorted(categorias.items()):
        score = dados["score"]

        cards.append(
            f"""
            <article class="category-card">
                <div class="category-header">
                    <h3>{escape(categoria)}</h3>
                    <strong>{score}%</strong>
                </div>

                <div class="progress">
                    <div
                        class="progress-value"
                        style="width: {score}%"
                    ></div>
                </div>

                <div class="category-details">
                    <span>✅ {dados["approved"]}</span>
                    <span>❌ {dados["rejected"]}</span>
                    <span>⚠️ {dados["error"]}</span>
                </div>
            </article>
            """
        )

    return "\n".join(cards)


def criar_tabela_itens(
    itens: dict[str, dict[str, Any]],
) -> str:
    linhas = []

    ordem_status = {
        "rejected": 1,
        "error": 2,
        "approved": 3,
    }

    itens_ordenados = sorted(
        itens.items(),
        key=lambda item: (
            ordem_status.get(
                item[1].get("status", "error"),
                2,
            ),
            item[0].casefold(),
        ),
    )

    for nome, dados in itens_ordenados:
        status = dados.get("status", "error")
        observacao = dados.get("obs", "").strip()
        imagens = dados.get("imgs", [])

        observacao_html = (
            escape(observacao).replace("\n", "<br>")
            if observacao
            else '<span class="muted">Nenhuma ocorrência.</span>'
        )

        links_imagens = []

        for indice, imagem in enumerate(imagens, start=1):
            caminho = caminho_evidencia_html(imagem)

            links_imagens.append(
                f"""
                <a
                    class="evidence-link"
                    href="{escape(caminho)}"
                    target="_blank"
                >
                    Evidência {indice}
                </a>
                """
            )

        evidencias_html = (
            " ".join(links_imagens)
            if links_imagens
            else '<span class="muted">—</span>'
        )

        linhas.append(
            f"""
            <tr>
                <td>
                    <strong>{escape(nome)}</strong>
                </td>

                <td>
                    <span class="status-badge {classe_status(status)}">
                        {texto_status(status)}
                    </span>
                </td>

                <td class="observation">
                    {observacao_html}
                </td>

                <td>
                    {evidencias_html}
                </td>
            </tr>
            """
        )

    return "\n".join(linhas)


def exportar_relatorio_html(
    url_inicial: str,
    paginas: list[dict[str, Any]],
    itens_prontuario: dict[str, dict[str, Any]],
    caminho_saida: Path,
) -> Path:
    estatisticas = calcular_estatisticas(
        itens_prontuario
    )

    dominio = urlparse(url_inicial).netloc
    data_execucao = datetime.now().strftime(
        "%d/%m/%Y às %H:%M"
    )

    cards_categorias = criar_cards_categorias(
        estatisticas["categorias"]
    )

    tabela_itens = criar_tabela_itens(
        itens_prontuario
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>QA Auditor — {escape(dominio)}</title>

    <style>
        :root {{
            --background: #0b1020;
            --surface: #131a2d;
            --surface-light: #1a2339;
            --border: #2a3653;
            --text: #f4f7fb;
            --muted: #9ba8bf;
            --primary: #7c8cff;
            --approved: #32d583;
            --rejected: #f97066;
            --warning: #fdb022;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background:
                radial-gradient(
                    circle at top right,
                    rgba(124, 140, 255, 0.15),
                    transparent 32%
                ),
                var(--background);
            color: var(--text);
            font-family:
                Inter,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }}

        .container {{
            width: min(1400px, calc(100% - 40px));
            margin: 0 auto;
            padding: 40px 0 80px;
        }}

        .hero {{
            display: flex;
            justify-content: space-between;
            gap: 24px;
            align-items: flex-start;
            margin-bottom: 32px;
        }}

        .hero h1 {{
            margin: 0 0 8px;
            font-size: clamp(30px, 5vw, 48px);
        }}

        .hero p {{
            margin: 4px 0;
            color: var(--muted);
        }}

        .score-main {{
            min-width: 180px;
            padding: 24px;
            border: 1px solid var(--border);
            border-radius: 20px;
            background: rgba(19, 26, 45, 0.9);
            text-align: center;
        }}

        .score-main strong {{
            display: block;
            font-size: 48px;
            line-height: 1;
        }}

        .score-main span {{
            display: block;
            margin-top: 8px;
            color: var(--muted);
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}

        .summary-card,
        .category-card {{
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--surface);
            padding: 20px;
        }}

        .summary-card span {{
            display: block;
            margin-bottom: 8px;
            color: var(--muted);
        }}

        .summary-card strong {{
            font-size: 30px;
        }}

        .section {{
            margin-top: 36px;
        }}

        .section-title {{
            margin: 0 0 18px;
            font-size: 24px;
        }}

        .category-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
        }}

        .category-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
        }}

        .category-header h3 {{
            margin: 0;
            font-size: 17px;
        }}

        .category-header strong {{
            font-size: 22px;
        }}

        .progress {{
            height: 9px;
            margin: 18px 0;
            overflow: hidden;
            border-radius: 999px;
            background: var(--surface-light);
        }}

        .progress-value {{
            height: 100%;
            border-radius: 999px;
            background: var(--primary);
        }}

        .category-details {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            color: var(--muted);
            font-size: 14px;
        }}

        .table-wrapper {{
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--surface);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 850px;
        }}

        th,
        td {{
            padding: 16px;
            border-bottom: 1px solid var(--border);
            text-align: left;
            vertical-align: top;
        }}

        th {{
            background: var(--surface-light);
            color: var(--muted);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        tr:last-child td {{
            border-bottom: 0;
        }}

        .observation {{
            min-width: 320px;
            line-height: 1.55;
        }}

        .status-badge {{
            display: inline-flex;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 700;
        }}

        .status-approved {{
            background: rgba(50, 213, 131, 0.14);
            color: var(--approved);
        }}

        .status-rejected {{
            background: rgba(249, 112, 102, 0.14);
            color: var(--rejected);
        }}

        .status-error {{
            background: rgba(253, 176, 34, 0.14);
            color: var(--warning);
        }}

        .evidence-link {{
            display: inline-block;
            margin: 0 6px 6px 0;
            padding: 7px 10px;
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            text-decoration: none;
        }}

        .evidence-link:hover {{
            border-color: var(--primary);
            color: var(--primary);
        }}

        .muted {{
            color: var(--muted);
        }}

        .empty-state {{
            padding: 24px;
            border: 1px dashed var(--border);
            border-radius: 16px;
            color: var(--muted);
        }}

                .action-bar {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: rgba(19, 26, 45, 0.92);
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.18);
        }}

        .action-bar-title {{
            margin-right: auto;
        }}

        .action-bar-title strong {{
            display: block;
            margin-bottom: 3px;
            font-size: 16px;
        }}

        .action-bar-title span {{
            color: var(--muted);
            font-size: 13px;
        }}

        .action-button {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 42px;
            padding: 10px 15px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: var(--surface-light);
            color: var(--text);
            font: inherit;
            font-size: 14px;
            font-weight: 700;
            text-decoration: none;
            cursor: pointer;
            transition:
                border-color 0.2s ease,
                color 0.2s ease,
                transform 0.2s ease;
        }}

        .action-button:hover {{
            border-color: var(--primary);
            color: var(--primary);
            transform: translateY(-1px);
        }}

        .action-button-primary {{
            border-color: rgba(50, 213, 131, 0.45);
            background: rgba(50, 213, 131, 0.12);
            color: var(--approved);
        }}

        .action-button-primary:hover {{
            border-color: var(--approved);
            color: var(--approved);
        }}

        .print-message {{
            display: none;
        }}

        footer {{
            margin-top: 40px;
            color: var(--muted);
            text-align: center;
            font-size: 14px;
        }}

        @media (max-width: 850px) {{
            .hero {{
                flex-direction: column;
            }}

            .score-main {{
                width: 100%;
            }}

            .summary-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}

        @media (max-width: 520px) {{
            .container {{
                width: min(100% - 24px, 1400px);
                padding-top: 24px;
            }}

            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
                @media print {{
            :root {{
                --background: #ffffff;
                --surface: #ffffff;
                --surface-light: #f4f4f5;
                --border: #d4d4d8;
                --text: #18181b;
                --muted: #52525b;
            }}

            body {{
                background: #ffffff;
                color: #18181b;
            }}

            .container {{
                width: 100%;
                padding: 0;
            }}

            .action-bar {{
                display: none;
            }}

            .summary-card,
            .category-card,
            .table-wrapper,
            .score-main {{
                background: #ffffff;
                box-shadow: none;
            }}

            .table-wrapper {{
                overflow: visible;
            }}

            table {{
                min-width: 0;
                font-size: 10px;
            }}

            th,
            td {{
                padding: 8px;
            }}

            .observation {{
                min-width: 0;
            }}

            .evidence-link {{
                display: none;
            }}

            footer {{
                color: #52525b;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">
        <nav
            class="action-bar"
            aria-label="Ações do relatório"
        >
            <div class="action-bar-title">
                <strong>Ações rápidas</strong>

                <span>
                    Acesse os arquivos gerados pela auditoria.
                </span>
            </div>

            <a
                class="action-button action-button-primary"
                href="prontuario_automatico.json"
                download="prontuario_automatico.json"
            >
                📥 Baixar JSON do Prontuário
            </a>

            <a
                class="action-button"
                href="auditoria_completa.json"
                target="_blank"
                rel="noopener noreferrer"
            >
                📋 Abrir Auditoria Completa
            </a>

            <button
                class="action-button"
                type="button"
                onclick="window.print()"
            >
                🖨️ Exportar PDF
            </button>
        </nav>

        <header class="hero">
            <div>
                <h1>QA Auditor Framework</h1>

                <p>
                    <strong>Site:</strong>
                    {escape(dominio)}
                </p>

                <p>
                    <strong>Executado em:</strong>
                    {escape(data_execucao)}
                </p>
            </div>

            <div class="score-main">
                <strong>{estatisticas["score_geral"]}%</strong>
                <span>Score geral</span>
            </div>
        </header>

        <section class="summary-grid">
            <article class="summary-card">
                <span>Páginas auditadas</span>
                <strong>{len(paginas)}</strong>
            </article>

            <article class="summary-card">
                <span>Checks aprovados</span>
                <strong>{estatisticas["aprovados"]}</strong>
            </article>

            <article class="summary-card">
                <span>Checks rejeitados</span>
                <strong>{estatisticas["rejeitados"]}</strong>
            </article>

            <article class="summary-card">
                <span>Erros de execução</span>
                <strong>{estatisticas["erros"]}</strong>
            </article>
        </section>

        <section class="section">
            <h2 class="section-title">
                Resultado por categoria
            </h2>

            <div class="category-grid">
                {cards_categorias}
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">
                Itens do prontuário
            </h2>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Validação</th>
                            <th>Status</th>
                            <th>Observações</th>
                            <th>Evidências</th>
                        </tr>
                    </thead>

                    <tbody>
                        {tabela_itens}
                    </tbody>
                </table>
            </div>
        </section>

         <footer>
            Relatório gerado automaticamente pelo QA Auditor Framework.

            <div class="print-message">
                Para salvar este relatório, utilize a opção
                “Salvar como PDF” na janela de impressão.
            </div>
        </footer>
    </main>
</body>
</html>
"""

    caminho_saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_saida.write_text(
        html,
        encoding="utf-8",
    )

    return caminho_saida