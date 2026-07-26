"""Keeping the launching terminal tidy while the server runs in the foreground.

This is terminal handling, not HTTP, so it does not belong in the server module —
but the *web* command is what needs it, because launching a browser is what tends
to leave a tty in a strange state.
"""

import contextlib
import os
import sys
import webbrowser

try:
    import termios
except ImportError:      # Windows
    termios = None


# The game lives in the browser, but the server keeps a terminal in the
# foreground.  If anything switches the terminal's mouse reporting on (a browser
# launcher poking the tty, or a leftover mode from an earlier program), every
# mouse move sends an escape sequence that the tty happily echoes back at us as
# gibberish like "35;80;24M".  Turn reporting off, and keep echo off while we run.
MOUSE_OFF = "".join("\033[?%dl" % m for m in (1000, 1002, 1003, 1004, 1005, 1006, 1015))


def _tty_fd():
    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            return sys.stdin.fileno()
    except (ValueError, OSError):
        pass
    return None


def _write_tty(text):
    with contextlib.suppress(Exception):
        if sys.stdout.isatty():  # never scribble escapes into a pipe or log file
            sys.stdout.write(text)
            sys.stdout.flush()


@contextlib.contextmanager
def quiet_terminal():
    """Silence mouse-report noise for as long as the server is in the foreground."""
    fd = _tty_fd()
    saved = None
    if fd is not None and termios is not None:
        with contextlib.suppress(termios.error, OSError):
            saved = termios.tcgetattr(fd)
            attrs = list(saved)
            attrs[3] &= ~termios.ECHO  # lflags; ISIG stays on so ctrl-c still works
            termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
    _write_tty(MOUSE_OFF)
    try:
        yield
    finally:
        _write_tty(MOUSE_OFF)  # again: the browser launcher may have re-enabled it
        if saved is not None:
            with contextlib.suppress(termios.error, OSError):
                termios.tcsetattr(fd, termios.TCSADRAIN, saved)
                termios.tcflush(fd, termios.TCIFLUSH)  # drop queued mouse bytes


def open_browser(url):
    """webbrowser.open(), but with the launcher detached from our terminal.

    Popen inherits stdin/stdout/stderr, so `gio open` & friends (or a console
    browser fallback) can write escape sequences straight into our tty.
    """
    with contextlib.suppress(Exception):
        sys.stdout.flush()
        sys.stderr.flush()
        saved = [os.dup(fd) for fd in (0, 1, 2)]
        null = os.open(os.devnull, os.O_RDWR)
        try:
            for fd in (0, 1, 2):
                os.dup2(null, fd)
            webbrowser.open(url)
        finally:
            for fd, old in zip((0, 1, 2), saved):
                os.dup2(old, fd)
                os.close(old)
            os.close(null)
