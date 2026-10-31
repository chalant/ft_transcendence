from django.db import models

class Game(models.Model):
	game_name = models.CharField(max_length=50, unique=True)
	min_players = models.IntegerField(default=2)

class Player(models.Model):
	player_name = models.CharField(max_length=50)
	user_name = models.CharField(max_length=50)
	user_id = models.IntegerField(null=False)
	is_guest = models.BooleanField(default=False)

class Tournament(models.Model):
	game = models.ForeignKey(Game, on_delete=models.CASCADE)
	tournament_id = models.CharField(max_length=100, primary_key=True)
	# if it is null then it is an anonymous tournament.
	tournament_name = models.CharField(max_length=100, default=None, blank=True, null=True)
	game_room_count = models.IntegerField(default=0)
	participants = models.IntegerField(default=0)
	max_participants = models.IntegerField(default=8)
	created_at = models.DateTimeField(auto_now_add=True)
	closed = models.BooleanField(default=False)
	local = models.BooleanField(default=False)

class GameRoom(models.Model):
	room_name = models.CharField(max_length=100, primary_key=True)
	# a game room can only have one game.
	game = models.ForeignKey(Game, on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)
	num_players = models.IntegerField(default=0)
	in_session = models.BooleanField(default=False)
	is_local = models.BooleanField(default=False)
	closed = models.BooleanField(default=False)

# associate a player to a room.
class PlayerRoom(models.Model):
	player = models.ForeignKey(Player, on_delete=models.CASCADE)
	# a player can only have one room.
	game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
	player_position = models.IntegerField(default=0)

class GameResult(models.Model):
	winner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='won_games')
	loser = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='lost_games')
	winner_score = models.IntegerField(default=0)
	loser_score = models.IntegerField(default=0)
	game_duration = models.IntegerField(default=0)
	game_date = models.DateTimeField(auto_now_add=True)
	game = models.ForeignKey(Game, on_delete=models.CASCADE)

class TournamentParticipant(models.Model):
	player = models.ForeignKey(Player, on_delete=models.CASCADE)
	tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
	status = models.CharField(max_length=20, default="PLAYING")
	tournament_round = models.IntegerField(default=0)
	tournament_position = models.IntegerField(default=0)
	is_host	= models.BooleanField(default=False)

class TournamentGameRoom(models.Model):
	tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
	game_room = models.ForeignKey(GameRoom, on_delete=models.CASCADE)
	tournament_round = models.IntegerField(default=0)

class TournamentResult(models.Model):
	tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
	game_result = models.ForeignKey(GameResult, on_delete=models.CASCADE)
	is_final = models.BooleanField(default=False)
