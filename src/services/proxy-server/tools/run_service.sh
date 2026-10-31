#!/bin/sh

MAX_RETRIES=60

# nginx resolves the upstream hosts when it starts: wait until they all answer.
for host in website matchmaking game-server; do
	retries=0
	echo "Waiting for $host service to be ready..."
	while ! nc -z "$host" 8000; do
		retries=$((retries + 1))
		sleep 1
		if [ $retries -ge $MAX_RETRIES ]; then
			echo "Reached maximum number of retries, exiting..."
			exit 1
		fi
	done
done

echo "Launching proxy-server..."
nginx -g "daemon off;"
