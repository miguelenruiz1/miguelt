#!/usr/bin/env bash
# Seed end-to-end San Alberto (Cesar) -> Mannheim (DE) palma traceability data.
#
# Creates lote CPO-CES-2026-088:
#   - Plot: Indupalma San Alberto, ~850 ha.
#     commodity_type=palm, scientific_name=Elaeis guineensis Jacq.
#   - Producer: Indupalma S.A., NIT 860.007.301-1.
#   - Asset CPO (5.000 kg crude palm oil).
#   - Multi-output recipe RFF -> CPO (main, factor 0.20) + PKO (byproduct 0.05).
#   - Quality tests: FFA 3.8% (passed <5%), DOBI 2.6 (passed >2.3).
#   - Customer: Bunge Loders Croklaan Mannheim (EORI DE123456789).
#   - SO: 5.000 kg, USD, CIF, destino DE, commodity_type=palm.
#   - Record with rspo_trace_model=identity_preserved.
#
# Usage:
#   ./scripts/seed_palma_cesar.sh

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

PATCH() {
  local path="$1" body="$2"
  curl -sS -X PATCH "${GATEWAY}${path}" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
    -d "$body"
}

say "1/10  Create plot Indupalma San Alberto (Cesar) — ~850 ha square"
# Square ~2.92 km side -> ~854 ha centered at 7.76, -73.39.
PLOT_BODY=$(cat <<'JSON'
{
  "plot_code": "CES-SANALBERTO-001",
  "country_code": "CO",
  "region": "Cesar",
  "municipality": "San Alberto",
  "vereda": "Santa Barbara",
  "frontera_agricola_status": "within",
  "coordinate_system_datum": "WGS84",
  "plot_area_ha": 854.0,
  "geolocation_type": "polygon",
  "lat": 7.76,
  "lng": -73.39,
  "geojson_data": {
    "type": "Polygon",
    "coordinates": [[
      [-73.403200, 7.746900],
      [-73.376800, 7.746900],
      [-73.376800, 7.773100],
      [-73.403200, 7.773100],
      [-73.403200, 7.746900]
    ]]
  },
  "crop_type": "palma",
  "commodity_type": "palm",
  "scientific_name": "Elaeis guineensis Jacq.",
  "last_harvest_date": "2026-03-05",
  "deforestation_free": true,
  "degradation_free": true,
  "cutoff_date_compliant": true,
  "legal_land_use": true,
  "producer_name": "Indupalma S.A.",
  "producer_id_type": "NIT",
  "producer_id_number": "860007301-1",
  "owner_name": "Indupalma S.A.",
  "owner_id_type": "NIT",
  "owner_id_number": "860007301-1",
  "tenure_type": "owned",
  "capture_method": "rtk_gps",
  "gps_accuracy_m": 0.05,
  "producer_scale": "industrial"
}
JSON
)
PLOT_RESP=$(POST "/api/v1/compliance/plots" "$PLOT_BODY")
PLOT_ID=$(echo "$PLOT_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
[ -n "$PLOT_ID" ] || fail "Plot create: $PLOT_RESP"
echo "  plot_id=$PLOT_ID"

say "2/10  Create asset CPO 5.000 kg linked to plot"
ASSET_BODY=$(cat <<JSON
{
  "asset_mint": "sim_CPO-CES-2026-088",
  "product_type": "palm_oil",
  "metadata": {"lote": "CPO-CES-2026-088", "weight_kg": 5000, "commodity_type": "palm"},
  "initial_custodian_wallet": "IndupalmaMillSanAlberto33333333333333333",
  "plot_id": "${PLOT_ID}"
}
JSON
)
ASSET_RESP=$(POST "/api/v1/assets" "$ASSET_BODY")
ASSET_ID=$(echo "$ASSET_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
[ -n "$ASSET_ID" ] || fail "Asset create: $ASSET_RESP"
echo "  asset_id=$ASSET_ID"

say "3/10  Custody events (harvest -> mill -> storage -> loaded -> CIF Mannheim)"
for EVT in COSECHA_RFF MOLIENDA CLARIFICACION ALMACENAMIENTO HANDOFF LOADED ARRIVED_BARRANQUILLA LOADED_CIF ARRIVED_MANNHEIM; do
  RESP=$(curl -sS -o /tmp/seed_evt.json -w "%{http_code}" -X POST \
    "${GATEWAY}/api/v1/assets/${ASSET_ID}/events" \
    -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
    -d "{\"event_type\":\"${EVT}\",\"location\":{\"lat\":7.76,\"lng\":-73.39,\"city\":\"San Alberto\",\"country\":\"CO\"},\"data\":{}}")
  echo "  ${EVT} HTTP ${RESP}"
done

say "4/10  Multi-output recipe RFF -> CPO (0.20 main) + PKO (0.05 byproduct)"
# Products ids are placeholders — replace with real entity ids in a live seed.
RECIPE_BODY=$(cat <<'JSON'
{
  "name": "Extraccion RFF Indupalma San Alberto",
  "output_entity_id": "product-cpo-placeholder",
  "output_quantity": 0.20,
  "description": "Molienda RFF palma aceitera: CPO principal 20%, PKO subproducto 5%.",
  "is_active": true,
  "components": [
    {"component_entity_id": "product-rff-placeholder", "quantity_required": 1.0}
  ],
  "output_components": [
    {"output_entity_id": "product-cpo-placeholder", "output_quantity": 0.20, "conversion_factor": 0.20, "is_main": true},
    {"output_entity_id": "product-pko-placeholder", "output_quantity": 0.05, "conversion_factor": 0.05, "is_main": false}
  ]
}
JSON
)
curl -sS -o /tmp/seed_recipe.json -w "  recipe HTTP %{http_code}\n" -X POST \
  "${GATEWAY}/api/v1/recipes" \
  -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
  -d "$RECIPE_BODY"

say "5/10  Compliance record (palm, HS 1511, RSPO identity_preserved)"
REC_BODY=$(cat <<JSON
{
  "asset_id": "${ASSET_ID}",
  "framework_slug": "eudr",
  "hs_code": "1511",
  "commodity_type": "palm",
  "product_description": "Aceite crudo de palma (CPO) — origen Indupalma San Alberto",
  "scientific_name": "Elaeis guineensis Jacq.",
  "quantity_kg": 5000,
  "quantity_unit": "kg",
  "country_of_production": "CO",
  "production_period_start": "2026-03-01",
  "production_period_end": "2026-03-10",
  "supplier_name": "Indupalma S.A.",
  "buyer_name": "Bunge Loders Croklaan Mannheim",
  "operator_eori": "DE123456789",
  "deforestation_free_declaration": true,
  "legal_compliance_declaration": true,
  "rspo_trace_model": "identity_preserved"
}
JSON
)
REC_RESP=$(POST "/api/v1/compliance/records/" "$REC_BODY")
REC_ID=$(echo "$REC_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
echo "  record_id=${REC_ID:-<unknown>}"

say "6/10  Quality test FFA 3.8% (passed <5%)"
curl -sS -o /tmp/seed_ffa.json -w "  FFA HTTP %{http_code}\n" -X POST \
  "${GATEWAY}/api/v1/quality-tests" \
  -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
  -d '{"batch_id":"CPO-CES-2026-088","test_type":"ffa","value":3.8,"unit":"percent","threshold_max":5,"test_date":"2026-03-09","lab":"Indupalma lab"}'

say "7/10  Quality test DOBI 2.6 (passed >=2.3)"
curl -sS -o /tmp/seed_dobi.json -w "  DOBI HTTP %{http_code}\n" -X POST \
  "${GATEWAY}/api/v1/quality-tests" \
  -H "$H_TENANT" -H "$H_USER" -H "$H_S2S" -H "$H_JSON" \
  -d '{"batch_id":"CPO-CES-2026-088","test_type":"dobi","value":2.6,"unit":"ratio","threshold_min":2.3,"test_date":"2026-03-09","lab":"Indupalma lab"}'

say "8/10  Customer Bunge Loders Croklaan Mannheim (EORI DE)"
CUST_BODY=$(cat <<'JSON'
{
  "name": "Bunge Loders Croklaan Mannheim",
  "code": "BLC-DE",
  "tax_id": "DE123456789",
  "tax_id_type": "EORI",
  "contact_name": "Oils Trade Desk",
  "email": "palm@bunge.example",
  "address": {"city": "Mannheim", "country": "DE"}
}
JSON
)
CUST_RESP=$(POST "/api/v1/customers" "$CUST_BODY")
CUST_ID=$(echo "$CUST_RESP" | python -c 'import json,sys;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)
echo "  customer_id=${CUST_ID:-<unknown>}"

say "9/10  Sales order USD / CIF / DE"
if [ -n "$CUST_ID" ]; then
  SO_BODY=$(cat <<JSON
{
  "customer_id": "${CUST_ID}",
  "currency": "USD",
  "incoterm": "CIF",
  "destination_country": "DE",
  "commodity_type": "palm",
  "notes": "Lote CPO-CES-2026-088 — 5000 kg CPO — San Alberto a Mannheim",
  "lines": []
}
JSON
)
  SO_RESP=$(POST "/api/v1/sales-orders" "$SO_BODY")
  echo "  sales-order create: $(echo "$SO_RESP" | head -c 200)..."
fi

say "10/10 Done"
echo "Plot id     : ${PLOT_ID}"
echo "Asset id    : ${ASSET_ID}"
echo "Record id   : ${REC_ID:-<unknown>}"
echo "Customer id : ${CUST_ID:-<unknown>}"
