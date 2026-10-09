# 隔离、密钥和计费

## 隔离边界

每台沙箱是一台 Firecracker microVM，有自己的内核视角。调用方拿到的是这台 VM 里的 shell，不是宿主机的 shell。

`base` 的默认用户是 `user`，工作目录是 `/home/user`。需要 root 时在单条命令上指定 `user="root"`，例如 SDK 启动 MCP gateway 时就是这么做的。不要把整个模板改回 root，除非明确知道安装步骤要求这样。

Python SDK 2.52.0 的 `Sandbox.create(secure=...)` 已废弃。文档字符串写明：每台沙箱都会保护 envd 访问，这个参数还会被接受，但会被忽略。

API key 是 Project 级凭证。拿到 key 的人可以在这个 Project 里创建沙箱、读取正在运行的沙箱列表、销毁沙箱。key 放在 `examples/e2b/.env`，文件名在 `.gitignore` 里。示例只通过环境变量读取，不会把 key 打印出来。

这把 key 的完整字符串曾经出现在一次对话里。仓库历史里没有它。如果那段对话会离开这台机器，到 [Console](https://console.e2b.dev) 轮换，并更新本地 `.env`。

## 网络作为第二道边界

VM 隔离不等于出网隔离。默认沙箱可以访问互联网。跑不受信任的代码时，至少做下面一件事：

- `allow_internet_access=False`，关掉全部出网。
- `deny_out` 拒绝 `0.0.0.0/0`，`allow_out` 只留需要的域名或 IP。

allow 优先于 deny。被拒绝的 TCP 在沙箱内仍可能看起来连接成功，要用应用层响应确认。共享 CDN 上，放行一个主机名可能碰到同一入口后的其他目标。更严的限制走自己的 SOCKS5 代理，也就是文档里的 BYOP。出口代理功能如果账号没开，API 会 403，原文类似 `Egress proxy (network.egressProxy) is not enabled for this team.` 这次探活没有发送 egress proxy 配置。

公开 URL 默认任何人都能访问。不需要公网入口时，创建时把 `allow_public_traffic` 设为 false。这个开关创建后不能改。

## Secret 和 workload identity

Secret 存在 E2B 里，值不会从读取接口返回。用法是在 `network.rules` 里引用名字，由出口代理在沙箱外面把值填进 HTTPS 请求。沙箱进程和调用方代码都看不到替换后的值。

2026-10-03 这把 key 调用 `GET /secrets?limit=5` 的结果是 HTTP 403，正文是：

```json
{"code": 403, "message": "Secrets are not available for this team"}
```

所以当前 Project 不能创建或列出 Secret。要等功能对这个 Project 开放之后，再把密钥迁出沙箱环境变量。在那之前，传给沙箱的 `envs` 会出现在沙箱内部，不要把长期凭证放进去。

workload identity 是另一条路：创建沙箱时登记 `iam.tokens`，出口代理按请求签发短时令牌。占位符不会在调用方进程里被换成真令牌。这条能力这次没有试。

## 计费

只在沙箱 running 时按秒计费。单价乘的是分配额，不是实际占用。paused 和 killed 停止计运行费。磁盘包含在套餐里：Hobby 10 GiB，Pro 20 GiB。

文档给出的公式：

```text
cost = (vCPU × vCPU_rate + RAM_GiB × RAM_rate) × seconds_running
```

2026-10-03 文档上的费率：

| 资源 | 每秒 | 每小时 |
| --- | --- | --- |
| vCPU | 0.000014 美元 / vCPU | 0.0504 美元 / vCPU |
| 内存 | 0.0000045 美元 / GiB | 0.0162 美元 / GiB |

默认 2 vCPU、0.5 GiB 跑 1 小时，文档的例算是大约 0.109 美元。同一规格跑 60 秒是这个数的 1/60，大约 0.0018 美元。费率会变，以 [定价页](https://e2b.dev/pricing) 为准。

这次探活把沙箱的 `end_at` 设在 `started_at` 之后 60 秒，并在打印完三条命令后立刻 `kill()`。实际运行短于 60 秒。账单以 Console 的 usage 为准。

套餐上限，摘自同一天的 billing 文档：

| | Hobby | Pro |
| --- | --- | --- |
| 月费 | 0 | 150 美元 |
| 新用户额度 | 一次性 100 美元 | 升级不另送额度 |
| 连续运行 | 1 小时 | 24 小时 |
| 同时 running 的沙箱 | 20 | 100，附加包可到 1100 |
| 同时构建 | 20 | 20 |
| 创建速率 | 每秒 1 个 | 每秒 5 个 |
| paused 保留 | 无期限 | 无期限 |

额度用完后账号会被挡住，需要加支付方式。可以在 Console 的 budget 页设花费上限。这把 key 的剩余额度和当前套餐，列表接口没有返回。

API 限流按 Project、按端点、按秒计算。Hobby 上列出的那些 GET 大多是每秒 10 次，Pro 是 20 次。超限返回 429，带 `Retry-After`。SDK 从 2.49.1 起会按这个头自动重试。

## 用完即停

探活脚本的结构是 `try` / `finally` 里调用 `kill()`。超时默认动作也是 kill，但默认寿命在 v2 API 上是 300 秒，中间一直在计费。批量任务结束要主动 `kill()`。还要接着用的会话用 pause，而不是把 timeout 拉到套餐上限后放着。
