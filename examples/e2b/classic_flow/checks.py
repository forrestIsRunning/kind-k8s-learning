"""One assertion with the expected value and the observed value."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent / ".run"


@dataclass
class Check:
    name: str
    expected: str
    actual: str
    ok: bool

    def message(self) -> str:
        return (
            f"{self.name}\n"
            f"expected: {self.expected}\n"
            f"actual: {self.actual}"
        )


def record(check: Check) -> Check:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    with (RUN_DIR / "checks.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(check), ensure_ascii=False) + "\n")
    return check


def expect(name: str, expected: object, actual: object) -> None:
    check = record(
        Check(
            name=name,
            expected=repr(expected),
            actual=repr(actual),
            ok=actual == expected,
        )
    )
    assert check.ok, check.message()


def expect_true(name: str, ok: bool, *, expected: str, actual: str) -> None:
    check = record(Check(name=name, expected=expected, actual=actual, ok=ok))
    assert check.ok, check.message()
