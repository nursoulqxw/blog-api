#!/bin/bash
set -e

mkdir -p /app/data /app/staticfiles /app/logs

echo "Waiting for Redis..."
until python -c "import redis; r = redis.Redis(host='redis', port=6379); r.ping()" 2>/dev/null; do
    sleep 1
done
echo "Redis is ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Compiling translations..."
python manage.py compilemessages

if [ "$BLOG_SEED_DB" = "true" ]; then
    echo "Seeding database..."
    python manage.py seed
fi

exec "$@"