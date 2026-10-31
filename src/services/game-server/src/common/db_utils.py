from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import BaseChannelLayer

from games.models import (
	Game,
	Player,
	PlayerRoom,
	TournamentGameRoom,
	GameRoom,
	Tournament,
	TournamentParticipant)

from games.views import _join_tournament

@database_sync_to_async
def get_player_room(user_id: str, game_room: str, player_name="host") -> PlayerRoom:
	return PlayerRoom.objects.filter(
		player__player_name=player_name,
		player__user_id=user_id,
		game_room__room_name=game_room).first()

@database_sync_to_async
def leave_game_room(player: Player, game_room: GameRoom):
	PlayerRoom.objects.filter(player=player, game_room=game_room).delete()
	game_room.num_players -= 1
	game_room.save(update_fields=['num_players'])

@database_sync_to_async
def get_tournament_room_name(tournament_room: TournamentGameRoom) -> str:
	return tournament_room.game_room.room_name

@database_sync_to_async
def get_tournament_player_room(player: Player, rooms):
	return PlayerRoom.objects.filter(
		player=player,
		game_room__in=rooms).first()

@database_sync_to_async
def get_player_room_player(player_room: PlayerRoom) -> Player:
	return player_room.player

@database_sync_to_async
def get_player_room_player_id(player_room: PlayerRoom) -> int:
	return player_room.player.player_id

@database_sync_to_async
def get_expected_players(player_room: PlayerRoom) -> int:
	return player_room.game_room.expected_players

@database_sync_to_async
def get_player_id(player_room: PlayerRoom) -> int:
	return player_room.player.player_id

@database_sync_to_async
def set_player_position(player_room: PlayerRoom, position: int) -> None:
	player_room.player_position = position
	player_room.save()

@database_sync_to_async
def get_player_position(player_room: PlayerRoom) -> int:
	return player_room.player_position

@database_sync_to_async
def get_player_game_room(player_room: PlayerRoom) -> GameRoom:
	return player_room.game_room

@database_sync_to_async
def get_game_room_game(game_room: GameRoom) -> Game:
	return game_room.game

@database_sync_to_async
def set_in_session(game_room, value: bool):
	game_room.in_session = value
	# ! important ! it is important to spefify that this is the only field that needs to be updated
	# otherwise the game room data gets overwritten with old data
	game_room.save(update_fields=['in_session'])

@database_sync_to_async
def set_player_count(game_room, value: int):
	game_room.player_count = value
	game_room.save()

@database_sync_to_async
def in_session(game_room):
	return game_room.in_session

@database_sync_to_async
def get_min_players(game_room):
	return game_room.game.min_players

@database_sync_to_async
def delete_game_room(game_room):
	if game_room:
		game_room.delete()

@database_sync_to_async
def store_game_result(game_result):
	game_result.save()

@database_sync_to_async
def get_tournament_room(game_room: GameRoom) -> TournamentGameRoom:
	return TournamentGameRoom.objects.filter(game_room=game_room).first()

@database_sync_to_async
def get_tournament_room(game_room: GameRoom) -> TournamentGameRoom:
	return TournamentGameRoom.objects.filter(game_room=game_room).first()

@database_sync_to_async
def get_tournament_room_tournament(tournament_room: TournamentGameRoom) -> Tournament:
	return tournament_room.tournament

@database_sync_to_async
def get_remaining_participants(tournament: Tournament) -> int:
	return TournamentParticipant.objects.filter(status="PLAYING", tournament=tournament).count()

@database_sync_to_async
def qualify_player(player: Player, tournament: Tournament) -> None:
	participant = TournamentParticipant.objects.filter(player=player, tournament=tournament).first()
	participant.tournament_round += 1
	participant.save(update_fields=['tournament_round'])
	# creates or joins a room in the tournament.
	_join_tournament(tournament.game, player, tournament, participant)

@database_sync_to_async
def get_tournament_participant(player: Player, tournament: Tournament) -> None:
	return TournamentParticipant.objects.filter(
		player=player, tournament=tournament).first()

@database_sync_to_async
def eliminate_player(player: Player, tournament: Tournament) -> TournamentParticipant:
	participant = TournamentParticipant.objects.filter(player=player, tournament=tournament).first()
	participant.status = "ELIMINATED"
	participant.save(update_fields=["status"])
	return participant

@database_sync_to_async
def set_tournament_winner(player: Player, tournament: Tournament) -> TournamentParticipant:
	participant = TournamentParticipant.objects.filter(player=player, tournament=tournament).first()
	participant.status = "WINNER"
	participant.save(update_fields=["status"])
	return participant

@database_sync_to_async
def delete_tournament(tournament: Tournament) -> None:
	if tournament:
		tournament.delete()

@database_sync_to_async
def close_tournament(tournament: Tournament) -> Tournament:
	tournament.closed = True
	tournament.save(update_fields=['closed'])

@database_sync_to_async
def tournament_is_closed(tournament: Tournament) -> bool:
	tournament = Tournament.objects.filter(tournament_id=tournament.tournament_id).first()
	return tournament.closed

@database_sync_to_async
def get_room_num_players(room: GameRoom) -> int:
	return room.num_players

@database_sync_to_async
def get_tournament_room_tournament_id(tournament_room: TournamentGameRoom) -> str:
	return tournament_room.tournament.tournament_id

@database_sync_to_async
def get_game_room(room_name: str) -> GameRoom:
	return GameRoom.objects.filter(room_name=room_name).first()

@database_sync_to_async
def get_tournament(tournament_id: str) -> GameRoom:
	return Tournament.objects.filter(tournament_id=tournament_id).first()

@database_sync_to_async
def delete_guest_player(player: Player) -> int:
	Player.objects.filter(
		is_guest=True, 
		player_name=player.player_name, 
		user_id=player.user_id).delete()

@database_sync_to_async
def delete_guest_players_in_room(user_id: int, room_name:str, closed=True) -> int:
	rooms = PlayerRoom.objects.filter(game_room__room_name=room_name, game_room__closed=closed).values_list('player_id', flat=True)
	Player.objects.filter(is_guest=True, user_id=user_id, id__in=rooms).delete()

@database_sync_to_async
def delete_guest_players_in_tournament(user_id: int, tournament: Tournament) -> int:
	tournament_rooms = TournamentGameRoom.objects.filter(tournament=tournament).values_list('game_room', flat=True)
	rooms = PlayerRoom.objects.filter(game_room__in=tournament_rooms).values_list('player_id', flat=True)
	deleted, _ = Player.objects.filter(is_guest=True, user_id=user_id, id__in=rooms).delete()

@database_sync_to_async
def close_game_room(game_room: GameRoom) -> None:
	game_room.closed = True
	game_room.save(update_fields=['closed'])

@database_sync_to_async
def get_participant_player(participant: TournamentParticipant):
	return participant.player

@database_sync_to_async
def remove_participant(tournament: Tournament, player: Player):
	TournamentParticipant.objects.filter(tournament=tournament, player=player).delete()

@database_sync_to_async
def update_tournament(tournament: Tournament, fields):
	tournament.save(update_fields=fields)

@database_sync_to_async
def player_at_position(room_name: str, position: int):
	room = PlayerRoom.objects.filter(
		game_room__room_name=room_name,
		player_position=position).first()
	if room:
		return room.player
	return
