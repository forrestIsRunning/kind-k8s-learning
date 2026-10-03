.PHONY: create delete nodes status context-check register unregister help

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
	@echo "kind create writes $(LAB_KUBECONFIG), then register merges into $(SYS_KUBECONFIG)."
	@echo "kind export kubeconfig --name $(CLUSTER) also switches current-context;"
	@echo "use make register instead."

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
