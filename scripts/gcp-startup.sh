#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# gcp-startup.sh — Prende infra Trace desde estado shutdown.
#
# Fases:
#   1. Crea VPC connector                          (~2 min)
#   2. Crea Redis Memorystore 1GB BASIC            (~5-8 min)
#   3. Recupera IP nueva de Redis
#   4. Actualiza REDIS_URL en los 9 Cloud Run svcs (~30 seg c/u = 5 min)
#   5. Inicia Cloud SQL                            (~3 min)
#   6. Smoke test del gateway
#
# Tiempo total: ~15-20 minutos.
# Uso: bash scripts/gcp-startup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT=trace-log
REGION=southamerica-east1
SQL_INSTANCE=trace-db
REDIS_INSTANCE=trace-redis
VPC_CONNECTOR=trace-connector
VPC_NETWORK=default
VPC_RANGE=10.8.0.0/28
GATEWAY_URL=https://gateway-421343664920.southamerica-east1.run.app

# Mapa service → número de Redis DB (relevado con gcloud run services describe).
# Si agregas/cambiás un servicio, actualizá esta lista.
declare -A REDIS_DB_BY_SVC=(
  [trace-api]=0
  [user-api]=2
  [subscription-api]=3
  [inventory-api]=4
  [integration-api]=5
  [compliance-api]=6
  [ai-api]=7
  [media-api]=8
)

echo ""
echo "============================================================"
echo "  TRACE — STARTUP GCP"
echo "============================================================"
read -r -p "Confirmá con 'yes' para prender todo (~15-20min): " confirm
if [[ "$confirm" != "yes" ]]; then
  echo "Cancelado."
  exit 1
fi

# ─── 1. VPC Connector ───────────────────────────────────────────────────────
echo ""
echo "[1/6] Creando VPC connector $VPC_CONNECTOR ..."
if gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" \
      --region="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  echo "  (ya existe — skip)"
else
  gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
    --project="$PROJECT" \
    --region="$REGION" \
    --network="$VPC_NETWORK" \
    --range="$VPC_RANGE" \
    --min-instances=2 \
    --max-instances=10 \
    --machine-type=e2-micro \
    2>&1 | tail -5
fi

# ─── 2. Redis Memorystore ───────────────────────────────────────────────────
echo ""
echo "[2/6] Creando Redis Memorystore $REDIS_INSTANCE (1GB BASIC) ..."
if gcloud redis instances describe "$REDIS_INSTANCE" \
      --region="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  echo "  (ya existe — skip)"
else
  gcloud redis instances create "$REDIS_INSTANCE" \
    --project="$PROJECT" \
    --region="$REGION" \
    --tier=BASIC \
    --size=1 \
    --network="$VPC_NETWORK" \
    2>&1 | tail -5
fi

# ─── 3. Redis IP ────────────────────────────────────────────────────────────
echo ""
echo "[3/6] Obteniendo IP de Redis ..."
REDIS_IP=$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" --project="$PROJECT" \
  --format='value(host)')
REDIS_PORT=$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" --project="$PROJECT" \
  --format='value(port)')
if [[ -z "$REDIS_IP" ]]; then
  echo "  ERROR: no pude obtener IP de Redis. Abort."
  exit 2
fi
echo "  IP:$REDIS_IP  Port:$REDIS_PORT"

# ─── 4. Cloud Run env update ────────────────────────────────────────────────
echo ""
echo "[4/6] Actualizando REDIS_URL + vpc-connector en los 9 Cloud Run services ..."
for svc in "${!REDIS_DB_BY_SVC[@]}"; do
  db="${REDIS_DB_BY_SVC[$svc]}"
  new_url="redis://$REDIS_IP:$REDIS_PORT/$db"
  echo "  · $svc (db=$db)"
  gcloud run services update "$svc" \
    --project="$PROJECT" \
    --region="$REGION" \
    --update-env-vars="REDIS_URL=$new_url" \
    --vpc-connector="$VPC_CONNECTOR" \
    --no-traffic \
    --quiet 2>&1 | tail -1
done
# Route 100% traffic to the new revision of each service
echo "  · Ruteando tráfico a las revisiones nuevas..."
for svc in "${!REDIS_DB_BY_SVC[@]}"; do
  gcloud run services update-traffic "$svc" \
    --project="$PROJECT" \
    --region="$REGION" \
    --to-latest \
    --quiet 2>&1 | tail -1
done

# ─── 5. Cloud SQL ───────────────────────────────────────────────────────────
echo ""
echo "[5/6] Iniciando Cloud SQL $SQL_INSTANCE ..."
gcloud sql instances patch "$SQL_INSTANCE" \
  --project="$PROJECT" \
  --activation-policy=ALWAYS \
  --quiet 2>&1 | tail -3
echo "  Esperando RUNNABLE ..."
for _ in {1..30}; do
  state=$(gcloud sql instances describe "$SQL_INSTANCE" \
    --project="$PROJECT" --format='value(state)')
  if [[ "$state" == "RUNNABLE" ]]; then
    echo "  ✓ Cloud SQL RUNNABLE"
    break
  fi
  sleep 10
done

# ─── 6. Smoke test ──────────────────────────────────────────────────────────
echo ""
echo "[6/6] Smoke test del gateway ..."
sleep 20  # dar unos segundos extra para cold-start Cloud Run
for path in "/api/v1/auth/me" "/api/v1/plans/" "/api/v1/compliance/frameworks"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL$path" || echo "000")
  echo "  $code  $path"
done

echo ""
echo "============================================================"
echo "  ✓ Startup completo."
echo "============================================================"
echo ""
echo "Frontend:  https://front-trace-421343664920.southamerica-east1.run.app"
echo "Gateway:   $GATEWAY_URL"
echo ""
echo "Cuando termines:  bash scripts/gcp-shutdown.sh"
echo ""
