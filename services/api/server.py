"""Stdlib JSON/HTTP server exposing TradingApp. No third-party dependencies.

Run:  PYTHONPATH=. python3 -m services.api.server   (PORT env overrides 8080)

Routes:
  GET  /health
  POST /instruments/equity            {symbol}
  POST /instruments/option            {symbol, underlying, expiry, strike, right, multiplier?}
  GET  /instruments/{symbol}
  GET  /chain/{underlying}
  POST /accounts/{id}/fund            {amount}
  GET  /accounts/{id}/balance
  GET  /accounts/{id}/positions
  POST   /orders                      {account, symbol, side, price, quantity}
  GET    /orders/{id}
  DELETE /orders/{id}                 cancel an open order
  GET  /accounts/{id}/trades          account trade history
  GET  /trades/{symbol}               public tape for a symbol
  GET  /book/{symbol}
  GET  /snapshot/{symbol}             book + tape + last/best (UI poll)
  GET  /instruments                   list all instruments
  POST /combos                        {account, legs:[{symbol,side,price,quantity}]}
  POST/GET /accounts/{id}/alerts      price alerts
  GET  /accounts/{id}/statement       account statement
  POST /accounts/{id}/greeks          {spots, rate, vol, as_of}
  POST /corporate-actions/{split,dividend}
  GET  /surveillance
  POST /ohlc/{symbol}                 {bucket_ns}
  POST /pricing/option                {S, K, t, r, sigma, right}
  POST /risk/kill                     {engaged}
  GET  /                              served web dashboard
  GET  /stream                        Server-Sent Events (live trade/order feed)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from services.api.app import TradingApp
from services.api.config import load_config
from services.api.metrics import Metrics, render_prometheus
from services.api.web import DASHBOARD_HTML
from services.core.ledger import LedgerError

logger = logging.getLogger("chronos.api")


def route(app: TradingApp, method: str, parts: list[str], body: dict):
    """Return (status_code, payload) for a request. Raises map to error codes in the handler."""
    if method == "GET" and parts == ["health"]:
        return 200, {"status": "ok", "service": "chronos-trade-core"}
    if method == "GET" and parts == ["readyz"]:
        return 200, {"status": "ready"}

    if method == "POST" and parts == ["instruments", "equity"]:
        return 201, app.add_equity(body["symbol"])
    if method == "POST" and parts == ["instruments", "option"]:
        return 201, app.add_option(**body)
    if method == "GET" and len(parts) == 2 and parts[0] == "instruments":
        return 200, app.instrument(parts[1])
    if method == "GET" and len(parts) == 2 and parts[0] == "chain":
        return 200, {"underlying": parts[1], "chain": app.chain(parts[1])}

    if method == "POST" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "fund":
        return 200, app.fund(parts[1], body["amount"])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "balance":
        return 200, app.balance(parts[1])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "positions":
        return 200, app.positions(parts[1])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "orders":
        return 200, app.orders(parts[1])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "cashflow":
        return 200, app.cashflow(parts[1])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "trades":
        return 200, app.trades(parts[1])
    if method == "POST" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "greeks":
        return 200, app.position_greeks(parts[1], **body)
    if method == "POST" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "alerts":
        return 201, app.add_alert(parts[1], body["symbol"], body["op"], body["price"])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "alerts":
        return 200, app.alerts_for(parts[1])
    if method == "GET" and len(parts) == 3 and parts[0] == "accounts" and parts[2] == "statement":
        return 200, app.statement(parts[1])
    if method == "POST" and parts == ["corporate-actions", "split"]:
        return 200, app.apply_split(body["symbol"], body["numerator"], body.get("denominator", 1))
    if method == "POST" and parts == ["corporate-actions", "dividend"]:
        return 200, app.apply_dividend(body["symbol"], body["per_share"])
    if method == "GET" and parts == ["surveillance"]:
        return 200, app.run_surveillance()
    if method == "POST" and len(parts) == 2 and parts[0] == "ohlc":
        return 200, app.ohlc(parts[1], int(body["bucket_ns"]))
    if method == "GET" and len(parts) == 2 and parts[0] == "trades":
        return 200, app.symbol_trades(parts[1])

    if method == "POST" and parts == ["orders"]:
        return 201, app.place_order(**body)
    if method == "POST" and parts == ["combos"]:
        return 201, app.place_combo(body["account"], body["legs"])
    if method == "GET" and len(parts) == 2 and parts[0] == "orders":
        return 200, app.get_order(int(parts[1]))
    if method == "DELETE" and len(parts) == 2 and parts[0] == "orders":
        return 200, app.cancel_order(int(parts[1]))

    if method == "GET" and parts == ["instruments"]:
        return 200, app.instruments()
    if method == "GET" and parts == ["markets"]:
        return 200, app.markets()
    if method == "GET" and len(parts) == 2 and parts[0] == "book":
        return 200, app.book(parts[1])
    if method == "GET" and len(parts) == 2 and parts[0] == "snapshot":
        return 200, app.snapshot(parts[1])

    if method == "POST" and parts == ["pricing", "option"]:
        return 200, app.price_option(**body)
    if method == "POST" and parts == ["risk", "kill"]:
        app.risk.kill_switch = bool(body.get("engaged", True))
        return 200, {"kill_switch": app.risk.kill_switch}

    raise KeyError(f"no route for {method} /{'/'.join(parts)}")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # default stderr access log replaced by _log()
        pass

    # ---- request lifecycle helpers ----
    def _begin(self) -> None:
        self._t0 = time.monotonic()
        self._rid = self.headers.get("X-Request-Id") or uuid.uuid4().hex[:8]

    def _log(self, status: int) -> None:
        metrics = getattr(self.server, "metrics", None)  # type: ignore[attr-defined]
        if metrics is not None:
            metrics.inc_request(status)
        try:
            ms = round((time.monotonic() - getattr(self, "_t0", time.monotonic())) * 1000, 2)
            logger.info(json.dumps({"rid": getattr(self, "_rid", "-"), "method": self.command,
                                    "path": self.path, "status": status, "ms": ms}))
        except Exception:
            pass

    def _cors(self) -> None:
        allowed = getattr(self.server, "cors_origins", ["*"])  # type: ignore[attr-defined]
        origin = self.headers.get("Origin")
        if allowed == ["*"]:
            value = "*"
        elif origin and origin in allowed:
            value = origin
        else:
            value = allowed[0]
        self.send_header("Access-Control-Allow-Origin", value)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Request-Id")
        self.send_header("Vary", "Origin")

    def _authorized(self) -> bool:
        token = getattr(self.server, "api_token", None)  # type: ignore[attr-defined]
        if not token:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {token}"

    def _send(self, status: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-Id", getattr(self, "_rid", "-"))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        self._log(status)

    def _send_html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        self._log(200)

    def _send_text(self, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        body = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        self._log(200)

    def do_OPTIONS(self):  # CORS preflight — never requires auth
        self._begin()
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        self._begin()
        if self.path in ("/", "/index.html", "/dashboard"):
            return self._send_html(DASHBOARD_HTML)
        if self.path == "/metrics":
            metrics = self.server.metrics  # type: ignore[attr-defined]
            return self._send_text(render_prometheus(metrics, self.server.app),  # type: ignore[attr-defined]
                                   "text/plain; version=0.0.4; charset=utf-8")
        if self.path == "/stream":
            return self._stream()
        self._dispatch("GET", {})

    def _stream(self) -> None:
        """Server-Sent Events: push trade/order events to the client in real time."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()
        bus = self.server.app.events  # type: ignore[attr-defined]
        q = bus.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")  # keep-alive heartbeat
                    self.wfile.flush()
                    continue
                self.wfile.write(b"data: " + json.dumps(event).encode() + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # client disconnected
        finally:
            bus.unsubscribe(q)

    def do_DELETE(self):
        self._begin()
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        self._dispatch("DELETE", {})

    def do_POST(self):
        self._begin()
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        try:
            body = self._read_body()
        except json.JSONDecodeError:
            return self._send(400, {"error": "invalid JSON body"})
        self._dispatch("POST", body)

    def _dispatch(self, method: str, body: dict) -> None:
        parts = [p for p in self.path.strip("/").split("/") if p != ""]
        app: TradingApp = self.server.app  # type: ignore[attr-defined]
        try:
            status, payload = route(app, method, parts, body)
        except KeyError as e:
            status, payload = 404, {"error": str(e).strip('"')}
        except (ValueError, LedgerError, TypeError) as e:
            status, payload = 400, {"error": str(e)}
        except Exception as e:  # pragma: no cover - safety net
            status, payload = 500, {"error": str(e)}
        self._send(status, payload)


class _Server(ThreadingHTTPServer):
    daemon_threads = True       # don't let lingering SSE connections block shutdown
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Client disconnects (SSE close, keep-alive reset) are benign — stay quiet.
        import sys
        if isinstance(sys.exc_info()[1], (ConnectionError, OSError)):
            return
        super().handle_error(request, client_address)


def make_server(host: str = "127.0.0.1", port: int = 8080, db_path: str | None = None,
                api_token: str | None = None,
                cors_origins: list[str] | None = None) -> ThreadingHTTPServer:
    server = _Server((host, port), _Handler)
    server.app = TradingApp(db_path=db_path)  # type: ignore[attr-defined]
    server.api_token = api_token  # type: ignore[attr-defined]
    server.cors_origins = cors_origins or ["*"]  # type: ignore[attr-defined]
    server.metrics = Metrics()  # type: ignore[attr-defined]
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()
    srv = make_server("0.0.0.0", cfg.port, db_path=cfg.db_path,
                      api_token=cfg.api_token, cors_origins=cfg.cors_origins)
    store = f"persistent: {cfg.db_path}" if cfg.db_path else "in-memory"
    auth = "token-protected writes" if cfg.api_token else "open"
    cors = "*" if cfg.cors_origins == ["*"] else ",".join(cfg.cors_origins)
    print(f"[chronos-trade-core] HTTP API on :{cfg.port} ({store}; {auth}; cors={cors})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
