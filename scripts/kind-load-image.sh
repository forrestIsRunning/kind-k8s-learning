#!/usr/bin/env bash
# Pull an image on the host, then import it into kind nodes.
# kind load docker-image fails on Docker Desktop multi-arch indexes;
# docker save | ctr import works.
set -euo pipefail

CLUSTER="${KIND_CLUSTER_NAME:-k8s-lab}"
if [[ $# -lt 1 ]]; then
  echo "usage: $0 <image> [image...]" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1 && [[ -x /Applications/Docker.app/Contents/Resources/bin/docker ]]; then
  PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
fi

nodes="$(kind get nodes --name "$CLUSTER")"
if [[ -z "$nodes" ]]; then
  echo "no nodes for kind cluster $CLUSTER" >&2
  exit 1
fi

for image in "$@"; do
  docker pull "$image"
  while IFS= read -r node; do
    echo "import $image -> $node"
    docker save "$image" | docker exec -i "$node" ctr -n k8s.io images import --snapshotter=overlayfs -
  done <<< "$nodes"
done
