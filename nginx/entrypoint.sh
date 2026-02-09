#!/bin/sh
set -e

CERT_DIR="/etc/nginx/certs"
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

LISTEN_PORT="${LISTEN_PORT:-8889}"
export LISTEN_PORT

# Generate nginx config from template
echo "Configuring nginx to listen on port $LISTEN_PORT..."
envsubst '${LISTEN_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Ensure certs directory exists
mkdir -p "$CERT_DIR"

# Generate self-signed certificate if not provided
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "No SSL certificate found. Generating self-signed certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/CN=localhost/O=ServiceMeow/C=US"
    echo "Self-signed certificate generated."
else
    echo "Using existing SSL certificate."
fi

echo "Starting nginx..."
exec nginx -g "daemon off;"
