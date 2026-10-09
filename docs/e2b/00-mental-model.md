# 心智模型

E2B 把「跑不受信任的代码」收成一次 API 调用。调用方不管理宿主机，只拿一把 API key 创建沙箱、在里面执行命令，然后暂停或销毁。

官方对沙箱的描述是按需创建的 Linux VM，底层是 Firecracker microVM。文档写的内核基线是 LTS 6.1。2026-10-03 这台默认 `base` 沙箱的 `uname -a` 是 `6.1.158+`，主机名 `e2b.local`，架构 `x86_64`。

## 两条通路

控制面和沙箱内部不是同一个地址。

| 通路 | 地址 | 谁在用 | 认证 |
| --- | --- | --- | --- |
| 平台 API | `https://api.e2b.app` | 创建、列表、暂停、销毁、模板、volume | 请求头 `X-API-Key` |
| envd | 沙箱自己的主机名 | 命令、文件系统、PTY | 创建沙箱时下发的 envd access token |

SDK 把第二条通路藏起来了。`Sandbox.create()` 先打平台 API，再用返回的沙箱地址去跟 envd 说话。`commands.run()` 和 `files.read()` 走的是 envd，不是 `api.e2b.app`。

OpenAPI 还写了一条共享入口：envd 也可以打到 `sandbox.e2b.app`，用 `E2b-Sandbox-Id` 和 `E2b-Sandbox-Port` 指到某一台。日常用 SDK 时不用自己拼这两个头。

对外暴露沙箱里某个端口时，主机名形式是 `{port}-{sandboxID}.{domain}`。这次探活里 `get_host(8080)` 返回 `8080-izt3sl117umxgsyby1eki.e2b.app`。同一份 `get_info()` 的 `sandbox_domain` 字段是空的，公开主机名仍然落到了 `e2b.app`。

## 四个对象

**Project。** 一把 API key 只属于一个 Project。这个 Project 里的 sandbox、template 和账单都由这把 key 决定。文档说明 Project 以前叫 Team，API、模板 slug 和已有集成不用改。`GET /teams` 用 `X-API-Key` 会 401，原文是 `authorization header is missing`。Project 的名字、成员和套餐要到 Console 看，不能从这几个资源接口读出来。

**Template。** 模板是一次构建结束时拍下的沙箱快照，里面有文件系统，也有当时还在跑的进程。之后每次 `Sandbox.create(template)` 都从这份快照启动。不传模板时，Python SDK 2.52.0 的 `default_template` 是字符串 `base`。

**Sandbox。** 从模板启动出来的那一台 VM。它有自己的 ID、CPU、内存、到期时间和状态。状态见 [生命周期](01-sandbox-lifecycle.md)。默认规格在文档和这次探活里一致：2 vCPU，512 MiB 内存。

**持久化。** 三样东西名字接近，留下的东西不同。pause 暂停同一台沙箱。snapshot 从一台正在跑的沙箱复制出可多次启动的检查点。volume 是可以挂到多台沙箱上的独立磁盘，目前是 private beta。对照表在 [持久化](04-persistence.md)。

## 一次创建在代码里长什么样

```python
from e2b import Sandbox

sandbox = Sandbox.create(timeout=60)  # 省略 template 时使用 base
result = sandbox.commands.run("echo hello")
print(result.stdout)
sandbox.kill()
```

`timeout=60` 的单位是秒。JavaScript SDK 的对应参数叫 `timeoutMs`，单位是毫秒。同一份官方示例里两边数字不能直接对抄。

Python SDK 2.52.0 在 `timeout=None` 时不把该字段发给 API。`POST /v2/sandboxes` 的 OpenAPI 把 `timeout` 默认写成 300 秒。旧版 `POST /sandboxes` 文档里出现过 15 秒。写代码时显式传入，避免踩到默认值差异。

## 和「在本机开 Docker」的差别

沙箱的默认用户是 `user`，工作目录是 `/home/user`。这次探活的 `whoami` 和 `pwd` 就是这两个值。Docker 镜像常见的默认是 `root` 和 `/`。E2B 把这个默认写进模板，是为了安装工具时有一个家目录，同时少用 root。

模板在构建时固定内核。文档的分界是：2025-11-27 及之后构建的模板用 6.1.158，更早的用 6.1.102。已有模板不能原地升级内核，要重建。

## 接着读

生命周期、超时和暂停：[01-sandbox-lifecycle.md](01-sandbox-lifecycle.md)。这把 key 当天的空账号和那台 60 秒沙箱：[06-this-account.md](06-this-account.md)。
