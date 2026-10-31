#!/bin/sh

MAX_RETRIES=60
UPSTREAM_CONF=/etc/nginx/game_servers.conf

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

# addresses of the game-server replicas that accept connections, one per line (a
# starting replica already has an address but still waits for its migrations).
resolve() {
	for address in $(getent ahostsv4 game-server | awk '{print $1}' | sort -u); do
		nc -z -w 1 "$address" 8000 && echo "$address"
	done
}

# Room affinity needs one `server` line per replica: nginx's consistent hash
# ignores the key (falls back to round robin) for a single hostname that
# resolves to several addresses.
write_upstream() {
	{
		echo "upstream game_servers {"
		echo "	hash \$game_room consistent;"
		for address in $1; do
			echo "	server $address:8000;"
		done
		echo "}"
	} > "$UPSTREAM_CONF"
}

known=$(resolve)
write_upstream "$known"

# game-server replicas come and go: regenerate the upstream and reload.
(
	while sleep 10; do
		current=$(resolve)
		# an empty answer is a failed lookup: keep the current upstreams.
		if [ -n "$current" ] && [ "$current" != "$known" ]; then
			echo "game-server replicas changed, reloading nginx"
			write_upstream "$current"
			nginx -s reload && known=$current
		fi
	done
) &

echo "Launching proxy-server..."
exec nginx -g "daemon off;"
