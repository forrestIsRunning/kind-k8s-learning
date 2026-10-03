# kind-k8s-learning

本地 kind 学习集群：1 个 control-plane + 1 个 worker。

kind 里的 control-plane 就是常见文档里的 master。`make create` 会把 context `kind-k8s-lab` 加进 `kubectx`，但保持当前 context 不变。

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

`make create` 等到两个节点 Ready，再 `make register`：把 `kind-k8s-lab` 写入 `~/.kube/config`，然后把 current-context 切回原来的集群。

```bash
kubectx                 # 列表里应有 kind-k8s-lab
kubectx kind-k8s-lab    # 切到学习集群
kubectl get nodes
kubectx -               # 切回上一个 context
```

不要直接跑 `kind export kubeconfig --name k8s-lab`。这条会把 current-context 切到 `kind-k8s-lab`。用 `make register`。

## 集群配置

见 [`cluster/kind.yaml`](./cluster/kind.yaml)。control-plane 映射了本机 `8080 -> 80`、`8443 -> 443`，方便以后加 Ingress；第一版不安装 Ingress Controller。

## agent-sandbox（kubernetes-sigs）

kind 节点访问不了本机 `127.0.0.1:1087` 代理，所以镜像要在宿主机 `docker pull` 后再导入节点。不要跑上游 `make deploy-kind`：它会 **重建** 名为 `agent-sandbox` 的集群。

已安装版本：`v1.0.5`（`sandbox-with-extensions.yaml`）。

```bash
kubectx kind-k8s-lab

# 控制器
kubectl -n agent-sandbox-system get pods

# 示例沙箱
kubectl apply -f manifests/agent-sandbox/hello-sandbox.yaml
kubectl get sandbox,pod,svc -n agent-sandbox-demo
kubectl exec -n agent-sandbox-demo hello-busybox -- echo ok
```
