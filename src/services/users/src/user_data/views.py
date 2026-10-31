from user_data.models import UserProfile
from django.http import HttpResponse, JsonResponse, FileResponse, HttpRequest
import json
from django.conf import settings
import os
from http import client
from django.contrib.auth import get_user_model
from friends.models import Relation

User = get_user_model()

def _attach_opponent_names(data: dict) -> None:
    # replaces each game's "opponent_id" with the opponent's username (single query).
    results = [
        result
        for game, stats in data.items()
        if game != 'status' and 'games' in stats
        for result in stats['games']
    ]
    names = dict(User.objects.filter(
        id__in={result["opponent_id"] for result in results}
    ).values_list('id', 'username'))
    for result in results:
        result["opponent"] = names.get(result.pop("opponent_id"), "deleted user")

def get_image(request : HttpRequest, filename: str):
    if request.method != 'GET':
        return HttpResponse(status=405)
    image_path = request.path
    full_image_path = os.path.join(settings.MEDIA_ROOT, image_path.lstrip('/'))
    if os.path.exists(full_image_path):
        return FileResponse(open(full_image_path, 'rb'), content_type='image/jpeg')
    else:
       return HttpResponse(status=404)

def change_profile_picture(request : HttpRequest) -> JsonResponse:
    if request.method != 'POST':
        return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'status': 0, 'message': 'User not connected'}, status=401)
    image = request.FILES['profile_picture']
    user = UserProfile.objects.get(user_id=request.user.id)
    user.profile_picture.save(f"{user.user_id}.jpg", image)
    user.save()
    return JsonResponse({'status': 1, 'message': 'Profile picture updated', 'new_profile_picture_url': user.profile_picture.url}, status=200)

def personal_stats(request : HttpRequest) -> JsonResponse:
    if request.method != 'GET':
        return JsonResponse({'status': 0, 'message': 'Only GET method is allowed'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'status': 0, 'message': 'User not connected'}, status=401)
    connection = client.HTTPConnection("game-server:8000", timeout=5)
    connection.request("GET", f"/game_stats/{request.user.id}/")
    response = connection.getresponse()
    data = json.loads(response.read().decode())
    connection.close()
    if response.status != 200 or data['status'] == 0:
        return JsonResponse(data, status=response.status)

    _attach_opponent_names(data)

    return JsonResponse(data, status=response.status)

def get_profile(request: HttpRequest, username: str) -> JsonResponse:
    if request.method != 'GET':
        return JsonResponse({'status': 0, 'message': 'Only GET method is allowed'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'status': 0, 'message': 'User not connected'}, status=401)
    if not User.objects.filter(username=username).exists():
        return JsonResponse({'status': 0, 'message': 'User not found'}, status=404)
    user = User.objects.get(username=username)
    user_profile = UserProfile.objects.get(user=user)
    if not user_profile:
        return JsonResponse({'status': 0, 'message': 'User profile not found'}, status=404)

    connection = client.HTTPConnection("game-server:8000", timeout=5)
    connection.request("GET", f"/game_stats/{user.id}/")
    response = connection.getresponse()
    data = json.loads(response.read().decode())
    connection.close()

    _attach_opponent_names(data)

    if not UserProfile.objects.filter(user=request.user).exists():
        return JsonResponse({'status': 0, 'message': 'Could not get user info'}, status=400)
    request_user_profile = UserProfile.objects.get(user=request.user)

    # different possibilities of current friendship status: yourself, not friend, friend, pending request, request received
    # yourself: 0, not friend: 1, friend: 2, pending request: 3, request received: 4
    if Relation.objects.filter(user=request_user_profile, friend=user_profile).exists():
        relation = Relation.objects.get(user=request_user_profile, friend=user_profile)
        if (relation.status == True):
            friendship = {'status': 2, 'id': relation.id}
        else:
            friendship = {'status': 3, 'id': relation.id}
    elif Relation.objects.filter(user=user_profile, friend=request_user_profile).exists():
        relation = Relation.objects.get(user=user_profile, friend=request_user_profile)
        if (relation.status == True):
            friendship = {'status': 2, 'id': relation.id}
        else:
            friendship = {'status': 4, 'id': relation.id}
    else:
        friendship = {'status': 1}
    if request_user_profile == user_profile:
        friendship = {'status': 0}

    return JsonResponse({'status': 1, 'username': username, 'id': user.id, 'profile_picture': user_profile.profile_picture.url, 'stats': data, 'friendship': friendship, 'is42': True if user.username42 else False}, status=200)