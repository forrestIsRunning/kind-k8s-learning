# hello_sandbox

拉起一台默认 `base` 沙箱，打印规格和三条命令的输出，然后立刻销毁。

对应笔记：[这把 key 的探活记录](../../../docs/e2b/06-this-account.md)。

## 准备

```bash
cd examples/e2b
cp .env.example .env
```

把 API key 写进 `.env` 的 `E2B_API_KEY=`。这个文件被 git 忽略。已经导出的环境变量优先，脚本不会覆盖它。

## 运行

```bash
cd examples/e2b/hello_sandbox
uv sync
uv run python main.py
```

`uv sync` 会按 `pyproject.toml` 安装 `e2b>=2.52.0`。2026-10-03 解析到的版本是 2.52.0，解释器是 CPython 3.13。

脚本做四件事：

1. `Sandbox.create(timeout=60)`。不传模板名，SDK 使用 `base`。
2. 打印 `get_info()` 里的模板、CPU、内存、envd 版本和到期时间。
3. 运行 `uname -a`、`whoami`、`pwd`。
4. 在 `finally` 里 `kill()`，无论前面有没有抛错。

成功时最后一行是 `killed=True`。沙箱 ID 会打印出来。那是已销毁沙箱的标识，不是密钥。

## 费用

默认规格是 2 vCPU 和 512 MiB。文档费率下跑满 60 秒大约 0.0018 美元。脚本在命令结束后就销毁，实际时间更短。当前费率以 [E2B pricing](https://e2b.dev/pricing) 为准。
