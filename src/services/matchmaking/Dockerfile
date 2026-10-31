FROM		python:3.11-slim

COPY		services/matchmaking/requirements.txt /tmp/requirements.txt
RUN			pip install --no-cache-dir -r /tmp/requirements.txt

COPY		services/matchmaking/src /home/service
# code shared with other services (build context is src/).
COPY		libs/games /home/service/games
COPY		libs/auth_client.py /home/service/auth_client.py
COPY		services/matchmaking/tools/run_service.sh /bin/run_service.sh

RUN			chmod +x /bin/run_service.sh

EXPOSE		8000

ENTRYPOINT	[ "run_service.sh" ]
