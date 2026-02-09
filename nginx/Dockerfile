# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx with certs + frontend
FROM nginx:alpine

RUN apk add --no-cache openssl

# Copy nginx config template (processed at runtime by entrypoint)
COPY nginx/nginx.conf.template /etc/nginx/nginx.conf.template

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8889

ENTRYPOINT ["/entrypoint.sh"]
