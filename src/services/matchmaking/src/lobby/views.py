import uuid
import json
import os
from django.http import JsonResponse, HttpRequest
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.db.models import Subquery
from django.db.utils import DatabaseError

from games.models import (
	GameRoom,
	PlayerRoom,
	Player,
	Game,
	Tournament,
	TournamentGameRoom,
	TournamentParticipant,
	GameResult
)

import auth_client as auth
from .locks import advisory_lock

MAX_TOURNAMENT_PARTICIPANTS = 4

def get_host_player(user_data: dict) -> Player:
	player, created = Player.objects.get_or_create(
		player_name="host",
		user_id=int(user_data['user_id']))
	player.user_name = user_data['username']
	player.save(update_fields=['user_name'])
	return player

def check_request(func):
	def wrapper(request:HttpRequest) -> JsonResponse:
		user_data = auth.get_user(request)
		if request.method != 'POST':
			return JsonResponse({
				'status': 0,
				'message': 'Only POST requests are allowed'
				}, status=405)
		if not user_data:
			return JsonResponse({
				'status': 0,
				'message': 'Invalid token'
			}, status=401)
		try:
			json_request = json.loads(request.body)
			if 'game' not in json_request:
				return JsonResponse({
					'status': 0,
					'message': "missing required field: {}".format('game')
					}, status=400)
			game = Game.objects.filter(game_name=json_request['game']).first()
			if not game:
				return JsonResponse({
					'status': 0,
					'message': f"Game {json_request['game']} does not exist"
					}, status=404)
			local = False
			if 'mode' in json_request:
				if json_request['mode'] != 'local':
					return JsonResponse({
					'status': 0,
					'message': 'Insupported mode'
					}, status=400)
				local = json_request['mode'] == 'local'
			try:
				with transaction.atomic():
					return func(request, user_data, game, json_request, local)
			except DatabaseError:
				return JsonResponse({
					'status': 0,
					'message': 'Invalid request'
					}, status=400)
		except json.decoder.JSONDecodeError:
			return JsonResponse({
				'status': 0,
				'message': 'Couldn\'t read input'
				}, status=400)
	return wrapper

def tournament_request(func):
	def wrapper(request: HttpRequest, user_data, game, json_request, local) -> JsonResponse:
		if 'tournament_id' in json_request:
			tournament = Tournament.objects.filter(tournament_id=json_request['tournament_id']).first()
			if not tournament:
				return JsonResponse({
					'status': 0,
					'message': f"Tournament {json_request['tournament_id']} does not exist"
					},
					status=404)
			return func(request, user_data, game, json_request, local, tournament)
		return func(request, user_data, game, json_request, local)
	return wrapper

def get_player_room(user_id, player_name="host"):
	# get the player room excluding tournament rooms.
	return PlayerRoom.objects.filter(
		player__user_id=int(user_id),
		player__player_name=player_name).exclude(
			game_room__in=Subquery(TournamentGameRoom.objects.values('game_room'))).first()

@check_request
def create_game(request: HttpRequest, user_data: dict, game: Game, game_request, local) -> JsonResponse:

	if not local:
		# reconnection
		room_player = get_player_room(user_data['user_id'], "host")

		# the player is already into a game room so do nothing.
		if room_player:
			return JsonResponse({
				'ip_address': os.environ.get('IP_ADDRESS'),
				'game_room_id': room_player.game_room.room_name,
				'status': 'playing',
				'player_id': room_player.player.player_name
				}, status=200)

	# rooms are filled one request at a time, otherwise num_players is lost
	# updates and rooms end up with more players than they allow.
	advisory_lock(f"room:{game.game_name}")

	if local:
		if 'guest_name' not in game_request:
			return JsonResponse({
				'status': 0,
				'message': "missing required field: {} for local mode".format('guest_name')
			}, status=400)
		# delete all guest tournaments
		guest_tournaments = Tournament.objects.filter(
		tournament_id__in=TournamentParticipant.objects.filter(
			player__is_guest=True,
			player__user_id=user_data['user_id']).values('tournament_id'))
		guest_tournaments.delete()
		guest_players = Player.objects.filter(user_id=user_data['user_id'], is_guest=True)
		if guest_players.count() >= 2:
			# delete players in other rooms
			Player.objects.filter(is_guest=True, user_id=user_data['user_id']).delete()
			guest_players.delete()
		player, created = Player.objects.get_or_create(
			player_name=game_request['guest_name'],
			user_id=int(user_data['user_id']),
			is_guest=True)
	else:
		player = get_host_player(user_data)

	# if the player is not found in any room, either assign it the oldest room that isn't full
	# or create a new room
	rooms = GameRoom.objects.filter(
		game__game_name=game_request['game'].lower(),
		num_players__lt=game.min_players).order_by('created_at').exclude(
			pk__in=Subquery(TournamentGameRoom.objects.values('game_room_id')
		))

	room = rooms.first()
	if room:
		room.num_players += 1
		room.save(update_fields=['num_players'])
		PlayerRoom(
			player=player,
			game_room=room,
			player_position=room.num_players - 1).save()
		return JsonResponse({
			'ip_address': os.environ.get('IP_ADDRESS'),
			'game_room_id': room.room_name,
			'status': 'joined',
			'player_id': player.player_name
			}, status=200)

	# create new room if room does not exist
	room = GameRoom(
		room_name=str(uuid.uuid4()),
		game=game,
		is_local=local)
	room.num_players += 1
	room.save()
	PlayerRoom(
		player=player,
		game_room=room,
		player_position=room.num_players - 1).save()
	return JsonResponse({
		'ip_address': os.environ.get('IP_ADDRESS'),
		'game_room_id': room.room_name,
		'status': 'created',
		'player_id': player.player_name
	}, status=201)

def add_player_to_room(player: Player, game_room: GameRoom) -> PlayerRoom:
	player_room = PlayerRoom(
		player=player,
		game_room=game_room,
		player_position=game_room.num_players)

	game_room.num_players += 1
	game_room.save(update_fields=['num_players'])
	player_room.save()
	return player_room

def create_game_room(player: Player, game: Game) -> GameRoom:
	# create new room, add the player to it
	game_room = GameRoom(room_name=str(uuid.uuid4()), game=game)
	game_room.save()
	# map player to game room.
	add_player_to_room(player, game_room)
	return game_room

def add_participant(
	player: Player,
	tournament: Tournament,
	is_host=False) -> TournamentParticipant:

	participant = TournamentParticipant(
		player=player,
		tournament=tournament,
		status="PLAYING",
		is_host=is_host)

	participant.tournament_position = tournament.participants
	tournament.participants += 1
	if tournament.participants == tournament.max_participants:
		tournament.closed = True
	tournament.save()
	participant.save()
	return participant

def tournament_response(
	player:Player,
	game_room:GameRoom,
	tournament: Tournament,
	internal_status: str,
	http_status: int) -> JsonResponse:
	return JsonResponse({
			'ip_address': os.environ.get('IP_ADDRESS'),
			'game_room_id': game_room.room_name,
			'status': internal_status,
			'player_id': player.user_id,
			'player_name': player.player_name,
			'tournament_id': tournament.tournament_id
		}, status=http_status)

def _join_tournament(
	game: Game,
	player: Player,
	tournament: Tournament,
	participant: TournamentParticipant=None) -> JsonResponse:
	advisory_lock(f"tournament:{tournament.tournament_id}")

	# join the tournament by either reconnecting,
	# joining a room or create a new room.

	if not participant:
		game_rooms_in_tournament = TournamentGameRoom.objects.filter(
			tournament=tournament
			).values_list('game_room', flat=True)
	else:
		# the tournament room that matches the round of the participant.
		game_rooms_in_tournament = TournamentGameRoom.objects.filter(
			tournament=tournament,
			tournament_round=participant.tournament_round,
			).values_list('game_room', flat=True)

	player_room = PlayerRoom.objects.filter(
		player=player,
		game_room__in=game_rooms_in_tournament).first()

	# if player is already in a room return it (reconnecting him to the room)
	if player_room:
		return tournament_response(player, player_room.game_room, tournament, 'playing', 200)

	if not participant:
		add_participant(player, tournament)

	# get the oldest game_room in the tournament that isn't full
	game_room = GameRoom.objects.filter(
		room_name__in=game_rooms_in_tournament,
		num_players__lt=game.min_players
		).order_by('created_at').first()

	if not game_room:
		game_room = create_game_room(player, game)
		if tournament:
			# map game room to tournament.
			tgame_room = TournamentGameRoom(tournament=tournament, game_room=game_room)
			if participant:
				tgame_room.tournament_round = participant.tournament_round
			tgame_room.save()
		return tournament_response(player, game_room, tournament, 'created', 201)
	add_player_to_room(player, game_room)
	return tournament_response(player, game_room, tournament, 'joined', 200)

def _create_tournament(player: Player, game:Game, max_participants=MAX_TOURNAMENT_PARTICIPANTS, local=False) -> GameRoom:
	tournament = Tournament(
		game=game,
		tournament_id=str(uuid.uuid4()),
		max_participants=max_participants,
		local=local)
	game_room = create_game_room(player, game)
	# don't add the player if it is in local mode, it will be added as a guest after.
	add_participant(player, tournament, True)
	# map game room to tournament
	tgame_room = TournamentGameRoom(
		tournament=tournament,
		game_room=game_room)
	tgame_room.save()
	return tournament, game_room

def create_or_join_tournament(player: Player, game:Game, max_participants=MAX_TOURNAMENT_PARTICIPANTS, local=False) -> JsonResponse:
	advisory_lock(f"tournament-queue:{game.game_name}:{local}")
	# if the player is not a participant,
	# try to join the oldest tournament that isn't full.
	tournament = Tournament.objects.filter(
		game__game_name=game.game_name,
		closed=False,
		participants__lt=max_participants,
		local=local).order_by('created_at').first()

	# if there is no tournament, create a new one and a new game room.
	if not tournament:
		tournament, game_room = _create_tournament(player, game)
		return tournament_response(player, game_room, tournament, 'created', 201)
	return _join_tournament(game, player, tournament)

@check_request
def create_tournament_view(request: HttpRequest, user_data: dict, game:Game, json_request, local) -> JsonResponse:
	'''
	NOTE: if it is a named tournament, it becomes public.
	'''
	if not local:
		return JsonResponse({
			'status': 0,
			'message': f"Can only create local tournaments"
			},
			status=400)

	# delete all guest players and guest tournaments
	guest_tournaments = Tournament.objects.filter(
		tournament_id__in=TournamentParticipant.objects.filter(
			player__is_guest=True,
			player__user_id=user_data['user_id']).values('tournament_id'))
	guest_tournaments.delete()
	# delete all previous users
	Player.objects.filter(is_guest=True, user_id=user_data['user_id']).delete()
	if not 'max_players' in json_request:
		return JsonResponse({
				'status': 0,
				'message': f"Missing required field: max_players"
				},
				status=400)
	player = get_host_player(user_data)
	try:
		max_players = int(json_request['max_players'])
		# check if the max amount of players is a power of 2 and is at least for and at most 16
		if not (max_players > 3 and (max_players & (max_players - 1)) == 0 and max_players < 17):
			return JsonResponse({
			'status': 0,
			'message': f"Invalid amount of players, should be one of 4, 8 or 16"},
			status=400)
		tournament = Tournament(
			game=game,
			tournament_id=str(uuid.uuid4()),
			max_participants=max_players,
			local=local
		)
		tournament.save()
		return JsonResponse({
			"tournament_id": tournament.tournament_id
		})
	except ValueError:
		return JsonResponse({
			'status': 0,
			'message': f"max_players is not an integer"},
			status=400)

@check_request
@tournament_request
def get_tournament_room(request: HttpRequest, user_data: dict, game:Game, json_request, local, tournament: Tournament) -> JsonResponse:
	'''
	returns the earliest active room of round r of tournament t. If none is found, returns a 404
	'''
	try:
		if not 'round' in json_request:
			return JsonResponse({
				'status': 0,
				'message': f"Missing required field: round"},
				status=400)
		current_round = int(json_request['round'])
		if current_round > 3 and current_round < 0:
			return JsonResponse({
				'status': 0,
				'message': f"Invalid round number"},
				status=400)
		earliest_room = TournamentGameRoom.objects.filter(
			tournament=tournament.tournament_id,
			game_room__closed=False).order_by('game_room__created_at').first()
		if not earliest_room:
			try:
				tournament.delete()
			except Exception as e:
				pass
			return JsonResponse({
			'status': 0,
			'message': f"No more rooms for current round"},
			status=404)
		players = [player for player in PlayerRoom.objects.filter(game_room=earliest_room.game_room).order_by('player_position')]
		if not players:
			return JsonResponse({
			'status': 0,
			'message': f"room is empty"},
			status=400)
		if len(players) < 2:
			try:
				tournament.delete()
			except Exception as e:
				pass
			return JsonResponse({
			'status': 0,
			'message': f"No more rooms for current round"},
			status=404)
		print("EARLIEST ROOM", earliest_room.tournament_round, flush=True)
		return JsonResponse({
			'ip_address': os.environ.get('IP_ADDRESS'),
			'game_room_id': earliest_room.game_room.room_name,
			'status': 'playing',
			'player1': players[0].player.player_name,
			'player2': players[1].player.player_name,
			'player1_position': players[0].player_position,
			'player2_position': players[1].player_position,
			'round': earliest_room.tournament_round
		})
	except ValueError as e:
		return JsonResponse({
			'status': 0,
			'message': f"round is not an integer"},
			status=400)

@check_request
@tournament_request
def	find_tournament_view(request: HttpRequest, user_data: dict, game: Game, json_request, local, tournament=None) -> JsonResponse:
	if not local:
		player = get_host_player(user_data)
	else:
		player, created = Player.objects.get_or_create(
			is_guest=True,
			player_name=json_request["guest_name"],
			user_id=int(user_data['user_id']))

	participant = TournamentParticipant.objects.filter(player=player).first()
	# ================== RECONNECT OR MOVE TO THE NEXT ROUND ========================
	if participant:
		if participant.status == "ELIMINATED" or participant.status == "WINNER":
			# if a tournament is provided
			if tournament:
				return JsonResponse({
					'status': 0,
					'message': f"Cannot join tournament reason: {participant.status}"},
					status=400)
			return create_or_join_tournament(player, game)
		elif participant.status == "PLAYING":
			return _join_tournament(game, player, participant.tournament, participant)
	# join tournament if provided
	if tournament:
		if tournament.closed:
			return JsonResponse({
				'status': 0,
				'message': f"Cannot join tournament reason: tournament is closed"
			},
			status=400)
		return _join_tournament(game, player, tournament)
	# creates a random tournament and puts player in it.
	return create_or_join_tournament(player, game)

def game_stats(request: HttpRequest, user_id : int) -> JsonResponse:
	if request.method != 'GET':
		return JsonResponse({'status': 0, 'message': 'Only GET method is allowed'}, status=405)

	# the player never played a game
	if not Player.objects.filter(user_id=user_id, player_name="host").exists():
		return JsonResponse({'status': 0, 'message': 'Player never played'}, status=200)

	player = Player.objects.get(user_id=user_id, player_name="host")

	list_games = Game.objects.all()
	if list_games.count() == 0:
		return JsonResponse({'status': 0, 'message': 'No game found'}, status=404)

	response_data = {'status': 1}
	nb_games = 0
	for game in list_games:
		games_won = GameResult.objects.filter(winner=player, game=game)
		games_lost = GameResult.objects.filter(loser=player, game=game)

		win_count = games_won.count()
		loss_count = games_lost.count()
		if win_count + loss_count == 0:
			response_data[game.game_name] = {
				'total_games': 0
			}
			continue
		nb_games += 1

		games_data = []
		total_points = 0
		total_total_points = 0
		playtime = 0
		for result in games_won.union(games_lost):
			total_points += result.winner_score if result.winner == player else result.loser_score
			total_total_points += result.winner_score + result.loser_score
			playtime += result.game_duration
			games_data.append({
				'is_winner': result.winner == player,
				'opponent_id': result.loser.user_id if result.winner == player else result.winner.user_id,
				'personal_score': result.winner_score if result.winner == player else result.loser_score,
				'opponent_score': result.loser_score if result.winner == player else result.winner_score,
				'game_date': result.game_date,
				'game_duration': str(datetime.timedelta(seconds=result.game_duration))
			})

		playtime = str(datetime.timedelta(seconds=playtime))
		# maybe add average score, average duration
		response_data[game.game_name] = {
			'total_games': win_count + loss_count,
			'total_wins': win_count,
			'average_score': round(total_points / (win_count + loss_count), 1),
			'playtime' : playtime,
			'win_percentage': round(win_count / (win_count + loss_count) * 100, 1),
			'games': games_data
		}
		if game.game_name == 'pong':
			response_data[game.game_name]["precision"] = round(total_points / total_total_points * 100, 1)
		elif game.game_name == 'snake':
			response_data[game.game_name]["high_score"] = max([data['personal_score'] for data in games_data])

	if nb_games == 0:
		return JsonResponse({'status': 0, 'message': 'Player never played'}, status=200)
	return JsonResponse(response_data, status=200)

@csrf_exempt
def advance(request: HttpRequest) -> JsonResponse:
	'''
	Internal (game-server -> matchmaking): a player won a round, move them to the next
	round of the tournament and put them in a room. Blocked from outside by the proxy.
	'''
	if request.method != 'POST':
		return JsonResponse({'status': 0, 'message': 'Only POST method is allowed'}, status=405)
	try:
		body = json.loads(request.body)
		tournament_id = body['tournament_id']
		player_id = body['player_id']
		if not isinstance(tournament_id, str) or not isinstance(player_id, int):
			raise ValueError
	except (ValueError, KeyError, TypeError):
		return JsonResponse({'status': 0, 'message': 'Invalid body'}, status=400)

	with transaction.atomic():
		participant = TournamentParticipant.objects.select_related(
			'player', 'tournament__game').filter(
				tournament_id=tournament_id, player_id=player_id).first()
		if not participant:
			return JsonResponse({'status': 0, 'message': 'Participant not found'}, status=404)
		participant.tournament_round += 1
		participant.save(update_fields=['tournament_round'])
		# creates or joins a room in the tournament.
		_join_tournament(
			participant.tournament.game,
			participant.player,
			participant.tournament,
			participant)
	return JsonResponse({'status': 1})
