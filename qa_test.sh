#!/bin/bash
B="https://gateway-421343664920.southamerica-east1.run.app"
A="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMzJiNDU2MS0zMmVlLTQ4NWMtYjY2My00NDRhODc0ZjM4NTkiLCJ0ZW5hbnRfaWQiOiJxYXRlc3Rlci00NjI4NTIiLCJ0eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzc1Nzc2MDkxLCJleHAiOjE3NzU4MDQ4OTF9.prJ_fmiEgzhu6DI3DmTAPo6anrmfhmzdDP2gRjR504c"
T="X-Tenant-Id: qatester-462852"
C="Content-Type: application/json"

get_id() { python3 -c "import sys,json; print(json.load(sys.stdin).get('id','NOID'))" 2>/dev/null; }

test_endpoint() {
  local name="$1" path="$2" create_data="$3" update_data="$4"
  echo "=== $name ==="

  # CREATE
  RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" -d "$create_data" "$B$path")
  HTTP=$(echo "$RESP" | tail -1)
  BODY=$(echo "$RESP" | sed '$d')
  ID=$(echo "$BODY" | get_id)
  echo "CREATE: HTTP $HTTP (ID=$ID)"
  if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY"; fi

  # LIST
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B$path")
  echo "LIST:   HTTP $HTTP"

  # GET
  if [ "$ID" != "NOID" ] && [ -n "$ID" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B$path/$ID")
    echo "GET:    HTTP $HTTP"
  else
    echo "GET:    SKIP (no ID)"
  fi

  # UPDATE
  if [ -n "$update_data" ] && [ "$ID" != "NOID" ] && [ -n "$ID" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -H "$A" -H "$T" -H "$C" -d "$update_data" "$B$path/$ID")
    echo "UPDATE: HTTP $HTTP"
  else
    echo "UPDATE: SKIP"
  fi

  # DELETE
  if [ "$ID" != "NOID" ] && [ -n "$ID" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$A" -H "$T" "$B$path/$ID")
    echo "DELETE: HTTP $HTTP"
  else
    echo "DELETE: SKIP (no ID)"
  fi

  echo ""
  # Export ID for dependent tests
  export LAST_ID="$ID"
}

# 1. Categories
test_endpoint "CATEGORIES" "/api/v1/categories" \
  '{"name":"QA Cat2","description":"test"}' \
  '{"name":"QA Cat2 Upd"}'

# Save category for products
CAT_FOR_PROD="$LAST_ID"

# 2. Warehouses
test_endpoint "WAREHOUSES" "/api/v1/warehouses" \
  '{"name":"QA WH","code":"QAWH02","warehouse_type":"main","address":"Addr 1"}' \
  '{"name":"QA WH Upd"}'

WH_FOR_STOCK="$LAST_ID"

# 3. Suppliers
test_endpoint "SUPPLIERS" "/api/v1/suppliers" \
  '{"name":"QA Supplier","contact_email":"sup@qa.com","phone":"+573001111","address":"Sup Addr"}' \
  '{"name":"QA Sup Upd"}'

SUP_ID="$LAST_ID"

# 4. UoM
test_endpoint "UOM" "/api/v1/uom" \
  '{"name":"QA Unit","abbreviation":"QAU","category":"weight","conversion_factor":1.0}' \
  '{"name":"QA Unit Upd","abbreviation":"QAX","category":"weight","conversion_factor":2.0}'

# 5. Tax Rates
test_endpoint "TAX RATES" "/api/v1/tax-rates" \
  '{"name":"QA Tax 19","rate":19.0,"description":"IVA"}' \
  '{"name":"QA Tax 5","rate":5.0}'

# 6. Tax Categories
test_endpoint "TAX CATEGORIES" "/api/v1/tax-categories" \
  '{"name":"QA TaxCat","description":"test cat"}' \
  '{"name":"QA TaxCat Upd"}'

# 7. Customers
test_endpoint "CUSTOMERS" "/api/v1/customers" \
  '{"name":"QA Cust","email":"cust@qa.com","phone":"+573002222","address":"Cust Addr"}' \
  '{"name":"QA Cust Upd"}'

CUST_ID="$LAST_ID"

# 8. Events
test_endpoint "EVENTS" "/api/v1/events" \
  '{"event_type":"note","title":"QA Event","description":"test event"}' \
  '{"title":"QA Event Upd"}'

# 9. Products (needs category)
# First recreate a category for products
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" -d '{"name":"Prod Cat","description":"for products"}' "$B/api/v1/categories")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
PCAT_ID=$(echo "$BODY" | get_id)
echo "=== PRODUCTS ==="
echo "(Using category $PCAT_ID)"

RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d "{\"name\":\"QA Product\",\"sku\":\"QA-SKU-001\",\"category_id\":\"$PCAT_ID\",\"unit_price\":100.0}" \
  "$B/api/v1/products")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
PROD_ID=$(echo "$BODY" | get_id)
echo "CREATE: HTTP $HTTP (ID=$PROD_ID)"
if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY"; fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/products")
echo "LIST:   HTTP $HTTP"

if [ "$PROD_ID" != "NOID" ]; then
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/products/$PROD_ID")
  echo "GET:    HTTP $HTTP"
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -H "$A" -H "$T" -H "$C" -d '{"name":"QA Prod Upd"}' "$B/api/v1/products/$PROD_ID")
  echo "UPDATE: HTTP $HTTP"
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$A" -H "$T" "$B/api/v1/products/$PROD_ID")
  echo "DELETE: HTTP $HTTP"
fi
echo ""

# 10. Recreate product & warehouse for PO/SO/Stock tests
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d "{\"name\":\"Stock Prod\",\"sku\":\"QA-STK-001\",\"category_id\":\"$PCAT_ID\",\"unit_price\":50.0}" "$B/api/v1/products")
PROD2_ID=$(echo "$RESP" | sed '$d' | get_id)

RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d '{"name":"Stock WH","code":"QASTK01","warehouse_type":"main","address":"WH Addr"}' "$B/api/v1/warehouses")
WH2_ID=$(echo "$RESP" | sed '$d' | get_id)

# Recreate supplier for PO
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d '{"name":"PO Supplier","contact_email":"po@qa.com","phone":"+573003333","address":"PO Addr"}' "$B/api/v1/suppliers")
SUP2_ID=$(echo "$RESP" | sed '$d' | get_id)

# Recreate customer for SO
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d '{"name":"SO Customer","email":"so@qa.com","phone":"+573004444","address":"SO Addr"}' "$B/api/v1/customers")
CUST2_ID=$(echo "$RESP" | sed '$d' | get_id)

echo "=== PURCHASE ORDERS ==="
echo "(supplier=$SUP2_ID, wh=$WH2_ID, prod=$PROD2_ID)"
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d "{\"supplier_id\":\"$SUP2_ID\",\"warehouse_id\":\"$WH2_ID\",\"lines\":[{\"product_id\":\"$PROD2_ID\",\"quantity\":10,\"unit_price\":50.0}]}" \
  "$B/api/v1/purchase-orders")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
PO_ID=$(echo "$BODY" | get_id)
echo "CREATE: HTTP $HTTP (ID=$PO_ID)"
if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY"; fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/purchase-orders")
echo "LIST:   HTTP $HTTP"

if [ "$PO_ID" != "NOID" ] && [ -n "$PO_ID" ]; then
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/purchase-orders/$PO_ID")
  echo "GET:    HTTP $HTTP"
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -H "$A" -H "$T" -H "$C" -d "{\"supplier_id\":\"$SUP2_ID\",\"warehouse_id\":\"$WH2_ID\",\"lines\":[{\"product_id\":\"$PROD2_ID\",\"quantity\":20,\"unit_price\":45.0}]}" "$B/api/v1/purchase-orders/$PO_ID")
  echo "UPDATE: HTTP $HTTP"
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$A" -H "$T" "$B/api/v1/purchase-orders/$PO_ID")
  echo "DELETE: HTTP $HTTP"
fi
echo ""

echo "=== SALES ORDERS ==="
echo "(customer=$CUST2_ID, wh=$WH2_ID, prod=$PROD2_ID)"
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d "{\"customer_id\":\"$CUST2_ID\",\"warehouse_id\":\"$WH2_ID\",\"lines\":[{\"product_id\":\"$PROD2_ID\",\"quantity\":5,\"unit_price\":100.0}]}" \
  "$B/api/v1/sales-orders")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
SO_ID=$(echo "$BODY" | get_id)
echo "CREATE: HTTP $HTTP (ID=$SO_ID)"
if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY"; fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/sales-orders")
echo "LIST:   HTTP $HTTP"

if [ "$SO_ID" != "NOID" ] && [ -n "$SO_ID" ]; then
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/sales-orders/$SO_ID")
  echo "GET:    HTTP $HTTP"
  RESP=$(curl -s -w "\n%{http_code}" -X PUT -H "$A" -H "$T" -H "$C" -d "{\"customer_id\":\"$CUST2_ID\",\"warehouse_id\":\"$WH2_ID\",\"lines\":[{\"product_id\":\"$PROD2_ID\",\"quantity\":8,\"unit_price\":90.0}]}" "$B/api/v1/sales-orders/$SO_ID")
  HTTP=$(echo "$RESP" | tail -1)
  BODY2=$(echo "$RESP" | sed '$d')
  echo "UPDATE: HTTP $HTTP"
  if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY2"; fi
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$A" -H "$T" "$B/api/v1/sales-orders/$SO_ID")
  echo "DELETE: HTTP $HTTP"
fi
echo ""

echo "=== STOCK LEVELS ==="
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/stock")
echo "LIST: HTTP $HTTP"
# Stock typically doesn't have direct CREATE/UPDATE/DELETE (managed via movements)
RESP=$(curl -s -w "\n%{http_code}" -H "$A" -H "$T" "$B/api/v1/stock")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
echo "BODY: $BODY"
echo ""

echo "=== MOVEMENTS ==="
RESP=$(curl -s -w "\n%{http_code}" -X POST -H "$A" -H "$T" -H "$C" \
  -d "{\"product_id\":\"$PROD2_ID\",\"warehouse_id\":\"$WH2_ID\",\"movement_type\":\"adj_in\",\"quantity\":100,\"reference\":\"QA-ADJ-001\"}" \
  "$B/api/v1/movements")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
MOV_ID=$(echo "$BODY" | get_id)
echo "CREATE: HTTP $HTTP (ID=$MOV_ID)"
if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY"; fi

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/movements")
echo "LIST:   HTTP $HTTP"

if [ "$MOV_ID" != "NOID" ] && [ -n "$MOV_ID" ]; then
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/movements/$MOV_ID")
  echo "GET:    HTTP $HTTP"
fi
echo ""

echo "=== CONFIG: WAREHOUSE-TYPES ==="
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/config/warehouse-types")
echo "LIST: HTTP $HTTP"
RESP=$(curl -s -w "\n%{http_code}" -H "$A" -H "$T" "$B/api/v1/config/warehouse-types")
echo "BODY: $(echo "$RESP" | sed '$d')"
echo ""

echo "=== CONFIG: MOVEMENT-TYPES ==="
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "$A" -H "$T" "$B/api/v1/config/movement-types")
echo "LIST: HTTP $HTTP"
RESP=$(curl -s -w "\n%{http_code}" -H "$A" -H "$T" "$B/api/v1/config/movement-types")
echo "BODY: $(echo "$RESP" | sed '$d')"
echo ""

echo "=== ANALYTICS ==="
RESP=$(curl -s -w "\n%{http_code}" -H "$A" -H "$T" "$B/api/v1/analytics/overview")
HTTP=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
echo "OVERVIEW: HTTP $HTTP"
if [ "$HTTP" -ge 400 ]; then echo "  ERR: $BODY"; fi
echo ""

echo "=== DONE ==="
