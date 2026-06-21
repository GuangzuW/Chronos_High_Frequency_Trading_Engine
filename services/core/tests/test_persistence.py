"""Durability tests — state must survive a process 'restart' (a fresh object on the same DB)."""

import os
import shutil
import tempfile
import unittest

from services.api.app import TradingApp
from services.core.ledger import Ledger
from services.core.money import to_price, to_quantity
from services.core.persistence import Database


class LedgerPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "ledger.db")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_balances_and_holds_survive_reopen(self):
        db = Database(self.path)
        led = Ledger(db=db)
        led.fund("alice", 100_000, "f1")
        led.reserve("h1", "alice", 30_000)
        db.close()

        # "restart": brand new objects on the same file.
        db2 = Database(self.path)
        led2 = Ledger(db=db2)
        self.assertEqual(led2.balance("alice"), 100_000)
        self.assertEqual(led2.reserved("alice"), 30_000)
        self.assertEqual(led2.available("alice"), 70_000)
        self.assertEqual(led2.total_balance(), 0)  # invariant holds after replay
        db2.close()

    def test_release_persists(self):
        db = Database(self.path)
        led = Ledger(db=db)
        led.fund("a", 100_000, "f1")
        led.reserve("h1", "a", 30_000)
        led.release("h1")
        db.close()

        db2 = Database(self.path)
        led2 = Ledger(db=db2)
        self.assertEqual(led2.reserved("a"), 0)
        self.assertEqual(led2.available("a"), 100_000)
        db2.close()

    def test_replay_is_not_double_counted(self):
        db = Database(self.path)
        led = Ledger(db=db)
        led.fund("a", 100_000, "f1")
        led.transfer("a", "b", 25_000, "t1")
        db.close()

        db2 = Database(self.path)
        led2 = Ledger(db=db2)
        self.assertEqual(led2.balance("a"), 75_000)
        self.assertEqual(led2.balance("b"), 25_000)
        self.assertEqual(led2.total_balance(), 0)
        db2.close()


class AppPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "app.db")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_full_state_and_open_book_survive_restart(self):
        app = TradingApp(db_path=self.path)
        app.add_equity("AAPL")
        app.fund("alice", 10_000.0)
        app.portfolio.seed("bob", "AAPL", to_quantity(10), to_price(140))  # 10 @ $140
        sell = app.place_order("bob", "AAPL", "sell", 150.25, 10)          # rests as ask
        bob_id = sell["id"]
        self.assertEqual(sell["status"], "new")
        app.close()

        # ---- restart ----
        app2 = TradingApp(db_path=self.path)
        app2.add_equity("AAPL")  # reference data is config, re-seeded at boot

        # Ledger, positions, order history and the OPEN BOOK are all restored.
        self.assertEqual(app2.balance("alice")["cash"], 10_000.0)
        self.assertEqual(app2.get_order(bob_id)["status"], "new")
        self.assertEqual(app2.venue.book("AAPL").best_ask(), to_price(150.25))
        bobpos = {p["symbol"]: p for p in app2.positions("bob")["positions"]}
        self.assertEqual(bobpos["AAPL"]["quantity"], 10.0)

        # A new buy crosses the RESTORED resting ask -> fills, cash & positions update.
        buy = app2.place_order("alice", "AAPL", "buy", 150.25, 10)
        self.assertEqual(buy["status"], "filled")
        self.assertEqual(app2.balance("alice")["cash"], 10_000.0 - 1_502.50)
        self.assertEqual(app2.balance("bob")["cash"], 1_502.50)
        self.assertEqual(app2.get_order(bob_id)["status"], "filled")  # restored order advanced
        self.assertEqual(app2.positions("bob")["positions"][0]["realized_pnl"], 102.50)
        app2.close()

    def test_trades_persist_and_seq_continues_after_restart(self):
        app = TradingApp(db_path=self.path)
        app.add_equity("AAPL")
        app.fund("alice", 10_000.0)
        app.portfolio.seed("bob", "AAPL", to_quantity(10), to_price(140))
        app.place_order("bob", "AAPL", "sell", 150.25, 10)
        app.place_order("alice", "AAPL", "buy", 150.25, 10)  # one execution
        self.assertEqual(len(app.trades("alice")["trades"]), 1)
        app.close()

        # ---- restart ----
        app2 = TradingApp(db_path=self.path)
        app2.add_equity("AAPL")
        restored = app2.trades("alice")["trades"]
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0]["side"], "buy")
        self.assertEqual(restored[0]["price"], 150.25)
        self.assertEqual(restored[0]["quantity"], 10.0)
        self.assertEqual(restored[0]["counterparty"], "bob")

        # A new execution after restart continues the seq (no reuse, no settlement collision).
        app2.fund("carol", 10_000.0)
        app2.place_order("dave", "AAPL", "sell", 150.25, 1)   # dave shorts 1 (allowed in reference)
        app2.place_order("carol", "AAPL", "buy", 150.25, 1)
        tape = app2.symbol_trades("AAPL")["trades"]
        self.assertEqual(len(tape), 2)
        self.assertEqual(tape[1]["seq"], 2)
        app2.close()

    def test_pending_stop_survives_restart_and_triggers(self):
        app = TradingApp(db_path=self.path)
        app.add_equity("AAPL")
        app.fund("alice", 100_000.0)
        app.fund("mm", 1_000_000.0)                                  # fund the bid maker
        app.place_order("mm", "AAPL", "buy", 148.0, 100)              # deep bid $148
        app.place_order("mm", "AAPL", "buy", 150.0, 10)              # bid $150
        stop = app.place_order("alice", "AAPL", "sell", quantity=10,
                               order_type="stop", stop_price=149.0)
        self.assertEqual(stop["status"], "pending")
        app.place_order("s1", "AAPL", "sell", 150.0, 10)            # trade @150 -> last 15000
        app.close()

        # ---- restart ----
        app2 = TradingApp(db_path=self.path)
        app2.add_equity("AAPL")
        # Pending stop restored; last price recovered but not auto-fired.
        self.assertEqual(app2.get_order(stop["id"])["status"], "pending")
        # A trade at $148 after restart drives last price through the stop -> it fires.
        app2.place_order("s2", "AAPL", "sell", 148.0, 10)
        self.assertEqual(app2.get_order(stop["id"])["status"], "filled")
        app2.close()

    def test_order_id_sequence_continues_after_restart(self):
        app = TradingApp(db_path=self.path)
        app.add_equity("AAPL")
        app.fund("a", 100_000.0)
        o1 = app.place_order("a", "AAPL", "buy", 10.0, 1)  # rests
        app.close()

        app2 = TradingApp(db_path=self.path)
        app2.add_equity("AAPL")
        o2 = app2.place_order("a", "AAPL", "buy", 9.0, 1)
        self.assertGreater(o2["id"], o1["id"])  # no id reuse across restart
        app2.close()

    def test_canceled_order_not_restored_to_book(self):
        app = TradingApp(db_path=self.path)
        app.add_equity("AAPL")
        app.fund("a", 10_000.0)
        order = app.place_order("a", "AAPL", "buy", 100.0, 10)  # rests, reserves $1000
        app.cancel_order(order["id"])
        self.assertEqual(app.balance("a")["available"], 10_000.0)
        app.close()

        app2 = TradingApp(db_path=self.path)
        app2.add_equity("AAPL")
        # Canceled order keeps its status, is NOT re-rested, and its hold stays released.
        self.assertEqual(app2.get_order(order["id"])["status"], "canceled")
        self.assertIsNone(app2.venue.book("AAPL").best_bid())
        self.assertEqual(app2.balance("a")["available"], 10_000.0)
        self.assertEqual(app2.balance("a")["reserved"], 0.0)
        app2.close()

    def test_open_buy_hold_survives_restart(self):
        app = TradingApp(db_path=self.path)
        app.add_equity("AAPL")
        app.fund("a", 10_000.0)
        app.place_order("a", "AAPL", "buy", 100.0, 10)  # $1000 notional rests; reserves buying power
        self.assertEqual(app.balance("a")["available"], 10_000.0 - 1_000.0)
        app.close()

        app2 = TradingApp(db_path=self.path)
        app2.add_equity("AAPL")
        # The reservation for the still-open order is restored.
        self.assertEqual(app2.balance("a")["available"], 10_000.0 - 1_000.0)
        self.assertEqual(app2.balance("a")["reserved"], 1_000.0)
        app2.close()


if __name__ == "__main__":
    unittest.main()
