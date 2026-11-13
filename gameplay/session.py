"""Host session: match, network host and bots together.

Used by play.py (host = player 1) and server.py (dedicated server process).
Remote players do not send a command every host tick; their last command keeps
applying, one-shot inputs (buy, reload, weapon switch, ability) only once.
"""
from __future__ import annotations

from dataclasses import replace

from gameplay.bots import BotDirector
from gameplay.match import Command, GameEvent, Match, PlayerState
from gameplay.netgame import DEFAULT_PORT, NetHost
from gameplay.world import PLAYABLE_MAP_KEYS, load_playable_map

SNAPSHOT_RATE = 30.0  # snapshots per second sent to clients


def _held_part(cmd: Command) -> Command:
    """Only the held inputs of a command, without one-shot inputs."""
    return replace(cmd, buy=[], reload=False, slot=None, ability=None, drop=False, equipment_actions=[],
                   request=None, request_clicks=[])


class HostSession:
    def __init__(self, match: Match, host_name: str, port: int | None = DEFAULT_PORT, mode: str = "lan") -> None:
        self.match = match
        self.net = NetHost(match, host_name, mode=mode, port=port)
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
        """Fills both teams with bots up to team_size."""
        agents = list(self.match.agents)
        with self.net.lock:
            team_size = max(team_size, *self.team_counts())
            for team in (0, 1):
                count = self.team_counts()[team]
                for i in range(count, team_size):
                    self.match.add_player(f"Bot {team + 1}-{i + 1}", team, agents[i % len(agents)], is_bot=True)

    def start(self, team_size: int) -> bool:
        with self.net.lock:
            if self.match.phase != "lobby":
                return False
            self.net.accepting = False
            self.net.pending.clear()
            self.last.clear()
            self.fill_bots(team_size)
            self.match.start()
            return True

    def configure_lobby(self, *, map_key: str | None = None, mode: str | None = None) -> bool:
        with self.net.lock:
            if self.match.phase != "lobby":
                return False
            if map_key is not None and map_key not in PLAYABLE_MAP_KEYS:
                return False
            if mode is not None and mode not in ("standard", "quick", "deathmatch"):
                return False
            world = load_playable_map(map_key) if map_key and map_key != self.match.world.key else self.match.world
            self.match.world = world
            if mode is not None:
                self.match.set_mode(mode)
            return True

    def end_deathmatch_phase(self) -> bool:
        with self.net.lock:
            return self.match.end_deathmatch_phase()

    def toggle_deathmatch_timer(self) -> bool:
        with self.net.lock:
            return self.match.toggle_deathmatch_timer()

    def surrender(self, team: int) -> bool:
        with self.net.lock:
            event_count = len(self.match.events)
            if not self.match.surrender(team):
                return False
            self._pending_events.extend(self.match.events[event_count:])
            self.net.broadcast(self._pending_events)
            self._pending_events.clear()
            self._since_broadcast = 0.0
            return True

    def return_to_lobby(self) -> bool:
        with self.net.lock:
            old = self.match
            if old.phase != "over":
                return False
            match = Match(old.world, old.cfg, agent_roster=old.agents)
            match.time = old.time
            match.set_mode(old.mode)
            for player in old.players.values():
                if not player.is_bot:
                    match.players[player.pid] = PlayerState(
                        pid=player.pid, name=player.name, team=player.team, agent=player.agent,
                        weapon_skins=dict(player.weapon_skins), credits=int(match._eco["start"]),
                        request_revision=player.request_revision,
                    )
            self.match = self.net.match = match
            self.bots = BotDirector(match)
            self.last.clear()
            self._pending_events.clear()
            self._since_broadcast = 1.0 / SNAPSHOT_RATE
            self.net.pending.clear()
            self.net.dropped.clear()
            self.net.tokens = {token: pid for token, pid in self.net.tokens.items() if pid in match.players}
            self.net.generation += 1
            self.net.accepting = True
            return True

    def step(self, dt: float, local: dict[int, Command] | None = None) -> list[GameEvent]:
        """One host tick. local: commands from players on this machine."""
        with self.net.lock:
            commands = self.bots.commands(dt)
            remote = self.net.take_commands()
            for pid, p in self.match.players.items():
                if p.is_bot:
                    self.last.pop(pid, None)
                    continue
                if local and pid in local:
                    continue
                if pid in remote:
                    commands[pid] = remote[pid]
                    self.last[pid] = _held_part(remote[pid])
                elif pid in self.last:
                    commands[pid] = self.last[pid]
            if local:
                commands.update(local)
            events = self.match.tick(dt, commands)
        self._pending_events += events
        self._since_broadcast += dt
        if self._since_broadcast >= 1.0 / SNAPSHOT_RATE:
            self._since_broadcast = 0.0
            with self.net.lock:
                for pid in list(self.net.pid_of.values()):
                    rtt = self.net.ping(pid)
                    p = self.match.players.get(pid)
                    if p is not None:
                        p.ping_ms = round(rtt * 1000) if rtt is not None else None
                self.net.broadcast(self._pending_events)
            self._pending_events = []
        return events

    def close(self) -> None:
        self.net.close()
