from common import jwt

from django.shortcuts import render
from django.contrib.auth import get_user_model, login, logout
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.db.utils import IntegrityError, DataError

import os
import json
from uuid import uuid4
from http import client
import random
import string
import time
from datetime import datetime, timedelta
from .models import UserToken
from user_data.models import UserProfile
from user_data.services import create_profile
from .validators import validate_username
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

SECRET = os.environ.get('JWT_SECRET_KEY').encode('utf-8')

MIN_PASSWORD_LENGTH = 5

def create_jwt(username):
	header = {
		"alg": "HS256",
		"typ": "JWT"
	}

	now = datetime.now()
	exp = now + timedelta(hours=2)

	payload = {
		"sub": uuid4().int,
		"name": username,
		"iat": int(now.timestamp()),
		"exp": int(exp.timestamp()),
		"iss": "ft_transcendence.com"
	}

	payload_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
	payload_b64 = jwt.base64url_encode(payload_json)
	header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
	header_b64 = jwt.base64url_encode(header_json)
	signature = jwt.hmac.new(SECRET, f"{header_b64}.{payload_b64}".encode('utf-8'), jwt.hashlib.sha256).digest()
	signature_b64 = jwt.base64url_encode(signature)

	return f"{header_b64}.{payload_b64}.{signature_b64}"

def get_jwt(request):
	auth = request.headers.get('Authorization')
	if not auth:
		return None
	if not 'Bearer ' in auth:
		return None
	values = auth.split(' ')
	if len(values) != 2:
		return None
	if values[1] == 'null':
		return None
	return values[1]

def validate_jwt(token):
	if not token:
		raise ValueError("No token")
	payload = jwt.verify_jwt(token, SECRET)
	exp = payload.get("exp")
	if exp is None:
		raise ValueError("Token has no expiration time")
	# Compare with the current time
	current_time = int(time.time())
	if current_time > exp:
		raise ValueError("Token has expired")

def check_jwt(request) -> User:
	# check if we have the token in the database -> means that user has not logged out
	token = get_jwt(request)
	user_token = UserToken.objects.filter(token=token).first()
	if not user_token:
		return None
	# check if the token is still valid.
	try:
		validate_jwt(token)
		return user_token.user
	except ValueError:
		# remove the token from the database as it is invalid
		user_token.delete()
		return None

def custom_login(request : HttpRequest, username, password):
	user = User.objects.filter(username=username).first()
	if user is None:
		return JsonResponse({
			'status': 0,
			'message':
			'User does not exist'}, status=401)
	if user.username42 is not None:
		return JsonResponse({'status': 0, 'message': 'You should login through 42auth'}, status=401)
	if user.check_password(password):
		login(request, user)
		return profile_mini(request, False)
	return JsonResponse({
		'status': 0,
		'message': 'Login failed'}, status=401)

def login_view(request : HttpRequest) -> JsonResponse:
	if request.method != 'POST':
		return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
	if request.user.is_authenticated:
		return JsonResponse({'status': 0, 'message': 'Already logged in'}, status=200)
	try:
		data = json.loads(request.body)
	except json.decoder.JSONDecodeError:
		return JsonResponse({'status': 0, 'message': 'Couldn\'t read input'}, status=400)
	username = data["username"]
	password = data["password"]
	return custom_login(request, username, password)

def logout_view(request : HttpRequest) -> JsonResponse:
	if request.method != 'POST':
		return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
	if not request.user.is_authenticated:
		return JsonResponse({'status': 0, 'message': 'not logged in'}, status=401)
	# delete token from database.
	user_token = UserToken.objects.filter(user=request.user).first()
	if user_token:
		user_token.delete()
	channel_layer = get_channel_layer()
	async_to_sync(channel_layer.group_send)(
		f"user_{request.user.id}",  # Channel group name
		{
			'type': 'user.logout',  # Custom event type
			'message': 'User logged out',
		}
	)
	logout(request)
	return JsonResponse({'status' : 1}, status=200)

def profile_mini(request : HttpRequest, jwt_existing: bool) -> JsonResponse:
	try:
		profile_picture = UserProfile.objects.get(user_id=request.user.id).profile_picture.url
	except UserProfile.DoesNotExist:
		return JsonResponse({'status': 0, 'message': 'Profile picture not found'}, status=404)

	if not jwt_existing:
		token = create_jwt(request.user.username)
		user_token, created = UserToken.objects.get_or_create(user=request.user)
		user_token.token = token
		if not created:
			user_token.save(update_fields=['token'])
		else:
			user_token.save()
	else:
		token = get_jwt(request)

	return JsonResponse({
		'status': 1,
		'message': 'logged-in',
		'token': token,
		'user': {
			'username': request.user.username,
			'profile_picture': profile_picture
		}
	}, status=200)

def sign_up_view(request : HttpRequest) -> JsonResponse:
	if request.method != 'POST':
		return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
	if request.user.is_authenticated:
		return JsonResponse({'status': 0, 'message': 'Already logged in'}, status=200)
	try:
		data: dict = json.loads(request.body)
	except json.decoder.JSONDecodeError:
		return JsonResponse({'status': 0, 'message': 'Couldn\'t read input'}, status=400)
	if (data["password"] != data["confirm_password"]):
		return JsonResponse({'status': 0, 'message' : 'Passwords do not match'}, status=400)

	if (len(data["password"]) < MIN_PASSWORD_LENGTH):
		return JsonResponse({'status': 0, 'message' : 'Password too short'}, status=400)
	error = validate_username(data["username"])
	if error:
		return JsonResponse({'status': 0, 'message': error}, status=400)

	try:
		user = User.objects.create_user(data["username"], password=data["password"])
	except IntegrityError:
		return JsonResponse({'status': 0, 'message': "Username already taken"}, status=400)
	except DataError:
		return JsonResponse({'status': 0, 'message': "Username too long"}, status=400)
	except Exception:
		return JsonResponse({'status': 0, 'message': 'An unexpected error occurred'}, status=400)

	user.is_active = True
	user.save()

	try:
		create_profile(user)
	except Exception:
		user.delete()
		return JsonResponse({'status': 0, 'message': 'User creation failed'}, status=400)

	login(request, user)
	return profile_mini(request, False)

def is_authenticated_view(request : HttpRequest) -> JsonResponse:
	if request.method != 'GET':
		return JsonResponse({'status': 0, 'message': 'Only GET method is allowed'}, status=405)
	# check if it has a valid token first
	jwt_existing = False
	if get_jwt(request):
		jwt_existing = True
	if request.user.is_authenticated:
		return profile_mini(request, jwt_existing)
	user = check_jwt(request)
	if user:
		login(request, user)
		return profile_mini(request, jwt_existing)
	else :
		return JsonResponse({'status': 0, 'message': 'User not connected'}, status=200)

def check_token(request : HttpRequest) -> JsonResponse:
	if check_jwt(request):
		return HttpResponse(status=200)
	return HttpResponse(status=401)

def get_user(request : HttpRequest) -> JsonResponse:
	user = check_jwt(request)
	if user:
		return JsonResponse({
			'username': user.username,
			'user_id': user.id
		}, status=200)
	return JsonResponse({}, status=401)

def authenticate_42API(request) -> tuple:
	path = request.get_full_path()
	if "error" in path:
		return None, 'Failed to authenticate'

	code = path[14:]
	client_id = os.environ.get('CLIENT_ID')
	client_secret = os.environ.get('CLIENT_SECRET')
	redirect_uri = os.environ.get("REDIRECT_URI")

	auth_url = "api.intra.42.fr"
	endpoint = "/oauth/token"

	fields = {
		'grant_type': 'authorization_code',
		'client_id': client_id,
		'client_secret': client_secret,
		'code': code,
		'redirect_uri': redirect_uri
	}

	boundary = uuid4().hex
	body = ''
	for key, value in fields.items():
		body += f'--{boundary}\r\n'
		body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
		body += f'{value}\r\n'
	body += f'--{boundary}--\r\n'

	body = body.encode('utf-8')

	headers = {
		'Content-Type': f'multipart/form-data; boundary={boundary}',
		'Content-Length': str(len(body))
	}

	connection = client.HTTPSConnection(auth_url)
	connection.request("POST", endpoint, body, headers)

	response = connection.getresponse()
	data = response.read().decode()
	connection.close()
	print(data, flush=True)

	if response.status != 200:
		return None, 'Failed to authenticate'
	return json.loads(data), None

def generate_username() -> str:
	words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "lima"]
	username = random.choice(words) + "".join(random.choices(string.digits, k=4))
	return username

def auth42_response(request : HttpRequest, status : int, message : str) -> HttpResponse:
	return render(request, 'api42.html', {'json_data': json.dumps({'status': status, 'message': message})})

def auth42_view(request : HttpRequest) -> HttpResponse:
	if request.user.is_authenticated:
		return auth42_response(request, 0, "Already logged in")

	auth_response, error_message = authenticate_42API(request)
	if error_message:
		return auth42_response(request, 0, error_message)

	headers = {
		"Authorization": "Bearer " + auth_response["access_token"]
	}

	api_url = "api.intra.42.fr"
	endpoint = "/v2/me"

	connection = client.HTTPSConnection(api_url)
	connection.request("GET", endpoint, "", headers)
	api_response = connection.getresponse()
	data = api_response.read().decode()
	connection.close()

	if api_response.status != 200:
		return auth42_response(request, 0, "Failed to retrieve user data, please try again later")

	MeData = json.loads(data)
	user = User.objects.filter(username42=MeData["login"]).first()
	if user is None:
		username = generate_username()
		while User.objects.filter(username=username).exists():
			username = generate_username()
		new_user = User.objects.create_user(username=username, username42=MeData["login"])
		new_user.is_active = True
		new_user.save()

		try:
			create_profile(new_user, MeData["image"]["link"])
		except Exception:
			new_user.delete()
			return auth42_response(request, 0, "Could not create user")
		login(request, new_user)
	else:
		login(request, user)
	return auth42_response(request, 1, "Welcome")

def change_username_view(request : HttpRequest) -> JsonResponse:
	if not request.user.is_authenticated:
		return JsonResponse({'status': 0, 'message': 'User not connected'}, status=401)
	if request.method != 'POST':
		return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
	try:
		data: dict = json.loads(request.body)
	except json.decoder.JSONDecodeError:
		return JsonResponse({'status': 0, 'message': 'Couldn\'t read input'}, status=400)
	error = validate_username(data["username"])
	if error:
		return JsonResponse({'status': 0, 'message': error}, status=400)
	if User.objects.filter(username=data["username"]).exists():
		return JsonResponse({'status': 0, 'message' : 'Username already exists'}, status=400)
	user = User.objects.get(id=request.user.id)
	try:
		user.username = data["username"]
		user.save()
	except DataError:
		return JsonResponse({'status': 0, 'message': "Username too long"}, status=400)
	return JsonResponse({'status': 1, 'message': 'Username changed', 'username': data['username']}, status=200)

def change_password_view(request : HttpRequest) -> JsonResponse:
	if not request.user.is_authenticated:
		return JsonResponse({'status': 0, 'message': 'User not connected'}, status=401)
	if request.method != 'POST':
		return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
	try:
		data: dict = json.loads(request.body)
	except json.decoder.JSONDecodeError:
		return JsonResponse({'status': 0, 'message': 'Couldn\'t read input'}, status=400)
	if (data["new_password"] != data["confirm_new_password"]):
		return JsonResponse({'status': 0, 'message' : 'Passwords do not match'}, status=400)
	if (len(data["new_password"]) < MIN_PASSWORD_LENGTH):
		return JsonResponse({'status': 0, 'message' : 'Password too short'}, status=400)
	user = User.objects.get(id=request.user.id)
	if user.username42:
		return JsonResponse({'status': 0, 'message' : 'Cannot change password of 42 account'}, status=400)
	if not user.check_password(data["old_password"]):
		return JsonResponse({'status': 0, 'message' : 'Incorrect password'}, status=400)
	user.set_password(data["new_password"])
	user.save()
	return JsonResponse({'status': 1, 'message': 'Password changed'}, status=200)
