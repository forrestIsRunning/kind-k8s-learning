# E2B 托管 API 示例

打 `https://api.e2b.app`，按秒计费。需要 `E2B_API_KEY`。说明见 [`../../docs/e2b/README.md`](../../docs/e2b/README.md)。

```bash
cd examples/e2b
cp .env.example .env
# 写入 E2B_API_KEY=

cd hello_sandbox
uv sync
uv run python main.py

cd ../classic_flow
uv sync
uv run pytest -q
```

`.env` 放在本目录，不进 git。已经导出的环境变量优先，脚本不会覆盖它。
