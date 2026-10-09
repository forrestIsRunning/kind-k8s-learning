# 三条主流用法

E2B 现在被用起来的方式，可以收成三种产品形态。官方 cookbook 里数量最多的例子，都落在这三行里：代码解释器、把编码 Agent 放进沙箱、以及让人通过 URL 看到沙箱里跑起来的东西。

1. 跑一段不受信任的代码，拿回结果。沙箱活几十秒，结果在 stdout、执行对象或文件里，然后销毁。
2. 把一个编码会话放进沙箱。Agent 读仓库、改文件、跑测试、交出 diff。空闲就暂停，下次用同一个 sandbox id 接着做。每次请求都要的依赖放进模板。
3. 沙箱里跑一个服务，外面通过 URL 看结果。生成式界面、预览、人机确认都是这一类。外面看的是 HTTPS 响应，不是 TCP 是否连上。

三种形态的账单不同。第一种按秒计，结束即停。第二种暂停期间不计运行费，恢复后连续运行窗口重新计算。第三种只在有人看的那一小段保持 running。

下面每节先给可复制的 Python，再写做错时会发生什么。测试函数在 `examples/e2b/classic_flow/test_classic_flow.py`。对象模型的展开说明在 [心智模型](00-mental-model.md)。

## 一次调用里有哪些对象

调用方持有的是一把 Project 的 API key。Project 以前叫 Team。模板决定沙箱启动时磁盘和进程长什么样，默认公共模板是 `base`，代码解释器用 `code-interpreter-v1`。沙箱是从模板启动的 Firecracker microVM。envd 是沙箱里的控制进程，命令和文件走它，不走 `api.e2b.app`。

三条主线都不要绕过这四个对象。不要在宿主机上执行模型写出来的代码。不要把沙箱 id 当成密钥。不要把长期凭证放进 `envs`。

## 代码解释器

多格 Python 用 `e2b_code_interpreter` 的 `run_code`。同一个沙箱里的后一次调用能看见前一次留下的变量。这是内核状态，不是把脚本拼进 `python -c`。

```python
from e2b_code_interpreter import Sandbox

sandbox = Sandbox.create(timeout=120, metadata={"demo": "classic-flow"})
try:
    first = sandbox.run_code("x = 21")
    assert first.error is None
    second = sandbox.run_code("print(x * 2)")
    assert "".join(second.logs.stdout).strip() == "42"
finally:
    sandbox.kill()
```

`logs.stdout` 是字符串列表。`error` 为空表示这段代码没有抛异常。代码抛异常时，`run_code` 仍正常返回，异常在 `execution.error` 里，字段是 `name`、`value`、`traceback`。内核不会因为一次 `ZeroDivisionError` 死掉，下一次 `print(1)` 还应该成功。调用方如果把异常当成进程崩溃，就会误杀沙箱，或者更糟，忘了杀。

图表在 `execution.results` 里。`matplotlib` 的 `plt.show()` 会带一个 `png` 字段，内容是 base64，同时还有结构化的 `chart`。判断图画出来了，要解码后看到 PNG 文件头，不能只看 `results` 非空。不要在沙箱里先调用 `matplotlib.use("Agg")`。解释器自己挂了捕获图像的后端，换成 Agg 之后单元能跑完，但 `results` 是空的。

做错时会怎样：

- 用 shell 跑一段 `python -c`，变量不会留到下一次。
- 只看 stdout，会把 `1/0` 当成「没有输出」而不是错误。
- 创建时不写 `timeout`。Python SDK 2.52.0 会省略该字段，`POST /v2/sandboxes` 的默认值是 300 秒，这段时间按分配的 vCPU 和内存计费。JavaScript 的对应参数是 `timeoutMs`，单位是毫秒。
- `finally` 里没有 `kill()`。异常路径会把沙箱留到超时。

对应测试：`test_interpreter_state`、`test_interpreter_chart`、`test_interpreter_error_is_data`。

## 文件和编码回路

文件用 `files.write` 和 `files.read`。路径放在 `/home/user` 下面。父目录不存在时写入会补上。已有文件会被覆盖。二进制用 `format="bytes"`，不要经 shell 做 base64。

```python
from e2b import Sandbox

sandbox = Sandbox.create(timeout=120)
try:
    sandbox.files.write("/home/user/data.csv", "alpha,1\nbeta,2\n")
    raw = sandbox.files.read("/home/user/data.csv", format="bytes")
    assert bytes(raw) == b"alpha,1\nbeta,2\n"
finally:
    sandbox.kill()
```

编码 Agent 的最小闭环和模型无关：写入函数、写入测试、跑测试、取出 diff。生产环境把 git、语言运行时和测试工具预装进模板，启动后直接干活。`base` 上临时 `apt-get install git` 只是这套 demo 在没有现成模板时的退路。Claude Code、Codex 这一类还要把 Agent 自己的二进制和凭证放进模板或安全注入。这把 key 没有那些模型凭证，所以测试停在 diff，不启动 Agent。

做错时会怎样：

- 用 `commands.run("cat > file")` 写二进制，引号和编码会把内容写坏。
- 只把 stdout 当交付物，调用方拿不到补丁，下一轮会话无法审查改了什么。
- 每次请求都 `pip install`。安装时间算在 running 的账单里，而且失败面比模板构建更大。

对应测试：`test_files_roundtrip`、`test_coding_loop`。

## 暂停、快照、模板

| | pause | snapshot | template |
| --- | --- | --- | --- |
| 留下什么 | 同一台沙箱 | 一个可复制的时间点 | 一份可重复构建的启动盘 |
| 原来的沙箱 | 停在 paused | 短暂停顿后继续 running | 构建用的沙箱在构建结束时消失 |
| 能不能长出第二台 | 不能，恢复的还是这一台 | 能，一台快照启动多台 | 能，每次 create 都是新沙箱 |
| 运行费 | 暂停后停止 | 拍摄期间原沙箱仍在跑 | 只在构建和之后的运行期计费 |
| 什么时候用 | 会话还要续 | 危险操作前留退路，或并行试几条路 | 每次请求都要的包和工具 |

```python
sandbox = Sandbox.create(timeout=120)
sandbox.run_code("x = 7")
sandbox.files.write("/home/user/note.txt", "kept")
sandbox.pause()
resumed = Sandbox.connect(sandbox.sandbox_id, timeout=120)
again = resumed.run_code("print(x)")
```

`connect` 只延长寿命，不缩短。还剩 20 分钟时，用较短的 timeout 去 connect，到期时间不变。要缩短用 `set_timeout`。

文档给出的耗时：保存内存大约每 1 GiB 4 秒，恢复大约 1 秒。节点若还在做同一台沙箱的上一份快照，pause 会返回 HTTP 503，Python SDK 抛 `ServiceBusyException`。沙箱仍在 running，状态没有丢。做法是等几秒再暂停，而不是再创建一台。

snapshot 会打断已经连上的 WebSocket、PTY 和命令流。拍完用返回的 `snapshot_id` 作为 `Sandbox.create` 的模板参数。用完 `Sandbox.delete_snapshot`。从这份快照启动的沙箱还在 running 时，删除会返回 400，正文是 cannot delete template because there are running sandboxes using it。先 `kill` 这些沙箱，再删快照。能写成模板命令的环境优先用模板，因为构建结束时客户机会重启，内存更干净，冷启动也更稳。`base` 的 envd 在 2026-10-03 的探活里是 0.6.10，高于 snapshot 要求的 0.5.0。

模板构建：

```python
from e2b import Template

template = (
    Template()
    .from_base_image()
    .run_cmd(
        "mkdir -p /opt/demo && echo classic-flow-marker > /opt/demo/marker",
        user="root",
    )
)
built = Template.build(
    template,
    "classic-flow-marker",
    cpu_count=2,
    memory_mb=512,
)
```

CPU 和内存在构建时指定，不在 `Sandbox.create` 时临时改。默认够用就保持 2 vCPU 和 512 MiB。这套 demo 在断言通过后删除 `classic-flow-marker`，定义留在测试里，避免账号上堆一个不再使用的模板。

2026-10-03 的一次实跑里，标记文件内容和 `DELETE` 的 204 都已通过，紧接着的 `GET /templates` 在响应头到达前断开，httpx 抛出 `RemoteProtocolError: Server disconnected without sending a response`。当时账号上模板数是 0，断连发生在确认列表，不是构建失败。测试里的控制面请求对 `httpx.TransportError` 最多试 3 次，间隔 2 秒、4 秒。HTTP 状态码不重试，4xx 和 5xx 仍然原样进入断言。

做错时会怎样：

- 用 snapshot 保存「装好 git」这种可重复的状态。下次依赖升级无法重建。
- pause 之后不保存 sandbox id。平台不会发一个列表给业务数据库，调用方自己的库才是索引。
- 以为 paused 会过期。文档写明没有 TTL，只能 `kill`。

对应测试：`test_pause_keeps_kernel_and_file`、`test_snapshot_forks_old_state`、`test_template_marker`。

## 预览和出网

服务要绑在 `0.0.0.0`。本机访问：

```python
host = sandbox.get_host(8080)
url = f"https://{host}/"
```

主机名形状是 `{port}-{sandboxID}.e2b.app`。公网侧是 HTTPS。沙箱里的进程可以讲 HTTP，由代理转到外面。`allow_public_traffic` 只在创建时能定，默认公开。不需要被人访问的任务不要开端口。

出网默认是开的。不受信任的代码在创建时关掉：

```python
sandbox = Sandbox.create(timeout=120, allow_internet_access=False)
```

这和 `deny_out` 设为 `0.0.0.0/0` 等价。验证时看应用层：`curl -fsS --max-time 8 https://example.com` 的退出码必须非 0，正文里不能出现示例站点的标题。防火墙会先接受 TCP 再决定是否丢弃，所以沙箱里的套接字可能显示已经连上。只断言 TCP 成功会把「已经隔离」判断反。

更细的规则是 allow 优先于 deny。域名只能写在 allow 里，而且只覆盖 80 端口的 Host 和 443 端口的 TLS SNI。别的端口只看 IP 和 CIDR。

做错时会怎样：

- 服务绑在 `127.0.0.1`，代理连不上。
- 在沙箱里面 curl 自己的公网 URL，这证明不了调用方的机器能打开预览。
- 关掉出网之后还把「curl 退出码 0」当通过。

对应测试：`test_preview_http`、`test_egress_closed`。

## 会话索引和清扫

metadata 是给列表接口过滤用的字符串键值，不是密钥存储。一个用户会话对应一台沙箱时，创建时写入业务自己的 `run_id`，之后按它查询。

```python
from e2b import Sandbox, SandboxQuery

sandbox = Sandbox.create(
    timeout=120,
    metadata={"demo": "classic-flow", "run_id": run_id},
)
found = Sandbox.list(SandboxQuery(metadata={"demo": "classic-flow", "run_id": run_id}))
```

这套测试的清扫有两层。每个测试在 `finally` 里 `kill` 自己创建的 id。进程结束时再按 `demo=classic-flow` 列出 running 和 paused，剩下的也杀掉。paused 没有自动删除，所以第二层不能只查 running。

Hobby 文档上的创建速率是每秒 1 个。测试串行跑。并行创建会收到 429，SDK 从 2.49.1 起会按 `Retry-After` 重试，但测试仍然不要靠重试堆并发。

对应测试：`test_metadata_is_the_index`。套件结束时的清扫在 `conftest.py`。

## 这把 key 跑不了的部分

Secret 用来把凭证留在出口代理上，沙箱进程看不到值。2026-10-03 的 `GET /secrets` 返回 403，正文是 `Secrets are not available for this team`。在这个 Project 开通之前，不要把长期凭证放进 `envs` 凑合。

Volume 是独立于沙箱的磁盘，官方仍标 private beta。测试会尝试创建一块盘。返回 403 或明确的未开通错误时，pytest 记为「此 Project 未开通」，不因此失败。创建成功则写入、读回、销毁，这三步必须通过。

Claude Code、Codex、OpenAI Agents 需要各自的模型密钥，还通常要一份预装了 Agent 的模板。那些例子在 cookbook 里是主流，但这份仓库没有那些密钥。`test_coding_loop` 跑的是它们共同的后半段：改文件、跑测试、取 diff。

## 最佳实践和测试的对应

| 做法 | 锁住它的测试 |
| --- | --- |
| 解释器变量跨调用，结果在 stdout | `test_interpreter_state` |
| 图表以 PNG 字节交付 | `test_interpreter_chart` |
| 代码异常是数据，内核还在，`finally` 仍要销毁 | `test_interpreter_error_is_data` |
| 文件字节进、文本结果出 | `test_files_roundtrip` |
| 依赖进模板，`base` 上没有那份标记 | `test_template_marker` |
| pause 保住内核变量和文件，kill 后列表为空 | `test_pause_keeps_kernel_and_file` |
| snapshot 复制旧现场，原沙箱继续新现场 | `test_snapshot_forks_old_state` |
| 本机打公网 HTTPS，看状态码和正文 | `test_preview_http` |
| 关闭出网后本地命令仍可用，HTTPS 拿不到示例页 | `test_egress_closed` |
| metadata 是找回沙箱的索引 | `test_metadata_is_the_index` |
| 编码会话的交付物是通过的测试和 diff | `test_coding_loop` |

运行：

```bash
cd examples/e2b/classic_flow
uv sync
uv run pytest -q
```

API key 放在 `examples/e2b/.env`，变量名 `E2B_API_KEY`。测试不会打印它。
