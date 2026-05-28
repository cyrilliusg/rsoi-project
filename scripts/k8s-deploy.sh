#!/usr/bin/env bash
# Sequential helm upgrade for the full rsoi stack.
#
# Required env:
#   IMAGE_OWNER     GHCR owner; lowercased automatically
#   IMAGE_TAG       image tag to deploy (e.g. github SHA or "latest")
#   PG_PASSWORD     same value as bootstrap
#
# Optional env:
#   NS_APP
#   NS_DATA
#
# Run scripts/k8s-bootstrap.sh first, and `helm dependency update helm/kafka`.
set -euo pipefail

NS_APP="${NS_APP:-rsoi-app}"
NS_DATA="${NS_DATA:-rsoi-data}"

: "${IMAGE_OWNER:?must be set}"
: "${IMAGE_TAG:?must be set}"
: "${PG_PASSWORD:?must be set}"

OWNER_LC=$(echo "$IMAGE_OWNER" | tr '[:upper:]' '[:lower:]')
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> postgres (NS=$NS_DATA)"
helm upgrade --install postgres "$ROOT/helm/postgres" -n "$NS_DATA" \
  --set "appUser.password=$PG_PASSWORD" \
  --wait --timeout 5m

echo "==> rsoi-kafka (NS=$NS_DATA)"
helm upgrade --install rsoi-kafka "$ROOT/helm/kafka" -n "$NS_DATA" \
  --wait --timeout 10m

# Workloads sharing helm/service: release_name : values_filename : image_name.
# `image_name` differs from release_name only when one image runs in two
# roles (gateway-service / gateway-worker, statistics-service /
# statistics-consumer).
WORKLOADS=(
  "identity-provider:identity-provider:identity-provider"
  "car-service:car-service:car-service"
  "rental-service:rental-service:rental-service"
  "payment-service:payment-service:payment-service"
  "statistics-service:statistics-service:statistics-service"
  "statistics-consumer:statistics-consumer:statistics-service"
  "gateway-service:gateway-service:gateway-service"
  "frontend:frontend:frontend"
)

for entry in "${WORKLOADS[@]}"; do
  IFS=':' read -r release values image <<< "$entry"
  echo "==> $release (image=ghcr.io/$OWNER_LC/$image:$IMAGE_TAG)"
  helm upgrade --install "$release" "$ROOT/helm/service" \
    -n "$NS_APP" \
    -f "$ROOT/helm/values/$values.yaml" \
    --set "image.repository=ghcr.io/$OWNER_LC/$image" \
    --set "image.tag=$IMAGE_TAG" \
    --wait --timeout 5m
done

echo "Deploy complete. Verify with:"
echo "  kubectl get pods -n $NS_DATA"
echo "  kubectl get pods -n $NS_APP"
echo "  kubectl get ingress -n $NS_APP"
