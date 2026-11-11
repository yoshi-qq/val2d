"""Host-Sitzung: Match, Netz-Host und Bots zusammen.

Genutzt von play.py (Host = Spieler 1) und server.py (eigener Server-Prozess).
Ferne Spieler senden nicht in jedem Host-Tick einen Befehl; ihr letzter Befehl gilt
weiter, einmalige Eingaben (Kauf, Nachladen, Waffenwechsel, Fähigkeit) nur einmal.
"""
from __future__ import annotations

from dataclasses import replace

from gameplay.bots import BotDirector
from gameplay.match import Command, GameEvent, Match
from gameplay.net import DEFAULT_PORT, Host

SNAPSHOT_RATE = 30.0  # Abbilder je Sekunde an die Clients


def _held_part(cmd: Command) -> Command:
    """Nur gehaltene Eingaben eines Befehls, ohne einmalige."""
    return replace(cmd, buy=[], reload=False, slot=None, ability=None)


class HostSession:
    def __init__(self, match: Match, host_name: str, port: int = DEFAULT_PORT) -> None:
        self.match = match
        self.net = Host(match, host_name, port)
        self.bots = BotDirector(match)
        self.last: dict[int, Command] = {}
        self._pending_events: list[GameEvent] = []
        self._since_broadcast = 0.0

    @property
    def started(self) -> bool:
        return self.match.phase != "lobby"

    def team_counts(self) -> list[int]:
        return [sum(1 for p in self.match.players.values() if p.team == t) for t in (0, 1)]

    def fill_bots(self, team_size: int) -> None:
        """Füllt beide Teams mit Bots auf team_size auf."""
        agents = list(self.match.agents) or ["kestrel"]
        with self.net.lock:
            for team in (0, 1):
                count = self.team_counts()[team]
                for i in range(count, team_size):
                    self.match.add_player(f"Bot {team + 1}-{i + 1}", team, agents[i % len(agents)], is_bot=True)

    def start(self, team_size: int) -> None:
        with self.net.lock:
            self.net.accepting = False
        self.fill_bots(team_size)
        self.match.start()

    def step(self, dt: float, local: dict[int, Command] | None = None) -> list[GameEvent]:
        """Ein Host-Tick. local: Befehle von Spielern an diesem Rechner."""
        commands = self.bots.commands(dt)
        remote = self.net.take_commands()
        for pid, p in self.match.players.items():
            if p.is_bot or pid in (local or {}):
                continue
            if pid in remote:
                commands[pid] = remote[pid]
                self.last[pid] = _held_part(remote[pid])
            elif pid in self.last:
                commands[pid] = self.last[pid]
        if local:
            commands.update(local)
        with self.net.lock:
            events = self.match.tick(dt, commands)
        self._pending_events += events
        self._since_broadcast += dt
        if self._since_broadcast >= 1.0 / SNAPSHOT_RATE:
            self._since_broadcast = 0.0
            self.net.broadcast(self._pending_events)
            self._pending_events = []
        return events

    def close(self) -> None:
        self.net.close()
