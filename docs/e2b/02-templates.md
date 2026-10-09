# Template

Template 是沙箱的启动盘。它不是一份 Dockerfile 文本存在平台上，而是构建结束时那台沙箱的快照：文件系统，加上当时还活着的进程。官方写的冷启动量级大约是 80 毫秒，前提是进程已经在快照里跑起来了。

## 构建时发生什么

文档里的顺序是：

1. 按模板定义做出一个容器，抽出文件系统，做配置，跑每一层命令，然后启动一台沙箱。
2. 如果定义了 start command，就执行它。没有则跳过。
3. 等就绪。定义了 start command 时默认等 20 秒，也可以换成 ready command。没有 start command 则立刻视为就绪。
4. 给这台沙箱拍快照。这份快照就是以后 `Sandbox.create()` 用的模板。

内核在这一刻固定。2025-11-27 及之后构建的模板是 6.1.158，更早是 6.1.102。配置在 [e2b-dev/fc-kernels](https://github.com/e2b-dev/fc-kernels/tree/main/configs)。旧模板不能改内核，只能重建。

默认用户是 `user`，工作目录是 `/home/user`。模板里最后一次 `set_user` 会变成以后每台沙箱的默认用户。

## 在代码里定义

CPU 和内存写在构建参数上，不写在运行时的 `Sandbox.create()` 里。文档给出的默认规格是 2 vCPU 和 512 MiB，和这次从 `base` 拉起的沙箱一致。Hobby 上限是 8 vCPU、8 GiB 内存、10 GiB 磁盘。Pro 的磁盘从 20 GiB 起，CPU 和内存可以再加。

```python
from e2b import Template, default_build_logger

template = (
    Template()
    .from_base_image()
    .run_cmd("whoami")  # user
    .run_cmd("pwd")     # /home/user
)

Template.build(
    template,
    "my-template",
    cpu_count=2,
    memory_mb=512,
    on_build_logs=default_build_logger(),
)
```

构建需要 SDK 至少 2.3.0 才能用这套 user 和 workdir 行为。本仓库的示例锁定 `e2b>=2.52.0`，满足这个要求。

## 名字

每个 Project 有一个 slug。模板 `my-app` 在 slug 为 `your-project-slug` 的项目里，全名是 `your-project-slug/my-app`。同一个 Project 里可以只用短名。别的 Project 要引用公开模板时用全名。

tag 用来标版本和环境。同一条模板可以有多次 build，tag 指向其中某一次。构建状态在 API 里是 `building`、`waiting`、`ready`、`error`、`uploaded`。

## 这把 key 上的模板

2026-10-03，`GET /templates` 和 `GET /v2/templates` 都返回空数组。这个 Project 还没有自定义模板。

直接 `Sandbox.create()` 用的是公共模板 `base`。探活读到：

| 字段 | 值 |
| --- | --- |
| `template_id` | `rki5dems9wqfm4r03t7g` |
| `name` | `base` |
| `envd_version` | `0.6.10` |
| 内核 | `6.1.158+`，构建标记 `Fri Jul 3 14:02:15 UTC 2026` |

`envd` 0.6.10 高于 snapshot 要求的 0.5.0，所以这台 `base` 可以做 snapshot。自定义模板如果是 0.5.0 之前建的，要先重建才能拍 snapshot。

官方生命周期文档的示例里，`base` 的 `templateId` 也是 `rki5dems9wqfm4r03t7g`。这是公共模板的 ID，不是这个 Project 的私有资源。

## 和 snapshot 怎么选

模板由声明式定义产生，每次构建走同一条命令。snapshot 抓住的是某一时刻内存和磁盘的现场。文档的性能判断是：能写成模板的环境，冷启动和预取都比 snapshot 好，因为构建结束前客户机会重启，内存更紧，用不到的安装进程不在快照里。按客户或按项目建很多模板是支持的用法。

还没准备好写自定义模板时，继续用 `base`，在沙箱里用 `commands.run()` 临时安装。那个安装只活在这一台沙箱里，除非 pause、snapshot，或写进下一次模板构建。
