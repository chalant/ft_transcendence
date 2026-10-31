#!/bin/sh

cd /home/service
python3 manage.py migrate
python3 manage.py collectstatic --noinput
exec uvicorn src.asgi:application --host 0.0.0.0 --port 8000
