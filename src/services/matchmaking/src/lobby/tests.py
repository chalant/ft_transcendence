import json

from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from django.db import connection
from django.test import Client, TransactionTestCase

from games.models import (
	Game,
	GameRoom,
	Player,
	PlayerRoom,
	Tournament,
	TournamentGameRoom,
	TournamentParticipant,
)


class AdvanceTests(TransactionTestCase):
	def setUp(self):
		self.game = Game.objects.get_or_create(game_name='pong', defaults={'min_players': 2})[0]
		self.tournament = Tournament.objects.create(
			game=self.game, tournament_id='t-1', max_participants=4,
			participants=4, closed=True)
		self.players = [
			Player.objects.create(player_name=f'p{i}', user_name=f'user{i}', user_id=i)
			for i in range(4)
		]
		for position, player in enumerate(self.players):
			TournamentParticipant.objects.create(
				player=player, tournament=self.tournament, tournament_position=position)

	def post(self, body):
		return self.client.post(
			'/internal/advance/', json.dumps(body), content_type='application/json')

	def test_advance_moves_player_to_next_round_room(self):
		player = self.players[0]
		response = self.post({'tournament_id': 't-1', 'player_id': player.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {'status': 1})
		participant = TournamentParticipant.objects.get(player=player)
		self.assertEqual(participant.tournament_round, 1)
		room = TournamentGameRoom.objects.get(tournament=self.tournament, tournament_round=1)
		self.assertTrue(PlayerRoom.objects.filter(player=player, game_room=room.game_room).exists())

	def test_two_winners_share_the_next_round_room(self):
		self.post({'tournament_id': 't-1', 'player_id': self.players[0].id})
		self.post({'tournament_id': 't-1', 'player_id': self.players[1].id})

		rooms = TournamentGameRoom.objects.filter(tournament=self.tournament, tournament_round=1)
		self.assertEqual(rooms.count(), 1)
		self.assertEqual(PlayerRoom.objects.filter(game_room=rooms.get().game_room).count(), 2)

	def test_unknown_participant_is_404(self):
		response = self.post({'tournament_id': 't-1', 'player_id': 999999})
		self.assertEqual(response.status_code, 404)
		self.assertEqual(response.json()['message'], 'Participant not found')

	def test_invalid_body_is_400(self):
		self.assertEqual(self.post({'tournament_id': 't-1'}).status_code, 400)
		self.assertEqual(self.post({'tournament_id': 1, 'player_id': 'x'}).status_code, 400)

	def test_get_is_405(self):
		self.assertEqual(self.client.get('/internal/advance/').status_code, 405)


class CreateGameTests(TransactionTestCase):
	def setUp(self):
		Game.objects.get_or_create(game_name='pong', defaults={'min_players': 2})
		# check_request asks the users service who the caller is.
		patcher = mock.patch(
			'lobby.views.auth.get_user',
			side_effect=lambda request: json.loads(request.headers['X-Test-User']))
		patcher.start()
		self.addCleanup(patcher.stop)

	def create_game(self, user_id, client=None):
		user = json.dumps({'user_id': user_id, 'username': f'user{user_id}'})
		return (client or self.client).post(
			'/create_game/', json.dumps({'game': 'pong'}),
			content_type='application/json', HTTP_X_TEST_USER=user)

	def test_two_players_end_up_in_one_room(self):
		first = self.create_game(1).json()
		second = self.create_game(2).json()

		self.assertEqual(first['status'], 'created')
		self.assertEqual(second['status'], 'joined')
		self.assertEqual(first['game_room_id'], second['game_room_id'])
		self.assertEqual(GameRoom.objects.get().num_players, 2)

	def test_concurrent_requests_never_overfill_a_room(self):
		users = 20

		def request(user_id):
			try:
				return self.create_game(user_id, Client()).status_code
			finally:
				connection.close()

		with ThreadPoolExecutor(users) as pool:
			statuses = list(pool.map(request, range(1, users + 1)))

		self.assertEqual(set(statuses), {200, 201})
		for room in GameRoom.objects.all():
			self.assertEqual(room.num_players, 2)
			self.assertEqual(PlayerRoom.objects.filter(game_room=room).count(), 2)
		self.assertEqual(GameRoom.objects.count(), users // 2)
