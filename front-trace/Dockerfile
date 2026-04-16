FROM node:20-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --no-audit --no-fund && npm i @rollup/rollup-linux-x64-gnu
COPY . .
# The old lowercase-bridge step was removed — both shadcn (badge.tsx) and
# custom components (EmptyState.tsx) coexist now and must keep their own
# casing for imports to resolve on Linux.
ARG VITE_API_URL
ARG VITE_TENANT_ID=default
ENV VITE_API_URL=$VITE_API_URL VITE_TENANT_ID=$VITE_TENANT_ID
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
RUN printf 'gzip on;\n\
gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;\n\
gzip_min_length 256;\n\
gzip_vary on;\n\
\n\
server {\n\
  listen 8080;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location / {\n\
    try_files $uri $uri/ /index.html;\n\
    add_header Cache-Control "no-cache, no-store, must-revalidate";\n\
  }\n\
  location /assets/ {\n\
    try_files $uri /index.html;\n\
    expires 1y;\n\
    add_header Cache-Control "public, immutable";\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 8080
