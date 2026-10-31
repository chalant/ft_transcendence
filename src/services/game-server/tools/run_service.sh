#!/bin/sh

cd /home/service

python3 manage.py makemigrations
until python3 manage.py migrate; do
	echo "Waiting for database..."
	sleep 2
done

exec uvicorn src.asgi:application --host 0.0.0.0 --port 8000
