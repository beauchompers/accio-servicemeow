#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

# --- Copy .env.example → .env if missing ---
if [ ! -f "$ENV_FILE" ]; then
  if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "Error: .env.example not found. Are you in the project root?" >&2
    exit 1
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created .env from .env.example"
fi

# --- Generate missing secrets ---
generate_secret() {
  local key="$1"
  local current
  current=$(grep "^${key}=" "$ENV_FILE" | cut -d= -f2-)

  # Skip if already set to a real value (not a placeholder)
  if [ -n "$current" ] && [[ "$current" != *"change"*"production"* ]] && [[ "$current" != *"secret"* ]]; then
    return
  fi

  local value
  case "$key" in
    JWT_SECRET)
      value=$(openssl rand -hex 32)
      ;;
    POSTGRES_PASSWORD)
      value=$(openssl rand -hex 16)
      ;;
    DEFAULT_ADMIN_PASSWORD)
      value=$(openssl rand -base64 16)
      ;;
    *)
      return
      ;;
  esac

  # Use pipe delimiter to avoid conflicts with special characters
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi

  echo "Generated $key"
}

# --- Copy seed.json.example → seed.json if missing ---
SEED_FILE="$SCRIPT_DIR/seed.json"
SEED_EXAMPLE="$SCRIPT_DIR/seed.json.example"

if [ ! -f "$SEED_FILE" ]; then
  if [ -f "$SEED_EXAMPLE" ]; then
    cp "$SEED_EXAMPLE" "$SEED_FILE"
    echo "Created seed.json from seed.json.example"
    echo "  Tip: Edit seed.json to customize users and groups before first start."
  fi
fi

generate_secret JWT_SECRET
generate_secret POSTGRES_PASSWORD
generate_secret DEFAULT_ADMIN_PASSWORD

# Update DATABASE_URL to use the generated password
DB_PASS=$(grep "^POSTGRES_PASSWORD=" "$ENV_FILE" | cut -d= -f2-)
DB_USER=$(grep "^POSTGRES_USER=" "$ENV_FILE" | cut -d= -f2-)
DB_NAME=$(grep "^POSTGRES_DB=" "$ENV_FILE" | cut -d= -f2-)
sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@postgres:5432/${DB_NAME}|" "$ENV_FILE"

# Clean up sed backup file
rm -f "$ENV_FILE.bak"

# --- Read values for banner ---
get_env() {
  grep "^${1}=" "$ENV_FILE" | cut -d= -f2-
}

ASM_PORT=$(get_env ASM_PORT 2>/dev/null || echo "8889")
ADMIN_USER=$(get_env DEFAULT_ADMIN_USERNAME 2>/dev/null || echo "admin")
ADMIN_PASS=$(get_env DEFAULT_ADMIN_PASSWORD)

# Handle empty values
ASM_PORT="${ASM_PORT:-8889}"
ADMIN_USER="${ADMIN_USER:-admin}"

# --- Start Docker Compose ---
echo ""
echo "Starting Accio ServiceMeow..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build

# --- Wait for health check ---
echo ""
echo "Waiting for ServiceMeow to become healthy..."
MAX_WAIT=90
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  if curl -sk "https://localhost:${ASM_PORT}/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo "Warning: ServiceMeow did not respond within ${MAX_WAIT}s. Check 'docker compose logs' for details."
fi

# --- Print startup banner ---
echo ""
echo "============================================"
echo " Accio ServiceMeow is running!"
echo ""
echo " Web UI:  https://localhost:${ASM_PORT}"
echo " Login:   ${ADMIN_USER} / ${ADMIN_PASS}"
echo ""
echo " MCP:     https://localhost:${ASM_PORT}/mcp"
echo "============================================"
echo ""
