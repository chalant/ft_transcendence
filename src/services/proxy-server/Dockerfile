FROM		alpine:3.20

RUN			apk update && apk upgrade && apk add \
			openssl \
			nginx

RUN			rm -f /etc/nginx/nginx.conf && \
			mkdir /etc/nginx/ssl && \
			openssl req -x509 -nodes \
			-out /etc/nginx/ssl/ft_transcendence.crt \
			-keyout /etc/nginx/ssl/ft_transcendence.key \
			-subj "/C=BE/ST=IDF/L=Bruxelles/O=42/OU=42/CN=ft_transcendence.fr/UID=login"

COPY		conf/nginx.conf /etc/nginx/nginx.conf
COPY		conf/proxy_params.conf /etc/nginx/proxy_params.conf
COPY		tools/run_service.sh /bin/run_service.sh

RUN			chmod +x /bin/run_service.sh
EXPOSE		443

CMD	[ "run_service.sh" ]