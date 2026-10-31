FROM		python:3.11-slim

COPY		requirements.txt /tmp/requirements.txt
RUN			pip install --no-cache-dir -r /tmp/requirements.txt

COPY		src /home/service
COPY		tools/run_service.sh /bin/run_service.sh

RUN			chmod +x /bin/run_service.sh

EXPOSE		8000

ENTRYPOINT	[ "run_service.sh" ]
