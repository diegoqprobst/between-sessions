#!/usr/bin/env bash
set -euo pipefail
gcloud run deploy between-sessions --source . --region us-east1 --allow-unauthenticated \
  --min-instances=1 --max-instances=1 \
  --set-env-vars "$(grep -v '^#' .env | grep -v '^$' | grep -v '^PUBLIC_URL=' | grep -v '^DB_PATH=' | tr '\n' ',' | sed 's/,$//')"
