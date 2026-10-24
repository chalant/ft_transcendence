FROM		python:3.11-slim

RUN			apt-get update && apt-get install -y netcat-traditional && apt-get clean
RUN			pip install django channels uvicorn[standard]
RUN			pip install "psycopg[binary]"
RUN         pip install channels_redis "redis<6"

COPY		src /home/service
COPY		tools/run_service.sh /bin/run_service.sh

RUN			chmod +x /bin/run_service.sh

EXPOSE		8000

ENTRYPOINT	[ "run_service.sh" ]