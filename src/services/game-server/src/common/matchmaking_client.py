import json
from http import client

MATCHMAKING_HOST = 'matchmaking:8000'
TIMEOUT = 5


def advance(tournament_id: str, player_id: int) -> None:
	"""Ask matchmaking to move `player_id` to the next round of the tournament.

	Blocking call: run it from a thread (database_sync_to_async).
	"""
	conn = client.HTTPConnection(MATCHMAKING_HOST, timeout=TIMEOUT)
	try:
		conn.request(
			'POST', '/internal/advance/',
			json.dumps({'tournament_id': tournament_id, 'player_id': player_id}),
			{'Content-Type': 'application/json'})
		response = conn.getresponse()
		response.read()
		if response.status != 200:
			raise RuntimeError(f"matchmaking advance failed: {response.status}")
	finally:
		conn.close()
