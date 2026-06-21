"""Integration tests over real HTTP — starts the stdlib server on an ephemeral port and
drives it with urllib. Each test uses a unique symbol/account so the shared server state
does not bleed between tests.
"""

import json
import threading
import unittest
import urllib.error
import urllib.request

from services.api.server import make_server


class HttpApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)          # port 0 -> OS picks a free port
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def req(self, method, path, body=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            url, data=data, method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_readyz(self):
        status, payload = self.req("GET", "/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")

    def test_request_id_header_echoed(self):
        url = f"http://127.0.0.1:{self.port}/health"
        req = urllib.request.Request(url, headers={"X-Request-Id": "abc123"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.headers.get("X-Request-Id"), "abc123")

    def test_health(self):
        status, payload = self.req("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_end_to_end_over_http(self):
        self.assertEqual(self.req("POST", "/instruments/equity", {"symbol": "MSFT"})[0], 201)
        self.assertEqual(self.req("POST", "/accounts/a1/fund", {"amount": 10_000})[0], 200)

        # Seed a resting ask by funding b1 and letting b1 short-sell (allowed in reference).
        sell_status, sell = self.req(
            "POST", "/orders",
            {"account": "b1", "symbol": "MSFT", "side": "sell", "price": 150.25, "quantity": 10},
        )
        self.assertEqual(sell_status, 201)
        self.assertEqual(sell["status"], "new")

        # a1 buys, crossing the ask.
        buy_status, buy = self.req(
            "POST", "/orders",
            {"account": "a1", "symbol": "MSFT", "side": "buy", "price": 150.25, "quantity": 10},
        )
        self.assertEqual(buy_status, 201)
        self.assertEqual(buy["status"], "filled")
        self.assertEqual(buy["filled"], 10.0)

        bal_status, bal = self.req("GET", "/accounts/a1/balance")
        self.assertEqual(bal_status, 200)
        self.assertEqual(bal["cash"], 10_000.0 - 1_502.50)

        _, order = self.req("GET", f"/orders/{buy['id']}")
        self.assertEqual(order["status"], "filled")

    def test_unknown_instrument_rejected_200_with_reason(self):
        self.req("POST", "/accounts/a2/fund", {"amount": 1_000})
        status, payload = self.req(
            "POST", "/orders",
            {"account": "a2", "symbol": "NOPE", "side": "buy", "price": 10.0, "quantity": 1},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["status"], "rejected")
        self.assertIn("unknown instrument", payload["reject_reason"])

    def test_pricing_endpoint(self):
        status, payload = self.req(
            "POST", "/pricing/option",
            {"S": 100, "K": 100, "t": 1, "r": 0.05, "sigma": 0.2, "right": "call"},
        )
        self.assertEqual(status, 200)
        self.assertGreater(payload["price"], 0.0)

    def test_kill_switch_endpoint(self):
        status, payload = self.req("POST", "/risk/kill", {"engaged": True})
        self.assertEqual(status, 200)
        self.assertTrue(payload["kill_switch"])
        # turn it back off so it can't affect other tests
        self.req("POST", "/risk/kill", {"engaged": False})

    def test_markets_board(self):
        self.req("POST", "/instruments/equity", {"symbol": "MKT"})
        self.req("POST", "/accounts/mk1/fund", {"amount": 100_000})
        self.req("POST", "/orders", {"account": "mmM", "symbol": "MKT", "side": "sell",
                                     "price": 42.0, "quantity": 5})
        self.req("POST", "/orders", {"account": "mk1", "symbol": "MKT", "side": "buy",
                                     "price": 41.0, "quantity": 5})
        status, res = self.req("GET", "/markets")
        self.assertEqual(status, 200)
        row = next(m for m in res["markets"] if m["symbol"] == "MKT")
        self.assertEqual(row["best_ask"], 42.0)
        self.assertEqual(row["best_bid"], 41.0)

    def test_cashflow_series(self):
        self.req("POST", "/instruments/equity", {"symbol": "CF"})
        self.req("POST", "/accounts/cf1/fund", {"amount": 10_000})
        self.req("POST", "/orders", {"account": "mmCF", "symbol": "CF", "side": "sell",
                                     "price": 100.0, "quantity": 5})
        self.req("POST", "/orders", {"account": "cf1", "symbol": "CF", "side": "buy",
                                     "price": 100.0, "quantity": 5})   # spends $500
        status, cf = self.req("GET", "/accounts/cf1/cashflow")
        self.assertEqual(status, 200)
        self.assertEqual(cf["funded"], 10_000.0)
        self.assertEqual(cf["ending_cash"], 9_500.0)         # 10,000 funded - 500 spent
        kinds = [p["kind"] for p in cf["series"]]
        self.assertIn("fund", kinds)
        self.assertIn("trade", kinds)
        self.assertEqual(cf["series"][-1]["balance"], 9_500.0)

    def test_position_greeks_uses_last_price_when_spot_omitted(self):
        self.req("POST", "/instruments/equity", {"symbol": "UND"})
        self.req("POST", "/instruments/option",
                 {"symbol": "UNDC", "underlying": "UND", "expiry": "2026-12-18",
                  "strike": 100.0, "right": "call", "multiplier": 100})
        self.req("POST", "/accounts/gk/fund", {"amount": 1_000_000})
        # Establish a last trade price for the UNDERLYING (UND @ $100).
        self.req("POST", "/orders", {"account": "mmU", "symbol": "UND", "side": "sell",
                                     "price": 100.0, "quantity": 1})
        self.req("POST", "/orders", {"account": "gk", "symbol": "UND", "side": "buy",
                                     "price": 100.0, "quantity": 1})
        # Take an option position.
        self.req("POST", "/orders", {"account": "wG", "symbol": "UNDC", "side": "sell",
                                     "price": 5.0, "quantity": 2})
        self.req("POST", "/orders", {"account": "gk", "symbol": "UNDC", "side": "buy",
                                     "price": 5.0, "quantity": 2})
        # No spots provided -> backend uses the underlying's last price.
        status, g = self.req("POST", "/accounts/gk/greeks",
                             {"rate": 0.05, "vol": 0.2, "as_of": "2026-06-04"})
        self.assertEqual(status, 200)
        self.assertGreater(g["net"]["delta"], 0.0)  # long calls, spot sourced from last trade

    def test_list_account_orders(self):
        self.req("POST", "/instruments/equity", {"symbol": "ORD"})
        self.req("POST", "/accounts/ow/fund", {"amount": 100_000})
        self.req("POST", "/orders", {"account": "ow", "symbol": "ORD", "side": "buy",
                                     "price": 10.0, "quantity": 5})
        self.req("POST", "/orders", {"account": "ow", "symbol": "ORD", "side": "buy",
                                     "price": 11.0, "quantity": 3})
        status, res = self.req("GET", "/accounts/ow/orders")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(res["orders"]), 2)
        self.assertGreater(res["orders"][0]["id"], res["orders"][1]["id"])  # newest first

    def test_cancel_order_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "GOOG"})
        self.req("POST", "/accounts/c1/fund", {"amount": 10_000})
        _, order = self.req(
            "POST", "/orders",
            {"account": "c1", "symbol": "GOOG", "side": "buy", "price": 100.0, "quantity": 5},
        )
        self.assertEqual(order["status"], "new")

        status, canceled = self.req("DELETE", f"/orders/{order['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(canceled["status"], "canceled")

        # Book is empty and buying power is fully restored.
        _, book = self.req("GET", "/book/GOOG")
        self.assertEqual(book["bids"], [])
        _, bal = self.req("GET", "/accounts/c1/balance")
        self.assertEqual(bal["available"], 10_000.0)
        self.assertEqual(bal["reserved"], 0.0)

    def test_cancel_filled_order_400(self):
        self.req("POST", "/instruments/equity", {"symbol": "NFLX"})
        self.req("POST", "/accounts/c2/fund", {"amount": 10_000})
        self.req("POST", "/orders",
                 {"account": "mm2", "symbol": "NFLX", "side": "sell", "price": 100.0, "quantity": 5})
        _, buy = self.req("POST", "/orders",
                          {"account": "c2", "symbol": "NFLX", "side": "buy", "price": 100.0, "quantity": 5})
        self.assertEqual(buy["status"], "filled")
        status, payload = self.req("DELETE", f"/orders/{buy['id']}")
        self.assertEqual(status, 400)
        self.assertIn("cannot cancel", payload["error"])

    def test_trade_history_endpoints(self):
        self.req("POST", "/instruments/equity", {"symbol": "TSLA"})
        self.req("POST", "/accounts/t1/fund", {"amount": 10_000})
        self.req("POST", "/orders",
                 {"account": "mm3", "symbol": "TSLA", "side": "sell", "price": 200.0, "quantity": 3})
        self.req("POST", "/orders",
                 {"account": "t1", "symbol": "TSLA", "side": "buy", "price": 200.0, "quantity": 3})

        status, acct = self.req("GET", "/accounts/t1/trades")
        self.assertEqual(status, 200)
        self.assertEqual(len(acct["trades"]), 1)
        self.assertEqual(acct["trades"][0]["side"], "buy")
        self.assertEqual(acct["trades"][0]["price"], 200.0)
        self.assertEqual(acct["trades"][0]["counterparty"], "mm3")

        _, tape = self.req("GET", "/trades/TSLA")
        self.assertEqual(len(tape["trades"]), 1)
        self.assertEqual(tape["trades"][0]["quantity"], 3.0)

    def test_ioc_order_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "AMD"})
        self.req("POST", "/accounts/i1/fund", {"amount": 100_000})
        self.req("POST", "/orders",
                 {"account": "mm4", "symbol": "AMD", "side": "sell", "price": 100.0, "quantity": 3})
        status, order = self.req(
            "POST", "/orders",
            {"account": "i1", "symbol": "AMD", "side": "buy", "price": 100.0, "quantity": 10,
             "tif": "ioc"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(order["tif"], "ioc")
        self.assertEqual(order["filled"], 3.0)
        self.assertEqual(order["status"], "canceled")     # remainder killed, not rested
        _, book = self.req("GET", "/book/AMD")
        self.assertEqual(book["bids"], [])

    def test_fok_kill_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "INTC"})
        self.req("POST", "/accounts/f1/fund", {"amount": 100_000})
        self.req("POST", "/orders",
                 {"account": "mm5", "symbol": "INTC", "side": "sell", "price": 50.0, "quantity": 2})
        _, order = self.req(
            "POST", "/orders",
            {"account": "f1", "symbol": "INTC", "side": "buy", "price": 50.0, "quantity": 10,
             "tif": "fok"},
        )
        self.assertEqual(order["status"], "canceled")
        self.assertEqual(order["filled"], 0.0)

    def test_market_order_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "ORCL"})
        self.req("POST", "/accounts/m1/fund", {"amount": 100_000})
        self.req("POST", "/orders",
                 {"account": "mm6", "symbol": "ORCL", "side": "sell", "price": 100.0, "quantity": 5})
        status, order = self.req(
            "POST", "/orders",
            {"account": "m1", "symbol": "ORCL", "side": "buy", "quantity": 5, "order_type": "market"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(order["order_type"], "market")
        self.assertEqual(order["status"], "filled")
        self.assertEqual(order["filled"], 5.0)
        self.assertEqual(order["fills"][0]["price"], 100.0)

    def test_stop_order_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "NVDA"})
        self.req("POST", "/accounts/sa/fund", {"amount": 100_000})
        self.req("POST", "/accounts/mmS/fund", {"amount": 1_000_000})  # fund the bid maker
        self.req("POST", "/orders",
                 {"account": "mmS", "symbol": "NVDA", "side": "buy", "price": 148.0, "quantity": 100})
        self.req("POST", "/orders",
                 {"account": "mmS", "symbol": "NVDA", "side": "buy", "price": 150.0, "quantity": 10})
        status, stop = self.req(
            "POST", "/orders",
            {"account": "sa", "symbol": "NVDA", "side": "sell", "quantity": 10,
             "order_type": "stop", "stop_price": 149.0},
        )
        self.assertEqual(status, 201)
        self.assertEqual(stop["status"], "pending")
        self.assertEqual(stop["stop_price"], 149.0)

        self.req("POST", "/orders",
                 {"account": "x1", "symbol": "NVDA", "side": "sell", "price": 150.0, "quantity": 10})
        self.assertEqual(self.req("GET", f"/orders/{stop['id']}")[1]["status"], "pending")

        self.req("POST", "/orders",
                 {"account": "x2", "symbol": "NVDA", "side": "sell", "price": 148.0, "quantity": 10})
        self.assertEqual(self.req("GET", f"/orders/{stop['id']}")[1]["status"], "filled")

    def test_options_trading_and_position_greeks(self):
        self.req("POST", "/instruments/equity", {"symbol": "AAPL"})
        self.req("POST", "/instruments/option",
                 {"symbol": "AAPLC", "underlying": "AAPL", "expiry": "2026-12-18",
                  "strike": 150.0, "right": "call", "multiplier": 100})
        self.req("POST", "/accounts/og/fund", {"amount": 100_000})

        # writer sells 2 calls @ $2.50; og buys 2. Premium = 2 x $2.50 x 100 = $500.
        self.req("POST", "/orders",
                 {"account": "writer", "symbol": "AAPLC", "side": "sell", "price": 2.50, "quantity": 2})
        status, buy = self.req("POST", "/orders",
                               {"account": "og", "symbol": "AAPLC", "side": "buy",
                                "price": 2.50, "quantity": 2})
        self.assertEqual(buy["status"], "filled")
        _, bal = self.req("GET", "/accounts/og/balance")
        self.assertEqual(bal["cash"], 100_000.0 - 500.0)   # multiplier applied

        status, g = self.req(
            "POST", "/accounts/og/greeks",
            {"spots": {"AAPL": 150.0}, "rate": 0.05, "vol": 0.2, "as_of": "2026-06-03"},
        )
        self.assertEqual(status, 200)
        self.assertGreater(g["net"]["delta"], 0.0)   # 2 long ATM calls -> positive net delta
        self.assertGreater(g["net"]["gamma"], 0.0)
        self.assertEqual(g["positions"][0]["contracts"], 2.0)

    def test_multi_leg_combo_over_http(self):
        self.req("POST", "/instruments/option",
                 {"symbol": "OC1", "underlying": "AAPL", "expiry": "2026-12-18",
                  "strike": 150.0, "right": "call", "multiplier": 100})
        self.req("POST", "/instruments/option",
                 {"symbol": "OC2", "underlying": "AAPL", "expiry": "2026-12-18",
                  "strike": 160.0, "right": "call", "multiplier": 100})
        self.req("POST", "/accounts/cb/fund", {"amount": 100_000})
        self.req("POST", "/orders", {"account": "w1", "symbol": "OC1", "side": "sell",
                                     "price": 5.0, "quantity": 1})
        self.req("POST", "/orders", {"account": "w2", "symbol": "OC2", "side": "sell",
                                     "price": 2.0, "quantity": 1})
        status, res = self.req("POST", "/combos", {"account": "cb", "legs": [
            {"symbol": "OC1", "side": "buy", "price": 5.0, "quantity": 1},
            {"symbol": "OC2", "side": "buy", "price": 2.0, "quantity": 1},
        ]})
        self.assertEqual(status, 201)
        self.assertEqual(res["status"], "filled")
        self.assertEqual(len(res["orders"]), 2)

    def test_price_alert_fires_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "ALRT"})
        self.req("POST", "/accounts/mka/fund", {"amount": 100_000})
        self.req("POST", "/accounts/al/alerts", {"symbol": "ALRT", "op": "above", "price": 100.0})
        # Generate a trade at $100 to fire the alert.
        self.req("POST", "/orders", {"account": "mka", "symbol": "ALRT", "side": "buy",
                                     "price": 100.0, "quantity": 1})
        self.req("POST", "/orders", {"account": "sa2", "symbol": "ALRT", "side": "sell",
                                     "price": 100.0, "quantity": 1})
        _, alerts = self.req("GET", "/accounts/al/alerts")
        self.assertEqual(len(alerts["fired"]), 1)

    def test_dividend_and_statement_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "DIV"})
        self.req("POST", "/accounts/inv/fund", {"amount": 100_000})
        self.req("POST", "/orders", {"account": "seller", "symbol": "DIV", "side": "sell",
                                     "price": 10.0, "quantity": 100})
        self.req("POST", "/orders", {"account": "inv", "symbol": "DIV", "side": "buy",
                                     "price": 10.0, "quantity": 100})   # buys 100 @ $10 = $1000
        self.req("POST", "/corporate-actions/dividend", {"symbol": "DIV", "per_share": 0.5})  # +$50
        _, bal = self.req("GET", "/accounts/inv/balance")
        self.assertEqual(bal["cash"], 100_000.0 - 1_000.0 + 50.0)
        _, stmt = self.req("GET", "/accounts/inv/statement")
        self.assertEqual(stmt["account"], "inv")
        self.assertGreaterEqual(len(stmt["trades"]), 1)

    def test_surveillance_detects_self_trade_over_http(self):
        self.req("POST", "/instruments/equity", {"symbol": "WASH"})
        self.req("POST", "/accounts/sw/fund", {"amount": 100_000})
        self.req("POST", "/orders", {"account": "sw", "symbol": "WASH", "side": "sell",
                                     "price": 10.0, "quantity": 5})
        self.req("POST", "/orders", {"account": "sw", "symbol": "WASH", "side": "buy",
                                     "price": 10.0, "quantity": 5})   # crosses its own ask
        _, report = self.req("GET", "/surveillance")
        self.assertGreaterEqual(report["self_trade_count"], 1)

    def test_dashboard_html_served_at_root(self):
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=5) as r:
            ctype = r.headers.get("Content-Type", "")
            cors = r.headers.get("Access-Control-Allow-Origin")
            html = r.read().decode()
        self.assertIn("text/html", ctype)
        self.assertEqual(cors, "*")
        self.assertIn("CHRONOS", html)
        self.assertIn("Order Book", html)

    def test_instruments_and_snapshot_endpoints(self):
        self.req("POST", "/instruments/equity", {"symbol": "SNAP"})
        self.req("POST", "/accounts/sn1/fund", {"amount": 100_000})
        self.req("POST", "/orders", {"account": "mmN", "symbol": "SNAP", "side": "sell",
                                     "price": 50.0, "quantity": 5})   # resting ask
        self.req("POST", "/orders", {"account": "sn1", "symbol": "SNAP", "side": "buy",
                                     "price": 50.0, "quantity": 5})   # trade @50

        _, instr = self.req("GET", "/instruments")
        self.assertIn("SNAP", [i["symbol"] for i in instr["instruments"]])

        status, snap = self.req("GET", "/snapshot/SNAP")
        self.assertEqual(status, 200)
        self.assertEqual(snap["last"], 50.0)
        self.assertEqual(len(snap["trades"]), 1)
        self.assertIn("bids", snap)
        self.assertIn("asks", snap)

    def test_sse_stream_pushes_trade_events(self):
        import urllib.request
        self.req("POST", "/instruments/equity", {"symbol": "STRM"})
        self.req("POST", "/accounts/st/fund", {"amount": 100_000})
        # Open the SSE stream first so we are subscribed before the trade is published.
        resp = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/stream", timeout=5)
        try:
            # Generate a trade.
            self.req("POST", "/orders", {"account": "mmZ", "symbol": "STRM", "side": "sell",
                                         "price": 20.0, "quantity": 2})
            self.req("POST", "/orders", {"account": "st", "symbol": "STRM", "side": "buy",
                                         "price": 20.0, "quantity": 2})
            # Read frames until a trade event for our symbol arrives (tolerate transient
            # socket aborts on teardown — common on Windows).
            got = None
            for _ in range(200):
                try:
                    line = resp.readline()
                except OSError:
                    break
                if not line:
                    break
                if line.startswith(b"data:"):
                    ev = json.loads(line[5:].strip())
                    if ev.get("type") == "trade" and ev.get("symbol") == "STRM":
                        got = ev
                        break
            self.assertIsNotNone(got)
            self.assertEqual(got["price"], 20.0)
            self.assertEqual(got["quantity"], 2.0)
        finally:
            resp.close()

    def test_cors_preflight(self):
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/orders", method="OPTIONS")
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.status, 204)
            self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), "*")

    def test_unknown_route_404(self):
        status, _ = self.req("GET", "/nonsense/path")
        self.assertEqual(status, 404)

    def test_bad_json_400(self):
        url = f"http://127.0.0.1:{self.port}/orders"
        req = urllib.request.Request(url, data=b"{not json", method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        self.assertEqual(status, 400)


class AuthApiTest(unittest.TestCase):
    """Server with CHRONOS_API_TOKEN set: writes need a bearer token; reads stay open."""

    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0, api_token="secret",
                                 cors_origins=["http://localhost:3000"])
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def req(self, method, path, body=None, token=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_get_is_open(self):
        status, payload = self.req("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_write_without_token_is_401(self):
        status, payload = self.req("POST", "/instruments/equity", {"symbol": "AUTH"})
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "unauthorized")

    def test_write_with_token_succeeds(self):
        status, _ = self.req("POST", "/instruments/equity", {"symbol": "AUTH"}, token="secret")
        self.assertEqual(status, 201)

    def test_wrong_token_is_401(self):
        status, _ = self.req("POST", "/instruments/equity", {"symbol": "NOPE"}, token="bad")
        self.assertEqual(status, 401)

    def test_cors_echoes_allowed_origin(self):
        url = f"http://127.0.0.1:{self.port}/health"
        req = urllib.request.Request(url, headers={"Origin": "http://localhost:3000"})
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), "http://localhost:3000")

    def test_cors_rejects_unlisted_origin(self):
        url = f"http://127.0.0.1:{self.port}/health"
        req = urllib.request.Request(url, headers={"Origin": "http://evil.example"})
        with urllib.request.urlopen(req, timeout=5) as r:
            # Falls back to the configured origin, never echoes the unlisted one.
            self.assertNotEqual(r.headers.get("Access-Control-Allow-Origin"), "http://evil.example")


if __name__ == "__main__":
    unittest.main()
