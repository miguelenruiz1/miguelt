FROM nginx:1.27-alpine

# Static config for Docker Compose (local dev)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Entrypoint for Cloud Run (generates config from env vars)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9000

# In Docker Compose: uses nginx.conf directly (CMD default)
# In Cloud Run: set ENTRYPOINT override via --command or use entrypoint.sh
CMD ["sh", "/entrypoint.sh"]
