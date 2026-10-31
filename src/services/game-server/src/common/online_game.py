import json

from channels.layers import BaseChannelLayer
from channels.generic.websocket import AsyncWebsocketConsumer

from common.db_utils import (
	get_player_room,
	get_player_game_room,
	get_min_players,
	get_player_position,
	get_player_room_player,
	store_game_result
)

from games.models import GameResult
from common.game_session import GameSession

class OnlineMode(object):
	def __init__(self,
		game_server,
		user: dict,
		room_name: str,
		channel_layer: BaseChannelLayer,
		consumer: AsyncWebsocketConsumer) -> None:

		self._game_server = game_server
		self._player_room = None
		self._user = user
		self.game_room = None
		self.room_name = room_name
		self.channel_layer = channel_layer
		self.consumer = consumer
		self._lost_connection = False
		self._disconnected = False
		self.player_position = 0
		self._game_session = None
		self._players = [None, None]
		self.game_mode = None

	async def validate_player(self):
		if not self._player_room:
			self._player_room = player_room = await get_player_room(
				self._user['user_id'],
				self.room_name)
			if not player_room:
				return False
		return True

	async def get_game_room(self):
		if not self._player_room:
			self._player_room = await get_player_room(
				self._user['user_id'],
				self.room_name)
		self.game_room = await get_player_game_room(self._player_room)
		return self.game_room

	async def state_callback(self, data):
		await self.channel_layer.group_send(
			self.room_name, {
				'type': 'game_state',
				'message': data
			})

	async def start_session(self, game_mode, state_callback):
		player_room = self._player_room
		if not player_room:
			await self.get_game_room()
		expected_players = await get_min_players(self.game_room)
		async with self._game_server.room_lock(self.room_name):
			session = self._game_server.get_game_session(self.game_room, game_mode)
			# if the amount of players is met, notify all clients.
			self.player_position = await get_player_position(player_room)
			self.player = await get_player_room_player(player_room)
			session.add_consumer(self.player_position, self)
			self._game_session = session
			if session.get_player(self.player_position):
				if session.current_players == expected_players:
					was_paused = session.paused
					await game_mode.ready(
						session, self.room_name,
						self.game_room, state_callback)
					if was_paused and not session.paused:
						await self.channel_layer.group_send(
							self.room_name, {
								'type': 'game_state',
								'message': {
									'type': 'player.reconnected',
									'player_position': self.player_position
								}
							})
				elif session.current_players < expected_players:
					await self.channel_layer.group_send(
					self.room_name,
					{
						'type': 'game_status',
						'message': {
							'status': 'waiting'
							}
					})
				return
			self._players[self.player_position] = await get_player_room_player(player_room)
			session.set_player(
				self.player_position,
				await get_player_room_player(player_room))
			if session.current_players == expected_players:
				await game_mode.ready(
					session, self.room_name,
					self.game_room, state_callback)
			elif session.current_players < expected_players:
				await self.channel_layer.group_send(
				self.room_name,
				{
					'type': 'game_status',
					'message': {
						'status': 'waiting'
						}
				})

	async def update(self, bytes_data):
		if self._disconnected:
			return
		if self._game_session:
			await self._game_session.update(bytes_data, self.player_position)
		else:
			await self.channel_layer.group_send(
				self.room_name,
				{
					'type': 'game_state',
					'message': {'status': 'no session'}
				})

	# in local mode there is no waiting time.
	async def tournament_message(self, event, game_mode):
		# attempt to launch tournament.
		if not self._game_session:
			return
		if not game_mode.started:
			async with self._game_server.room_lock(self.room_name):
				await game_mode.ready(
					self._game_session,
					self.room_name,
					self.game_room,
					self.state_callback)

	async def flush_game_session(self, data):
		try:
			async with self._game_server.room_lock(self.room_name):
				if self._disconnected:
					return
				if data['player'] == self.player_position:
					data = {
						'type': 'end',
						'context': data['type'],
						'status': 'win',
						'winner': self.player_position,
						'player_name': self.player.player_name if self.player.is_guest else self.player.user_name,
						'player_id': self.player.user_id
						}
				else:
					player = self._game_session.get_player(1 - self.player_position)
					data = {
						'type': 'end',
						'context': data['type'],
						'status': 'lost',
						'winner': 1 - self.player_position,
						'player_name': player.player_name if player.is_guest else player.user_name,
						'player_id': player.user_id}
				# sends only to the concerned consumer.
				await self.consumer.send(text_data=json.dumps(data))
				await self.consumer.broadcast_participants()
				await self.channel_layer.group_discard(
					self.room_name, self.consumer.channel_name)
		except RuntimeError as e:
			pass

	async def connection_lost(
			self, session: GameSession,
			game_mode, data: dict, game_result: GameResult):
		if not self._disconnected:
			# if did not disconnect then it is the winner.
			winner_index = self.player_position
			loser_index = 1 - self.player_position
			game_result.winner = session.get_player(winner_index)
			game_result.loser = session.get_player(loser_index)
			game_result.winner_score = data["score"][winner_index]
			game_result.loser_score = data["score"][loser_index]
			data = await game_mode.handle_end_game(
				data, session.consumers, game_result)
			data['reason'] = 'disconnection'
			data['player'] = self.player_position
			# the remaining player stores the game_result
			await store_game_result(game_result)
			await self.flush_game_session(data)
			self._lost_connection = True
			return

	async def cleanup_data(self, tournament=None):
		pass

	async def disconnect(self, channel_name, channel_layer, game_mode):
		if not self._game_session:
			return
		async with self._game_server.room_lock(self.room_name):
			session = self._game_session
			session.remove_consumer(self.player_position, self)
			if session.current_players == 1:
				session.pause()
				if session.started and session.is_running:
					# tell the remaining player how long before the game ends.
					await self.channel_layer.group_send(
						self.room_name, {
							'type': 'game_state',
							'message': {
								'type': 'player.disconnected',
								'player_position': self.player_position,
								'player_name': self.player.player_name if self.player.is_guest else self.player.user_name,
								'timeout': session.pause_timeout
							}
						})
			if game_mode:
				await game_mode.handle_disconnection(
					channel_name,
					channel_layer,
					self.room_name,
					session.get_player_by_id(self._user['user_id']))
			await self.channel_layer.group_discard(self.room_name, self.consumer.channel_name)
			self._disconnected = True
