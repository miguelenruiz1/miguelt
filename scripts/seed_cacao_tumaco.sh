#!/usr/bin/env bash
# Seed end-to-end Tumaco -> Amsterdam cacao traceability data for EUDR smoke.
#
# Creates lote LT-APRO-2026-042:
#   - Plot: Finca El Diviso, vereda La Variante, Llorente/Tumaco (Narino), ~3 ha.
#     commodity_type=cacao, scientific_name=Theobroma cacao L.
#   - Asset linked to plot (1.000 kg cacao seco).
#   - Custody chain: cosecha -> desgrane -> fermentacion (5d) -> secado ->
#     clasificacion -> handoff exportador -> loaded -> arrived (Cartagena) ->
#     loaded (FOB) -> arrived (Amsterdam).
#   - Quality test: cadmio 0.42 mg/kg (passed EU Reg 2023/915).
#   - Customer: Daarnhouwer & Co B.V. (EORI NL803428519).
#   - SO: 1.000 kg, EUR, FOB, destino NL, commodity_type=cacao.
#   - Cadmium test POSTed to the record endpoint.
#
# Usage:
#   ./scripts/seed_cacao_tumaco.sh
#
# The script is a best-effort scaffolding: each call prints its HTTP code so
# the operator can verify end-to-end. If your tenant has not configured the
# custody event slugs (COSECHA/DESGRANE/FERMENTACION/...), those POSTs will
# fail with 422 — that does NOT stop the rest of the seed.

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

say "1/10  Create plot Finca El Diviso (Llorente, Tumaco, Narino)"
PLOT_BODY=$(cat <<'JSON'
{
  "plot_code": "LT-DIVISO-001",
  "country_code": "CO",
  "region": "Narino",
  "municipality": "Tumaco",
  "vereda": "La Variante",
  "frontera_agricola_status": "within",
  "coordinate_system_datum": "WGS84",
  "plot_area_ha": 3.0,
  "geolocation_type": "polygon",
  "lat": 1.8105,
  "lng": -78.7642,
  "geojson_data": {
    "type": "Polygon",
    "coordinates": [[
      [-78.765180, 1.809600],
      [-78.763220, 1.809600],
      [-78.763220, 1.811400],
      [-78.765180, 1.811400],
      [-78.765180, 1.809600]
    ]]
  },
  "crop_type": "cacao",
  "commodity_type": "cacao",
  "scientific_name": "Theobroma cacao L.",
  "last_harvest_date": "2026-02-10",
  "deforestation_free": true,
  "degradation_free": true,
  "cutoff_date_compliant": true,
  "legal_land_use": true,
  "producer_name": "Asociacion de Productores de Cacao Aprotumaco",
  "producer_id_type": "NIT",
  "producer_id_number": "900123456-1",
  "tenure_type": "afro_collective",
  "capture_method": "handheld_gps",
  "gps_accuracy_m": 5.0,
  "producer_scale": "smallholder"
}
JSON
)
PLOT_RESP=$(POST "/api/v1/compliance/plots/" "$PLOT_BODY")
PLOT_ID=$(echo "$PLOT_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
[ -n "$PLOT_ID" ] || fail "Plot create: $PLOT_RESP"
echo "  plot_id=$PLOT_ID"

say "2/10  Create asset linked to plot"
ASSET_BODY=$(cat <<JSON
{
  "asset_mint": "sim_LT-APRO-2026-042",
  "product_type": "cocoa_beans",
  "metadata": {"lote": "LT-APRO-2026-042", "weight_kg": 1000, "commodity_type": "cacao"},
  "initial_custodian_wallet": "AprotumacoCoopCacao2222222222222222222222",
  "plot_id": "${PLOT_ID}"
}
JSON
)
ASSET_RESP=$(POST "/api/v1/assets" "$ASSET_BODY")
ASSET_ID=$(echo "$ASSET_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
[ -n "$ASSET_ID" ] || fail "Asset create: $ASSET_RESP"
echo "  asset_id=$ASSET_ID"

say "3/10  Custody events (cosecha -> desgrane -> fermentacion -> secado -> clasificacion)"
for EVT in COSECHA DESGRANE FERMENTACION SECADO CLASIFICACION HANDOFF LOADED ARRIVED_CARTAGENA LOADED_FOB ARRIVED_AMSTERDAM; do
  RESP=$(curl -sS -o /tmp/seed_evt.json -w "%{http_code}" -X POST \
    "${GATEWAY}/api/v1/assets/${ASSET_ID}/events" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
    -d "{\"event_type\":\"${EVT}\",\"location\":{\"lat\":1.8105,\"lng\":-78.7642,\"city\":\"Tumaco\",\"country\":\"CO\"},\"data\":{}}")
  echo "  ${EVT} HTTP ${RESP}"
done

say "4/10  Create compliance record (cacao, HS 1801)"
REC_BODY=$(cat <<JSON
{
  "asset_id": "${ASSET_ID}",
  "framework_slug": "eudr",
  "hs_code": "1801",
  "commodity_type": "cacao",
  "product_description": "Cacao en grano seco, fermentado, origen Tumaco",
  "scientific_name": "Theobroma cacao L.",
  "quantity_kg": 1000,
  "quantity_unit": "kg",
  "country_of_production": "CO",
  "production_period_start": "2026-02-01",
  "production_period_end": "2026-02-28",
  "supplier_name": "Aprotumaco",
  "buyer_name": "Daarnhouwer & Co B.V.",
  "operator_eori": "NL803428519",
  "deforestation_free_declaration": true,
  "legal_compliance_declaration": true
}
JSON
)
REC_RESP=$(POST "/api/v1/compliance/records/" "$REC_BODY")
REC_ID=$(echo "$REC_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
echo "  record_id=${REC_ID:-<unknown>}"

say "5/10  Cadmium lab test (0.42 mg/kg — below EU 0.60 cap)"
if [ -n "$REC_ID" ]; then
  CD_RESP=$(curl -sS -o /tmp/seed_cd.json -w "%{http_code}" -X POST \
    "${GATEWAY}/api/v1/compliance/records/${REC_ID}/cadmium-test" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
    -d '{"value_mg_per_kg":0.42,"test_date":"2026-02-25","lab":"Labtoxcol SAS (Bogota)"}')
  echo "  cadmium-test HTTP ${CD_RESP}"
fi

say "6/10  Customer Daarnhouwer & Co B.V. (EORI NL)"
CUST_BODY=$(cat <<'JSON'
{
  "name": "Daarnhouwer & Co B.V.",
  "code": "DRN-NL",
  "tax_id": "NL803428519",
  "tax_id_type": "EORI",
  "contact_name": "Amsterdam Cocoa Desk",
  "email": "cocoa@daarnhouwer.example",
  "address": {"city": "Wormerveer", "country": "NL"}
}
JSON
)
CUST_RESP=$(POST "/api/v1/customers" "$CUST_BODY")
CUST_ID=$(echo "$CUST_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
echo "  customer_id=${CUST_ID:-<unknown>}"

say "7/10  Sales order EUR / FOB / NL"
if [ -n "$CUST_ID" ]; then
  SO_BODY=$(cat <<JSON
{
  "customer_id": "${CUST_ID}",
  "currency": "EUR",
  "incoterm": "FOB",
  "destination_country": "NL",
  "commodity_type": "cacao",
  "notes": "Lote LT-APRO-2026-042 — 1000 kg cacao seco — Tumaco a Amsterdam",
  "lines": []
}
JSON
)
  SO_RESP=$(POST "/api/v1/sales-orders" "$SO_BODY")
  echo "  sales-order create: $(echo "$SO_RESP" | head -c 200)..."
fi

say "8/10  Quality test humedad 7.3% (passed 5-8%)"
# Assumes a batch exists; if inventory is not seeded this will 404, informational only.
curl -sS -o /tmp/seed_qt.json -w "  humidity HTTP %{http_code}\n" -X POST \
  "${GATEWAY}/api/v1/quality-tests" \
  -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
  -d '{"batch_id":"LT-APRO-2026-042","test_type":"humidity","value":7.3,"unit":"percent","threshold_min":5,"threshold_max":8,"test_date":"2026-02-24","lab":"Aprotumaco"}'

say "9/10  Smoke check plot list"
curl -sS -o /tmp/seed_plots.json -w "  plots HTTP %{http_code}\n" \
  "${GATEWAY}/api/v1/compliance/plots/?limit=1" \
  -H "$H_TENANT" -H "$H_S2S"

say "10/10 Done"
echo "Plot id     : ${PLOT_ID}"
echo "Asset id    : ${ASSET_ID}"
echo "Record id   : ${REC_ID:-<unknown>}"
echo "Customer id : ${CUST_ID:-<unknown>}"
