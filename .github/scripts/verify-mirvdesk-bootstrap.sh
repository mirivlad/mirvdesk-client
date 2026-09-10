#!/usr/bin/env bash
set -euo pipefail

artifact="${1:-}"
url="${MIRVDESK_SERVER_URL:-}"
url="${url%/}"

if [[ -z "$artifact" || ! -f "$artifact" ]]; then
  echo "::error::MirvDesk bootstrap verifier needs an existing artifact path"
  exit 1
fi
if [[ -z "$url" ]]; then
  echo "::error::MIRVDESK_SERVER_URL is required and must not be empty"
  exit 1
fi

case "$artifact" in
  *.deb)
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    dpkg-deb -x "$artifact" "$tmp"
    if ! grep -aRqsF -- "$url" "$tmp/usr/share/mirvdesk"; then
      echo "::error::$artifact does not contain the configured MirvDesk bootstrap URL"
      exit 1
    fi
    ;;
  *)
    echo "::error::unsupported artifact type for bootstrap verification: $artifact"
    exit 1
    ;;
esac

echo "Verified MirvDesk bootstrap URL in $artifact"
