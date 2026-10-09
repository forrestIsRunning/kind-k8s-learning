# 资料与版本

核对日期：2026-10-03。

页面内容会变。下面的链接是笔记里事实的出处。和探活不一致的地方，以 [06-this-account.md](06-this-account.md) 里写下的原始输出为准，并在笔记里分开写。

## 官方文档

- 文档索引：<https://docs.e2b.dev/llms.txt>
- 文档首页：<https://docs.e2b.dev/>
- Sandbox 生命周期：<https://docs.e2b.dev/sandbox>
- 暂停与恢复：<https://docs.e2b.dev/sandbox/persistence>
- Snapshot：<https://docs.e2b.dev/sandbox/snapshots>
- Template 如何构建：<https://docs.e2b.dev/template/how-it-works>
- 默认用户和工作目录：<https://docs.e2b.dev/template/user-and-workdir>
- 命令：<https://docs.e2b.dev/commands>
- 出网：<https://docs.e2b.dev/network/internet-access>
- Volume：<https://docs.e2b.dev/volumes>
- Project：<https://docs.e2b.dev/projects>
- 计费与限额：<https://docs.e2b.dev/billing>
- 价格计算：<https://docs.e2b.dev/faq/calculate-sandbox-price>
- 定价页：<https://e2b.dev/pricing>
- 创建沙箱 v2：<https://docs.e2b.dev/api-reference/sandboxes/create-sandbox-v2>
- Console：<https://console.e2b.dev>
- 内核配置：<https://github.com/e2b-dev/fc-kernels/tree/main/configs>

## 本机依赖

- Python 包 `e2b` 2.52.0
- 解析工具：`uv`
- 解释器：CPython 3.13.12，由 `uv` 安装
- 平台 API：`https://api.e2b.app`

## 探活范围

只读：templates、sandboxes、volumes、secrets、teams。

写入：一次 `POST` 创建，模板 `base`，`timeout` 60 秒，随后 `kill`。没有模板构建、pause、snapshot、volume 创建或 webhook。
