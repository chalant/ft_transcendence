from django.db import migrations

GAMES = ('pong', 'snake')


def seed_games(apps, schema_editor):
    Game = apps.get_model('games', 'Game')
    for name in GAMES:
        Game.objects.get_or_create(game_name=name, defaults={'min_players': 2})


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_games, migrations.RunPython.noop),
    ]
