# 这把 key 的探活记录

日期：2026-10-03。平台：`https://api.e2b.app`。认证头：`X-API-Key`。SDK：Python `e2b` 2.52.0，由 `uv` 安装到 `examples/e2b/hello_sandbox/.venv`，解释器 CPython 3.13.12。

key 本身不写在这里。本地文件是 `examples/e2b/.env`。

## 只读结果

调用前后各列了一次。创建沙箱之前和 `kill()` 之后，下面四行相同。

| 请求 | 状态 | 结果 |
| --- | --- | --- |
| `GET /v2/templates?limit=20` | 200 | 空数组 |
| `GET /templates` | 200 | 空数组 |
| `GET /v2/sandboxes?limit=20` | 200 | 空数组 |
| `GET /volumes` | 200 | 空数组 |
| `GET /secrets?limit=5` | 403 | `Secrets are not available for this team` |
| `GET /teams` | 401 | `authorization header is missing` |

`GET /v2/volumes`、`GET /events`、`GET /webhooks` 返回 404，正文是 `validation error: no matching operation was found`。这些路径和当前 OpenAPI 不一致，不能当成「功能不存在」。volume 的有效列表路径是 `GET /volumes`。

从这些响应看不出 Project 名称、slug、套餐和剩余额度。

## 一台 60 秒的 base 沙箱

命令是 `examples/e2b/hello_sandbox/main.py`：`Sandbox.create(timeout=60)`，读 `get_info()`，跑三条命令，在 `finally` 里 `kill()`。

| 字段 | 观察到的值 |
| --- | --- |
| `sandbox_id` | `izt3sl117umxgsyby1eki` |
| `template_id` | `rki5dems9wqfm4r03t7g` |
| `template_name` | `base` |
| `state` | `running` |
| `cpu_count` | `2` |
| `memory_mb` | `512` |
| `envd_version` | `0.6.10` |
| `sandbox_domain` | `None` |
| `get_host(8080)` | `8080-izt3sl117umxgsyby1eki.e2b.app` |
| `started_at` | `2026-10-03T10:02:44.119643+00:00` |
| `end_at` | `2026-10-03T10:03:44.119643+00:00` |
| `kill()` 返回值 | `True` |

`end_at` 比 `started_at` 正好晚 60 秒，和传入的 `timeout=60` 一致。

命令输出：

```text
$ uname -a
Linux e2b.local 6.1.158+ #1 SMP PREEMPT_DYNAMIC Fri Jul  3 14:02:15 UTC 2026 x86_64 GNU/Linux

$ whoami
user

$ pwd
/home/user
```

三条命令的退出码都是 0。`kill()` 之后再次 `GET /v2/sandboxes` 仍是空数组，没有残留的 running 或 paused 沙箱。

## 这次没有做的事

没有创建自定义模板，没有 pause，没有 snapshot，没有 `Volume.create()`，没有注册 webhook，没有改网络规则，没有往沙箱里写入文件。

因此只能确认：key 有效、`base` 能启动、默认规格和用户与文档一致、销毁后列表为空。不能用这次结果推断 Secret 以外的 403 功能、volume 创建，或 Hobby / Pro 档位。
