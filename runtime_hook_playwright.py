
from __future__ import annotations

import os
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    pasta_browsers = (
        Path(sys._MEIPASS) / "ms-playwright"
    )

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
        pasta_browsers
    )
