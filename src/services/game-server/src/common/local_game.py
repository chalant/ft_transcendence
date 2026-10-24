import json
import os
import django


from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import BaseChannelLayer

from common.db_utils import (
	get_player_room,
	get_player_game_room,
	get_player_position,
	get_player_room_player,
	get_game_room,
	delete_game_room,
	delete_guest_players_in_room,
	delete_guest_players_in_tournament
)

from common.game_session import GameSession

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

class LocalMode(object):
	def __init__(self,
		game_server,
		player_ids: list,
		room_name: str,
		host_user_id: str,
		channel_layer: BaseChannelLayer,
		consumer: AsyncWebsocketConsumer) -> None:

		self._player_ids = player_ids
		self._game_server = game_server
		self.channel_layer = channel_layer
		self.consumer = consumer
		self.room_name = room_name
		self.game_room = None
		self._player_room = None
		self._loaded = False
		self._players_positions = [0, 1]
		self._host_user_id = int(host_user_id)
		self._game_session = None
		self._disconnected = False
		self._player_rooms = [None, None]
		self.game_mode = None

	async def _load_players(self):
		self._player_rooms[0] = player1_room = await get_player_room(
			self._host_user_id,
			self.room_name,
			self._player_ids[0])
		if not player1_room:
			return False
		self._player_rooms[1] = player2_room = await get_player_room(
			self._host_user_id,
			self.room_name,
			self._player_ids[1])
		if not player2_room:
			return False
		self._loaded = True
		return self._loaded

	async def validate_player(self):
		if not await self._load_players():
			return False
		return True

	async def get_game_room(self):
		if not self._player_room:
			self._player_room = await get_player_room(
				self._host_user_id,
				self.room_name,
				self._player_ids[0])
		self.game_room = await get_player_game_room(self._player_room)
		return self.game_room

	async def state_callback(self, data):
		await self.channel_layer.group_send(
				self.room_name,
				{
					'type': 'game_state',
					'message': data
				})

	async def start_session(self, game_mode, state_callback):
		if not self._loaded:
			await self._load_players()
		async with self._game_server as server:
			if not self.game_room:
				self.game_room = await self.get_game_room()
			session = server.get_game_session(self.game_room, game_mode)
			session.current_players = 2
			for i, player_room in enumerate(self._player_rooms):
				position = await get_player_position(player_room)
				session.set_player(
					position,
					await get_player_room_player(player_room))
				self._players_positions[i] = position
				session.add_consumer(i, self)
			self._game_session = session
			await game_mode.ready(
				session, self.room_name,
				self.game_room, state_callback)

	async def update(self, bytes_data):
		if self._disconnected:
			return
		session = self._game_session
		# update for the given position.
		await session.update(
			bytes_data,
			self._players_positions[int(bytes_data[3])])

	# in local mode there is no waiting time.
	async def tournament_message(self, event, game_mode):
		pass

	async def flush_game_session(self, data):
		# just send the winner to client in local mode.
		for position in self._players_positions:
			player = await get_player_room_player(self._player_rooms[position])
			if data['player'] == position:
				data = {
					'type': 'end',
					'context': data['type'],
					'status': 'win',
					'winner': position,
					'player_name': player.player_name if player.is_guest else player.user_name,
					'player_id': player.user_id
					}
				await self.consumer.send(text_data=json.dumps(data))
				break

	async def connection_lost(
			self, session: GameSession,
			game_mode, data: dict, game_result):
		await self.cleanup_data(tournament=game_mode.tournament)

	async def cleanup_data(self, room_closed=False, tournament=None):
		if tournament:
			await delete_guest_players_in_tournament(self._host_user_id, tournament)
			return
		await delete_guest_players_in_room(self._host_user_id, self.room_name, room_closed)

	async def disconnect(self, channel_name, channel_layer, game_mode):
		self._loaded = False
		self._disconnected = True
		async with self._game_server as server:
			game_room = await get_game_room(self.room_name)
			if game_room:
				session = server.get_game_session(game_room, game_mode)
				session.remove_consumer(0, self)
				server.remove_session(session._session_id)
				await delete_game_room(game_room)
			await channel_layer.group_discard(self.room_name, self.consumer.channel_name)