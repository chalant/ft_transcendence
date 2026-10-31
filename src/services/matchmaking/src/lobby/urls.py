from django.urls import path
from . import views

urlpatterns = [
	# routes to the authentication microservice.
	path('create_game/', views.create_game, name='create_game'),
	path('join_tournament/', views.find_tournament_view, name='join_tournament'),
	path('create_tournament/', views.create_tournament_view, name='create_tournament'),
	path('next_tournament_room/', views.get_tournament_room, name='next_tournament_room'),
	path('game_stats/<int:user_id>/', views.game_stats, name='game_stats'),
	path('internal/advance/', views.advance, name='advance')
]