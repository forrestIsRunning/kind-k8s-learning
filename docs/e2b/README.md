# E2B 托管沙箱笔记

材料来自 2026-10-03 的官方文档，以及同一天用本机 API key 对 `https://api.e2b.app` 做的一次短时探活。SDK 版本是 Python `e2b` 2.52.0。

这份笔记原先在独立仓库 `forrestIsRunning/e2b`，现已并入本仓库。和 kind 上的 SIG / OpenSandbox / Cube 对照见 [`../overview.md`](../overview.md)。

## 先说结论

E2B 提供按需创建的 Linux 微虚拟机，让 Agent 在隔离环境里跑命令、读写文件、访问网络。调用方持有的是一把属于单个 Project 的 API key。Project 以前叫 Team。

一次调用里真正打交道的对象只有四个：

1. Project：key、sandbox、template、计费的边界。
2. Template：沙箱的启动快照。不指定时用公共模板 `base`。
3. Sandbox：一台正在跑或已暂停的 Firecracker microVM。里面的控制进程叫 envd。
4. 持久化：pause 保住同一台沙箱，snapshot 复制出一个时间点，volume 是独立于沙箱的磁盘。volume 仍是 private beta。

2026-10-03 这把 key 能调用平台 API。自定义 template、sandbox、volume 都是 0。`GET /secrets` 返回 403，原文是 `Secrets are not available for this team`。套餐档位和剩余额度这些接口没有返回，要到 [Console](https://console.e2b.dev) 看。

CubeSandbox 的 CubeAPI 把 `POST /sandboxes` 做成接近 E2B 的形状。托管 E2B 的对象模型见本文；本机 Cube 创建请求怎么走见 [`../cubesandbox-request-flow.md`](../cubesandbox-request-flow.md)。两条路径的运行时不同：这里打 `api.e2b.app`，Cube 打本机 `:3000`。

## 推荐阅读顺序

只有 20 分钟：

1. [10 分钟建立直觉](00-mental-model.md)
2. [三条主流用法和最佳实践](07-mainstream-usage.md)
3. [这把 key 的探活记录](06-this-account.md)
4. [可运行示例](../../examples/e2b/classic_flow/README.md)
5. [这次跑通了什么](08-classic-flow-run.md)

需要自己管生命周期时，按这个顺序：

1. [Sandbox 生命周期](01-sandbox-lifecycle.md)
2. [Template 怎么变成启动盘](02-templates.md)
3. [沙箱里面：命令、文件、网络](03-inside-the-sandbox.md)
4. [pause、snapshot、volume](04-persistence.md)
5. [隔离、密钥和计费](05-security-and-billing.md)
6. [三条主流用法](07-mainstream-usage.md)
7. [一次全绿的运行记录](08-classic-flow-run.md)

资料出处：[sources.md](sources.md)。

## 本仓库里的位置

```text
docs/e2b/                 笔记（本目录）
examples/e2b/
  .env.example            真实 key 放同目录 .env，不进仓库
  hello_sandbox/          创建 base、打印事实、立刻 kill
  classic_flow/           三条主线的 pytest
```

## 本地运行示例

这些命令会创建 **计费** 的托管沙箱。`make` 不会跑它们。

```bash
cd examples/e2b
cp .env.example .env
# 把 key 写进 .env 的 E2B_API_KEY=
cd hello_sandbox
uv sync
uv run python main.py
```

示例会拉起一台 `timeout=60` 的沙箱，打印系统信息，然后 `kill()`。按文档费率，默认规格跑满 60 秒大约 0.002 美元。定价以 [pricing](https://e2b.dev/pricing) 为准。

仓库里没有 key。如果 key 曾经出现在对话里，到 Console 轮换，并改本地 `examples/e2b/.env`。

## 学完应能回答

- API key、Project、template、sandbox 各管什么？
- Python 的 `timeout` 为什么是秒，JavaScript 为什么是毫秒？
- `set_timeout` 和 `connect` 对剩余寿命的处理有什么差别？
- pause、snapshot、volume 分别留下什么，原来的沙箱还在不在？
- 默认 `base` 的用户、目录、CPU、内存、内核是什么？
- 为什么 `GET /secrets` 在这把 key 上是 403？
- 沙箱暂停之后为什么不再计运行费，却仍然占着一个可恢复的 ID？
