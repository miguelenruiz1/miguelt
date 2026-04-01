FROM node:20-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci && npm i @rollup/rollup-linux-x64-gnu
COPY . .
ARG VITE_API_URL
ARG VITE_TENANT_ID=default
ENV VITE_API_URL=$VITE_API_URL VITE_TENANT_ID=$VITE_TENANT_ID
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
RUN printf 'server {\n\
  listen 8080;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location / {\n\
    try_files $uri $uri/ /index.html;\n\
  }\n\
  location /assets/ {\n\
    expires 1y;\n\
    add_header Cache-Control "public, immutable";\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 8080
