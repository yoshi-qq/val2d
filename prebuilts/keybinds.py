from classes.keys import KeyInputKey, InputKey

K = KeyInputKey
I = InputKey

DEFAULT_KEY_BINDS: dict[KeyInputKey, InputKey] = {
    # Movement
    K.W: I.UP,
    K.S: I.DOWN,
    K.A: I.LEFT,
    K.D: I.RIGHT,
    K.SPACE: I.JUMP,
    K.CTRL: I.CROUCH,
    # Interaction
    K.MOUSE_LEFT: I.FIRE,
    K.MOUSE_RIGHT: I.ALT_FIRE,
    K.R: I.RELOAD,
    K.F: I.INTERACT,
    K.Y: I.INSPECT,
    # Inventory
    K.NUM_4: I.SPIKE,
    K.NUM_3: I.MELEE,
    K.NUM_2: I.SIDEARM,
    K.NUM_1: I.PRIMARY,
    K.C: I.BASIC,
    K.Q: I.TACTICAL,
    K.E: I.SIGNATURE,
    K.X: I.ULTIMATE,
    # UI
    K.ESCAPE: I.MENU,
    K.M: I.MAP,
    K.TAB: I.SCOREBOARD,
    K.RETURN: I.CHAT,
}

keybinds = DEFAULT_KEY_BINDS