# classic flow 的一次全绿实跑

日期：2026-10-03。代码：原独立仓库 `forrestIsRunning/e2b` 的 `38951d5`。命令在 `examples/e2b/classic_flow` 里执行：`uv run pytest -v --tb=short`。仓库文档里的日常命令是 `uv run pytest -q`，收集到的是同一批测试。

解释器：CPython 3.13.12。包版本：`e2b` 2.52.0，`e2b-code-interpreter` 2.10.1，`pytest` 9.1.1。平台仍是 `https://api.e2b.app`。key 不在这里，只在 `examples/e2b/.env`。

pytest 结果：13 passed，耗时 74.52 秒，退出码 0。`conftest.py` 写下的 `.run/cleanup.json` 是 `exitstatus` 0、`swept` 空、`leftover` 空。检查记录共 34 条，全部 `ok`。`.run/` 被 gitignore，下面的表是从那次 `checks.jsonl` 整理的。

同日早一次全套件失败在 `test_template_marker`。标记文件和 `DELETE` 的 204 已经通过，随后 `GET /templates` 在响应头之前断开。那次的修复是 `38951d5`，对 `httpx.TransportError` 重试，不改断言。下面的数字只来自修复之后这一次，不和失败那次混写。

## 三条主线各自交出了什么

代码解释器。`run_code("x = 21")` 的 `error` 是 None。下一格 `print(x * 2)` 的 stdout 去掉空白后是 `42`。这是同一个 Jupyter 内核里的变量，不是把两段脚本拼成一次 `python -c`。

图表。单元格没有调用 `matplotlib.use("Agg")`，只有 `pyplot` 的 `plot` 和 `show`。`error` 是 None。唯一一个 result 的格式是 `text`、`png`、`chart`。PNG 的 base64 解码后长度 16705，前缀是 `b'\x89PNG\r\n\x1a\n'`。`code-interpreter-v1` 这台沙箱里 matplotlib 可用。缺 matplotlib 会让这条测试失败，不会被跳过。

错误是数据。`run_code("1/0")` 没有把进程打崩，异常在 `execution.error` 里，`name` 是 `ZeroDivisionError`，`value` 是 `division by zero`。traceback 把用户代码标在 `Cell In[1], line 6`，那一行是 `1/0`。前面几行是解释器自己写上的环境变量：`E2B_SANDBOX=true`，`E2B_SANDBOX_ID=i00fiyllhmm5ddcpq9koi`，`E2B_TEMPLATE_ID=nlhz8vlwyupq845jsdg9`。所以 traceback 的行号不是「用户字符串的第 1 行」。SDK 常量 `DEFAULT_TEMPLATE` 是 `code-interpreter-v1`。这次没有把 `nlhz8vlwyupq845jsdg9` 解析成模板名。它和 [探活](06-this-account.md) 里 `base` 的 `rki5dems9wqfm4r03t7g` 不是同一个 id。下一格 `print(1)` 的 stdout 是 `1`，`error` 仍是 None。内核还在，调用方仍然要在 `finally` 里 `kill`。

文件。写入 `/home/user/data.csv` 的字节是 `b'alpha,1\nbeta,2\n'`，读回相等。沙箱里的 Python 把第二列求和写到 `/home/user/sum.txt`，命令退出码 0，下载后的文本是 `3`。

编码回路。这次 `git --version` 的退出码是 0，测试没有走 `apt-get`，所以记录里没有 `git_installed_for_demo`。只能说这次的 `base` 沙箱上已经有 git，不能写成 `base` 永远带 git。生产环境仍应把 git 放进模板。`python3 -m unittest test_add.py` 退出码 0。stdout 是空的，`Ran 1 test in 0.000s` 和 `OK` 写在 stderr。成功看退出码，不看 stderr 是否为空。`git diff --cached` 里同时有 `add.py` 和 `test_add.py`。断言只要求 diff 含有 `def add`。`git init` 把默认分支名 `master` 的 hint 打在 stderr，退出码仍是 0。没有启动 Claude Code 或 Codex。

暂停。`pause()` 第一次就成功，记录里没有 `pause_retried_after_503`。列表里这台沙箱的状态是 `paused`，id 是 `i23gj5uyiodxvbclon84l`。`connect` 之后 `print(x)` 的 stdout 是 `7`，`/home/user/note.txt` 仍是 `kept`。`kill` 之后按 `demo=classic-flow` 列出的 id 是空的。暂停保住的是同一台机器上的内核和文件。

快照。子沙箱读到的是拍摄前的 `v1`。原沙箱重新连上之后读到的是拍摄后写入的 `v2`。两台都 `kill` 之后 `delete_snapshot` 返回 True。这次没有再碰到「还有沙箱在用这份快照」的 400。那个 400 的原文和先杀后删的原因写在 [三条主流用法](07-mainstream-usage.md)。

模板。`classic-flow-marker` 从 `base` 构建，构建日志末尾是 `Build finished, took 12s`。从该模板启动的沙箱里 `cat /opt/demo/marker` 退出码 0，stdout 是 `classic-flow-marker`。同一时刻从 `base` 启动的沙箱里，这条 `cat` 退出码 1，stderr 是 `cat: /opt/demo/marker: No such file or directory`。`DELETE /templates/{templateID}` 返回 204。断言接受 200 或 204，这次观察到的是 204。删除后的模板列表里不再有这个名字。

预览。宿主机用 HTTPS 请求 `https://8080-ivt09djha3e5zk4uapeqz.e2b.app/`，没有附加 traffic token。状态码 200，正文是 `classic-flow-preview` 加换行。服务进程绑的是 `0.0.0.0:8080`。判断依据是这段正文，不是沙箱内部的 TCP 是否连上。

出网关闭。`allow_internet_access=False` 的沙箱里，`echo ok` 退出码 0。`command -v curl` 退出码 0，路径是 `/usr/bin/curl`，所以没有在断网沙箱里 `apt-get`。`curl -fsS --max-time 8 https://example.com` 的退出码是 28，stdout 为空，stderr 是 `curl: (28) Resolving timed out after 8000 milliseconds`。正文里没有 `Example Domain`。这次「出网关掉」的样子是 DNS 解析超时，不是连接被立刻拒绝，也不是一个 HTTP 状态码。断言不锁定 28 这个数字，只锁定非 0 且拿不到示例页。换一天可能看到别的非 0 退出码，那仍然满足当前断言。本地命令还能跑，说明沙箱自己活着。

metadata。带唯一 `run_id` 的查询只命中 `i5eg9g3kj83skw2jan0ph`。`kill` 之后同一查询是空列表。metadata 在这里是索引，不是密钥。

## 34 条检查

| 检查 | 期望 | 实际 |
| --- | --- | --- |
| `interpreter_first_cell_has_no_error` | `error` 是 None | None |
| `interpreter_second_cell_has_no_error` | `error` 是 None | None |
| `interpreter_stdout` | `42` | `42` |
| `chart_cell_has_no_error` | `error` 是 None | None |
| `chart_has_png` | 至少一个带 png 的 result | 格式 `text`、`png`、`chart` |
| `chart_png_bytes` | PNG，长度大于 8 | 长度 16705，前缀 `89 50 4E 47 0D 0A 1A 0A` |
| `division_error_name` | `ZeroDivisionError` | 名称匹配，`1/0` 在 Cell 第 6 行 |
| `kernel_still_runs` | stdout `1` 且没有 error | stdout `1`，error 是 None |
| `uploaded_bytes` | `b'alpha,1\nbeta,2\n'` | 字节相等 |
| `sum_command` | 退出码 0 | 退出码 0，stdout 和 stderr 都是空 |
| `downloaded_sum` | `3` | `3` |
| `marker_on_custom_template` | stdout 等于 `classic-flow-marker` | 退出码 0，构建日志写 `took 12s` |
| `marker_absent_on_base` | `base` 上退出码非 0 | 退出码 1，文件不存在 |
| `template_delete_status` | 204（断言也接受 200） | 204 |
| `template_gone` | 列表里没有这个名字 | `[]` |
| `pause_setup` | `error` 是 None | None |
| `listed_as_paused` | 状态是 paused | `i23gj5uyiodxvbclon84l` 为 paused |
| `kernel_value_survives_pause` | stdout `7` | stdout `7`，error 是 None |
| `file_survives_pause` | `kept` | `kept` |
| `gone_after_kill` | id 不在 demo 列表 | `[]` |
| `child_keeps_v1` | `v1` | `v1` |
| `parent_has_v2` | `v2` | `v2` |
| `snapshot_deleted` | True | True |
| `preview_status` | 200 且正文含标记 | 200，正文 `classic-flow-preview` |
| `local_command` | 退出码 0，stdout `ok` | 退出码 0，stdout `ok` |
| `curl_exists` | `curl` 在 PATH 上 | `/usr/bin/curl` |
| `egress_blocked` | curl 非 0，且没有示例页标题 | 退出码 28，DNS 在 8000 毫秒超时，stdout 空 |
| `metadata_hits_one_id` | 只有这一台 | `i5eg9g3kj83skw2jan0ph` |
| `metadata_empty_after_kill` | `[]` | `[]` |
| `unittest_passes` | 退出码 0 | 退出码 0，stderr 里是 `OK` |
| `diff_contains_add` | 暂存 diff 含 `def add` | 退出码 0，`add.py` 与 `test_add.py` 都在 diff 里 |
| `volume_not_enabled_on_this_project` | 403 或明确的未开通 | `status=None 403: use of volumes is not enabled` |
| `no_demo_sandbox_left` | `[]` | `[]` |
| `no_demo_template_left` | `[]` | `[]` |

## 这把 key 上没有跑通的路径

Volume。`Volume.create` 抛出 `VolumeException`。异常对象的 `status_code` 是 None，403 写在消息字符串里：`403: use of volumes is not enabled`。测试据此通过，并且没有进入写入、读回、销毁。那三步只有创建成功时才是必过项。这次不能把 volume 算作已经验证的磁盘。

Secret。这次套件没有请求 `/secrets`。[探活](06-this-account.md) 里的 403 原文 `Secrets are not available for this team` 仍然是那次只读的结果，不是这次 pytest 重新打出来的。

套餐。这些响应里仍然没有 Project 名称、Hobby 或 Pro、并发上限和剩余额度。74.52 秒是 pytest 的墙钟，不是一张账单。默认规格是 2 vCPU 和 512 MiB。文档费率是每 vCPU 秒 0.000014 美元、每 GiB 秒 0.0000045 美元，跑满 60 秒大约 0.0018 美元。每台沙箱的 `timeout` 是 120 秒，但测试在 `finally` 里 `kill`，不会把 120 秒坐满。精确费用以 Console 和 [pricing](https://e2b.dev/pricing) 为准。

这次也没有打到的分支：pause 返回 503 之后的重试，以及快照仍被运行中的沙箱引用时删除返回 400。代码里两条都还在。它们没出现，是因为这次第一次 pause 就成功，而且删除快照之前沙箱已经没了。

## 清扫

套件自己的最后一条测试看到 demo 沙箱列表为空，模板列表里没有 `classic-flow-marker`。session 结束时的第二轮清扫没有需要再杀的 id。

套件结束之后又查了一次，不经过 pytest：`GET /templates` 为 200，数量 0；`Sandbox.list()` 为 0；`Sandbox.list_snapshots()` 为 0。

预览那台沙箱被 `kill` 之后，我用刚才的 URL 又请求了一次。HTTP 502，正文是 `{"sandboxId":"ivt09djha3e5zk4uapeqz","message":"The sandbox was not found","code":502}`。这不是 pytest 断言，是清扫之后的旁证。运行中的 200 才是 `test_preview_http` 的通过条件。

## 这次记录能支持的判断

三条用法里，调用方要锁住的是交付物，不是「沙箱创建成功」。解释器锁 stdout、PNG 字节和异常名称。编码会话锁测试退出码和 diff。预览锁宿主机收到的 HTTPS 正文。出网关闭锁 curl 的非 0 和拿不到的页面，同时锁本地命令仍然是 0。

可重复的环境用模板。这次 12 秒的构建留下了 `/opt/demo/marker`，`base` 上没有它。pause 用来续同一台会话。snapshot 用来分叉一个旧现场，原沙箱继续往前走。用完的模板和快照要删，paused 没有 TTL，所以清扫必须同时覆盖 running 和 paused。
