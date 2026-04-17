#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# gcp-shutdown.sh — Apaga infra Trace en GCP para dejarla en costo mínimo.
#
#   - Cloud SQL      → STOPPED       (data preservada, solo storage ~$1.70/mes)
#   - Redis          → DELETED       (es cache, no hay data que perder)
#   - VPC connector  → DELETED       (cuesta $11/mes aunque esté idle)
#   - Cloud Run      → ingress=internal (bloquea tráfico de internet; sin
#                      esto un bot puede disparar 60s-timeouts y acumular
#                      costo real de CPU)
#
# Costo mensual mientras esté apagado: ~$3-4 USD.
# Tiempo total: ~2-3 minutos.
# Uso: bash scripts/gcp-shutdown.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT=trace-log
REGION=southamerica-east1
SQL_INSTANCE=trace-db
REDIS_INSTANCE=trace-redis
VPC_CONNECTOR=trace-connector

echo ""
echo "============================================================"
echo "  TRACE — SHUTDOWN GCP"
echo "============================================================"
echo "Proyecto: $PROJECT"
echo "Región:   $REGION"
echo ""
read -r -p "Confirmá con 'yes' para apagar todo: " confirm
if [[ "$confirm" != "yes" ]]; then
  echo "Cancelado."
  exit 1
fi

CLOUD_RUN_SERVICES=(ai-api compliance-api front-trace gateway integration-api inventory-api media-api subscription-api trace-api user-api)

echo ""
echo "[1/4] Deteniendo Cloud SQL $SQL_INSTANCE ..."
gcloud sql instances patch "$SQL_INSTANCE" \
  --project="$PROJECT" \
  --activation-policy=NEVER \
  --quiet 2>&1 | tail -3 || echo "  (ya detenida o error)"

echo ""
echo "[2/4] Eliminando Redis Memorystore $REDIS_INSTANCE ..."
gcloud redis instances delete "$REDIS_INSTANCE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --quiet 2>&1 | tail -3 || echo "  (no existe o ya borrada)"

echo ""
echo "[3/4] Eliminando VPC connector $VPC_CONNECTOR ..."
gcloud compute networks vpc-access connectors delete "$VPC_CONNECTOR" \
  --region="$REGION" \
  --project="$PROJECT" \
  --quiet 2>&1 | tail -3 || echo "  (no existe o ya borrado)"

echo ""
echo "[4/4] Bloqueando ingress externo en los Cloud Run services ..."
for svc in "${CLOUD_RUN_SERVICES[@]}"; do
  gcloud run services update "$svc" \
    --region="$REGION" --project="$PROJECT" \
    --ingress=internal --quiet 2>&1 | tail -1 &
done
wait

echo ""
echo "============================================================"
echo "  ✓ Shutdown completo."
echo "============================================================"
echo ""
echo "Estado actual:"
echo "  • Cloud SQL     → STOPPED (datos preservados)"
echo "  • Redis         → DELETED (cache, sin data crítica)"
echo "  • VPC connector → DELETED"
echo "  • Cloud Run     → ingress=internal (URLs devuelven 404, 0 CPU)"
echo ""
echo "Costo mensual estimado mientras esté apagado: ~\$3-4 USD"
echo ""
echo "Cuando quieras prender:  bash scripts/gcp-startup.sh"
echo ""
