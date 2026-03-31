FROM nginx:1.27-alpine

# Static config for Docker Compose (service names resolve via Docker DNS)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Template for Cloud Run (service URLs from env vars)
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# In Docker Compose: nginx.conf is used directly (static upstreams)
# In Cloud Run: set NGINX_ENVSUBST_TEMPLATE_DIR=/etc/nginx/templates
#               and provide *_UPSTREAM env vars

EXPOSE 9000
