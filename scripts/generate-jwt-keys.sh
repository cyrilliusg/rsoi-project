#!/usr/bin/env bash
# Generate an RSA-2048 keypair for the identity-provider JWT signing.
set -euo pipefail

JWT_DIR="${JWT_DIR:-secrets/idp}"
mkdir -p "$JWT_DIR"

if [ -f "$JWT_DIR/private.pem" ] && [ -z "${FORCE:-}" ]; then
  echo "Refusing to overwrite $JWT_DIR/private.pem (set FORCE=1 to override)."
  exit 1
fi

openssl genrsa -out "$JWT_DIR/private.pem" 2048
openssl rsa -in "$JWT_DIR/private.pem" -pubout -out "$JWT_DIR/public.pem"
chmod 600 "$JWT_DIR/private.pem"

echo "Wrote:"
echo "  $JWT_DIR/private.pem  (keep secret)"
echo "  $JWT_DIR/public.pem"
