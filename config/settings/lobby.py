"""Lobby rules: the defaults a new lobby starts with. The host (or the player in a match against bots) changes
them in the lobby before the match starts; they are not player settings."""

CONFIG = {
    'lobby_defaults': {
        'all_around_sight': False,
        'sound_rings': False,
        'win_rounds': 13,
        'overtime': False,             # Unrated ends in one deciding round; custom games can opt into win by two
        'play_all_rounds': False,
        'allow_cheats': False,
        'infinite_ammo': False,        # cheat
        'infinite_abilities': False,   # cheat
        'invincibility': False,        # cheat
        'bullet_tracers': False,       # cheat
        'team_size': 1,
    },
}
