"""Engine exceptions."""


class Defeat(Exception):
    """The player died. The message names what killed them."""


class InvalidAction(Exception):
    """The client sent an action the current state cannot accept.

    Front-ends should surface the message rather than swallowing it — a silently
    ignored action is indistinguishable from a hung UI.
    """
