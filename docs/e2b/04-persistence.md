# 持久化：pause、snapshot、volume

三样东西都叫「把沙箱里的东西留下来」，留下的对象不同。

| | pause | snapshot | volume |
| --- | --- | --- | --- |
| 留下什么 | 同一台沙箱的磁盘和内存 | 一个可重复启动的时间点 | 一块独立磁盘 |
| 原来的沙箱 | 停在 paused | 短暂停顿后继续 running，ID 不变 | 与沙箱寿命无关 |
| 能长出几台 | 恢复的还是这一台 | 一台快照可以启动多台 | 一块盘可以先后或分别挂到多台 |
| 计运行费 | 暂停期间不计 | 拍的过程中原来的沙箱仍在运行 | 盘本身不是沙箱 CPU |
| 自动删除 | 没有，只能 kill | 用 `delete_snapshot` 删 | 用 `destroy` 删 |
| 这把 key | 探活时没有留下 paused | 没有调用 | `GET /volumes` 是 200，列表长度为 0 |

## pause

适合「这个会话下次还要接着用」。把 `sandbox_id` 存到自己的数据库，以后 `Sandbox.connect(sandbox_id)`。

默认同时保存内存。`pause(keep_memory=False)` 或超时策略里的 `keep_memory: False` 只留文件系统，恢复时机器会重启，暂停前没写回磁盘的内存就没了。

paused 不占「正在运行」的那份连续时长。Hobby 的 1 小时、Pro 的 24 小时都是从恢复之后重新算。paused 会一直留着，平台没有「暂停 N 天后自动删」的开关。

并发上限数的是正在 running 的沙箱。暂停后不再为这台付 CPU 和内存的运行费。具体是否还占用别的配额，以 Console 和当时的 FAQ 为准。本笔记不把「不计费」写成「不占任何配额」。

## snapshot

适合「这个现场我要复制几份」。`sandbox.create_snapshot()` 或 `Sandbox.create_snapshot(sandbox_id)` 返回 `snapshot_id`。新沙箱从它启动：

```python
snapshot = sandbox.create_snapshot()
child = Sandbox.create(snapshot.snapshot_id)
```

拍摄期间原来的连接会断，包括 WebSocket、PTY 和命令流。客户端要能重连。拍完后原沙箱回到 running。

前置条件是模板的 envd 不低于 0.5.0。这次 `base` 的 envd 是 0.6.10，满足。

fork 是同一次调用里先拍再启动多台。原沙箱会被短暂停下、拍下含内存的快照、再在原节点恢复，ID 和到期时间不变。

文档建议：如果那个状态可以用模板命令重复做出来，优先用模板。模板在构建末尾会重启客户机，内存更干净，预取也更有效。snapshot 适合数据已经在内存里、或者要回滚一次有风险的操作。

## volume

volume 的生命周期不属于某一台沙箱。沙箱销毁后，写在 volume 里的文件还在。一块 volume 可以挂给多台沙箱，路径在创建沙箱时指定：

```python
from e2b import Volume, Sandbox

volume = Volume.create("my-volume")
sandbox = Sandbox.create(volume_mounts={"/mnt/my-data": volume})
```

没有挂载时，SDK 也能直接对 volume 做读写。官方说明 volume 仍是 private beta，要使用可写信给 `support@e2b.dev`。已知限制包括文件锁、大量小文件的性能，以及文件属主。

2026-10-03 这把 key 对 `GET /volumes` 返回 200 和空数组。列表接口是通的。本仓库没有调用 `Volume.create()`，所以不能从这次探活判断创建是否会因为 beta 被拒绝。

## 选择

会话还要继续，用 pause，并自己保存 `sandbox_id`。

要并行试几条路，或在危险操作前留退路，用 snapshot。

多台沙箱要看同一批文件，用 volume。在 beta 放开之前，不要把它当成已经能上线的磁盘。
