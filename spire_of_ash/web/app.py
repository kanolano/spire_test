"""The HTTP server.

One route table instead of an if/elif chain, one run per client instead of a
process-wide global, and errors that reach the browser as structured JSON rather
than a bare 500 the UI silently swallows.
"""

import argparse
import hashlib
import http.cookies
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..engine import records
from ..engine.errors import InvalidAction
from .dto import CLASS_ROSTER, piles_view, view
from .launcher import open_browser, quiet_terminal
from .sessions import COOKIE, SessionStore

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
UI_FILE = os.path.join(STATIC_DIR, "index.html")
CONTENT_TYPES = {".html": "text/html; charset=utf-8",
                 ".css": "text/css; charset=utf-8",
                 ".js": "text/javascript; charset=utf-8",
                 ".svg": "image/svg+xml",
                 ".woff2": "font/woff2"}
MAX_BODY = 64 * 1024          # actions are tiny; refuse anything remotely large
DEFAULT_PORT = 8765

log = logging.getLogger("spire")


class Handler(BaseHTTPRequestHandler):
    server_version = "SpireOfAsh"
    protocol_version = "HTTP/1.1"
    _body = b""                   # set per-request by do_POST

    # ── plumbing ──
    @property
    def store(self):
        return self.server.store

    def _send(self, code, body, ctype, extra_headers=()):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in extra_headers:
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200, extra_headers=()):
        self._send(code, json.dumps(obj), "application/json",
                   tuple(extra_headers) + (("Cache-Control", "no-store"),))

    def _error(self, code, message):
        """Errors are JSON so the client can show them instead of guessing."""
        self._json({"error": message}, code)

    def _cookie_sid(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            jar = http.cookies.SimpleCookie(raw)
        except http.cookies.CookieError:
            return None
        morsel = jar.get(COOKIE)
        return morsel.value if morsel else None

    @staticmethod
    def _set_cookie(sid):
        return ("Set-Cookie",
                f"{COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400")

    def _session(self, create=True):
        """The caller's session, minting one (and a cookie) on first contact."""
        sid = self._cookie_sid()
        session = self.store.get(sid)
        if session:
            return session, ()
        if not create:
            return None, ()
        session = self.store.create()
        return session, (self._set_cookie(session.sid),)

    def _same_origin(self):
        """Reject cross-site POSTs. Localhost-only, but free to enforce."""
        origin = self.headers.get("Origin")
        if origin is None:
            return True                     # curl and same-origin form posts
        host = self.headers.get("Host", "")
        return origin.split("//")[-1] == host

    def _drain_body(self):
        """Take the whole request body off the socket.

        This has to happen for *every* POST, including ones we refuse. We speak
        HTTP/1.1, so the connection is reused: bytes left unread become the
        start of the next request line. /abandon never read its body, so the
        very next click after Quit was parsed as a request whose method was
        `{}POST` and came back 501.
        """
        raw = self.headers.get("Content-Length") or "0"
        try:
            n = int(raw)
        except ValueError:
            raise InvalidAction("Bad Content-Length header.")
        if n < 0 or n > MAX_BODY:
            # Do not read it just to throw it away; the stream is untrustworthy
            # from here, so hang up rather than reuse the connection.
            self.close_connection = True
            raise InvalidAction("Request body too large.")
        return self.rfile.read(n)

    def _read_body(self):
        """The JSON body. do_POST has already drained it off the socket."""
        try:
            return json.loads(self._body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise InvalidAction("Body is not valid JSON.")

    # ── routes ──
    def do_GET(self):
        self._dispatch(GET_ROUTES)

    def do_HEAD(self):
        self._dispatch(GET_ROUTES)

    def do_POST(self):
        try:
            self._body = self._drain_body()
        except InvalidAction as e:
            self._error(400, str(e))
            return
        if not self._same_origin():
            self._error(403, "Cross-origin requests are not allowed.")
            return
        self._dispatch(POST_ROUTES)

    def _dispatch(self, routes):
        path = self.path.split("?")[0].rstrip("/") or "/"
        handler = routes.get(path)
        if handler is None and routes is GET_ROUTES and path.startswith("/static/"):
            handler = _static_handler(path)
        if handler is None:
            self._error(404, f"No route for {path}.")
            return
        try:
            handler(self)
        except InvalidAction as e:
            self._error(400, str(e))
        except BrokenPipeError:
            pass
        except Exception:
            log.exception("unhandled error on %s %s", self.command, path)
            self._error(500, "The engine hit an unexpected error.")

    def log_message(self, fmt, *args):
        log.info("%s %s", self.address_string(), fmt % args)


# ── handlers ──
def _serve_file(h, path, ctype):
    try:
        with open(path, "rb") as f:
            body = f.read()
    except OSError:
        log.error("static file missing: %s", path)
        h._error(500, "A file this page needs is missing on the server.")
        return
    etag = '"%s"' % hashlib.sha256(body).hexdigest()[:32]
    if h.headers.get("If-None-Match") == etag:
        h.send_response(304)
        h.send_header("ETag", etag)
        h.send_header("Content-Length", "0")
        h.end_headers()
        return
    h._send(200, body, ctype, (("ETag", etag), ("Cache-Control", "no-cache")))


def serve_ui(h):
    _serve_file(h, UI_FILE, CONTENT_TYPES[".html"])


def _static_handler(path):
    """Resolve /static/<name>, refusing anything that escapes the directory."""
    name = path[len("/static/"):]
    target = os.path.normpath(os.path.join(STATIC_DIR, name))
    if os.path.commonpath([target, STATIC_DIR]) != STATIC_DIR:
        return None
    if not os.path.isfile(target):
        return None
    ctype = CONTENT_TYPES.get(os.path.splitext(target)[1], "application/octet-stream")
    return lambda h: _serve_file(h, target, ctype)


def get_state(h):
    session, cookie = h._session()
    with session.lock:
        h._json(view(session.run), extra_headers=cookie)


def get_records(h):
    h._json(records.load_records())


def get_classes(h):
    h._json(CLASS_ROSTER)


def get_piles(h):
    """Draw/discard/exhaust contents, only when the player asks to see them."""
    session, cookie = h._session()
    with session.lock:
        h._json(piles_view(session.run), extra_headers=cookie)


def post_action(h):
    action = h._read_body()
    session, cookie = h._session()
    with session.lock:
        run = session.run
        was_finished = run.finished
        run.apply(action)
        if run.finished and not was_finished:
            _record_result(run)
        payload = view(run)
        try:
            h.store.save(session)
        except OSError:
            log.warning("could not persist session %s", session.sid)
    h._json(payload, extra_headers=cookie)


def post_abandon(h):
    """Throw the current run away and start fresh."""
    sid = h._cookie_sid()
    if sid:
        h.store.discard(sid)
    session = h.store.create()
    with session.lock:
        h._json(view(session.run), extra_headers=(h._set_cookie(session.sid),))


def _record_result(run):
    try:
        records.save_record(run.summary(run.screen == "win"))
    except OSError:
        log.warning("could not write the leaderboard")


GET_ROUTES = {
    "/": serve_ui,
    "/index.html": serve_ui,
    "/state": get_state,
    "/records": get_records,
    "/classes": get_classes,
    "/piles": get_piles,
}
POST_ROUTES = {
    "/action": post_action,
    "/abandon": post_abandon,
}


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, store):
        self.store = store
        super().__init__(addr, Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="spire-web",
                                     description="Play Spire of Ash in a browser.")
    parser.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-open", action="store_true",
                        help="don't launch a browser")
    parser.add_argument("--runs-dir", default=os.path.join(HERE, "..", "..", "runs"),
                        help="where to save runs so they survive a restart")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s")

    store = SessionStore(directory=os.path.abspath(args.runs_dir))
    srv = Server((args.host, args.port), store)
    url = f"http://{args.host}:{args.port}"
    with quiet_terminal():
        print(f"\n  Spire of Ash — open {url} in your browser")
        print("  (ctrl-c here to stop the server)\n")
        if not args.no_open:
            open_browser(url)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n  The Spire waits.\n")
        finally:
            srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
