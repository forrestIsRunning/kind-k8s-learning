# kind-k8s-learning

本地 kind 学习集群：1 个 control-plane + 1 个 worker。

kind 里的 control-plane 就是常见文档里的 master。kubeconfig 写在仓库内 `.kube/config`，不写入 `~/.kube/config`，不进入 `kubectx` 列表。

## 前置条件

- Docker Desktop 正在运行（`docker info` 成功）
- `kind`、`kubectl`

```bash
docker info >/dev/null
kind version
kubectl version --client
```

## 使用

```bash
cd ~/Projects/personal/kind-k8s-learning

make create
make nodes
make status
make context-check
make delete
```

`make create` 会等到两个节点 Ready。`make context-check` 应显示系统 current-context 仍是原来的 EKS / 其它集群，lab current-context 才是 `kind-k8s-lab`。

在该仓库目录学习时，可以把 kubeconfig 限定在当前 shell：

```bash
export KUBECONFIG="$PWD/.kube/config"
kubectl get nodes -o wide
```

新开终端、不设置 `KUBECONFIG` 时，默认仍使用 `~/.kube/config`。

## 不要做

不要执行：

```bash
kind export kubeconfig --name k8s-lab
kubectl config use-context kind-k8s-lab
```

这两条会改 `~/.kube/config`，把 `kind-k8s-lab` 写进 `kubectx`，并可能切走当前生产 context。

需要导出时指定文件：

```bash
kind export kubeconfig --name k8s-lab --kubeconfig "$PWD/.kube/config"
```

## 集群配置

见 [`cluster/kind.yaml`](./cluster/kind.yaml)。control-plane 映射了本机 `8080 -> 80`、`8443 -> 443`，方便以后加 Ingress；第一版不安装 Ingress Controller。
