from enum import Enum

class EventHead(Enum):
    END_SESSION = 0
    START_AGENT_SELECT_EVENT = 1
    UPDATE_REMAINING_SELECT_TIME_EVENT = 2
    GAME_START_EVENT = 3
    UPDATE_GAMESTATE_EVENT = 4

class RequestHead(Enum):
    PING_REQUEST = 100
    SELECT_AGENT = 101
    MOVEMENT_REQUEST = 102
    TURN_TO_REQUEST = 103
    SET_WALK_REQUEST = 104
    SET_CROUCH_REQUEST = 105

class MessageHead(Enum):
    PING = 200
    INITIATED = 201
    CONNECTED = 202
    HOSTED = 203
    CLIENT_CONNECTED = 204
    DISCONNECTED = 205
    OPEN_SERVER_AGENT_SELECT = 206
    LEAVE = 207
    JOIN = 208
    HOST = 209
    START = 210
    SELECT_AGENT = 211
    FORCE_START = 212
    START_AGENT_SELECT = 213
    END_AGENT_SELECT = 214
    UPDATE_REMAINING_SELECT_TIME = 215
    SERVER_GAME_START = 216
    CAST_UPDATE_GAMESTATE_EVENT = 217
    SEND_INPUT_REQUESTS = 218
    SEND_TURN_REQUEST = 219
    FORCE_DISCONNECT = 220


class DebugProblem(Enum):
    UNHANDLED_MESSAGE = 1
    UNHANDLED_EVENT = 2
    UNHANDLED_REQUEST = 3
    HANDLING_MESSAGE = 4
    HANDLING_EVENT = 5
    HANDLING_REQUEST = 6
    INITIATED = 7
    CLIENT_CONNECTED = 8
    CONNECTION_LOST = 9
    COULDNT_MOVE_PLAYER = 10
    COULDNT_MOVE_PLAYER_LOCALLY = 11
    NO_MOVEMENT_TICK = 12
    NO_MOUSE_HANDLING = 13
    UNHANDLED_INPUT = 14
    UNHANDLED_HELD_INPUT = 15
    WALK_STATUS_UNCHANGED = 16
    CROUCH_STATUS_UNCHANGED = 17
    COULDNT_UPDATE_GAMESTATE = 18
    NO_PLAYER_RESET_TO_LOCAL_VALUES = 19
    NO_PLAYER_RESET_TO_LOCAL_ORIENTATION = 20
    UNCOUNTED_MESSAGE = 21
    UNCOUNTED_EVENT = 22
    UNCOUNTED_REQUEST = 23
    AUTOMATION_UNSUCCESSFUL = 24
    FAST_TICK = 25
    SLOW_TICK = 26
    SELF_UPDATE = 27
    QUITTING = 28
class DebugReason(Enum):
    EMPTY = 0
    INVALID_MESSAGE_HEAD = 1
    INVALID_EVENT_HEAD = 2
    INVALID_REQUEST_HEAD = 3
    NO_MATCHING_MESSAGE_HEAD = 4
    NO_MATCHING_EVENT_HEAD = 5
    NO_MATCHING_REQUEST_HEAD = 6
    EXPECTED = 7
    CYCLE = 8
    COMM_IS_NONE = 9
    COMM_NOT_INITIALIZED = 10
    SESSION_ENDED = 11
    LOCAL_GAMESTATE_IS_NONE = 12
    PLAYER_NOT_FOUND_LOCALLY = 13
    PLAYER_IS_DEAD = 14
    NOT_INGAME = 15
    NO_INPUTTYPE_MATCH = 16
    LOCAL_PLAYER_IS_NONE = 17
    LOCAL_ANGLE_IS_NONE = 18
    SERVER_TOO_SLOW = 19
    INPUT = 20
    INVALID_INPUT_NUM = 21
class DebugDetails(Enum):
    EMPTY = 0
    MESSAGE_HEAD = 1
    EVENT_HEAD = 2
    REQUEST_HEAD = 3
    FULL_MESSAGE = 4
    FULL_EVENT = 5
    FULL_REQUEST = 6
    CLIENT_NAME = 7
    CLIENT_NAME_IS_NONE = 8
    PLAYER_NAME = 9
    PLAYER_OBJECT = 10
    INPUTTYPE = 11
    TICK_SPEED = 12
    KEY_NUM = 13

P = DebugProblem
debugProblems: dict[DebugProblem, tuple[str, str]] = {
    P.UNHANDLED_MESSAGE: ("Unhandled Message", "🛠️"),
    P.UNHANDLED_EVENT: ("Unhandled Event", "📅"),
    P.UNHANDLED_REQUEST: ("Unhandled Request", "📡"),
    P.HANDLING_MESSAGE: ("Handling Message", "🛠️"),
    P.HANDLING_EVENT: ("Handling Event", "📅"),
    P.HANDLING_REQUEST: ("Handling Request", "📡"),
    P.INITIATED: ("+++Initiated+++", ""),
    P.CLIENT_CONNECTED: ("Client connected", ""),
    P.CONNECTION_LOST: ("Connection lost", ""),
    P.COULDNT_MOVE_PLAYER: ("Couldn't move player", ""),
    P.COULDNT_MOVE_PLAYER_LOCALLY: ("Couldn't move player locally", ""),
    P.NO_MOVEMENT_TICK: ("Couldn't do Movement-Tick", ""),
    P.NO_MOUSE_HANDLING: ("Couldn't handle Mouse Movement", ""),
    P.UNHANDLED_INPUT: ("Unhandled Input", "🎮"),
    P.UNHANDLED_HELD_INPUT: ("Unhandled Held Input", "🎮"),
    P.WALK_STATUS_UNCHANGED: ("Couldn't change Walk Status", ""),
    P.CROUCH_STATUS_UNCHANGED: ("Couldn't change Crouch Status", ""),
    P.COULDNT_UPDATE_GAMESTATE: ("Couldn't update Gamestate", ""),
    P.NO_PLAYER_RESET_TO_LOCAL_VALUES: ("Couldn't reset Player Values to local ones", ""),
    P.NO_PLAYER_RESET_TO_LOCAL_ORIENTATION: ("Couldn't reset Player Orientation to local one", ""),
    P.UNCOUNTED_MESSAGE: ("Couldn't count Message", ""),
    P.UNCOUNTED_EVENT: ("Couldn't count Event", ""),
    P.UNCOUNTED_REQUEST: ("Couldn't count Request", ""),
    P.AUTOMATION_UNSUCCESSFUL: ("Couldn't handle Automation", ""),
    P.FAST_TICK: ("Tick fast enough", ""),
    P.SLOW_TICK: ("Tick too slow", ""),
    P.SELF_UPDATE: ("Self Updating", ""),
    P.QUITTING: ("Quitting Process", ""),
}

R = DebugReason
debugReasons: dict[DebugReason, tuple[str, str]] = {
    R.EMPTY: ("", ""),
    R.INVALID_MESSAGE_HEAD: ("Unknown Message Head", ""),
    R.INVALID_EVENT_HEAD: ("Unknown Event Head", ""),
    R.INVALID_REQUEST_HEAD: ("Unknown Request Head", ""),
    R.NO_MATCHING_MESSAGE_HEAD: ("No matching Case for Message Head", ""),
    R.NO_MATCHING_EVENT_HEAD: ("No matching Case for Event Head", ""),
    R.NO_MATCHING_REQUEST_HEAD: ("No matching Case for Request Head", ""),
    R.EXPECTED: ("Expected Behaviour", "✅"),
    R.CYCLE: ("Cycle Behaviour", "🔄"),
    R.COMM_IS_NONE: ("Comm is None", ""),
    R.COMM_NOT_INITIALIZED: ("Comm not correctly initialised", ""),
    R.SESSION_ENDED: ("Session was ended by Host", ""),
    R.LOCAL_GAMESTATE_IS_NONE: ("Local Gamestate is None", ""),
    R.PLAYER_NOT_FOUND_LOCALLY: ("Player wasn't found in local Gamestate", ""),
    R.PLAYER_IS_DEAD: ("Player is dead", ""),
    R.NOT_INGAME: ("Not In-Game", ""),
    R.NO_INPUTTYPE_MATCH: ("No matching Case for Input-Type", ""),
    R.LOCAL_PLAYER_IS_NONE: ("Local Player is None", ""),
    R.LOCAL_ANGLE_IS_NONE: ("Local Orientation is None", ""),
    R.SERVER_TOO_SLOW: ("Server is too slow", ""),
    R.INPUT: ("Manual Input", ""),
    R.INVALID_INPUT_NUM: ("Invalid Key Number", ""),
}

DD = DebugDetails
debugDetails: dict[DebugDetails, tuple[str, str]] = {
    DD.EMPTY: ("", ""),
    DD.MESSAGE_HEAD: ("Message Head", ""),
    DD.EVENT_HEAD: ("Event Head", ""),
    DD.REQUEST_HEAD: ("Request Head", ""),
    DD.FULL_MESSAGE: ("Message", ""),
    DD.FULL_EVENT: ("Event", ""),
    DD.FULL_REQUEST: ("Request", ""),
    DD.CLIENT_NAME: ("Client Name", ""),
    DD.CLIENT_NAME_IS_NONE: ("Client Name is None", ""),
    DD.PLAYER_NAME: ("Player Name", ""),
    DD.PLAYER_OBJECT: ("Player", ""),
    DD.INPUTTYPE: ("Input-Type", ""),
    DD.TICK_SPEED: ("Tick-Speed", ""),
    DD.KEY_NUM: ("Key-Number", ""),
}