import asyncio

from channels.layers import BaseChannelLayer

from games.models import (
	Player,
	PlayerRoom,
	GameResult,
	TournamentGameRoom,
	GameRoom,
	Tournament,
	TournamentParticipant)

from common.db_utils import (
	tournament_is_closed,
	get_game_room,
	in_session,
	set_in_session,
	get_tournament,
	eliminate_player,
	get_remaining_participants,
	delete_tournament,
	close_game_room,
	qualify_player,
	leave_game_room,
	get_room_num_players,
	delete_game_room,
	remove_participant,
	update_tournament,
	get_participant_player,
	get_tournament_player_room,
	get_player_room_player,
	delete_guest_player
)

from common import game_session

class TournamentMode(object):
	def __init__(
			self,
			tournament: Tournament,
			tournament_id,
			game_room,
			channel_name,
			channel_layer: BaseChannelLayer,
			game_locality) -> None:
		self.tournament = tournament
		self.channel_layer = channel_layer
		self._channel_name = channel_name
		self._ready = False
		self._tournament_id = tournament_id
		self._game_room = game_room
		self.room_name = None
		self.started = False
		self.game_locality = game_locality

	async def ready(self,
		session: game_session.GameSession,
		room_name: str,
		game_room: GameRoom,
		state_callback) -> None:
		if self.started:
			return
		closed = await tournament_is_closed(self.tournament)
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
		self.started = True
		self._game_room = game_room = await get_game_room(room_name)
		if not game_room:
			return
		await self.channel_layer.group_send(
			room_name, {
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

	async def handle_end_game(self, data: dict, consumers, game_result: GameResult):
		tournament = await get_tournament(self._tournament_id)
		await eliminate_player(game_result.loser, tournament)
		remaining_players = await get_remaining_participants(tournament)
		if remaining_players == 1:
			for consumer in consumers:
				await consumer.cleanup_data(tournament=tournament)
			await delete_tournament(tournament)
			data["type"] = "win"
			return data
		await close_game_room(self._game_room)
		await qualify_player(game_result.winner, tournament)
		# delete players in closed game_rooms
		await delete_guest_player(game_result.loser)
		data["type"] = "round"
		return data

	async def handle_disconnection(self, channel_name, channel_layer, room_name, player: Player):
		# delete game room if not is session (means player canceled)
		tournament = await get_tournament(self._tournament_id)
		if not tournament:
			return
		if not await tournament_is_closed(tournament):
			tournament.participants -= 1
			if player:
				await remove_participant(tournament, player)
			if tournament.participants == 0:
				await delete_tournament(tournament)
			else:
				await update_tournament(tournament, ['participants'])
			game_room = await get_game_room(room_name)
			if game_room and player:
				await leave_game_room(player, game_room)
				if await get_room_num_players(game_room) <= 0:
					await delete_game_room(game_room)
		await channel_layer.group_discard(
			self._tournament_id,
			channel_name)

	async def cleanup_data(self, consumers, room_name , players):
		for consumer in consumers:
			await consumer.cleanup_data(tournament=self.tournament)
		tournament = await get_tournament(self._tournament_id)
		await delete_tournament(tournament)

	async def get_participants(self, user, game_room):
		# returns all active players in the tournament
		participants = TournamentParticipant.objects.filter(
			tournament=self.tournament).order_by('tournament_position')
		result = []
		rooms = TournamentGameRoom.objects.filter(
			tournament=self.tournament).values_list('game_room', flat=True)
		async for participant in participants:
			player = await get_participant_player(participant)
			player_room = await get_tournament_player_room(player, rooms)
			if not player_room:
				continue
			result.append({
				'user_id': player.user_id,
				'player_name': player.player_name if player.is_guest else player.user_name,
				'player_type': 'guest' if player.is_guest else 'host',
				'player_position': player_room.player_position,
				'player_status': participant.status.lower(),
				'game_mode': 'tournament'})
		return result

	async def get_room_players(self, user, game_room):
		# returns players in a given game room.
		rooms = PlayerRoom.objects.filter(game_room=game_room)
		result = []
		async for room in rooms:
			player = await get_player_room_player(room)
			result.append(
				{
					'user_id': player.user_id,
					'player_name': player.player_name if player.is_guest else player.user_name,
					'player_type': 'guest' if player.is_guest else 'host',
					'player_position': room.player_position,
					'game_mode': 'tournament'
				}
			)
		return result
