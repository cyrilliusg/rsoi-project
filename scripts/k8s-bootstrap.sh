#!/usr/bin/env bash
# Create namespaces and secrets the application charts expect.
# Idempotent: safe to re-run; uses `kubectl apply` semantics.
#
# Required env:
#   PG_PASSWORD              app-DB password (must match helm/postgres
#                            `appUser.password` — pass the same via
#                            --set appUser.password=$PG_PASSWORD)
#   IDP_ADMIN_PASSWORD       bootstrap password for the IdP admin user
#
# Optional env:
#   NS_APP
#   NS_DATA
#   JWT_DIR
#   IDP_ADMIN_USERNAME
set -euo pipefail

NS_APP="${NS_APP:-rsoi-app}"
NS_DATA="${NS_DATA:-rsoi-data}"
JWT_DIR="${JWT_DIR:-secrets/idp}"
IDP_ADMIN_USERNAME="${IDP_ADMIN_USERNAME:-admin}"

: "${PG_PASSWORD:?must be set}"
: "${IDP_ADMIN_PASSWORD:?must be set}"

if [ ! -f "$JWT_DIR/private.pem" ] || [ ! -f "$JWT_DIR/public.pem" ]; then
  echo "Missing $JWT_DIR/private.pem or public.pem."
  echo "Run scripts/generate-jwt-keys.sh first."
  exit 1
fi

for ns in "$NS_APP" "$NS_DATA"; do
  kubectl get ns "$ns" >/dev/null 2>&1 || kubectl create ns "$ns"
done

# `postgres-credentials` in NS_APP — app pods consume APP_DB_PASSWORD via
# secretKeyRef (see helm/values/*.yaml). The helm/postgres chart creates
# its OWN postgres-credentials in NS_DATA for postgres itself; both must
# carry the same APP_DB_PASSWORD value.
kubectl create secret generic postgres-credentials \
  -n "$NS_APP" \
  --from-literal=APP_DB_PASSWORD="$PG_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# IdP RSA keys — mounted as files at /keys in the identity-provider pod.
kubectl create secret generic idp-jwt-keys \
  -n "$NS_APP" \
  --from-file=private.pem="$JWT_DIR/private.pem" \
  --from-file=public.pem="$JWT_DIR/public.pem" \
  --dry-run=client -o yaml | kubectl apply -f -

# Bootstrap admin — read by the IdP entrypoint to create the first admin user.
kubectl create secret generic idp-admin-bootstrap \
  -n "$NS_APP" \
  --from-literal=username="$IDP_ADMIN_USERNAME" \
  --from-literal=password="$IDP_ADMIN_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Bootstrap complete:"
echo "  namespaces: $NS_APP, $NS_DATA"
echo "  secrets in $NS_APP: postgres-credentials, idp-jwt-keys, idp-admin-bootstrap"
