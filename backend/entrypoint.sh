#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U "$POSTGRES_USER" -q; do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Running database migrations..."
alembic upgrade head

echo "Checking seed data..."
python seed.py --if-empty

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
