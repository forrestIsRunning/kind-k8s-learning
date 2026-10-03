.PHONY: create delete nodes status context-check help

# Isolated kubeconfig. Never write to ~/.kube/config; kubectx stays untouched.
KUBECONFIG := $(CURDIR)/.kube/config
export KUBECONFIG

CLUSTER := k8s-lab
KIND_CONFIG := cluster/kind.yaml

# Docker Desktop CLI. A leftover OrbStack symlink at /usr/local/bin/docker is broken.
ifneq ($(wildcard /Applications/Docker.app/Contents/Resources/bin/docker),)
export PATH := /Applications/Docker.app/Contents/Resources/bin:$(PATH)
endif

help:
	@echo "Targets:"
	@echo "  make create         - kind create cluster (1 control-plane + 1 worker)"
	@echo "  make nodes          - kubectl get nodes -o wide"
	@echo "  make status         - nodes + kube-system pods"
	@echo "  make context-check  - compare system kubeconfig vs lab kubeconfig"
	@echo "  make delete         - kind delete cluster"
	@echo ""
	@echo "Kubeconfig is $(KUBECONFIG)"
	@echo "Do not run: kind export kubeconfig --name $(CLUSTER)"
	@echo "That command writes into ~/.kube/config and changes kubectx."

create:
	@mkdir -p .kube
	kind create cluster --config $(KIND_CONFIG) --kubeconfig $(KUBECONFIG) --wait 5m
	kubectl wait --for=condition=Ready nodes --all --timeout=180s
	@$(MAKE) nodes
	@$(MAKE) context-check

nodes:
	kubectl get nodes -o wide

status:
	kubectl get nodes -o wide
	kubectl get pods -A

context-check:
	@echo "system current-context: $$(kubectl --kubeconfig $$HOME/.kube/config config current-context)"
	@echo "lab current-context:    $$(kubectl --kubeconfig $(KUBECONFIG) config current-context 2>/dev/null || echo '(missing)')"

delete:
	kind delete cluster --name $(CLUSTER) --kubeconfig $(KUBECONFIG)
