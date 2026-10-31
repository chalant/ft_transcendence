#!/bin/sh

cd /home/service

# the matchmaking service owns the schema of the `games` database: wait until it
# is applied (also fails while the database is unreachable).
until python3 manage.py migrate --check >/dev/null 2>&1; do
	echo "Waiting for matchmaking migrations..."
	sleep 2
done

exec uvicorn src.asgi:application --host 0.0.0.0 --port 8000
