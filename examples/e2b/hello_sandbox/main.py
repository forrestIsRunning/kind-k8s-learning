"""Create a short-lived base sandbox, print a few facts, then kill it.

Reads E2B_API_KEY from the environment. If it is unset, loads the gitignored
.env in examples/e2b/. The key is never printed.
"""

from __future__ import annotations

import os
from pathlib import Path

from e2b import Sandbox


def load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_dotenv()
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit(
            "E2B_API_KEY is not set. Copy examples/e2b/.env.example to examples/e2b/.env."
        )

    sandbox = Sandbox.create(timeout=60)
    try:
        info = sandbox.get_info()
        print(f"sandbox_id={sandbox.sandbox_id}")
        print(f"template_id={info.template_id}")
        print(f"template_name={info.name}")
        print(f"state={info.state}")
        print(f"cpu_count={info.cpu_count}")
        print(f"memory_mb={info.memory_mb}")
        print(f"envd_version={info.envd_version}")
        print(f"sandbox_domain={info.sandbox_domain}")
        print(f"started_at={info.started_at.isoformat()}")
        print(f"end_at={info.end_at.isoformat()}")
        print(f"public_host_8080={sandbox.get_host(8080)}")
        for cmd in ("uname -a", "whoami", "pwd"):
            result = sandbox.commands.run(cmd)
            stdout = result.stdout.rstrip("\n")
            print(f"cmd={cmd}")
            print(f"exit_code={result.exit_code}")
            print(f"stdout={stdout}")
    finally:
        killed = sandbox.kill()
        print(f"killed={killed}")


if __name__ == "__main__":
    main()
