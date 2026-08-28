"""The HTTP layer: routing, validation, session isolation, resume."""

import http.client
import json
import os
import re
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import helpers  # noqa: F401  (puts the package on sys.path)

from spire_of_ash import balance as B
from spire_of_ash.engine.run import Run
from spire_of_ash.web import app as web_app
from spire_of_ash.web.dto import view
from spire_of_ash.web.sessions import SessionStore


def _decode(raw, headers):
    """JSON bodies come back parsed; anything else (the UI) stays bytes."""
    if not raw:
        return None
    if "json" in (headers.get("Content-Type") or ""):
        return json.loads(raw)
    return raw


class Client:
    """A tiny cookie-keeping HTTP client."""

    def __init__(self, base):
        self.base = base
        self.cookie = None

    def request(self, path, data=None, headers=None, method=None):
        url = self.base + path
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body,
                                     method=method or ("POST" if body else "GET"))
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req) as r:
                raw = r.read()
                set_cookie = r.headers.get("Set-Cookie")
                if set_cookie:
                    self.cookie = set_cookie.split(";")[0]
                return r.status, _decode(raw, r.headers), r.headers
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {"raw": raw.decode(errors="replace")}
            return e.code, payload, e.headers


class WebTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.store = SessionStore(directory=os.path.join(cls.dir, "runs"))
        cls.server = web_app.Server(("127.0.0.1", 0), cls.store)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def client(self):
        return Client(self.base)


class TestRouting(WebTestCase):
    def test_unknown_path_is_404_json(self):
        status, body, _ = self.client().request("/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_state_returns_a_run(self):
        status, body, _ = self.client().request("/state")
        self.assertEqual(status, 200)
        self.assertIn("screen", body)
        self.assertIn("player", body)

    def test_records_endpoint(self):
        status, body, _ = self.client().request("/records")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)

    def test_classes_endpoint(self):
        status, body, _ = self.client().request("/classes")
        self.assertEqual(status, 200)
        self.assertTrue(any(d["key"] == "sentinel" for d in body))

    def test_state_is_idempotent(self):
        c = self.client()
        _, first, _ = c.request("/state")
        _, second, _ = c.request("/state")
        self.assertEqual(first, second)


class TestAscensionOverTheWire(WebTestCase):
    """The ladder is only a feature if a client can actually choose a rung."""

    def test_the_select_screen_is_told_what_each_rung_does(self):
        c = self.client()
        _, body, _ = c.request("/state")
        self.assertEqual(body["screen"], "select")
        ladder = body["ascension_ladder"]
        self.assertEqual([r["level"] for r in ladder],
                         list(range(1, B.MAX_ASCENSION + 1)))
        self.assertTrue(all(r["desc"] for r in ladder))

    def test_a_run_starts_at_the_rung_it_was_asked_for(self):
        c = self.client()
        _, body, _ = c.request("/action",
                               {"type": "new_run", "cls": "sentinel", "ascension": 5})
        self.assertEqual(body["ascension"], 5)
        # Rung 3 takes health off the top, so the climb starts hurt.
        self.assertLess(body["player"]["hp"], body["player"]["max_hp"])

    def test_omitting_it_is_the_plain_climb(self):
        c = self.client()
        _, body, _ = c.request("/action", {"type": "new_run", "cls": "sentinel"})
        self.assertEqual(body["ascension"], 0)
        self.assertEqual(body["player"]["hp"], body["player"]["max_hp"])

    def test_a_nonsense_rung_is_400_not_500(self):
        c = self.client()
        status, body, _ = c.request(
            "/action", {"type": "new_run", "cls": "sentinel", "ascension": "high"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_the_rung_survives_a_reload(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "sentinel", "ascension": 4})
        _, body, _ = c.request("/state")
        self.assertEqual(body["ascension"], 4)


class TestValidation(WebTestCase):
    def test_wrong_field_type_is_400_not_500(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "sentinel"})
        status, body, _ = c.request("/action", {"type": "play", "idx": "1"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_unknown_action_is_400(self):
        c = self.client()
        status, body, _ = c.request("/action", {"type": "nope"})
        self.assertEqual(status, 400)

    def test_malformed_json_is_400(self):
        req = urllib.request.Request(self.base + "/action", data=b"{oops",
                                     method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_oversized_body_is_rejected(self):
        payload = json.dumps({"type": "map", "idx": 0, "pad": "x" * 200_000}).encode()
        req = urllib.request.Request(self.base + "/action", data=payload,
                                     method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    def test_cross_origin_post_is_refused(self):
        c = self.client()
        status, body, _ = c.request("/action", {"type": "new_run"},
                                    headers={"Origin": "http://evil.example"})
        self.assertEqual(status, 403)

    def test_wrong_screen_action_is_400(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "sentinel"})
        status, _, _ = c.request("/action", {"type": "end_turn"})
        self.assertEqual(status, 400)


class TestSessions(WebTestCase):
    def test_two_clients_get_independent_runs(self):
        a, b = self.client(), self.client()
        _, sa, _ = a.request("/action", {"type": "new_run", "cls": "sentinel"})
        _, sb, _ = b.request("/action", {"type": "new_run", "cls": "ashwalker"})
        self.assertEqual(sa["player"]["cls"], "sentinel")
        self.assertEqual(sb["player"]["cls"], "ashwalker")
        self.assertNotEqual(a.cookie, b.cookie)

    def test_one_client_advancing_does_not_move_another(self):
        a, b = self.client(), self.client()
        a.request("/action", {"type": "new_run", "cls": "sentinel"})
        b.request("/action", {"type": "new_run", "cls": "sentinel"})
        _, before, _ = b.request("/state")
        a.request("/action", {"type": "map", "idx": 0})
        _, after, _ = b.request("/state")
        self.assertEqual(before, after)
        _, moved, _ = a.request("/state")
        self.assertNotEqual(moved["floor"], after["floor"])

    def test_session_survives_eviction_via_the_save_file(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "ashwalker"})
        c.request("/action", {"type": "map", "idx": 0})
        _, before, _ = c.request("/state")
        sid = c.cookie.split("=", 1)[1]
        self.store._sessions.clear()          # simulate a restart / eviction
        _, after, _ = c.request("/state")
        self.assertEqual(after["player"]["cls"], "ashwalker")
        self.assertEqual(after["screen"], before["screen"])

    def test_abandon_starts_a_fresh_run(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "sentinel"})
        c.request("/action", {"type": "map", "idx": 0})
        status, body, _ = c.request("/abandon", {})
        self.assertEqual(status, 200)
        self.assertEqual(body["floor"], 0)
        # the Quit button's whole point: land back on character select
        self.assertEqual(body["screen"], "select")
        self.assertIn("classes", body)

    def test_climbing_again_can_keep_the_class(self):
        """"Climb again" used to send new_run with no class, silently
        restarting whoever DEFAULT_CLASS is rather than who you played."""
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "ashwalker"})
        _, body, _ = c.request("/action", {"type": "new_run", "cls": "ashwalker"})
        self.assertEqual(body["player"]["cls"], "ashwalker")

    def test_a_post_does_not_desync_a_kept_alive_connection(self):
        """/abandon never read its body, and the server speaks HTTP/1.1: the
        unread bytes became the next request line, so the click after Quit came
        back 501 Unsupported method."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        try:
            hdrs = {"Content-Type": "application/json"}
            conn.request("POST", "/abandon", body="{}", headers=hdrs)
            first = conn.getresponse()
            first.read()
            self.assertEqual(first.status, 200)
            cookie = (first.getheader("Set-Cookie") or "").split(";")[0]

            # same connection, as a browser would
            conn.request("POST", "/action",
                         body=json.dumps({"type": "new_run", "cls": "ashwalker"}),
                         headers=dict(hdrs, Cookie=cookie))
            second = conn.getresponse()
            payload = json.loads(second.read())
            self.assertEqual(second.status, 200)
            self.assertEqual(payload["player"]["cls"], "ashwalker")
        finally:
            conn.close()

    def test_a_refused_cross_origin_post_also_drains(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        try:
            conn.request("POST", "/action", body=json.dumps({"type": "new_run"}),
                         headers={"Content-Type": "application/json",
                                  "Origin": "http://evil.example"})
            first = conn.getresponse()
            first.read()
            self.assertEqual(first.status, 403)
            conn.request("GET", "/state")
            second = conn.getresponse()
            second.read()
            self.assertEqual(second.status, 200)
        finally:
            conn.close()

    def test_store_evicts_over_the_cap(self):
        store = SessionStore(directory=None, max_sessions=3)
        for _ in range(10):
            store.create()
        self.assertLessEqual(store.count(), 3)

    def test_store_rejects_a_traversing_sid(self):
        store = SessionStore(directory=os.path.join(self.dir, "paths"))
        self.assertIsNone(store._path("../../etc/passwd"))
        self.assertIsNone(store._path(".hidden"))
        self.assertIsNotNone(store._path("a-normal-sid"))


class TestUi(WebTestCase):
    def test_index_is_served_with_an_etag(self):
        status, _, headers = self.client().request("/")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("ETag"))

    def test_etag_revalidation_returns_304(self):
        c = self.client()
        _, _, headers = c.request("/")
        etag = headers.get("ETag")
        req = urllib.request.Request(self.base + "/")
        req.add_header("If-None-Match", etag)
        # urllib raises on 3xx it cannot follow, so 304 arrives as an HTTPError
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 304)


class TestStatic(WebTestCase):
    def test_every_asset_the_shell_references_is_served(self):
        """The client is a hashed bundle, so the filenames change on every
        build. Asking index.html what it needs keeps this honest without
        pinning names the build owns."""
        status, body, _ = self.client().request("/")
        self.assertEqual(status, 200)
        refs = re.findall(r'(?:src|href)="(/static/[^"]+)"', body.decode())
        self.assertTrue(refs, "index.html references no assets")

        expected = {".css": "text/css", ".js": "text/javascript"}
        for path in refs:
            status, _, headers = self.client().request(path)
            self.assertEqual(status, 200, path)
            ctype = expected.get(os.path.splitext(path)[1])
            if ctype:
                self.assertIn(ctype, headers.get("Content-Type"), path)

    def test_path_traversal_is_refused(self):
        status, _, _ = self.client().request("/static/../app.py")
        self.assertEqual(status, 404)

    def test_missing_asset_is_404(self):
        status, _, _ = self.client().request("/static/nope.js")
        self.assertEqual(status, 404)

    def test_piles_are_fetched_separately(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "sentinel"})
        _, state, _ = c.request("/action", {"type": "map", "idx": 0})
        if state["screen"] != "combat":
            self.skipTest("this seed did not open on a combat node")
        # counts travel with state; contents do not
        self.assertIn("draw", state["combat"])
        self.assertNotIn("draw_pile", state["combat"])
        _, piles, _ = c.request("/piles")
        self.assertEqual(len(piles["draw_pile"]), state["combat"]["draw"])

    def test_piles_outside_combat_are_empty(self):
        c = self.client()
        c.request("/action", {"type": "new_run", "cls": "sentinel"})
        _, piles, _ = c.request("/piles")
        self.assertEqual(piles["draw_pile"], [])


class TestDto(unittest.TestCase):
    def test_view_is_json_serialisable_on_every_screen(self):
        for seed in range(8):
            run = Run("sentinel", seed=seed)
            for _ in range(60):
                json.dumps(view(run))
                if run.finished:
                    break
                helpers.autoplay(run, seed=seed, max_steps=1, keep_alive=True)

    def test_relics_and_potions_are_expanded(self):
        run = Run("sentinel", seed=1)
        run.player.potions.append("fire")
        v = view(run)
        self.assertIn("name", v["player"]["relics"][0])
        self.assertIn("desc", v["player"]["potions"][0])

    def test_statuses_ship_their_explanation(self):
        """The chip shows "Vuln 2"; the tooltip needs the rest."""
        run = Run("sentinel", seed=1)
        run.player.st["vulnerable"] = 2
        chip = view(run)["player"]["statuses"][0]
        self.assertEqual(chip["label"], "Vuln")
        self.assertEqual(chip["name"], "Vulnerable")
        self.assertIn("more damage", chip["desc"])

    def test_event_options_ship_a_preview(self):
        run = Run("sentinel", seed=1)
        run.open_event()
        for opt in view(run)["event"]["options"]:
            self.assertTrue(opt["label"] and opt["preview"])

    def test_event_options_survive_a_pre_preview_save(self):
        """Saves written before previews existed stored bare label strings."""
        run = Run("sentinel", seed=1)
        run.open_event()
        run.event["options"] = ["Ask for healing", "Leave"]
        self.assertEqual(view(run)["event"]["options"],
                         [{"label": "Ask for healing", "preview": ""},
                          {"label": "Leave", "preview": ""}])

    def test_reward_ships_what_is_still_claimable(self):
        run = Run("sentinel", seed=5)
        run.start_combat("elite")
        run.victory()
        r = view(run)["reward"]
        self.assertFalse(r["relic_taken"] or r["card_taken"])
        self.assertIn("desc", r["relic"])
        run.apply({"type": "reward", "what": "relic"})
        self.assertTrue(view(run)["reward"]["relic_taken"])

    def test_the_upgrade_picker_ships_what_each_card_becomes(self):
        run = Run("sentinel", seed=5)
        run.screen = "rest"
        run.apply({"type": "smith"})
        cards = view(run)["choose"]["cards"]
        self.assertTrue(cards)
        strike = next(c for c in cards if c["key"] == "strike")
        self.assertEqual(strike["desc"], "Deal 6 damage.")
        self.assertEqual(strike["up"]["name"], "Strike+")
        self.assertEqual(strike["up"]["desc"], "Deal 9 damage.")

    def test_the_deck_view_answers_it_too(self):
        """The picker is two clicks deep inside a campfire; the deck is one key."""
        run = Run("sentinel", seed=5)
        deck = view(run)["deck"]
        self.assertTrue(all(c["up"] for c in deck), "every starter is upgradable")
        bash = next(c for c in deck if c["key"] == "bash")
        self.assertEqual(bash["up"]["desc"], "Deal 10 damage. Apply 3 Vulnerable.")

    def test_an_already_upgraded_card_has_nothing_to_preview(self):
        run = Run("sentinel", seed=5)
        run.player.deck[0].upgrade()
        upgraded = [c for c in view(run)["deck"] if c["upgraded"]]
        self.assertTrue(upgraded)
        self.assertTrue(all(c["up"] is None for c in upgraded))

    def test_previewing_an_upgrade_does_not_apply_it(self):
        run = Run("sentinel", seed=5)
        run.screen = "rest"
        run.apply({"type": "smith"})
        view(run)
        self.assertFalse(any(k.upgraded for k in run.player.deck))

    def test_other_pickers_carry_no_upgrade_preview(self):
        run = Run("sentinel", seed=5)
        run.open_choose("remove", "Remove", list(run.player.deck), "map")
        self.assertNotIn("up", view(run)["choose"]["cards"][0])

    def test_class_roster_only_ships_on_the_select_screen(self):
        picked = Run("sentinel", seed=1)
        self.assertNotIn("classes", view(picked))
        selecting = Run(seed=1)
        self.assertIn("classes", view(selecting))


if __name__ == "__main__":
    unittest.main()
