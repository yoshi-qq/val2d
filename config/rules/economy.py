"""Credits. Estimates by Claude Code, 11.11.2026; units: metres, seconds, credits. Edit freely."""

RULES = {
    'economy': {
        'start': 800,
        'pistol_round_credits': 800,
        'win': 3000,
        'loss': [1900, 2400, 2900],     # loss streak: 1st, 2nd, 3rd+ lost round in a row
        'survivor_loss': 1000,          # instead: attackers alive when time runs out, defenders alive after detonation
        'orb': 0,                       # credits for an ultimate orb (it always gives one ultimate point)
        'kill': 200,
        'plant': 300,
        'max': 9000,
    },
}
