
from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
)


PROJECT_ROOT = Path(SPECPATH).resolve()

LOCAL_APP_DATA = Path(
    os.environ.get(
        "LOCALAPPDATA",
        str(Path.home() / "AppData" / "Local"),
    )
)

BROWSER_PATH = Path(
    os.environ.get(
        "PLAYWRIGHT_BROWSERS_PATH",
        str(LOCAL_APP_DATA / "ms-playwright"),
    )
).resolve()

# Somente os componentes do Playwright necessários
# para a instalação Chromium identificada no ambiente.
BROWSER_DIRECTORIES = (
    "chromium-1234",
    "chromium_headless_shell-1234",
    "ffmpeg-1011",
    "winldd-1007",
)

if not BROWSER_PATH.is_dir():
    raise SystemExit(
        "Pasta de navegadores do Playwright não encontrada: "
        f"{BROWSER_PATH}\n"
        "Execute: python -m playwright install chromium"
    )

browser_datas = []

for directory_name in BROWSER_DIRECTORIES:
    source = BROWSER_PATH / directory_name

    if not source.is_dir():
        raise SystemExit(
            "Componente necessário do Playwright não encontrado: "
            f"{source}\n"
            "Confira a instalação com: "
            "python -m playwright install chromium"
        )

    browser_datas.append(
        (
            str(source),
            str(Path("ms-playwright") / directory_name),
        )
    )

# Dependências e recursos do Playwright.
playwright_datas, playwright_binaries, playwright_hiddenimports = (
    collect_all("playwright")
)

# Módulos carregados dinamicamente pelo framework.
project_hiddenimports = []

for package in (
    "checks",
    "core",
    "services",
    "utils",
    "config",
):
    package_path = PROJECT_ROOT / package

    if package_path.is_dir():
        project_hiddenimports.extend(
            collect_submodules(package)
        )

runtime_hook = PROJECT_ROOT / "runtime_hook_playwright.py"

if not runtime_hook.is_file():
    raise SystemExit(
        f"Runtime hook não encontrado: {runtime_hook}"
    )

a = Analysis(
    [str(PROJECT_ROOT / "gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=playwright_binaries,
    datas=playwright_datas + browser_datas,
    hiddenimports=(
        playwright_hiddenimports
        + project_hiddenimports
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(runtime_hook)],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QA-Auditor-Framework",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="QA-Auditor-Framework",
)
