import json
from http import client

USERS_HOST = 'users:8000'
TIMEOUT = 5


def _get_user(headers, body=None):
	conn = client.HTTPConnection(USERS_HOST, timeout=TIMEOUT)
	try:
		conn.request('GET', '/get_user/', body, headers)
		response = conn.getresponse()
		if response.status != 200:
			return None
		return json.loads(response.read().decode())
	except (OSError, client.HTTPException, ValueError):
		return None
	finally:
		conn.close()

def get_user(request):
	return _get_user(request.headers, request.body)

def get_user_with_token(auth_token, csrf_token):
	return _get_user({
		'Authorization': 'Bearer ' + auth_token,
		'X-CSRFToken': csrf_token
	})
