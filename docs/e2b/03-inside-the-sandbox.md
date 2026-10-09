# 沙箱里面

沙箱跑起来之后，SDK 通过 envd 执行命令和访问文件。平台 API 不负责 `ls` 和写文件。

## 命令

```python
result = sandbox.commands.run("ls -l")
print(result.stdout, result.stderr, result.exit_code)
```

Python SDK 2.52.0 里，`commands.run()` 的 `timeout` 默认 60 秒，限制的是这条命令连接，不是沙箱寿命。传 `0` 表示不限制这条连接。非 0 退出码抛 `CommandExitException`，异常对象上仍然有 `stdout`、`stderr`、`exit_code`。

`background=True` 时方法返回 `CommandHandle`，不等待结束。`user` 和 `cwd` 可以覆盖模板默认值。不覆盖时，`base` 上是 `user` 和 `/home/user`，2026-10-03 的探活确认了这两个值。

`stdin=True` 之后可以用 `commands.send_stdin()` 往进程写。关掉前台进程的 stdin 用关闭调用。PTY 里表示 EOF 要送 `Ctrl-D`（字节 `0x04`），不能走那条关闭 stdin 的 RPC。

## 文件

同步 SDK 的文件入口是 `sandbox.files`。常用的是 `read`、`write`、`list`、`make_dir`、`remove`。写文件时如果父目录不存在，上传接口会把父目录补上。已存在的文件会被覆盖。

请求头 `X-Metadata-<key>` 会变成文件上的用户元数据，之后在文件信息里读回来。这是 envd 文件系统接口的行为，不是沙箱的 `metadata`。沙箱 `metadata` 是创建时挂在沙箱对象上的字符串键值，用来过滤列表。

## 从外面访问沙箱里的端口

```python
host = sandbox.get_host(8080)
# https://{host} 指向沙箱内的 8080
```

SDK 拼出来的主机名是 `{port}-{sandboxID}.{domain}`。这次探活的实际字符串是 `8080-izt3sl117umxgsyby1eki.e2b.app`。公网 URL 默认是 HTTPS。沙箱内部服务可以用 HTTP，由代理转到外面。如果沙箱里那个端口自己讲 HTTPS，创建时把它放进 `httpsPorts`。这个字段创建后不能改。envd 自己的端口 49983 不能放进这个列表。

`network.allowPublicTraffic` 默认 true。关掉之后，访问沙箱 URL 需要认证。它也是创建时决定的，运行中改网络规则不会改它。

暂停时，已经连上的客户端会断。恢复后 URL 还在，客户端要重新连。

## 出网

默认允许出网。关掉整个出网：

```python
sandbox = Sandbox.create(allow_internet_access=False)
```

这和 `network.deny_out` 设为 `0.0.0.0/0` 等价。更细的规则用 allow 和 deny。allow 永远优先于 deny。域名只能出现在 allow 里，deny 只接受 IP 和 CIDR。使用域名规则时要同时拒绝其余流量，否则域名过滤不成立。只要规则里有域名，DNS `8.8.8.8` 会被自动放行。

域名判断只覆盖 80 端口的 HTTP Host 和 443 端口的 TLS SNI。别的端口只看 IP 和 CIDR。QUIC / HTTP3 不走这套域名过滤。

防火墙要先接受 TCP，才能判断目的地是否允许。所以在沙箱里面，一条实际上被拒绝的连接仍可能显示套接字已经打开。确认流量是否到达，要看 HTTP 状态码、TLS 握手或协议字节，不要只看 TCP 是否连上。

运行中可以改出网，而且是整份替换，不是合并：

```python
sandbox.update_network({
    "deny_out": lambda ctx: [ctx.all_traffic],
    "allow_out": ["api.example.com"],
})
```

空对象会清掉创建时设的 allow 和 deny。省略 `rules` 也会清掉按主机注入请求头的规则。

`network.rules` 可以在出网 HTTPS 上按主机注入头。规则本身不授权出网，主机仍要出现在 allow 里。头的值可以引用 Secret 或 workload identity 的占位符，由出口代理在沙箱外面替换。这把 key 的 Secret API 当前不可用，见 [安全和计费](05-security-and-billing.md)。

## MCP

创建时传入 `mcp`，SDK 会在沙箱里启动 `mcp-gateway`。模板被省略时，SDK 改用 `default_mcp_template`，而不是 `base`。网关启动失败时 SDK 会尝试 `kill()` 这台沙箱再抛错。本仓库的示例没有开 MCP。
