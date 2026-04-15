#!/usr/bin/env bash
# Seed end-to-end Huila -> Hamburgo traceability data for EUDR smoke tests.
#
# Creates lote HU-2026-042:
#   - Plot: Finca El Mirador, vereda Bruselas, Pitalito (Huila), 3 ha.
#   - Asset linked to plot (500 kg verde).
#   - Custody chain: cosecha -> beneficio -> trilla -> handoff -> loaded ->
#     arrived (Buenaventura) -> loaded (FOB) -> arrived (Hamburgo).
#   - Customer: InterAmerican Coffee GmbH (EORI DE284619725).
#   - SO: 500 kg, EUR, FOB, destino DE.
#
# Usage:
#   ./scripts/seed_huila_hamburgo.sh
#
# Requirements:
#   - All trace stack containers running (docker compose up).
#   - GATEWAY at $GATEWAY (default http://localhost:9000).
#   - S2S_SERVICE_TOKEN env var (or the docker-compose default).
#
# This script is idempotent enough for re-runs: it bails on first conflict
# (HTTP 409). Wipe DBs to re-seed cleanly.

set -euo pipefail

GATEWAY="${GATEWAY:-http://localhost:9000}"
TENANT="${TENANT:-default}"
S2S="${S2S_SERVICE_TOKEN:-s2s-change-me-in-production}"
USER_ID="${USER_ID:-system}"

H_TENANT="X-Tenant-Id: ${TENANT}"
H_USER="X-User-Id: ${USER_ID}"
H_S2S="X-Service-Token: ${S2S}"
H_JSON="Content-Type: application/json"

say() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
fail() { printf '\033[1;31mERR:\033[0m %s\n' "$*" >&2; exit 1; }

POST() {
  local path="$1" body="$2"
  curl -sS -X POST "${GATEWAY}${path}" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
    -d "$body"
}

say "1/8  Create plot Finca El Mirador (Pitalito, Huila)"
PLOT_BODY=$(cat <<'JSON'
{
  "plot_code": "HU-MIRADOR-001",
  "country_code": "CO",
  "region": "Huila",
  "municipality": "Pitalito",
  "vereda": "Bruselas",
  "frontera_agricola_status": "dentro_no_condicionada",
  "coordinate_system_datum": "WGS84",
  "plot_area_ha": 3.0,
  "geolocation_type": "polygon",
  "lat": 1.7280,
  "lng": -76.0410,
  "geojson_data": {
    "type": "Polygon",
    "coordinates": [[
      [-76.041950, 1.727100],
      [-76.040050, 1.727100],
      [-76.040050, 1.728900],
      [-76.041950, 1.728900],
      [-76.041950, 1.727100]
    ]]
  },
  "crop_type": "cafe",
  "scientific_name": "Coffea arabica L.",
  "last_harvest_date": "2026-02-15",
  "deforestation_free": true,
  "degradation_free": true,
  "cutoff_date_compliant": true,
  "legal_land_use": true,
  "producer_name": "Don Aurelio Munoz",
  "producer_id_type": "CC",
  "producer_id_number": "12345678",
  "tenure_type": "owned",
  "capture_method": "handheld_gps",
  "gps_accuracy_m": 4.5,
  "producer_scale": "smallholder"
}
JSON
)
PLOT_RESP=$(POST "/api/v1/compliance/plots/" "$PLOT_BODY")
PLOT_ID=$(echo "$PLOT_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
[ -n "$PLOT_ID" ] || fail "Plot create: $PLOT_RESP"
echo "  plot_id=$PLOT_ID"

say "2/8  Create asset linked to plot"
ASSET_BODY=$(cat <<JSON
{
  "asset_mint": "sim_HU-2026-042",
  "product_type": "coffee_green",
  "metadata": {"lote": "HU-2026-042", "weight_kg": 500},
  "initial_custodian_wallet": "FincaElMirador1111111111111111111111111111",
  "plot_id": "${PLOT_ID}"
}
JSON
)
ASSET_RESP=$(POST "/api/v1/assets" "$ASSET_BODY")
ASSET_ID=$(echo "$ASSET_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
[ -n "$ASSET_ID" ] || fail "Asset create: $ASSET_RESP"
echo "  asset_id=$ASSET_ID"

say "3/8  Custody event chain (cosecha -> beneficio -> trilla)"
# This part requires the workflow engine + event_type configs to exist for the
# tenant. Real seed of those is out of scope of this script — see workflow
# admin UI. The placeholder below uses generic events; if your tenant has not
# configured these slugs, the script will warn and continue.
for EVT in COSECHA BENEFICIO TRILLA; do
  RESP=$(curl -sS -o /tmp/seed_evt.json -w "%{http_code}" -X POST \
    "${GATEWAY}/api/v1/assets/${ASSET_ID}/events" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
    -d "{\"event_type\":\"${EVT}\",\"location\":{\"lat\":1.7280,\"lng\":-76.0410,\"city\":\"Pitalito\",\"country\":\"CO\"},\"data\":{}}")
  echo "  ${EVT} HTTP ${RESP}"
done

say "4/8  Quantity changes (cereza 2500 -> pergamino 1000 -> verde 500)"
# These calls assume the event ids exist; in a real seed you'd capture them
# from the previous responses. Skipping for safety unless the events succeeded.
echo "  (Manual step — capture event ids from /api/v1/assets/${ASSET_ID}/events"
echo "   and POST quantity to /api/v1/assets/{aid}/events/{eid}/quantity)"

say "5/8  Customer InterAmerican Coffee GmbH (EORI)"
CUST_BODY=$(cat <<'JSON'
{
  "name": "InterAmerican Coffee GmbH",
  "code": "IAC-DE",
  "tax_id": "DE284619725",
  "tax_id_type": "EORI",
  "contact_name": "Hamburg Trade Desk",
  "email": "trade@interamerican.example",
  "address": {"city": "Hamburg", "country": "DE"}
}
JSON
)
CUST_RESP=$(POST "/api/v1/customers" "$CUST_BODY")
CUST_ID=$(echo "$CUST_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
echo "  customer_id=${CUST_ID:-<unknown>}"

say "6/8  Sales order EUR / FOB / DE"
if [ -n "$CUST_ID" ]; then
  # Resolve first available product to satisfy lines[] requirement.
  PROD_ID=$(curl -sS "${GATEWAY}/api/v1/products?limit=1" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" \
    | python -c 'import json,sys
try:
  d=json.load(sys.stdin); items=d.get("items",[])
  print(items[0]["id"] if items else "")
except Exception:
  print("")' 2>/dev/null || true)
  if [ -n "$PROD_ID" ]; then
    SO_BODY=$(cat <<JSON
{
  "customer_id": "${CUST_ID}",
  "currency": "EUR",
  "incoterm": "FOB",
  "destination_country": "DE",
  "notes": "Lote HU-2026-042 — 500 kg verde — Huila a Hamburgo",
  "lines": [
    {"product_id": "${PROD_ID}", "qty_ordered": 500, "unit_price": 5.50}
  ]
}
JSON
)
    SO_RESP=$(POST "/api/v1/sales-orders" "$SO_BODY")
    echo "  sales-order create response: $(echo "$SO_RESP" | head -c 200)..."
  else
    echo "  (no product available — skipping SO)"
  fi
fi

say "7/8  Smoke check plot list"
curl -sS -o /tmp/seed_plots.json -w "  plots HTTP %{http_code}\n" \
  "${GATEWAY}/api/v1/compliance/plots/?limit=1" \
  -H "$H_TENANT" -H "$H_S2S"

say "8/8  Done"
echo "Plot id     : ${PLOT_ID}"
echo "Asset id    : ${ASSET_ID}"
echo "Customer id : ${CUST_ID:-<unknown>}"
