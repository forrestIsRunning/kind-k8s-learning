"""Track sandbox ids and kill anything this demo left behind."""

from __future__ import annotations

from e2b import Sandbox, SandboxQuery, SandboxState

DEMO = "classic-flow"
TIMEOUT = 120


def list_demo_sandboxes() -> list:
    paginator = Sandbox.list(SandboxQuery(metadata={"demo": DEMO}))
    found = list(paginator.next_items())
    while paginator.has_next:
        found.extend(paginator.next_items())
    return found


def kill_sandbox(sandbox_id: str) -> str:
    try:
        killed = Sandbox.kill(sandbox_id)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return f"killed={killed}"


def sweep() -> list[str]:
    """Kill every running or paused sandbox tagged by this demo."""
    notes: list[str] = []
    for info in list_demo_sandboxes():
        state = getattr(info.state, "value", info.state)
        notes.append(f"{info.sandbox_id} state={state} {kill_sandbox(info.sandbox_id)}")
    return notes


class Guard:
    def __init__(self) -> None:
        self.ids: list[str] = []

    def track(self, sandbox):
        self.ids.append(sandbox.sandbox_id)
        return sandbox

    def close(self) -> None:
        for sandbox_id in self.ids:
            kill_sandbox(sandbox_id)
        sweep()


def metadata(scenario: str, run_id: str | None = None) -> dict[str, str]:
    data = {"demo": DEMO, "scenario": scenario}
    if run_id is not None:
        data["run_id"] = run_id
    return data


def states_of(sandbox_id: str) -> list[str]:
    return [
        str(getattr(info.state, "value", info.state))
        for info in list_demo_sandboxes()
        if info.sandbox_id == sandbox_id
    ]


def is_paused(sandbox_id: str) -> bool:
    return SandboxState.PAUSED.value in states_of(sandbox_id)
