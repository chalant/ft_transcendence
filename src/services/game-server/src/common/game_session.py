import time
import asyncio
import logging
import django
import django.db

from games.models import GameResult, Player
from common.db_utils import (
	get_game_room_game,
	store_game_result,
	get_game_room,
	delete_game_room,
	set_in_session
)

logger = logging.getLogger(__name__)

class GameSession(object):
	def __init__(self, game_logic, game_server, game_room, game_mode=None, pause_timeout=5):
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
		self._disconnected = False
		self._start_time = 0
		self._current_data = {
			"player": -1,
			"loser": -1,
			"score": [-1, -1]}
		self._paused = False
		self._consumers = []
		self.consumers_per_player = [0, 0]
		self.error = False

	@property
	def num_consumers(self):
		return len(self._consumers)

	@property
	def consumers(self):
		return self._consumers

	def set_player(self, position, player):
		self._players[position] = player

	def get_player(self, position) -> Player:
		return self._players[position]
	
	def get_player_by_id(self, user_id):
		for player in self._players:
			if player:
				if player.user_id == user_id:
					return player
		return

	async def update(self, data, player):
		await self._game_logic.update(data, player)

	async def start(self, callback):
		try:
			self._game_result.game = await get_game_room_game(self._game_room)
			await callback(await self._game_logic.startEvent())
			self._start_time = t0 = time.time()
			while self.is_running and not self.error:
				await asyncio.gather(
					self.game_loop(callback),
					asyncio.sleep(0.03)) # about 30 loops/second
			self._game_result.game_duration = time.time() - t0
			if not self._disconnected and not self.error:
				try:
					await store_game_result(self._game_result)
				except django.db.utils.IntegrityError:
					pass
			if self.error:
				await self._game_mode.cleanup_data(
					self._consumers, self._session_id, self._players)
		except Exception:
			# this runs as a detached task: without this the exception is
			# swallowed and the room/session are never released.
			logger.exception("game session %s crashed", self._session_id)
		finally:
			# always release the room, otherwise its players stay bound to a
			# dead session and can never join another game.
			self.is_running = False
			try:
				game_room = await get_game_room(self._session_id)
				if game_room:
					await delete_game_room(game_room)
			finally:
				self._game_server.remove_session(self._session_id)

	async def game_loop(self, callback):
		try:
			await asyncio.wait_for(self._pause_event.wait(), self._timeout)
		except asyncio.TimeoutError:
			for consumer in self._consumers:
				self._current_data['score'] = self._game_logic.score
				self._game_result.game_duration = time.time() - self._start_time
				await consumer.connection_lost(
					self,
					self._game_mode,
					self._current_data,
					self._game_result)
			await set_in_session(self._game_room, False)
			self.is_running = False
			self._disconnected = True
			return
		self._current_data = data = await self._game_logic.gameTick()
		await callback(data)
		async for data in self._game_logic.sendEvent():
			if data["type"] == "win":
				await set_in_session(self._game_room, False)
				self._game_result.winner = self._players[data["player"]]
				self._game_result.loser = self._players[data["loser"]]
				self._game_result.winner_score = data["score"][data["player"]]
				self._game_result.loser_score = data["score"][data["loser"]]
				if not self._players[data["loser"]] or not self._players[data["player"]]:
					self.error = True
					for consumer in self._consumers:
						await consumer.flush_game_session(data)
					return
				if self._game_mode:
					try:
						data = await self._game_mode.handle_end_game(
							data, self._consumers, self._game_result)
					except Exception as e:
						self.error = True
						return
				for consumer in self._consumers:
					await consumer.flush_game_session(data)
				self.is_running = False
				return
			await callback(data)
			await asyncio.sleep(0.001)

	def on_session_end(self, callback):
		self._end_callbacks.append(callback)

	def add_consumer(self, position, consumer):
		if self.consumers_per_player[position] == 0:
			self.current_players += 1
		self.consumers_per_player[position] += 1
		self._consumers.append(consumer)

	def remove_consumer(self, position, consumer):
		if self.consumers_per_player[position] > 0:
			self.consumers_per_player[position] -= 1
		if self.consumers_per_player[position] == 0:
			self.current_players -= 1
		try:
			self._consumers.remove(consumer)
		except ValueError:
			return

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
		self._paused = True

	def resume(self):
		if not self._paused:
			return
		self._pause_event.set()
		self._paused = False