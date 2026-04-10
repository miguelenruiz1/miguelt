#!/bin/sh
# Generate nginx config from environment variables at startup
cat > /etc/nginx/conf.d/default.conf <<EOF
resolver 8.8.8.8 valid=30s;

server {
    listen ${NGINX_PORT:-9000};
    server_name _;
    client_max_body_size 50m;

    proxy_http_version 1.1;
    proxy_ssl_server_name on;
    proxy_connect_timeout 10s;
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;

    # Hide CORS headers from backend (gateway adds its own)
    proxy_hide_header Access-Control-Allow-Origin;
    proxy_hide_header Access-Control-Allow-Methods;
    proxy_hide_header Access-Control-Allow-Headers;
    proxy_hide_header Access-Control-Allow-Credentials;
    proxy_hide_header Access-Control-Max-Age;

    add_header Access-Control-Allow-Origin \$http_origin always;
    add_header Access-Control-Allow-Methods "GET,POST,PUT,PATCH,DELETE,OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization,Content-Type,X-Tenant-Id,X-User-Id,X-Service-Token,X-Correlation-Id,Idempotency-Key,X-Admin-Key" always;
    add_header Access-Control-Allow-Credentials "true" always;
    add_header Access-Control-Max-Age 86400 always;

    if (\$request_method = OPTIONS) { return 204; }


    location = /health {
        return 200 '{"status":"ok","service":"gateway"}';
        add_header Content-Type application/json;
    }

    # Readiness (proxied to trace-api for Solana/DB/Redis checks)
    location = /ready { proxy_pass https://${TRACE_UPSTREAM}; proxy_set_header Host ${TRACE_UPSTREAM}; }

    # Public cNFT metadata (no auth, Solana explorers need access)
    location /api/v1/assets/metadata/ { proxy_pass https://${TRACE_UPSTREAM}; proxy_set_header Host ${TRACE_UPSTREAM}; }

    # User Service
    location /api/v1/auth            { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }
    location /api/v1/users           { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }
    location /api/v1/roles           { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }
    location /api/v1/permissions     { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }
    location /api/v1/email           { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }
    location /api/v1/notifications   { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }
    location /api/v1/onboarding      { proxy_pass https://${USER_UPSTREAM}; proxy_set_header Host ${USER_UPSTREAM}; }

    # Subscription Service
    location /api/v1/plans           { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/subscriptions   { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/licenses        { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/modules         { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/payments        { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/platform        { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/admin           { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/usage           { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/enforcement     { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/cms             { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }
    location /api/v1/pages           { proxy_pass https://${SUBS_UPSTREAM}; proxy_set_header Host ${SUBS_UPSTREAM}; }

    # Inventory analytics & audit
    location /api/v1/analytics       { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/audit           { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }

    # Inventory Service
    location /api/v1/categories      { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/products        { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/warehouses      { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/stock           { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/movements       { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/suppliers       { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/purchase        { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/sales           { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/customers       { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/partners        { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/customer-prices { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/serials         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/batches         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/recipes         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/production      { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/cycle           { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/imports         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/alerts          { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/portal          { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/reorder         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/tax-rates       { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/tax-categories  { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/uom             { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/variant         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/reports         { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/events          { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/config          { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }
    location /api/v1/config/workflow { proxy_pass https://${TRACE_UPSTREAM}; proxy_set_header Host ${TRACE_UPSTREAM}; }
    location /api/v1/kardex          { proxy_pass https://${INVENTORY_UPSTREAM}; proxy_set_header Host ${INVENTORY_UPSTREAM}; }

    # Integration Service
    location /api/v1/integrations    { proxy_pass https://${INTEGRATION_UPSTREAM}; proxy_set_header Host ${INTEGRATION_UPSTREAM}; }
    location /api/v1/resolutions     { proxy_pass https://${INTEGRATION_UPSTREAM}; proxy_set_header Host ${INTEGRATION_UPSTREAM}; }
    location /api/v1/webhooks        { proxy_pass https://${INTEGRATION_UPSTREAM}; proxy_set_header Host ${INTEGRATION_UPSTREAM}; }

    # Compliance Service
    location /api/v1/compliance      { proxy_pass https://${COMPLIANCE_UPSTREAM}; proxy_set_header Host ${COMPLIANCE_UPSTREAM}; }

    # AI Service
    location /api/v1/analyze         { proxy_pass https://${AI_UPSTREAM}; proxy_set_header Host ${AI_UPSTREAM}; }
    location /api/v1/settings        { proxy_pass https://${AI_UPSTREAM}; proxy_set_header Host ${AI_UPSTREAM}; }
    location /api/v1/memory          { proxy_pass https://${AI_UPSTREAM}; proxy_set_header Host ${AI_UPSTREAM}; }
    location /api/v1/metrics         { proxy_pass https://${AI_UPSTREAM}; proxy_set_header Host ${AI_UPSTREAM}; }

    # Media Service
    location /api/v1/media           { proxy_pass https://${MEDIA_UPSTREAM}; proxy_set_header Host ${MEDIA_UPSTREAM}; }

    # Trace Service (catch-all)
    location /api/v1/                { proxy_pass https://${TRACE_UPSTREAM}; proxy_set_header Host ${TRACE_UPSTREAM}; }
}
EOF

exec nginx -g 'daemon off;'
