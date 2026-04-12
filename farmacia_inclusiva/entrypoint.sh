#!/bin/sh
# entrypoint.sh

echo "========================================"
echo "  Farmacia Inclusiva - Iniciando..."
echo "========================================"

DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"

# Esperar puerto TCP de PostgreSQL
echo "Esperando PostgreSQL en $DB_HOST:$DB_PORT ..."
COUNT=0
while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge 40 ]; then
        echo "ERROR: timeout esperando PostgreSQL"
        exit 1
    fi
    echo "  intento $COUNT/40 - esperando 3s..."
    sleep 3
done
echo "Puerto abierto. Esperando 4s..."
sleep 4

# Makemigrations
echo "--- makemigrations ---"
python manage.py makemigrations usuarios       --no-input || echo "warn: usuarios"
python manage.py makemigrations proveedores    --no-input || echo "warn: proveedores"
python manage.py makemigrations medicamentos   --no-input || echo "warn: medicamentos"
python manage.py makemigrations ventas         --no-input || echo "warn: ventas"
python manage.py makemigrations notificaciones --no-input || echo "warn: notificaciones"
python manage.py makemigrations                --no-input || echo "warn: general"

# Migrate
echo "--- migrate ---"
python manage.py migrate --no-input
if [ $? -ne 0 ]; then
    echo "ERROR en migrate"
    exit 1
fi

# Collectstatic (no fatal si falla)
echo "--- collectstatic ---"
python manage.py collectstatic --no-input --clear 2>&1 || echo "warn: collectstatic fallo, continuando..."

# Setup inicial
echo "--- setup inicial ---"
python scripts/setup_inicial.py || echo "warn: setup fallo, continuando..."

# Iniciar servidor
echo ""
echo "========================================"
echo "  http://localhost:8000"
echo "========================================"
python manage.py runserver 0.0.0.0:8000
