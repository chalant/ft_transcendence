FROM		alpine:3.20

RUN			apk update && apk upgrade && apk add \
			python3-dev \
			build-base \
			jpeg-dev \
			zlib-dev \
			py3-django

COPY		src /home/service
COPY		tools/run_service.sh /bin/run_service.sh

RUN			chmod +x /bin/run_service.sh

EXPOSE		8000

ENTRYPOINT	[ "run_service.sh" ]
