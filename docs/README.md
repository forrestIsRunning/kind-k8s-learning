# 文档阅读顺序

本仓库关注沙箱相关技术。文档按产品分目录，不要把托管 E2B 和 kind 上的 Operator 当成同一套运行时。

## 先读

1. [`overview.md`](./overview.md) — 四套对照：E2B 托管、SIG agent-sandbox、OpenSandbox Operator、CubeSandbox 控制面。
2. 根目录 [`../README.md`](../README.md) — 两条动手入口：kind 集群 / E2B 托管 API。

## 按产品

| 产品 | 文档 | 本机能跑到哪 |
|---|---|---|
| E2B 托管 | [`e2b/README.md`](./e2b/README.md) | `api.e2b.app`，需要 API key，按秒计费 |
| SIG agent-sandbox | [`agent-sandbox-operator.md`](./agent-sandbox-operator.md) | kind 上 Pod Running + exec |
| OpenSandbox Operator | [`opensandbox-operator.md`](./opensandbox-operator.md) | kind 上 Pool 分配 + exec |
| CubeSandbox 控制面 | [`cubesandbox-controlplane.md`](./cubesandbox-controlplane.md) | 控制面 Ready，创建沙箱停在模板 130404 |
| Cube 创建请求 | [`cubesandbox-request-flow.md`](./cubesandbox-request-flow.md) | 源码路径；S6 之后本机未跑到 |

## 不在本仓库

- 2026-09-28 静态长文仍在 `~/Projects/experiments/sandbox/md/`（`OpenSandbox.md` / `CubeSandbox.md` / `agent-sandbox.md`）。本仓库不覆盖它们。
- 上游源码 clone 仍在 `~/Projects/experiments/sandbox/{OpenSandbox,CubeSandbox,agent-sandbox}`。
- 不包含 `e2b-dev/infra`、dashboard、open-computer-use。
