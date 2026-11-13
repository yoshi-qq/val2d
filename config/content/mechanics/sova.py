"""Steering and lifecycle for Sova's Owl Drone."""
from heapq import heappop, heappush
from math import atan2, cos, degrees, floor, radians, tan

from gameplay.geometry import MAX_DRONE_PITCH, Rect, Vec, angle_of, heading
from gameplay.kit import statuses
from gameplay.kit.builtins import game_event, select
from gameplay.kit.dsl import on, step, thing
from gameplay.kit.engine import place, remove_device
from gameplay.kit.registry import BOT_CONTROL, COMMAND_FILTERS, Ctx, effect, target
from gameplay.world import head_height


DRONE_RADIUS = 0.32
LAUNCH_DISTANCE = 1.25
CLIMB_SPEED = 2.0
MAX_CLIMB = 3.0


def drone_walls(match, level):
    return [w.rect for w in match.combat_walls() if w.solid and w.top > level
            and w.base <= level and match.wall_active(w)]


@target("owl_drone_launch")
def owl_drone_launch(match, player, _spec):
    aim = heading(player.facing)
    bounds = Rect(0, 0, match.world.width, match.world.height)
    point = match._move_against_walls(player.pos, player.pos + aim * LAUNCH_DISTANCE,
                                      DRONE_RADIUS, drone_walls(match, player.level), bounds)
    return point if (point - player.pos).dot(aim) >= DRONE_RADIUS else None


@effect("owl_drone_ping", per_player=False)
def drone_ping(ctx, _target, _spec):
    victim = ctx.m.players.get(ctx.obj.data["victim"])
    if victim is not None and victim.alive and victim.died_at < ctx.obj.data["impact"]:
        victim.revealed_until = max(victim.revealed_until, ctx.m.time + 0.6)


def dart_target(ctx, pitch):
    match, drone, aim = ctx.m, ctx.obj, ctx.aim
    height = drone.props.get("flight_height", drone.props["source_level"])
    level_height = float(match._mv["level_height"])
    angle = radians(max(-MAX_DRONE_PITCH, min(MAX_DRONE_PITCH, pitch)))
    slope = tan(angle) / level_height
    walls = [w for w in match.combat_walls() if w.blocks_sight and match.wall_active(w, for_sight=True)]
    candidates = select(ctx, {"radius": drone.radius})
    hits = []
    for candidate in candidates:
        offset = candidate.pos - drone.pos
        distance = offset.dot(aim)
        if (not 0 < distance <= drone.radius * cos(angle)
                or abs(offset.cross(aim)) > float(match._mv["radius"])
                or statuses.flag(match, candidate, "intangible")):
            continue
        end_height = height + slope * distance
        feet = candidate.ground + candidate.z
        top = feet + head_height() * (0.65 if candidate.crouching else 1.0)
        if not feet <= end_height * level_height <= top:
            continue
        if match.world.deck_blocks(drone.pos, height, drone.pos + aim * distance, end_height):
            continue
        for wall in walls:
            interval = wall.rect.ray_interval(drone.pos, aim)
            if interval is None or interval[0] >= distance:
                continue
            low, high = sorted((height + slope * interval[0], height + slope * min(distance, interval[1])))
            if low < wall.top and high >= wall.base:
                break
        else:
            hits.append((distance, candidate))
    return min(hits, key=lambda hit: hit[0])[1] if hits else None


def fire_dart(match, player, drone, pitch):
    drone.data["dart_ready"] = match.time + 5
    ctx = Ctx(match, player, player.team, drone.pos, drone.pos, heading(player.facing), obj=drone)
    if (victim := dart_target(ctx, pitch)) is None:
        return
    game_event(match, "owl_dart_hit", {"pid": player.pid, "key": "hit_body"})
    game_event(match, "owl_dart_hit", {"pid": victim.pid, "key": "cast_tech"})
    statuses.apply_status(match, victim, "owl_drone_spotted", 4)
    victim.passive_state["owl_drone_spotted_at"] = match.time
    marker = place(ctx, thing("none", hidden="all", lasts=4.1,
                   triggers=[on("every", [step("owl_drone_ping")], offset=1.6, seconds=1.8, count=2)]), victim.pos)
    marker.data.update(victim=victim.pid, impact=match.time)


@effect("pilot_owl_drone", per_player=False)
def pilot_owl_drone(ctx, _target, _spec):
    spec = ctx.ability["place"]
    ctx.owner.channel_until = ctx.m.time + float(spec["delay"]) + float(spec["lasts"])
    ctx.owner.vel = Vec(0, 0)


@effect("end_owl_drone", per_player=False)
def end_owl_drone(ctx, _target, _spec):
    if ctx.owner is not None:
        return_from_drone(ctx.m, ctx.owner)


def return_from_drone(match, player):
    player.channel_until = 0
    if player.alive:
        player.equip_until = match.time + 0.7
        player.reload_until, player.burst_left = 0.0, 0
        statuses.apply_status(match, player, "weapon_recovery", 0.7)


def active_drone(match, player):
    return next((e for e in match.effects if e.owner == player.pid and e.props.get("sprite") == "sova_owl_drone"
                 and not e.props.get("ended")), None)


@effect("interrupt_owl_drone", per_player=False)
def interrupt_owl_drone(ctx, _target, _spec):
    player = ctx.owner
    if player is not None and (drone := active_drone(ctx.m, player)) is not None:
        remove_device(ctx.m, drone, "cancel")


def filter_command(match, player, cmd, dt):
    if player.channel_until <= match.time:
        return cmd
    drone = active_drone(match, player)
    if drone is None:
        return_from_drone(match, player)
        return None
    if (cmd.ability == "C" and player.prev_ability != "C") or statuses.flag(match, player, "no_abilities"):
        remove_device(match, drone, "cancel")
        return None
    if match.time < drone.start:
        return None
    if cmd.facing is not None:
        player.facing = cmd.facing
    if cmd.fire and not player.prev_fire and match.time >= drone.data.get("dart_ready", 0):
        fire_dart(match, player, drone, cmd.drone_pitch)
    move = Vec(cmd.move_x, cmd.move_y)
    if move.length() > 1:
        move = move.normalized()
    level = drone.props["source_level"]
    world = match.world
    launch_level = drone.data.setdefault("launch_level", level)
    height = drone.props.get("flight_height", float(level))
    requested = max(world.ground_height(drone.pos, height),
                    min(launch_level + MAX_CLIMB, height + (int(cmd.jump) - int(cmd.crouch)) * CLIMB_SPEED * dt))
    if (deck := world.deck_at(drone.pos)) is not None:
        requested = min(requested, deck.underside - DRONE_RADIUS) if height < deck.level else max(requested, deck.level)
    if (not world.deck_blocks(drone.pos, height, drone.pos, requested)
            and not any(w.circle_push(drone.pos, DRONE_RADIUS) for w in drone_walls(match, requested))):
        height = requested
    drone.props["flight_height"] = height
    drone.props["source_level"] = floor(height)
    walls = drone_walls(match, height)
    speed = drone.props["ability"]["place"]["move"]
    drone.props["move"] = 0
    goal = drone.pos + move.rotated(player.facing) * (speed * dt)
    bounds = Rect(0, 0, world.width, world.height)
    point = match._move_against_walls(drone.pos, goal, DRONE_RADIUS, walls, bounds)
    if world.ground_height(point, height) <= height and not world.deck_blocks(drone.pos, height, point, height):
        drone.pos = point
    return None


COMMAND_FILTERS["sova"] = filter_command


def detour(world, start, goal, obstacles, reach, height=None):
    margin = 0.2
    points = [start, goal]
    for rect in obstacles:
        for x in (rect.x0 - margin, rect.x1 + margin):
            for y in (rect.y0 - margin, rect.y1 + margin):
                point = Vec(x, y)
                if (DRONE_RADIUS <= x <= world.width - DRONE_RADIUS
                        and DRONE_RADIUS <= y <= world.height - DRONE_RADIUS
                        and (point - start).length() <= reach
                        and not any(wall.contains(point) for wall in obstacles)):
                    points.append(point)
    pending = [((goal - start).length(), 0.0, 0)]
    costs = {0: 0.0}
    previous = {}
    while pending:
        _, cost, current = heappop(pending)
        if cost > costs[current]:
            continue
        if current == 1:
            route = []
            while (current := previous[current]) != 0:
                route.append(points[current])
            return route[::-1]
        origin = points[current]
        for index, point in enumerate(points[1:], 1):
            delta = point - origin
            new_cost = cost + delta.length()
            if new_cost >= costs.get(index, float("inf")):
                continue
            if height is not None and world.deck_blocks(origin, height, point, height):
                continue
            if any((hit := wall.ray_interval(origin, delta)) is not None and hit[0] < 1
                   for wall in obstacles):
                continue
            costs[index] = new_cost
            previous[index] = current
            heappush(pending, (new_cost + (point - goal).length(), new_cost, index))
    return None


def deck_transition(match, pos, deck, height, goal, goal_height, reach):
    world = match.world
    rect = deck.rect
    x = max(rect.x0, min(rect.x1, pos.x))
    y = max(rect.y0, min(rect.y1, pos.y))
    margin = DRONE_RADIUS + 0.2
    edges = (Vec(rect.x0 - margin, y), Vec(rect.x1 + margin, y),
             Vec(x, rect.y0 - margin), Vec(x, rect.y1 + margin))
    low, high = sorted((height, goal_height))
    walls = [w for w in match.combat_walls() if w.solid and match.wall_active(w)]
    bounds = Rect(0, 0, world.width, world.height)
    approach_walls = drone_walls(match, height)
    return_walls = drone_walls(match, goal_height)
    approach_obstacles = [Rect(w.x0 - DRONE_RADIUS, w.y0 - DRONE_RADIUS,
                               w.x1 + DRONE_RADIUS, w.y1 + DRONE_RADIUS) for w in approach_walls]
    obstacles = [Rect(w.x0 - DRONE_RADIUS, w.y0 - DRONE_RADIUS,
                      w.x1 + DRONE_RADIUS, w.y1 + DRONE_RADIUS) for w in return_walls]
    best = None
    for edge in sorted(edges, key=lambda p: (p - pos).length()):
        if not (DRONE_RADIUS <= edge.x <= world.width - DRONE_RADIUS
                and DRONE_RADIUS <= edge.y <= world.height - DRONE_RADIUS):
            continue
        if (world.deck_blocks(edge, height, edge, goal_height)
                or world.ground_height(edge, low) > low):
            continue
        if any(w.base <= high and w.top > low and w.rect.circle_push(edge, DRONE_RADIUS) is not None
               for w in walls):
            continue
        reached = match._move_against_walls(pos, edge, DRONE_RADIUS, approach_walls, bounds)
        approach = []
        if (reached - edge).length() >= 1e-6 or world.deck_blocks(pos, height, edge, height):
            approach = detour(world, pos, edge, approach_obstacles, reach, height)
            if approach is None:
                continue
        reached = match._move_against_walls(edge, goal, DRONE_RADIUS, return_walls, bounds)
        if ((reached - goal).length() < 1e-6
                and not world.deck_blocks(edge, goal_height, goal, goal_height)):
            route = []
        else:
            route = detour(world, edge, goal, obstacles, reach, goal_height)
            if route is None:
                continue
        points = [pos, *approach, edge, *route, goal]
        distance = sum((b - a).length() for a, b in zip(points, points[1:]))
        if distance <= reach and (best is None or distance < best[0]):
            best = distance, edge, approach, route
    return best[1:] if best is not None else (None, [], [])


def deck_return_route(match, pos, goal, height, reach):
    obstacles = [Rect(w.x0 - DRONE_RADIUS, w.y0 - DRONE_RADIUS,
                      w.x1 + DRONE_RADIUS, w.y1 + DRONE_RADIUS)
                 for w in drone_walls(match, height)]
    route = detour(match.world, pos, goal, obstacles, reach, height)
    if route is not None:
        points = [pos, *route, goal]
        if sum((b - a).length() for a, b in zip(points, points[1:])) <= reach:
            return route
    return None


def deck_shaft_blocked(match, pos, height, goal_height):
    low, high = sorted((height, goal_height))
    return (match.world.deck_blocks(pos, height, pos, goal_height)
            or any(w.solid and w.base <= high and w.top > low and match.wall_active(w)
                   and w.rect.circle_push(pos, DRONE_RADIUS) is not None for w in match.combat_walls()))


def bot_control(match, player, cmd, goal):
    drone = active_drone(match, player)
    if drone is None:
        return False
    if match.time < drone.start:
        return True
    ctx = Ctx(match, player, player.team, drone.pos, drone.pos, heading(player.facing), obj=drone)
    if not player.prev_fire and match.time >= drone.data.get("dart_ready", 0):
        level = drone.props.get("flight_height", drone.props["source_level"])
        height = level * float(match._mv["level_height"])
        enemies = sorted(select(ctx, {"radius": drone.radius}), key=lambda p: (p.pos - drone.pos).length())
        for enemy in enemies:
            offset = enemy.pos - drone.pos
            torso = enemy.ground + enemy.z + head_height() * (0.325 if enemy.crouching else 0.5)
            pitch = degrees(atan2(torso - height, offset.length()))
            facing = angle_of(offset)
            ctx.aim = heading(facing)
            if abs(pitch) <= MAX_DRONE_PITCH and dart_target(ctx, pitch) is not None:
                cmd.facing, cmd.drone_pitch, cmd.fire = facing, pitch, True
                return True
    level = drone.props["source_level"]
    height = drone.props.get("flight_height", float(level))
    ceiling = drone.data.get("launch_level", level) + MAX_CLIMB
    goal_deck = match.world.deck_at(goal) if goal is not None else None
    goal_height = None
    if goal_deck is not None:
        goal_height = (match.spike_ground if goal == match.spike_pos
                       else goal_deck.level if goal_deck.walkable else goal_deck.lower)
        if goal_height > ceiling:
            goal_height = None
    destination_key = (goal, goal_height)
    if drone.data.get("bot_destination") != destination_key:
        had_transition = drone.data.get("bot_deck_edge") is not None or drone.data.get("bot_deck_relocating")
        for key in ("bot_deck_edge", "bot_deck_return", "bot_deck_replan_at", "bot_deck_obstacles",
                    "bot_return_goal", "bot_route", "bot_route_goal", "bot_replan_at"):
            drone.data.pop(key, None)
        drone.data["bot_deck_relocating"] = bool(had_transition and goal_height is not None
                                               and match.world.deck_at(drone.pos) is None
                                               and abs(height - goal_height) > 0.05)
        drone.data["bot_destination"] = destination_key
    obstacles = (tuple(match.ability_walls()), frozenset(match.open_doors), frozenset(match.broken_cover))
    obstacles_changed = obstacles != drone.data.get("bot_deck_obstacles")
    speed = drone.props["ability"]["place"]["move"]
    remaining = drone.until - match.time
    if goal_height is not None and ((height >= goal_deck.level) != (goal_height >= goal_deck.level)
            or drone.data.get("bot_deck_relocating")
            or (drone.data.get("bot_deck_edge") is not None and abs(height - goal_height) > 0.05)):
        current_deck = match.world.deck_at(drone.pos)
        edge = drone.data.get("bot_deck_edge")
        vertical_time = abs(goal_height - height) / CLIMB_SPEED
        if remaining <= vertical_time:
            return True
        blocked_shaft = current_deck is None and deck_shaft_blocked(match, drone.pos, height, goal_height)
        relocating = drone.data.get("bot_deck_relocating")
        resume_here = relocating and obstacles_changed and current_deck is None and not blocked_shaft
        if resume_here:
            edge = drone.pos
            drone.data["bot_deck_edge"] = edge
        elif current_deck is not None or blocked_shaft or relocating:
            drone.data["bot_deck_relocating"] = current_deck is None or relocating or (
                edge is not None and (height >= goal_deck.level) == (goal_height >= goal_deck.level))
            if obstacles_changed:
                edge = None
                drone.data.pop("bot_deck_edge", None)
                drone.data.pop("bot_deck_return", None)
                drone.data.pop("bot_route", None)
                drone.data.pop("bot_deck_replan_at", None)
                drone.data["bot_deck_obstacles"] = obstacles
            if edge is None and match.time >= drone.data.get("bot_deck_replan_at", 0):
                reach = (remaining - vertical_time) * speed
                edge, approach, return_route = deck_transition(match, drone.pos, current_deck or goal_deck, height, goal,
                                                              goal_height, reach)
                drone.data["bot_deck_replan_at"] = match.time + 0.25
                drone.data["bot_deck_edge"] = edge
                drone.data["bot_deck_return"] = (goal, return_route)
                if edge is not None:
                    drone.data["bot_route_goal"] = edge
                    drone.data["bot_route"] = approach
        if edge is not None and (edge - drone.pos).length() > 0.12:
            goal = edge
        elif current_deck is not None or blocked_shaft:
            return True
        else:
            drone.data.pop("bot_deck_relocating", None)
            if edge is not None and obstacles_changed:
                route = deck_return_route(match, drone.pos, goal, goal_height, (remaining - vertical_time) * speed)
                drone.data["bot_deck_return"] = (goal, route)
                drone.data["bot_deck_obstacles"] = obstacles
            if edge is not None and drone.data.get("bot_deck_return") == (goal, None):
                return True
            cmd.jump = height < goal_height
            cmd.crouch = height > goal_height
            return True
    else:
        drone.data.pop("bot_deck_edge", None)
        drone.data.pop("bot_deck_relocating", None)
    if drone.data.get("bot_route_goal") != goal:
        drone.data.pop("bot_route", None)
        drone.data["bot_route_goal"] = goal
        drone.data.pop("bot_replan_at", None)
        return_goal, return_route = drone.data.get("bot_deck_return", (None, []))
        if return_goal == goal:
            drone.data["bot_route"] = return_route
            drone.data.pop("bot_deck_return")
            drone.data["bot_return_goal"] = goal
    if goal is not None and drone.data.get("bot_return_goal") == goal:
        if obstacles_changed:
            drone.data["bot_route"] = deck_return_route(match, drone.pos, goal, height, remaining * speed)
            drone.data["bot_deck_obstacles"] = obstacles
        if drone.data.get("bot_route") is None:
            return True
    route = drone.data.get("bot_route", [])
    if route and (route[0] - drone.pos).length() <= 0.12:
        route.pop(0)
    waypoint = route[0] if route else None
    destination = waypoint if waypoint is not None else goal
    tolerance = 0.12 if waypoint or goal == drone.data.get("bot_deck_edge") else DRONE_RADIUS
    if destination is not None and (offset := destination - drone.pos).length() > tolerance:
        cmd.facing = angle_of(offset)
        cmd.move_y = 1
        lookahead = min(1.0, offset.length())
        direction = offset.normalized()
        ahead = drone.pos + direction * lookahead
        deck = match.world.deck_at(drone.pos)
        climb_limit = min(ceiling, deck.underside - DRONE_RADIUS) if deck and height < deck.level else ceiling
        reach = min(climb_limit, goal_height) if goal_height is not None and goal_height < goal_deck.level else climb_limit
        desired = max(match.world.ground_height(drone.pos, height),
                      match.world.ground_height(ahead, reach))
        if goal_height is not None and goal_height >= goal_deck.level and height >= goal_deck.level:
            desired = max(desired, goal_height)
        obstacles = []
        blocked = False
        for wall in match.combat_walls():
            if not wall.solid or not match.wall_active(wall) or wall.base > height:
                continue
            rect = wall.rect
            clearance = Rect(rect.x0 - DRONE_RADIUS, rect.y0 - DRONE_RADIUS,
                             rect.x1 + DRONE_RADIUS, rect.y1 + DRONE_RADIUS)
            interval = clearance.ray_interval(drone.pos, direction)
            if wall.top > climb_limit and height < wall.top:
                obstacles.append(clearance)
                blocked |= interval is not None and interval[0] <= lookahead
            if interval is not None and interval[0] <= lookahead:
                if wall.top <= climb_limit:
                    desired = max(desired, wall.top)
        if blocked and match.time >= drone.data.get("bot_replan_at", 0):
            reach = (drone.until - match.time) * drone.props["ability"]["place"]["move"]
            route = detour(match.world, drone.pos, goal, obstacles, reach)
            drone.data["bot_route"] = route or []
            drone.data["bot_replan_at"] = match.time + 0.25
            if route:
                cmd.facing = angle_of(route[0] - drone.pos)
                desired = height
        cmd.jump = height < desired
        cmd.crouch = height > desired + 0.05
    return True


BOT_CONTROL["sova"] = bot_control
