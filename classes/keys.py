import pygame as p
from enum import Enum

class HandItemKey(Enum):
    MELEE = 0
    SIDEARM = 1
    PRIMARY = 2
    BASIC = 3
    TACTICAL = 4
    SIGNATURE = 5
    ULTIMATE = 6

class MenuKey(Enum):
    EMPTY = "empty"
    PLAY = "play"
    HOST_LOBBY = "hostLobby"
    PLAYER_LOBBY = "playerLobby"
    AGENT_SELECT = "agentSelect"
    HOST_AGENT_SELECT = "hostAgentSelect"
    IN_GAME_PLAYER = "inGamePlayer"
    IN_GAME_HOST = "inGameHost"

class MapKey(Enum):
    BIND = 1
    HAVEN = 2
    SPLIT = 3
    ASCENT = 4
    ICEBOX = 5
    BREEZE = 6
    FRACTURE = 7
    PEARL = 8
    LOTUS = 9
    SUNSET = 10
    ABYSS = 11

class EffectKey(Enum):
    # 01 Brimstone (1-10)
    # 02 Viper (11-20)
    # 03 Omen (21-30)
    SHROUDED_STEP_CAST = 21
    PARANOIA_CAST = 22
    DARK_COVER_CAST = 23
    FROM_THE_SHADOWS_CAST = 24
    # 04 Killjoy (31-40)
    # 05 Cypher (41-50)
    # 06 Sova (51-60)
    # 07 Sage (61-70)
    # 08 - (71-80)
    # 09 Phoenix (81-90)
    # 10 Jett (91-100)
    # 11 Reyna (101-110)
    # 12 Raze (111-120)
    # 13 Breach (121-130)
    # 14 Skye (131-140)
    # 15 Yoru (141-150)
    # 16 Astra (151-160)
    # 17 KAY/O (161-170)
    # 18 Chamber (171-180)
    # 19 Neon (181-190)
    # 20 Fade (191-200)
    # 21 Harbor (201-210)
    # 22 Gekko (211-220)
    # 23 Deadlock (221-230)
    # 24 Iso (231-240)
    # 25 Clove (241-250)
    # 26 Vyse (251-260)
    # 27 Tejo (261-270)
    # 28 Waylay (271-280)
    
    # GUNS (301-450)
    BURST_FIRE_3 = 301
    BURST_FIRE_4 = 302
    AIR_BURST_CANISTER_SHOT = 303

class AbilityKey(Enum):
    # 01 Brimstone (1-4)
    # 02 Viper (5-8)
    # 03 Omen (9-12)
    SHROUDED_STEP = 9
    PARANOIA = 10
    DARK_COVER = 11
    FROM_THE_SHADOWS = 12
    # 04 Killjoy (13-16)
    # 05 Cypher (17-20)
    # 06 Sova (21-24)
    # 07 Sage (25-28)
    # 08 - (29-32)
    # 09 Phoenix (33-36)
    # 10 Jett (37-40)
    # 11 Reyna (41-44)
    # 12 Raze (45-48)
    # 13 Breach (49-52)
    # 14 Skye (53-56)
    # 15 Yoru (57-60)
    # 16 Astra (61-64)
    # 17 KAY/O (65-68)
    # 18 Chamber (69-72)
    # 19 Neon (73-76)
    # 20 Fade (77-80)
    # 21 Harbor (81-84)
    # 22 Gekko (85-88)
    # 23 Deadlock (89-92)
    # 24 Iso (93-96)
    # 25 Clove (97-100)
    # 26 Vyse (101-104)
    # 27 Tejo (105-108)
    # 28 Waylay (109-112)

class MeleeKey(Enum):
    DEFAULT = 0
class SidearmKey(Enum):
    CLASSIC = 1
    SHORTY = 2
    FRENZY = 3
    GHOST = 4
    SHERIFF = 5
    GOLDEN_GUN = 6
    SNOWBALL_LAUNCHER = 7
    # 8-10 unused
class GunKey(Enum):
    # SMGs
    STINGER = 11
    SPECTRE = 12
    # Shotguns
    BUCKY = 13
    JUDGE = 14
    # Rifles
    BULLDOG = 15
    GUARDIAN = 16
    PHANTOM = 17
    VANDAL = 18
    # Sniper Rifles
    MARSHAL = 19
    OUTLAW = 20
    OP = 21
    # Machine Guns
    ARES = 22
    ODIN = 23

class AgentKey(Enum):
    BRIMSTONE = 1
    VIPER = 2
    OMEN = 3
    KILLJOY = 4
    CYPHER = 5
    SOVA = 6
    SAGE = 7
    # -- = 8
    PHOENIX = 9
    JETT = 10
    REYNA = 11
    RAZE = 12
    BREACH = 13
    SKYE = 14
    YORU = 15
    ASTRA = 16
    KAYO = 17
    CHAMBER = 18
    NEON = 19
    FADE = 20
    HARBOR = 21
    GEKKO = 22
    DEADLOCK = 23
    ISO = 24
    CLOVE = 25
    VYSE = 26
    TEJO = 27
    WAYLAY = 28

class SpriteSetKey(Enum):
    # AGENTS
    AGENT_BRIMSTONE = 1
    AGENT_VIPER = 2
    AGENT_OMEN = 3
    AGENT_KILLJOY = 4
    AGENT_CYPHER = 5
    AGENT_SOVA = 6
    AGENT_SAGE = 7
    AGENT_PHOENIX = 9
    AGENT_JETT = 10
    AGENT_REYNA = 11
    AGENT_RAZE = 12
    AGENT_BREACH = 13
    AGENT_SKYE = 14
    AGENT_YORU = 15
    AGENT_ASTRA = 16
    AGENT_KAYO = 17
    AGENT_CHAMBER = 18
    AGENT_NEON = 19
    AGENT_FADE = 20
    AGENT_HARBOR = 21
    AGENT_GEKKO = 22
    AGENT_DEADLOCK = 23
    AGENT_ISO = 24
    AGENT_CLOVE = 25
    AGENT_VYSE = 26
    AGENT_TEJO = 27
    AGENT_WAYLAY = 28
    
    # WEAPONS
    # Melee
    WEAPON_MELEE = 51
    # Sidearms
    WEAPON_CLASSIC = 52
    WEAPON_SHORTY = 53
    WEAPON_FRENZY = 54
    WEAPON_GHOST = 55
    WEAPON_SHERIFF = 56
    WEAPON_GOLDEN_GUN = 57
    WEAPON_SNOWBALL_LAUNCHER = 58
    # Primaries
    WEAPON_STINGER = 61
    WEAPON_SPECTRE = 62
    WEAPON_BUCKY = 63
    WEAPON_JUDGE = 64
    WEAPON_BULLDOG = 65
    WEAPON_GUARDIAN = 66
    WEAPON_PHANTOM = 67
    WEAPON_VANDAL = 68
    WEAPON_MARSHAL = 69
    WEAPON_OUTLAW = 70
    WEAPON_OP = 71
    WEAPON_ARES = 72
    WEAPON_ODIN = 73
    
    # Abilities
    # 01 Brimstone (1-4)
    # 02 Viper (5-8)
    # 03 Omen (9-12)
    ABILITY_SHROUDED_STEP = 9
    ABILITY_PARANOIA = 10
    ABILITY_DARK_COVER = 11
    ABILITY_FROM_THE_SHADOWS = 12
    # 04 Killjoy (13-16)
    # 05 Cypher (17-20)
    # 06 Sova (21-24)
    # 07 Sage (25-28)
    # 08 - (29-32)
    # 09 Phoenix (33-36)
    # 10 Jett (37-40)
    # 11 Reyna (41-44)
    # 12 Raze (45-48)
    # 13 Breach (49-52)
    # 14 Skye (53-56)
    # 15 Yoru (57-60)
    # 16 Astra (61-64)
    # 17 KAY/O (65-68)
    # 18 Chamber (69-72)
    # 19 Neon (73-76)
    # 20 Fade (77-80)
    # 21 Harbor (81-84)
    # 22 Gekko (85-88)
    # 23 Deadlock (89-92)
    # 24 Iso (93-96)
    # 25 Clove (97-100)
    # 26 Vyse (101-104)
    # 27 Tejo (105-108)
    # 28 Waylay (109-112)
    
    # OBJECTS

class GameModeKey(Enum):
    UNRATED = 0
    COMPETITIVE = 1
    DEATHMATCH = 2
    ESCALATION = 3
    SPIKE_RUSH = 4
    SWIFT_PLAY = 5
    TEAM_DEATHMATCH = 6
    REPLICATION = 7
    CUSTOM = 8

class ObjectiveKey(Enum):
    SPIKE = 0
    KILLS = 1

class KeyInputKey(Enum):
    MOUSE_LEFT = p.BUTTON_LEFT
    MOUSE_MIDDLE = p.BUTTON_MIDDLE
    MOUSE_RIGHT = p.BUTTON_RIGHT
    MOUSE_WHEEL_UP = p.BUTTON_WHEELUP
    MOUSE_WHEEL_DOWN = p.BUTTON_WHEELDOWN
    MOUSE_THUMB_4 = p.BUTTON_X1
    MOUSE_THUMB_5 = p.BUTTON_X2
    NUM_0 = p.K_0
    NUM_1 = p.K_1
    NUM_2 = p.K_2
    NUM_3 = p.K_3
    NUM_4 = p.K_4
    NUM_5 = p.K_5
    NUM_6 = p.K_6
    NUM_7 = p.K_7
    NUM_8 = p.K_8
    NUM_9 = p.K_9
    A = p.K_a
    B = p.K_b
    C = p.K_c
    D = p.K_d
    E = p.K_e
    F = p.K_f
    G = p.K_g
    H = p.K_h
    I = p.K_i
    J = p.K_j
    K = p.K_k
    L = p.K_l
    M = p.K_m
    N = p.K_n
    O = p.K_o
    P = p.K_p
    Q = p.K_q
    R = p.K_r
    S = p.K_s
    T = p.K_t
    U = p.K_u
    V = p.K_v
    W = p.K_w
    X = p.K_x
    Y = p.K_y
    Z = p.K_z
    UP = p.K_UP
    DOWN = p.K_DOWN
    LEFT = p.K_LEFT
    RIGHT = p.K_RIGHT
    SPACE = p.K_SPACE
    ESCAPE = p.K_ESCAPE
    RETURN = p.K_RETURN
    BACKSPACE = p.K_BACKSPACE
    TAB = p.K_TAB
    SHIFT = p.K_LSHIFT
    CTRL = p.K_LCTRL
    ALT = p.K_LALT

class InputKey(Enum):
    # Movement
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    JUMP = 4
    CROUCH = 5
    # Interaction
    FIRE = 6
    ALT_FIRE = 7
    RELOAD = 8
    INTERACT = 9
    INSPECT = 10
    # Inventory
    SPIKE = 11
    MELEE = 12
    SIDEARM = 13
    PRIMARY = 14
    BASIC = 15
    TACTICAL = 16
    SIGNATURE = 17
    ULTIMATE = 18
    # UI
    MENU = 20
    MAP = 19
    SCOREBOARD = 21
    CHAT = 22