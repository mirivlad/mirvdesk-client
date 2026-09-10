#!/usr/bin/env bash
set -euo pipefail

url="${MIRVDESK_SERVER_URL:-}"
url="${url%/}"

if [[ -z "$url" ]]; then
  echo "::error::MIRVDESK_SERVER_URL is required. Deploy your own MirvDesk Server and create this repository variable before building."
  exit 1
fi

case "$url" in
  http://*|https://*) ;;
  *)
    echo "::error::MIRVDESK_SERVER_URL must start with http:// or https://"
    exit 1
    ;;
esac

if [[ "$url" == *'@'* ]]; then
  echo "::error::MIRVDESK_SERVER_URL must not contain credentials"
  exit 1
fi

printf 'MirvDesk bootstrap configuration is valid: %s\n' "$url"
