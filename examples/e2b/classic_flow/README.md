# classic_flow

三条主流用法的实跑测试。说明在 [docs/e2b/07-mainstream-usage.md](../../../docs/e2b/07-mainstream-usage.md)。2026-10-03 一次全绿的期望值和实际值在 [docs/e2b/08-classic-flow-run.md](../../../docs/e2b/08-classic-flow-run.md)。

```bash
cd examples/e2b/classic_flow
uv sync
uv run pytest -q
```

API key 读 `examples/e2b/.env`。测试串行访问 E2B，包含一次模板构建，通常要几分钟到十几分钟。每台沙箱带 metadata `demo=classic-flow`，结束时会被 `kill`。

断言失败时，pytest 输出里同时有期望值和实际值。`.run/checks.jsonl` 是同一次运行的记录，不进 git。
