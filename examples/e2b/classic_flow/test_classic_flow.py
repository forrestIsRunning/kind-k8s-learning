"""Live checks for the three mainstream E2B sandbox shapes.

Each test talks to api.e2b.app. Failures keep the expected value and the
observed value. Sandboxes are killed in finally, then again by the session
sweep in conftest.py.
"""

from __future__ import annotations

import base64
import os
import time
import urllib.error
import urllib.request
from uuid import uuid4

import httpx
from e2b import (
    CommandExitException,
    Sandbox,
    SandboxQuery,
    ServiceBusyException,
    Template,
    Volume,
    VolumeException,
)
from e2b_code_interpreter import Sandbox as Interpreter

from checks import expect, expect_true
from guard import DEMO, TIMEOUT, Guard, is_paused, list_demo_sandboxes, metadata

MARKER = "classic-flow-marker"
TEMPLATE_NAME = "classic-flow-marker"
PREVIEW_BODY = "classic-flow-preview"


def _command(sandbox, command: str, **kwargs) -> tuple[int, str, str]:
    try:
        result = sandbox.commands.run(command, **kwargs)
    except CommandExitException as exc:
        return exc.exit_code, exc.stdout or "", exc.stderr or ""
    return result.exit_code, result.stdout or "", result.stderr or ""


def _stdout(execution) -> str:
    return "".join(execution.logs.stdout)


def _error_text(execution) -> str:
    if execution.error is None:
        return ""
    return (
        f"{execution.error.name}: {execution.error.value}\n"
        f"{execution.error.traceback}"
    )


def _ids(query: SandboxQuery) -> list[str]:
    paginator = Sandbox.list(query)
    found = [item.sandbox_id for item in paginator.next_items()]
    while paginator.has_next:
        found.extend(item.sandbox_id for item in paginator.next_items())
    return found


def _api(method: str, path: str) -> httpx.Response:
    """Call the control plane.

    A dropped connection is retried. An HTTP status is returned as-is so the
    assertions still see 4xx and 5xx.
    """
    last_error: httpx.TransportError | None = None
    for attempt in range(3):
        try:
            return httpx.request(
                method,
                "https://api.e2b.app" + path,
                headers={"X-API-Key": os.environ["E2B_API_KEY"]},
                timeout=60,
                trust_env=False,
            )
        except httpx.TransportError as exc:
            last_error = exc
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("template API retry exhausted") from last_error


def _template_items() -> list[dict]:
    response = _api("GET", "/templates")
    response.raise_for_status()
    body = response.json()
    return body if isinstance(body, list) else []


def _labels(item: dict) -> set[str]:
    return set(item.get("names") or []) | set(item.get("aliases") or [])


def _matches_template(item: dict, name: str) -> bool:
    for label in _labels(item):
        if label == name or label.endswith("/" + name) or label.startswith(name + ":"):
            return True
    return False


def _delete_template(template_id: str) -> int:
    return _api("DELETE", f"/templates/{template_id}").status_code


def _delete_snapshot(snapshot_id: str) -> bool:
    candidates = [snapshot_id]
    if ":" not in snapshot_id:
        candidates.append(f"{snapshot_id}:default")
    deleted = False
    for candidate in candidates:
        try:
            deleted = Sandbox.delete_snapshot(candidate)
        except Exception:
            deleted = False
            continue
        if deleted:
            return True
    return deleted


def _delete_named_templates(name: str) -> None:
    for item in _template_items():
        if _matches_template(item, name) and item.get("templateID"):
            _delete_template(item["templateID"])


def test_interpreter_state() -> None:
    guard = Guard()
    sandbox = guard.track(
        Interpreter.create(timeout=TIMEOUT, metadata=metadata("interpreter-state"))
    )
    try:
        first = sandbox.run_code("x = 21")
        expect_true(
            "interpreter_first_cell_has_no_error",
            first.error is None,
            expected="error is None",
            actual=_error_text(first) or "None",
        )
        second = sandbox.run_code("print(x * 2)")
        expect_true(
            "interpreter_second_cell_has_no_error",
            second.error is None,
            expected="error is None",
            actual=_error_text(second) or "None",
        )
        expect("interpreter_stdout", "42", _stdout(second).strip())
    finally:
        guard.close()


def test_interpreter_chart() -> None:
    guard = Guard()
    sandbox = guard.track(
        Interpreter.create(timeout=TIMEOUT, metadata=metadata("interpreter-chart"))
    )
    code = "\n".join(
        [
            "import matplotlib.pyplot as plt",
            "plt.plot([1, 2, 3, 4])",
            "plt.show()",
        ]
    )
    try:
        execution = sandbox.run_code(code)
        formats = [result.formats() for result in execution.results]
        expect_true(
            "chart_cell_has_no_error",
            execution.error is None,
            expected="error is None",
            actual=_error_text(execution) or "None",
        )
        pngs = [result.png for result in execution.results if result.png]
        expect_true(
            "chart_has_png",
            len(pngs) >= 1,
            expected="at least one png result",
            actual=repr(formats),
        )
        if pngs:
            raw = base64.b64decode(pngs[0])
            expect_true(
                "chart_png_bytes",
                raw.startswith(b"\x89PNG") and len(raw) > 8,
                expected="PNG longer than 8 bytes",
                actual=f"len={len(raw)} prefix={raw[:8]!r}",
            )
    finally:
        guard.close()


def test_interpreter_error_is_data() -> None:
    guard = Guard()
    sandbox = guard.track(
        Interpreter.create(timeout=TIMEOUT, metadata=metadata("interpreter-error"))
    )
    try:
        failed = sandbox.run_code("1/0")
        expect_true(
            "division_error_name",
            failed.error is not None and failed.error.name == "ZeroDivisionError",
            expected="ZeroDivisionError",
            actual=_error_text(failed) or "None",
        )
        followed = sandbox.run_code("print(1)")
        expect_true(
            "kernel_still_runs",
            followed.error is None and _stdout(followed).strip() == "1",
            expected="stdout 1 and no error",
            actual=f"stdout={_stdout(followed)!r} error={_error_text(followed) or 'None'}",
        )
    finally:
        guard.close()


def test_files_roundtrip() -> None:
    guard = Guard()
    sandbox = guard.track(
        Sandbox.create(timeout=TIMEOUT, metadata=metadata("files"))
    )
    payload = b"alpha,1\nbeta,2\n"
    try:
        sandbox.files.write("/home/user/data.csv", payload)
        raw = bytes(sandbox.files.read("/home/user/data.csv", format="bytes"))
        expect("uploaded_bytes", payload, raw)
        code, out, err = _command(
            sandbox,
            "python3 -c \"rows=open('/home/user/data.csv'); "
            "open('/home/user/sum.txt','w').write(str(sum(int(line.split(',')[1]) for line in rows)))\"",
        )
        expect_true(
            "sum_command",
            code == 0,
            expected="exit 0",
            actual=f"exit={code} stdout={out!r} stderr={err!r}",
        )
        text = sandbox.files.read("/home/user/sum.txt").strip()
        expect("downloaded_sum", "3", text)
    finally:
        guard.close()


def test_template_marker() -> None:
    guard = Guard()
    built = None
    _delete_named_templates(TEMPLATE_NAME)
    logs: list[str] = []
    try:
        template = (
            Template()
            .from_base_image()
            .run_cmd(
                f"mkdir -p /opt/demo && echo {MARKER} > /opt/demo/marker",
                user="root",
            )
        )
        built = Template.build(
            template,
            TEMPLATE_NAME,
            cpu_count=2,
            memory_mb=512,
            on_build_logs=lambda entry: logs.append(getattr(entry, "message", str(entry))),
        )
        marked = guard.track(
            Sandbox.create(
                TEMPLATE_NAME,
                timeout=TIMEOUT,
                metadata=metadata("template-marked"),
            )
        )
        code, out, err = _command(marked, "cat /opt/demo/marker")
        expect_true(
            "marker_on_custom_template",
            code == 0 and out.strip() == MARKER,
            expected=MARKER,
            actual=f"exit={code} stdout={out!r} stderr={err!r} log_tail={logs[-5:]!r}",
        )
        plain = guard.track(
            Sandbox.create("base", timeout=TIMEOUT, metadata=metadata("template-base"))
        )
        base_code, base_out, base_err = _command(plain, "cat /opt/demo/marker")
        expect_true(
            "marker_absent_on_base",
            base_code != 0,
            expected="non-zero exit on base",
            actual=f"exit={base_code} stdout={base_out!r} stderr={base_err!r}",
        )
    finally:
        guard.close()
        if built is not None:
            status = _delete_template(built.template_id)
        else:
            status = None
    expect_true(
        "template_delete_status",
        status in (200, 204),
        expected="204",
        actual=str(status),
    )
    still = [
        item.get("templateID")
        for item in _template_items()
        if _matches_template(item, TEMPLATE_NAME)
    ]
    expect("template_gone", [], still)


def test_pause_keeps_kernel_and_file() -> None:
    guard = Guard()
    sandbox = guard.track(
        Interpreter.create(timeout=TIMEOUT, metadata=metadata("pause"))
    )
    try:
        assigned = sandbox.run_code("x = 7")
        expect_true(
            "pause_setup",
            assigned.error is None,
            expected="error is None",
            actual=_error_text(assigned) or "None",
        )
        sandbox.files.write("/home/user/note.txt", "kept")
        try:
            sandbox.pause()
        except ServiceBusyException as exc:
            time.sleep(5)
            sandbox.pause()
            expect_true(
                "pause_retried_after_503",
                True,
                expected="retry after ServiceBusyException",
                actual=repr(exc),
            )
        expect_true(
            "listed_as_paused",
            is_paused(sandbox.sandbox_id),
            expected="paused",
            actual=repr(
                [
                    (info.sandbox_id, str(getattr(info.state, "value", info.state)))
                    for info in list_demo_sandboxes()
                ]
            ),
        )
        resumed = guard.track(Interpreter.connect(sandbox.sandbox_id, timeout=TIMEOUT))
        execution = resumed.run_code("print(x)")
        note = resumed.files.read("/home/user/note.txt")
        expect_true(
            "kernel_value_survives_pause",
            execution.error is None and _stdout(execution).strip() == "7",
            expected="stdout 7",
            actual=f"stdout={_stdout(execution)!r} error={_error_text(execution) or 'None'}",
        )
        expect("file_survives_pause", "kept", note.strip())
        resumed.kill()
        expect_true(
            "gone_after_kill",
            sandbox.sandbox_id not in {info.sandbox_id for info in list_demo_sandboxes()},
            expected="id absent",
            actual=repr([info.sandbox_id for info in list_demo_sandboxes()]),
        )
    finally:
        guard.close()


def test_snapshot_forks_old_state() -> None:
    guard = Guard()
    path = "/home/user/state.txt"
    sandbox = guard.track(
        Sandbox.create(timeout=TIMEOUT, metadata=metadata("snapshot-parent"))
    )
    snapshot_id = None
    try:
        sandbox.files.write(path, "v1")
        snapshot = sandbox.create_snapshot()
        snapshot_id = snapshot.snapshot_id
        original = guard.track(Sandbox.connect(sandbox.sandbox_id, timeout=TIMEOUT))
        original.files.write(path, "v2")
        child = guard.track(
            Sandbox.create(
                snapshot.snapshot_id,
                timeout=TIMEOUT,
                metadata=metadata("snapshot-child"),
            )
        )
        expect("child_keeps_v1", "v1", child.files.read(path).strip())
        expect("parent_has_v2", "v2", original.files.read(path).strip())
    finally:
        guard.close()
        deleted = None
        if snapshot_id is not None:
            deleted = _delete_snapshot(snapshot_id)
    expect_true(
        "snapshot_deleted",
        deleted is True,
        expected="True",
        actual=repr(deleted),
    )


def test_preview_http() -> None:
    guard = Guard()
    sandbox = guard.track(
        Sandbox.create(timeout=TIMEOUT, metadata=metadata("preview"))
    )
    try:
        sandbox.files.write("/home/user/site/index.html", PREVIEW_BODY + "\n")
        sandbox.commands.run(
            "python3 -m http.server 8080 --bind 0.0.0.0 --directory /home/user/site",
            background=True,
        )
        url = f"https://{sandbox.get_host(8080)}/"
        status = None
        body = ""
        error = ""
        for _ in range(20):
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    status = response.status
                    body = response.read().decode()
                break
            except urllib.error.HTTPError as exc:
                status = exc.code
                body = exc.read().decode(errors="replace")
                error = repr(exc)
                break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                time.sleep(1)
        expect_true(
            "preview_status",
            status == 200 and PREVIEW_BODY in body,
            expected=f"200 and {PREVIEW_BODY}",
            actual=f"url={url} status={status} body={body[:500]!r} error={error}",
        )
    finally:
        guard.close()


def test_egress_closed() -> None:
    guard = Guard()
    sandbox = guard.track(
        Sandbox.create(
            timeout=TIMEOUT,
            allow_internet_access=False,
            metadata=metadata("egress"),
        )
    )
    try:
        local_code, local_out, local_err = _command(sandbox, "echo ok")
        expect_true(
            "local_command",
            local_code == 0 and local_out.strip() == "ok",
            expected="exit 0 stdout ok",
            actual=f"exit={local_code} stdout={local_out!r} stderr={local_err!r}",
        )
        which_code, which_out, which_err = _command(sandbox, "command -v curl")
        expect_true(
            "curl_exists",
            which_code == 0,
            expected="curl on PATH",
            actual=f"exit={which_code} stdout={which_out!r} stderr={which_err!r}",
        )
        code, out, err = _command(
            sandbox,
            "curl -fsS --max-time 8 https://example.com",
            timeout=20,
        )
        combined = out + err
        expect_true(
            "egress_blocked",
            code != 0 and "Example Domain" not in combined,
            expected="non-zero curl and body without Example Domain",
            actual=f"exit={code} stdout={out!r} stderr={err!r}",
        )
    finally:
        guard.close()


def test_metadata_is_the_index() -> None:
    guard = Guard()
    run_id = uuid4().hex
    sandbox = guard.track(
        Sandbox.create(
            timeout=TIMEOUT,
            metadata=metadata("metadata", run_id),
        )
    )
    query = SandboxQuery(metadata={"demo": DEMO, "run_id": run_id})
    try:
        expect("metadata_hits_one_id", [sandbox.sandbox_id], _ids(query))
        sandbox.kill()
        expect("metadata_empty_after_kill", [], _ids(query))
    finally:
        guard.close()


def test_coding_loop() -> None:
    guard = Guard()
    sandbox = guard.track(
        Sandbox.create(timeout=TIMEOUT, metadata=metadata("coding"))
    )
    try:
        git_code, git_out, git_err = _command(sandbox, "git --version")
        if git_code != 0:
            install_code, install_out, install_err = _command(
                sandbox,
                "apt-get update && apt-get install -y git",
                user="root",
                timeout=180,
            )
            expect_true(
                "git_installed_for_demo",
                install_code == 0,
                expected="git already present, or apt-get exit 0",
                actual=(
                    f"git exit={git_code} stdout={git_out!r} stderr={git_err!r}; "
                    f"apt exit={install_code} stdout={install_out[-400:]!r} "
                    f"stderr={install_err[-400:]!r}"
                ),
            )
        sandbox.files.write(
            "/home/user/app/add.py",
            "def add(a, b):\n    return a + b\n",
        )
        sandbox.files.write(
            "/home/user/app/test_add.py",
            "\n".join(
                [
                    "import unittest",
                    "from add import add",
                    "",
                    "class AddTest(unittest.TestCase):",
                    "    def test_add(self):",
                    "        self.assertEqual(add(1, 2), 3)",
                    "",
                    "if __name__ == '__main__':",
                    "    unittest.main()",
                    "",
                ]
            ),
        )
        test_code, test_out, test_err = _command(
            sandbox,
            "python3 -m unittest test_add.py",
            cwd="/home/user/app",
        )
        expect_true(
            "unittest_passes",
            test_code == 0,
            expected="exit 0",
            actual=f"exit={test_code} stdout={test_out!r} stderr={test_err!r}",
        )
        diff_code, diff_out, diff_err = _command(
            sandbox,
            "git init && git add add.py test_add.py && git diff --cached",
            cwd="/home/user/app",
        )
        expect_true(
            "diff_contains_add",
            diff_code == 0 and "def add" in diff_out,
            expected="cached diff contains def add",
            actual=f"exit={diff_code} diff={diff_out!r} stderr={diff_err!r}",
        )
    finally:
        guard.close()


def test_volume_probe() -> None:
    name = f"classic-flow-{uuid4().hex[:8]}"
    try:
        volume = Volume.create(name)
    except VolumeException as exc:
        text = f"status={getattr(exc, 'status_code', None)} {exc}"
        unavailable = any(
            token in text.lower()
            for token in ("403", "not available", "not enabled", "beta")
        )
        expect_true(
            "volume_not_enabled_on_this_project",
            unavailable,
            expected="403 or an explicit not-enabled error",
            actual=text,
        )
        return
    try:
        volume.write_file("/marker.txt", "volume-ok")
        got = volume.read_file("/marker.txt")
        if isinstance(got, (bytes, bytearray)):
            text = bytes(got).decode()
        else:
            text = str(got)
        expect("volume_roundtrip", "volume-ok", text.strip())
    finally:
        destroyed = Volume.destroy(volume.volume_id)
        expect_true(
            "volume_destroyed",
            destroyed is True,
            expected="True",
            actual=repr(destroyed),
        )


def test_zzz_demo_resources_are_gone() -> None:
    leftover = [info.sandbox_id for info in list_demo_sandboxes()]
    expect("no_demo_sandbox_left", [], leftover)
    still = [
        item.get("templateID")
        for item in _template_items()
        if _matches_template(item, TEMPLATE_NAME)
    ]
    expect("no_demo_template_left", [], still)
