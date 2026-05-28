#!/usr/bin/env bash
# Generate a static-token kubeconfig that doesn't depend on `yc` CLI —
# usable as the KUBE_CONFIG GitHub Actions secret.
#
# Runs against your CURRENT kubectl context. Creates:
#   - ServiceAccount kube-system/deployer (idempotent)
#   - ClusterRoleBinding deployer (cluster-admin, idempotent)
#   - Secret kube-system/deployer-token of type service-account-token
#
# Output: secrets/kubeconfig-ci.yaml + secrets/kubeconfig-ci.b64.
set -euo pipefail

OUT_DIR="${OUT_DIR:-secrets}"
mkdir -p "$OUT_DIR"

echo "Current kubectl context: $(kubectl config current-context)"

kubectl create serviceaccount deployer -n kube-system \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create clusterrolebinding deployer \
  --clusterrole=cluster-admin \
  --serviceaccount=kube-system:deployer \
  --dry-run=client -o yaml | kubectl apply -f -

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: deployer-token
  namespace: kube-system
  annotations:
    kubernetes.io/service-account.name: deployer
type: kubernetes.io/service-account-token
EOF

# k8s controller may take a moment to populate the token field.
for _ in 1 2 3 4 5; do
  TOKEN=$(kubectl get secret deployer-token -n kube-system -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)
  [ -n "$TOKEN" ] && break
  sleep 1
done
[ -n "$TOKEN" ] || { echo "Token not populated — retry in a few seconds."; exit 1; }

CA=$(kubectl config view --raw --minify --flatten -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
SERVER=$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.server}')

cat > "$OUT_DIR/kubeconfig-ci.yaml" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: rsoi
    cluster:
      server: $SERVER
      certificate-authority-data: $CA
users:
  - name: deployer
    user:
      token: $TOKEN
contexts:
  - name: rsoi
    context:
      cluster: rsoi
      user: deployer
      namespace: default
current-context: rsoi
EOF

base64 -w0 "$OUT_DIR/kubeconfig-ci.yaml" > "$OUT_DIR/kubeconfig-ci.b64"

echo
echo "Wrote $OUT_DIR/kubeconfig-ci.yaml and $OUT_DIR/kubeconfig-ci.b64"
echo "Copy the contents of kubeconfig-ci.b64 into GitHub secret KUBE_CONFIG."
echo
echo "Sanity check (should print 'cluster reachable'):"
echo "  KUBECONFIG=$OUT_DIR/kubeconfig-ci.yaml kubectl get nodes && echo cluster reachable"
