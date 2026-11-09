
from pathlib import Path
from datetime import datetime
import re
import shutil

TARGET = Path("core/auditor.py")

if not TARGET.is_file():
    raise SystemExit(
        "ERRO: execute na raiz do qa-auditor-framework. "
        "Nenhum arquivo foi alterado."
    )

source = TARGET.read_text(encoding="utf-8")

pattern = re.compile(
    r"(?m)^def normalizar_status_prontuario\s*\(.*?"
    r"(?=^def salvar_prontuario_automatico\s*\()",
    re.S,
)

match = pattern.search(source)

if not match:
    raise SystemExit(
        "ERRO: não encontrei as funções esperadas. "
        "Nenhum arquivo foi alterado."
    )

replacement = r'''
def normalizar_status_prontuario(status):
    status = status.strip().lower() if isinstance(status, str) else ""

    if status in {"approved", "warning", "error", "rejected"}:
        return status

    return "error"


def combinar_itens_prontuario(nomes_checks, itens):
    encontrados = [
        (nome, itens[nome])
        for nome in nomes_checks
        if nome in itens and isinstance(itens[nome], dict)
    ]

    if not encontrados:
        return None

    prioridade = {
        "approved": 1,
        "warning": 2,
        "error": 3,
        "rejected": 4,
    }

    resultados = [
        (nome, resultado, normalizar_status_prontuario(
            resultado.get("status", "")
        ))
        for nome, resultado in encontrados
    ]

    status_final = max(
        (status for _, _, status in resultados),
        key=lambda status: prioridade[status],
    )

    ausentes = [
        nome for nome in nomes_checks
        if nome not in itens
    ]

    if ausentes and prioridade[status_final] < prioridade["warning"]:
        status_final = "warning"

    observacoes = []

    for nome, resultado, _ in resultados:
        observacao = resultado.get("obs", "")
        if isinstance(observacao, str) and observacao.strip():
            observacoes.append(f"{nome}:\n{observacao.strip()}")

    if ausentes:
        observacoes.append(
            "Checks não encontrados: " + ", ".join(ausentes)
        )

    imagens = []
    imagens_vistas = set()

    for _, resultado, _ in resultados:
        lista = resultado.get("imgs", [])
        if not isinstance(lista, list):
            continue

        for imagem in lista:
            if (
                isinstance(imagem, str)
                and imagem.strip()
                and imagem not in imagens_vistas
            ):
                imagens_vistas.add(imagem)
                imagens.append(imagem)

    return {
        "status": status_final,
        "obs": "\n\n".join(observacoes),
        "imgs": imagens,
    }


def _deduplicar_textos_importacao(valores):
    resultado = []
    vistos = set()

    for valor in valores:
        if not isinstance(valor, str):
            continue

        texto = valor.strip()
        if texto and texto not in vistos:
            vistos.add(texto)
            resultado.append(texto)

    return resultado


def _combinar_itens_importacao(item_existente, item_novo):
    prioridade = {
        "approved": 1,
        "warning": 2,
        "error": 3,
        "rejected": 4,
    }

    existente = dict(item_existente or {})
    novo = dict(item_novo or {})

    status_existente = normalizar_status_prontuario(
        existente.get("status", "")
    )
    status_novo = normalizar_status_prontuario(
        novo.get("status", "")
    )

    status_final = max(
        (status_existente, status_novo),
        key=lambda status: prioridade[status],
    )

    observacoes = _deduplicar_textos_importacao([
        existente.get("obs", ""),
        novo.get("obs", ""),
    ])

    imagens = []
    imagens_vistas = set()

    for lista in (existente.get("imgs", []), novo.get("imgs", [])):
        if not isinstance(lista, list):
            continue

        for imagem in lista:
            if (
                isinstance(imagem, str)
                and imagem.strip()
                and imagem not in imagens_vistas
            ):
                imagens_vistas.add(imagem)
                imagens.append(imagem)

    return {
        "status": status_final,
        "obs": "\n\n".join(observacoes),
        "imgs": imagens,
    }


def gerar_itens_importacao_prontuario(itens):
    itens_importacao = {}

    for nome, resultado in (itens or {}).items():
        if not isinstance(resultado, dict):
            continue

        nome_prontuario = MAPEAMENTO_DIRETO_PRONTUARIO.get(nome, nome)

        nome_valido = (
            nome in ITENS_DIRETOS_PRONTUARIO
            or nome in MAPEAMENTO_DIRETO_PRONTUARIO
        )

        if not nome_valido:
            continue

        item_novo = {
            "status": normalizar_status_prontuario(
                resultado.get("status", "")
            ),
            "obs": (
                resultado.get("obs", "")
                if isinstance(resultado.get("obs", ""), str)
                else ""
            ),
            "imgs": (
                resultado.get("imgs", [])
                if isinstance(resultado.get("imgs", []), list)
                else []
            ),
        }

        itens_importacao[nome_prontuario] = (
            _combinar_itens_importacao(
                itens_importacao.get(nome_prontuario),
                item_novo,
            )
        )

    for nome_grupo, nomes_checks in GRUPOS_PRONTUARIO.items():
        item_grupo = combinar_itens_prontuario(nomes_checks, itens)

        if item_grupo is None:
            continue

        itens_importacao[nome_grupo] = _combinar_itens_importacao(
            itens_importacao.get(nome_grupo),
            item_grupo,
        )

    return itens_importacao


'''

updated = source[:match.start()] + replacement + source[match.end():]


linha_mapeamento = (
    '    "Links de contatos clicáveis e funcionais": (\n'
    '        "Links de números clicáveis e funcionais"\n'
    '    ),'
)

mapeamento_maps = (
    '    "Google Maps carregando e funcional": '
    '"Google Maps - Carregando e funcional",'
)

if mapeamento_maps not in updated:
    if linha_mapeamento not in updated:
        raise SystemExit(
            "ERRO: não encontrei o ponto de inserção do mapeamento. "
            "Nenhum arquivo foi alterado."
        )

    updated = updated.replace(
        linha_mapeamento,
        linha_mapeamento + "\n" + mapeamento_maps,
        1,
    )

updated = updated.replace(
    '    "Google Maps carregando e funcional",\n',
    "",
    1,
)

try:
    compile(updated, str(TARGET), "exec")
except SyntaxError as exc:
    raise SystemExit(
        f"ERRO de sintaxe: {exc}. Nenhum arquivo foi alterado."
    )

backup = TARGET.with_name(
    f"auditor.py.backup_{datetime.now():%Y%m%d_%H%M%S}"
)

shutil.copy2(TARGET, backup)
TARGET.write_text(updated, encoding="utf-8", newline="\n")

print("Correção aplicada.")
print(f"Arquivo: {TARGET}")
print(f"Backup: {backup}")
print("Sintaxe Python validada.")
print("Nenhuma auditoria ou relatório foi executado/alterado.")
