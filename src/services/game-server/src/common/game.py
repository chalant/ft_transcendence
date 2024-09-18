import json
import abc
import asyncio
import os
import django
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import BaseChannelLayer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from common import auth_client as auth
from games.models import (
	Player,
	PlayerRoom, 
	GameResult, 
	TournamentGameRoom, 
	GameRoom, 
	Tournament, 
	TournamentParticipant)

@database_sync_to_async
def get_player_room(user_id, game_room):
    return PlayerRoom.objects.filter(
        player__player_id=user_id,
        game_room__room_name=game_room).first()

@database_sync_to_async
def get_player_room_player(player_room):
    return player_room.player

@database_sync_to_async
def get_player_room_player_id(player_room):
    return player_room.player.player_id

@database_sync_to_async
def get_expected_players(player_room):
    return player_room.game_room.expected_players

@database_sync_to_async
def get_player_id(player_room):
    return player_room.player.player_id

@database_sync_to_async
def set_player_position(player_room, position):
	player_room.player_position = position
	player_room.save()

@database_sync_to_async
def get_player_position(player_room):
	return player_room.player_position

@database_sync_to_async
def get_player_game_room(player_room):
	return player_room.game_room

@database_sync_to_async
def get_game_room_game(game_room):
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
	game_room.delete()

@database_sync_to_async
def store_game_result(game_result):
	game_result.save()

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
def get_tournament_room_tournament_id(tournament_room: TournamentGameRoom) -> str:
	return tournament_room.tournament.tournament_id

@database_sync_to_async
def get_game_room(room_name: str) -> GameRoom:
	return GameRoom.objects.filter(room_name=room_name).first()

@database_sync_to_async
def get_tournament(tournament_id: str) -> GameRoom:
	return Tournament.objects.filter(tournament_id=tournament_id).first()

class GameSession(object):
	def __init__(self, game_logic, game_server, game_room, game_mode=None, pause_timeout=60):
		self._game_logic = game_logic
		self.current_players = 0
		self._game_room = game_room
		self._game_server = game_server
		self._session_id = game_room.room_name
		self._game_mode = game_mode
		self._end_callbacks = []
		self._connection_lost_callbacks = []
		self._pause_event = asyncio.Event()
		self._pause_event.set()
		self._timeout = pause_timeout
		self.is_running = True
		self._players = [None, None]
		self._game_result = GameResult()

	def set_player(self, position, player):
		self._players[position] = player
	
	def get_player(self, position):
		return self._players[position]

	async def update(self, data, player):
		await self._game_logic.update(data, player)

	async def start(self, callback):
		await callback(await self._game_logic.startEvent())
		t0 = time.time()
		while self.is_running:
			await asyncio.gather(
				self.game_loop(callback),
				asyncio.sleep(0.03)) # about 30 loops/second
		self._game_result.game_duration = time.time() - t0
		await store_game_result(self._game_result)
		await delete_game_room(self._game_room)

	async def game_loop(self, callback):
		try:
			await asyncio.wait_for(self._pause_event.wait(), self._timeout)
		except asyncio.TimeoutError:
			for end in self._connection_lost_callbacks:
				await end()
			await set_in_session(self._game_room, False)
			# TODO: handle results storage on connection lost.
			# TODO: on connection lost, game results should be stored 
			# by the game consumers.
			#await store_game_result(game_result)
			return
		data = await self._game_logic.gameTick()
		await callback(data)
		async for data in self._game_logic.sendEvent():
			if data["type"] == "win":
				self._game_server.remove_session(self._session_id)
				await set_in_session(self._game_room, False)
				# todo: store game results and delete the game room
				self._game_result.winner = self._players[data["player"]]
				self._game_result.loser = self._players[data["loser"]]
				self._game_result.winner_score = data["score"][data["player"]]
				self._game_result.loser_score = data["score"][data["loser"]]
				self._game_result.game = await get_game_room_game(self._game_room)
				data = await self._game_mode.handle_end_game(data, self._game_result)
				for end in self._end_callbacks:
					await end(data)
				self.is_running = False
				return
			await callback(data)
			await asyncio.sleep(0.001)

	def on_session_end(self, callback):
		self._end_callbacks.append(callback)
	
	def remove_callback(self, event, callback):
		try:
			if event == 'session-end':
				self._end_callbacks.remove(callback)
			elif event == 'connection-lost':
				self._connection_lost_callbacks.remove(callback)
		except ValueError:
			pass

	def on_connection_lost(self, callback):
		self._connection_lost_callbacks.append(callback)

	def pause(self):
		self._pause_event.clear()

	def resume(self):
		self._pause_event.set()

class QuickGameMode(object):
	def __init__(self, channel_layer: BaseChannelLayer) -> None:
		self.channel_layer = channel_layer

	async def ready(self, session: GameSession, room_name: str, game_room: GameRoom, state_callback) -> None:
		await self.channel_layer.group_send(
		room_name,
		{
			'type': 'game_status',
			'message': {
				'status': 'ready'
				}
		})
		if not await in_session(game_room):
			asyncio.create_task(session.start(state_callback))
			session.resume()
			await set_in_session(game_room, True)
			return
		# resume game in case it paused.
		session.resume()

	async def handle_end_game(self, data, game_result):
		return data
	
	async def handle_disconnection(self):
		pass

class TournamentMode(object):
	def __init__(self, tournament: Tournament, tournament_id, channel_name, channel_layer: BaseChannelLayer) -> None:
		self._tournament = tournament
		self.channel_layer = channel_layer
		self._channel_name = channel_name
		self._ready = False
		self._tournament_id = tournament_id

	async def ready(self, session: GameSession, room_name: str, game_room: GameRoom, state_callback) -> None:
		closed = await tournament_is_closed(self._tournament)
		if not closed:
			await self.channel_layer.group_send(
				room_name,
				{
					'type': 'game_status',
					'message': {
						'status': 'waiting'
						}
				})
			return
		game_room = await get_game_room(room_name)
		if not game_room:
			return
		await self.channel_layer.group_send(
			room_name,
			{
				'type': 'game_status',
				'message': {
					'status': 'ready'
					}
			})
		if not await in_session(game_room):
			asyncio.create_task(session.start(state_callback))
			session.resume()
			await set_in_session(game_room, True)
			return
		# resume game in case it paused.
		session.resume()

	async def handle_end_game(self, data: dict, game_result: GameResult):
		tournament = await get_tournament(self._tournament_id)
		await eliminate_player(game_result.loser, tournament)
		remaining_players = await get_remaining_participants(tournament)
		if remaining_players == 1:
			await set_tournament_winner(game_result.winner, tournament)
			await delete_tournament(tournament)
			data["type"] = "win"
			return data
		await qualify_player(game_result.winner, tournament)
		data["type"] = "round"
		return data
	
	async def handle_disconnection(self):
		self.channel_layer.group_discard(
			self._tournament_id,
			self._channel_name
		)

class GameServer(object):
	def __init__(self, game_factory):
		self._game_sessions = {}
		self._rooms = []
		self._lock = asyncio.Lock()
		self._game_factory = game_factory

	def get_game_session(self, game_room, game_mode, pause_timeout=10) -> GameSession:
		if game_room.room_name not in self._game_sessions:
			self._game_sessions[game_room.room_name] = GameSession(
				self._game_factory(),
				self,
				game_room,
				game_mode,
				pause_timeout) # create new game logic for the game room.
		return self._game_sessions[game_room.room_name]
	
	def remove_session(self, session_id):
		if session_id in self._game_sessions:
			del self._game_sessions[session_id]

	async def __aenter__(self):
		await self._lock.acquire()
		return self

	async def __aexit__(self, exc_type, exc_value, exc_tb):
		self._lock.release()

class GameLogic(abc.ABC):
	@abc.abstractmethod
	async def startEvent():
		pass
	async def gameTick():
		pass
	async def update(data, player):
		pass
	async def sendEvent():
		pass

class GameConsumer(AsyncWebsocketConsumer):
	def __init__(self, game_server: GameServer, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._game_server = game_server
		self._game_session = None
		self.disconnected = False
		self._lost_connection = False
	
	async def send_json(self, data: dict):
		await self.send(text_data=json.dumps(data))

	async def state_callback(self, data):
		await self.channel_layer.group_send(
				self.room_name, 
				{
					'type': 'game_state',
					'message': data
				}
			)

	'''
	TODO: BUG when the same player joins the game from two windows it still works 
	(the same player gets in the session twice) !!!
	'''

	async def connect(self):
		self.room_name = room_name = self.scope['url_route']['kwargs']['room_name']
		query_string = self.scope.get('query_string').decode('utf-8')
		params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
		token = params.get('token')
		csrf = params.get('csrf_token')

		if not token and not csrf:
			# If the room does not exist, close the connection
			await self.accept()
			await self.send_json({
				"type": "websocket.close",
				"code": 4000,  # Custom close code
				"reason": "Tokens are missing."
			})
			await self.close()
			return

		user = auth.get_user_with_token(token, csrf)
		if not user:
			# If the room does not exist, close the connection
			await self.accept()
			await self.send_json({
				"type": "websocket.close",
				"code": 4000,  # Custom close code
				"reason": "Invalid tokens."
			})
			self.close()
			return

		self.player_room = player_room = await get_player_room(
			user['user_id'], 
			room_name)
		''' 
		TODO: check if the game room is in local mode if so, the game should start right away.
				  the opponent should already be present in the game room (after calling the api)
		'''
		if not player_room:
			await self.accept()
			await self.send_json({
				"type": "websocket.close",
				"code": 4000,  # Custom close code
				"reason": "Player has no game room."
			})
			self.close()
			return

		self.game_room = await get_player_game_room(self.player_room)
		self._expected_players = expected_players = await get_min_players(self.game_room)

		# check if the game room is in a tournament room.
		tournament_room = await get_tournament_room(self.game_room)
		if tournament_room:
			# add channel to tournament group.
			tournament_id = await get_tournament_room_tournament_id(tournament_room)
			self._game_mode = game_mode = TournamentMode(
				await get_tournament_room_tournament(tournament_room),
				tournament_id,
				self.channel_name,
				self.channel_layer
			)
			# notify all consumers that there is a new participant.
			await self.channel_layer.group_send(
				tournament_id,
				{
					'type': 'tournament_message',
					'message': {
						'subject': 'participant'
					}
				}
			)
			# add this channel to the group.
			await self.channel_layer.group_add(
				tournament_id,
				self.channel_name
			)
		else:
			self._game_mode = game_mode = QuickGameMode(self.channel_layer)
		await self.channel_layer.group_add(self.room_name, self.channel_name)
		# TODO: (fix for same player reconnection )store the channel name in the database. along with the player_id.
		# if there is match, close the previous channel. decrement current players.
		# previous_channel_name = await self.get_channel(self.client_id)
        # if previous_channel_name:
        #     # If a previous connection exists, send a disconnect message
        #     await self.channel_layer.send(
        #         previous_channel_name,
        #         {
        #             "type": "disconnect.old_connection",
        #         }
        #     )

        # # Store this connection's channel_name for the client
        # await self.set_channel(self.client_id, self.channel_name)

        # # Accept the new connection
        # await self.accept()

		# TODO: when in local mode, the game starts right away, no need to wait for other players.
		# create new game session if none exists.
		async with self._game_server as server:
			session = server.get_game_session(self.game_room, game_mode)
			# if the amount of players is met, notify all clients.
			self.player_position = await get_player_position(player_room)
			# if session.get_player(self.player_position):
			# 	pass
			session.current_players += 1
			session.set_player(self.player_position, await get_player_room_player(player_room))
			# TODO: also check against num_players in the game room (if it is one, there is an issue)
			session.on_session_end(self.flush_game_session)
			session.on_connection_lost(self.connection_lost)
			self._game_session = session
			if session.current_players == expected_players:
				await self.accept()
				await game_mode.ready(
					session, self.room_name, 
					self.game_room, self.state_callback)
			elif session.current_players < expected_players:
				await self.accept()
				await self.channel_layer.group_send(
				self.room_name,
				{
					'type': 'game_status',
					'message': {
						'status': 'waiting'
						}
				})

	async def flush_game_session(self, data):
		if data['player'] == self.player_position:
			data = {'type': 'end', 'context': data['type'], 'status': 'win'}
		else:
			data = {'type': 'end', 'context': data['type'], 'status': 'lost'}
		await self.send(text_data=json.dumps(data))
		await self.channel_layer.group_discard(self.room_name, self.channel_name)
		# TODO: close connection here.
		await self.disconnect(0)

	async def connection_lost(self):
		if not self.disconnected:
			# todo: also need to send that a player disconnected.
			await self.send_json({'type': 'end', 'status': 'win'})
			await self.close()
		self._lost_connection = True
		# todo: need to delete the game room...
		await self.channel_layer.group_discard(self.room_name, self.channel_name)

	# todo: notify the game loop to pause the game
	async def disconnect(self, close_code):
		async with self._game_server as server:
			session = server.get_game_session(self.game_room, self._game_mode)
			# todo: if both players disconnected, end the game
			if session.current_players > 0:
				session.current_players -= 1
			session.remove_callback(
				'session-end',
				self.flush_game_session)
			session.pause()
			# todo: send a message to clients when a player disconnects.
			await self.channel_layer.group_discard(self.room_name, self.channel_name)
			await self._game_mode.handle_disconnection()
			self.disconnected = True
			# TODO: delete player room -> if there is only one player in the GameRoom.

	# receives data from websocket.
	async def receive(self, bytes_data):
		if self.disconnected:
			return
		if self._game_session:
			await self._game_session.update(bytes_data, self.player_position)
		else:
			await self.channel_layer.group_send(
				self.room_name,
				{
					'type': 'game_state',
					'message': {'status': 'no session'}
				}
			)

	async def game_state(self, event):
		await self.send(text_data=json.dumps(event['message']))

	async def game_status(self, event):
		await self.send(text_data=json.dumps(event['message']))
	
	async def tournament_message(self, event):
		# attempt to launch tournament.
		async with self._game_server:
			await self._game_mode.ready(
				self._game_session, 
				self.room_name, 
				self.game_room, 
				self.state_callback)
		# TODO: send all participants to clients.
