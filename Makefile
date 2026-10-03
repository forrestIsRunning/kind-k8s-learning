.PHONY: create delete nodes status context-check register unregister help \
	load-image opensandbox opensandbox-hello cubesandbox-controlplane

# Do not export KUBECONFIG. A global export leaks into kubectl --kubeconfig
# calls against ~/.kube/config and can rewrite current-context.
LAB_KUBECONFIG := $(CURDIR)/.kube/config
SYS_KUBECONFIG := $(HOME)/.kube/config
CLUSTER := k8s-lab
CONTEXT := kind-k8s-lab
KIND_CONFIG := cluster/kind.yaml
KUBECTL_LAB := kubectl --kubeconfig $(LAB_KUBECONFIG)
KUBECTL_SYS := env -u KUBECONFIG kubectl --kubeconfig $(SYS_KUBECONFIG)
KIND := env -u KUBECONFIG kind
HELM_LAB := helm --kubeconfig $(LAB_KUBECONFIG)
SANDBOX_SRC ?= $(HOME)/Projects/experiments/sandbox
OS_CHARTS := $(SANDBOX_SRC)/OpenSandbox/manifests/charts
CUBE_CHART := $(SANDBOX_SRC)/CubeSandbox/deploy/kubernetes/chart

# Docker Desktop CLI. A leftover OrbStack symlink at /usr/local/bin/docker is broken.
ifneq ($(wildcard /Applications/Docker.app/Contents/Resources/bin/docker),)
export PATH := /Applications/Docker.app/Contents/Resources/bin:$(PATH)
endif

help:
	@echo "Targets:"
	@echo "  make create         - kind create cluster (1 control-plane + 1 worker)"
	@echo "  make register       - add $(CONTEXT) to kubectx, keep current-context"
	@echo "  make nodes          - kubectl get nodes -o wide"
	@echo "  make status         - nodes + kube-system pods"
	@echo "  make context-check  - system current-context vs lab kubeconfig"
	@echo "  make unregister     - remove $(CONTEXT) from ~/.kube/config"
	@echo "  make delete         - kind delete cluster + unregister"
	@echo ""
	@echo "  make load-image IMG=<ref>     - host docker pull + import into kind nodes"
	@echo "  make opensandbox              - Helm OpenSandbox CRD+controller (SANDBOX_SRC)"
	@echo "  make opensandbox-hello        - apply Pool + BatchSandbox hello"
	@echo "  make cubesandbox-controlplane - Helm Cube control-plane only; no cube-node/PVM"
	@echo ""
	@echo "kind create writes $(LAB_KUBECONFIG), then register merges into $(SYS_KUBECONFIG)."
	@echo "kind export kubeconfig --name $(CLUSTER) also switches current-context;"
	@echo "use make register instead."
	@echo "SANDBOX_SRC defaults to $(SANDBOX_SRC)."

create:
	@mkdir -p .kube
	$(KIND) create cluster --config $(KIND_CONFIG) --kubeconfig $(LAB_KUBECONFIG) --wait 5m
	$(KUBECTL_LAB) wait --for=condition=Ready nodes --all --timeout=180s
	@$(MAKE) register
	@$(MAKE) nodes
	@$(MAKE) context-check

register:
	@current=$$($(KUBECTL_SYS) config current-context); \
	$(KIND) export kubeconfig --name $(CLUSTER) --kubeconfig $(SYS_KUBECONFIG); \
	$(KUBECTL_SYS) config use-context "$$current" >/dev/null; \
	got=$$($(KUBECTL_SYS) config current-context); \
	if [ "$$got" != "$$current" ]; then \
	  echo "ERROR: current-context is $$got, expected $$current"; \
	  exit 1; \
	fi; \
	echo "registered $(CONTEXT); current-context still $$got"

unregister:
	-$(KUBECTL_SYS) config delete-context $(CONTEXT)
	-$(KUBECTL_SYS) config delete-cluster $(CONTEXT)
	-$(KUBECTL_SYS) config unset users.$(CONTEXT)

nodes:
	$(KUBECTL_LAB) get nodes -o wide

status:
	$(KUBECTL_LAB) get nodes -o wide
	$(KUBECTL_LAB) get pods -A

context-check:
	@echo "system current-context: $$($(KUBECTL_SYS) config current-context)"
	@echo "lab current-context:    $$($(KUBECTL_LAB) config current-context 2>/dev/null || echo '(missing)')"
	@$(KUBECTL_SYS) config get-contexts -o name | grep -qx $(CONTEXT) \
		&& echo "kubectx has $(CONTEXT)" \
		|| echo "kubectx missing $(CONTEXT) (run make register)"

delete:
	$(KIND) delete cluster --name $(CLUSTER) --kubeconfig $(LAB_KUBECONFIG)
	@$(MAKE) unregister

load-image:
	@test -n "$(IMG)" || (echo "IMG=<image> required" >&2; exit 2)
	./scripts/kind-load-image.sh $(IMG)

opensandbox:
	@test -d "$(OS_CHARTS)/base" || (echo "missing $(OS_CHARTS); set SANDBOX_SRC" >&2; exit 2)
	./scripts/kind-load-image.sh sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/controller:release-1.1.0
	$(HELM_LAB) upgrade --install opensandbox-base $(OS_CHARTS)/base \
		--set fastSandbox.crds.install=false \
		--set fastSandbox.namespaces.create=false
	$(HELM_LAB) upgrade --install opensandbox-controller $(OS_CHARTS)/controller \
		--namespace opensandbox-system --create-namespace
	$(KUBECTL_LAB) -n opensandbox-system rollout status deploy/opensandbox-controller-manager --timeout=120s

opensandbox-hello:
	$(KUBECTL_LAB) apply -f manifests/opensandbox/hello-pool.yaml
	$(KUBECTL_LAB) apply -f manifests/opensandbox/hello-batchsandbox.yaml
	$(KUBECTL_LAB) -n opensandbox get pool,batchsandbox,pod -o wide

cubesandbox-controlplane:
	@test -f "$(CUBE_CHART)/Chart.yaml" || (echo "missing $(CUBE_CHART); set SANDBOX_SRC" >&2; exit 2)
	$(KUBECTL_LAB) label node $(CLUSTER)-worker cube.tencent.com/cube-control=true --overwrite
	./scripts/kind-load-image.sh \
		cube-sandbox-int.tencentcloudcr.com/cube-sandbox/cube-api:v0.7.2 \
		cube-sandbox-int.tencentcloudcr.com/cube-sandbox/cube-master:v0.7.2 \
		cube-sandbox-int.tencentcloudcr.com/cube-sandbox/cube-templatecenter:v0.7.2 \
		cube-sandbox-int.tencentcloudcr.com/cube-sandbox/cubemastercli:v0.7.2 \
		mysql:8.0 \
		redis:7-alpine
	$(HELM_LAB) upgrade --install cubesandbox $(CUBE_CHART) \
		--namespace cubesandbox-system --create-namespace \
		-f manifests/cubesandbox/values-controlplane.yaml
	$(KUBECTL_LAB) -n cubesandbox-system get deploy,sts,ds,pods -o wide
