#!/usr/bin/env python3
"""启动 CASE API（仅绑定 127.0.0.1）。

用法：
    python backend/scripts/serve.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> int:
    print(f"CASE API  →  http://{settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
