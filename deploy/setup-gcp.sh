#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Trace Platform — GCP Initial Setup
# ═══════════════════════════════════════════════════════════════════════════════
# Run this ONCE to set up your GCP project.
# Prerequisites: gcloud CLI installed + logged in (gcloud auth login)
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ── Config (change these) ────────────────────────────────────────────────────
PROJECT_ID="trace-platform"          # Change to your project ID
REGION="southamerica-east1"          # Sao Paulo (closest to Colombia)
DB_PASSWORD="$(openssl rand -hex 16)"

echo "=== Trace Platform GCP Setup ==="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo ""

# 1. Create project (skip if exists)
gcloud projects create $PROJECT_ID --name="Trace Platform" 2>/dev/null || true
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firebase.googleapis.com \
  secretmanager.googleapis.com

# 3. Create Artifact Registry (Docker images)
echo "Creating Artifact Registry..."
gcloud artifacts repositories create trace \
  --repository-format=docker \
  --location=$REGION \
  --description="Trace Platform Docker images" 2>/dev/null || true

# 4. Create Cloud SQL (PostgreSQL)
echo "Creating Cloud SQL instance..."
gcloud sql instances create trace-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-size=10GB \
  --storage-auto-increase \
  --availability-type=zonal \
  --root-password=$DB_PASSWORD

# Create all 8 databases
for db in tracedb userdb subdb inventorydb integrationdb compliancedb aidb mediadb; do
  echo "  Creating database: $db"
  gcloud sql databases create $db --instance=trace-db 2>/dev/null || true
done

# 5. Create Redis (Memorystore)
echo "Creating Redis..."
gcloud redis instances create trace-redis \
  --size=1 \
  --region=$REGION \
  --tier=basic \
  --redis-version=redis_7_0 2>/dev/null || true

# 6. Get connection info
DB_IP=$(gcloud sql instances describe trace-db --format='value(ipAddresses[0].ipAddress)')
REDIS_IP=$(gcloud redis instances describe trace-redis --region=$REGION --format='value(host)' 2>/dev/null || echo "pending")

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Cloud SQL IP:    $DB_IP"
echo "  Cloud SQL Pass:  $DB_PASSWORD"
echo "  Redis IP:        $REDIS_IP"
echo ""
echo "  Next steps:"
echo "  1. Save DB_PASSWORD somewhere safe"
echo "  2. Create a service account for GitHub Actions:"
echo "     gcloud iam service-accounts create github-deploy"
echo "     gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "       --member=serviceAccount:github-deploy@$PROJECT_ID.iam.gserviceaccount.com \\"
echo "       --role=roles/run.admin"
echo "     gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "       --member=serviceAccount:github-deploy@$PROJECT_ID.iam.gserviceaccount.com \\"
echo "       --role=roles/artifactregistry.writer"
echo "     gcloud iam service-accounts keys create key.json \\"
echo "       --iam-account=github-deploy@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "  3. Add GitHub Secrets:"
echo "     GCP_PROJECT_ID = $PROJECT_ID"
echo "     GCP_SA_KEY     = (contents of key.json)"
echo ""
echo "  4. Push to main and the CI/CD will deploy everything"
echo "═══════════════════════════════════════════════════════════════"
