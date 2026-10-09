"""Load the local API key and sweep demo sandboxes after the session."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from guard import sweep

ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
RUN_DIR = Path(__file__).resolve().parent / ".run"


def _load_dotenv() -> None:
    if not ROOT_ENV.is_file():
        return
    for raw in ROOT_ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def pytest_sessionstart(session: pytest.Session) -> None:
    _load_dotenv()
    if not os.environ.get("E2B_API_KEY"):
        raise pytest.UsageError(
            "E2B_API_KEY is not set. Copy examples/e2b/.env.example to examples/e2b/.env."
        )
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    checks = RUN_DIR / "checks.jsonl"
    if checks.exists():
        checks.unlink()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    notes = sweep()
    leftover = sweep()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "cleanup.json").write_text(
        json.dumps(
            {"exitstatus": exitstatus, "swept": notes, "leftover": leftover},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
