#!/bin/sh
# Verify the exact public demo bundle and its saved audit against a separate seal.
set -eu

if [ "$#" -ne 3 ]; then
    echo "Usage: sh scripts/demo_preflight.sh AUDIT_COPY SEAL COUNT" >&2
    exit 2
fi
case "$3" in
    ''|*[!0-9]*) echo "COUNT must be a positive integer" >&2; exit 2 ;;
esac
[ "$3" -gt 0 ] || { echo "COUNT must be a positive integer" >&2; exit 2; }
unset MISTRAL_API_KEY NS_API_KEY SWISS_OTD_TOKEN DB_CLIENT_ID DB_API_KEY TRAIN_ARCHIVE_TOKEN
export PYTHONDONTWRITEBYTECODE=1

/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
    uv run --offline --no-sync nightdesk demo check --bundle demo
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
    uv run --offline --no-sync nightdesk audit verify --bundle demo --file "$1" --seal "$2" --count "$3"
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
    uv run --offline --no-sync pytest -q -p no:cacheprovider
uv run --offline --no-sync python tests/phase3_acceptance.py
echo "Public demo preflight passed for bundle demo."
