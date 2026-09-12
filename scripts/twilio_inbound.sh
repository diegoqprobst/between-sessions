#!/usr/bin/env bash
# Simula el webhook de Twilio. Requiere TWILIO_VALIDATE=0 en .env para pruebas locales.
# uso: scripts/twilio_inbound.sh "+13055550100" "hola"
curl -s -X POST "${SERVER:-http://localhost:8000}/twilio/webhook" \
  --data-urlencode "From=whatsapp:$1" --data-urlencode "Body=$2"
